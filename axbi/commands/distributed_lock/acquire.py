# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

import redis
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from axbi.commands.distributed_lock.base import (
    BaseDistributedLockCommand,
    get_default_lock_ttl,
    get_redis_client,
)
from axbi.commands.distributed_lock.kv_session import (
    create_lock_entry,
    delete_expired_lock_entries,
    independent_kv_session,
)
from axbi.exceptions import AcquireDistributedLockFailedException
from axbi.key_value.types import KeyValueResource
from axbi.utils.core import get_user_id
from axbi.utils.dates import naive_utcnow

logger = logging.getLogger(__name__)


class AcquireDistributedLock(BaseDistributedLockCommand):
    """
    Acquire a distributed lock with automatic backend selection.

    Uses Redis SET NX EX when DISTRIBUTED_COORDINATION_CONFIG is configured,
    otherwise falls back to KeyValue table.

    The KV backend uses an independent short-lived session so the lock row is
    committed immediately and visible to other processes even when the caller
    is already inside an outer ``@transaction`` unit of work.

    Raises AcquireDistributedLockFailedException if:
    - Lock is already held by another process
    - Redis connection fails
    """

    ttl_seconds: int

    def __init__(
        self,
        namespace: str,
        params: dict[str, Any] | None = None,
        ttl_seconds: int | None = None,
        *,
        owner_token: str,
    ) -> None:
        super().__init__(namespace, params)
        self.ttl_seconds = ttl_seconds or get_default_lock_ttl()
        self.owner_token = owner_token

    def run(self) -> None:
        if (redis_client := get_redis_client()) is not None:
            self._acquire_redis(redis_client)
        else:
            self._acquire_kv()

    def _acquire_redis(self, redis_client: Any) -> None:
        """Acquire lock using Redis SET NX EX (atomic)."""
        try:
            # SET NX EX: Set if not exists, with expiration
            # Returns True if lock acquired, None if already exists
            acquired = redis_client.set(
                self.redis_lock_key,
                self.owner_token,
                nx=True,
                ex=self.ttl_seconds,
            )

            if not acquired:
                logger.debug("Redis lock on %s already taken", self.redis_lock_key)
                raise AcquireDistributedLockFailedException("Lock already taken")

            logger.debug(
                "Acquired Redis lock: %s (TTL=%ds)",
                self.redis_lock_key,
                self.ttl_seconds,
            )

        except redis.RedisError as ex:
            logger.error("Redis lock error for %s: %s", self.redis_lock_key, ex)
            raise AcquireDistributedLockFailedException(
                f"Redis lock failed: {ex}"
            ) from ex

    def _acquire_kv(self) -> None:
        """Acquire lock using KeyValue table (database).

        Uses an independent session so the lock is durable before this method
        returns, regardless of any outer ``@transaction`` depth on ``db.session``.
        """
        try:
            encoded = self.codec.encode({"value": self.owner_token})
        except Exception as ex:
            raise AcquireDistributedLockFailedException(
                "Unable to encode lock value"
            ) from ex

        try:
            with independent_kv_session() as session:
                # Delete expired entries first to prevent stale locks from blocking
                delete_expired_lock_entries(session, self.resource.value)

                # Create entry - unique constraint will raise if lock already exists
                create_lock_entry(
                    session,
                    resource_value=KeyValueResource.LOCK.value,
                    key=self.key,
                    encoded_value=encoded,
                    expires_on=naive_utcnow() + timedelta(seconds=self.ttl_seconds),
                    created_by_fk=get_user_id(),
                )
        except IntegrityError as ex:
            logger.debug(
                "KV lock already taken: namespace=%s key=%s",
                self.namespace,
                self.key,
            )
            raise AcquireDistributedLockFailedException("Lock already taken") from ex
        except SQLAlchemyError as ex:
            raise AcquireDistributedLockFailedException(f"KV lock failed: {ex}") from ex

        logger.debug(
            "Acquired KV lock: namespace=%s key=%s (TTL=%ds)",
            self.namespace,
            self.key,
            self.ttl_seconds,
        )

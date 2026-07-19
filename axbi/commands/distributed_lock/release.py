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
from functools import partial
from typing import Any

import redis
from sqlalchemy.exc import SQLAlchemyError

from axbi.commands.distributed_lock.base import (
    BaseDistributedLockCommand,
    get_redis_client,
)
from axbi.exceptions import ReleaseDistributedLockFailedException
from axbi.extensions import db
from axbi.key_value.exceptions import KeyValueDeleteFailedError
from axbi.key_value.models import KeyValueEntry
from axbi.key_value.utils import get_filter
from axbi.utils.decorators import on_error, transaction

logger = logging.getLogger(__name__)

_COMPARE_AND_DELETE = """
if redis.call('get', KEYS[1]) == ARGV[1] then
  return redis.call('del', KEYS[1])
end
return 0
"""


class ReleaseDistributedLock(BaseDistributedLockCommand):
    """
    Release a distributed lock with automatic backend selection.

    Uses an owner-checked Redis Lua script when distributed coordination is
    configured, otherwise locks and checks the KeyValue row before deleting it.
    """

    def __init__(
        self,
        namespace: str,
        params: dict[str, Any] | None = None,
        *,
        owner_token: str,
    ) -> None:
        super().__init__(namespace, params)
        self.owner_token = owner_token

    def run(self) -> None:
        if (redis_client := get_redis_client()) is not None:
            self._release_redis(redis_client)
        else:
            self._release_kv()

    def _release_redis(self, redis_client: Any) -> None:
        """Release a Redis lock only when this acquisition still owns it."""
        try:
            released = redis_client.eval(
                _COMPARE_AND_DELETE,
                1,
                self.redis_lock_key,
                self.owner_token,
            )
            if released:
                logger.debug("Released Redis lock: %s", self.redis_lock_key)
            else:
                logger.debug(
                    "Skipped release for Redis lock no longer owned: %s",
                    self.redis_lock_key,
                )
        except redis.RedisError as ex:
            # Log warning but don't raise - TTL will handle cleanup
            logger.warning(
                "Failed to release Redis lock %s: %s (TTL will handle cleanup)",
                self.redis_lock_key,
                ex,
            )

    @transaction(
        on_error=partial(
            on_error,
            catches=(
                KeyValueDeleteFailedError,
                SQLAlchemyError,
            ),
            reraise=ReleaseDistributedLockFailedException,
        ),
    )
    def _release_kv(self) -> None:
        """Release lock using KeyValue table (database)."""
        entry = (
            db.session.query(KeyValueEntry)
            .filter_by(**get_filter(self.resource, self.key))
            .with_for_update()
            .one_or_none()
        )
        if (
            entry is not None
            and not entry.is_expired()
            and self.codec.decode(entry.value) == {"value": self.owner_token}
        ):
            db.session.delete(entry)
            logger.debug(
                "Released KV lock: namespace=%s key=%s",
                self.namespace,
                self.key,
            )
        else:
            logger.debug(
                "Skipped release for KV lock no longer owned: namespace=%s key=%s",
                self.namespace,
                self.key,
            )

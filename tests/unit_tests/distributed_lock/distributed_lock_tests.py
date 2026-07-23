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

# pylint: disable=invalid-name

from typing import Any
from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

import pytest
from freezegun import freeze_time
from sqlalchemy.orm import Session, sessionmaker

# Force module loading before tests run so patches work correctly
import axbi.commands.distributed_lock.acquire as acquire_module
import axbi.commands.distributed_lock.release as release_module
from axbi import db
from axbi.distributed_lock import DistributedLock
from axbi.distributed_lock.utils import get_key
from axbi.exceptions import AcquireDistributedLockFailedException
from axbi.key_value.types import JsonKeyValueCodec

MAIN_KEY = get_key("ns", a=1, b=2)
OTHER_KEY = get_key("ns2", a=1, b=2)


def _get_lock(key: UUID, session: Session) -> Any:
    from axbi.key_value.models import KeyValueEntry

    entry = db.session.query(KeyValueEntry).filter_by(uuid=key).first()
    if entry is None or entry.is_expired():
        return None

    return JsonKeyValueCodec().decode(entry.value)


def _get_other_session() -> Session:
    # This session is used to simulate what another worker will find in the metastore
    # during the locking process.
    from axbi import db

    bind = db.session.get_bind()
    SessionMaker = sessionmaker(bind=bind)  # noqa: N806
    return SessionMaker()


def test_distributed_lock_kv_happy_path() -> None:
    """
    Test successfully acquiring and returning the distributed lock via KV backend.

    Note, we're using another session for asserting the lock state in the Metastore
    to simulate what another worker will observe. Otherwise, there's the risk that
    the assertions would only be using the non-committed state from the main session.
    """
    session = _get_other_session()

    # Ensure Redis is not configured so KV backend is used
    with (
        patch.object(acquire_module, "get_redis_client", return_value=None),
        patch.object(release_module, "get_redis_client", return_value=None),
    ):
        with freeze_time("2021-01-01"):
            assert _get_lock(MAIN_KEY, session) is None

            with DistributedLock("ns", a=1, b=2) as key:
                assert key == MAIN_KEY
                lock_value = _get_lock(key, session)
                assert isinstance(lock_value["value"], str)
                assert lock_value["value"]
                assert _get_lock(OTHER_KEY, session) is None

                with pytest.raises(AcquireDistributedLockFailedException):
                    with DistributedLock("ns", a=1, b=2):
                        pass

            assert _get_lock(MAIN_KEY, session) is None


def test_distributed_lock_kv_expired() -> None:
    """
    Test expiration of the distributed lock via KV backend.

    Note, we're using another session for asserting the lock state in the Metastore
    to simulate what another worker will observe. Otherwise, there's the risk that
    the assertions would only be using the non-committed state from the main session.
    """
    session = _get_other_session()

    # Ensure Redis is not configured so KV backend is used
    with (
        patch.object(acquire_module, "get_redis_client", return_value=None),
        patch.object(release_module, "get_redis_client", return_value=None),
    ):
        with freeze_time("2021-01-01"):
            assert _get_lock(MAIN_KEY, session) is None
            with DistributedLock("ns", a=1, b=2):
                lock_value = _get_lock(MAIN_KEY, session)
                assert isinstance(lock_value["value"], str)
                assert lock_value["value"]
                with freeze_time("2022-01-01"):
                    assert _get_lock(MAIN_KEY, session) is None

            assert _get_lock(MAIN_KEY, session) is None


def test_stale_kv_owner_cannot_release_reacquired_lock() -> None:
    """A holder that outlives its TTL must not delete its successor's lock."""
    owner_a = uuid4().hex
    owner_b = uuid4().hex
    with (
        patch.object(acquire_module, "get_redis_client", return_value=None),
        patch.object(release_module, "get_redis_client", return_value=None),
    ):
        with freeze_time("2021-01-01"):
            acquire_module.AcquireDistributedLock(
                "ns",
                {"a": 1, "b": 2},
                ttl_seconds=30,
                owner_token=owner_a,
            ).run()

        with freeze_time("2021-01-02"):
            acquire_module.AcquireDistributedLock(
                "ns",
                {"a": 1, "b": 2},
                ttl_seconds=30,
                owner_token=owner_b,
            ).run()
            release_module.ReleaseDistributedLock(
                "ns",
                {"a": 1, "b": 2},
                owner_token=owner_a,
            ).run()

            assert _get_lock(MAIN_KEY, db.session) == {"value": owner_b}

            release_module.ReleaseDistributedLock(
                "ns",
                {"a": 1, "b": 2},
                owner_token=owner_b,
            ).run()


def test_kv_lock_visible_under_outer_transaction() -> None:
    """
    KV locks must commit independently of an outer @transaction unit of work.

    Without an independent session, nested @transaction on acquire left the
    lock row uncommitted until the outer boundary finished — concurrent
    workers then hit the unique key instead of seeing the lock.
    """
    from flask import g

    from axbi.utils.decorators import transaction

    other = _get_other_session()
    observed: dict[str, Any] = {}

    with (
        patch.object(acquire_module, "get_redis_client", return_value=None),
        patch.object(release_module, "get_redis_client", return_value=None),
    ):

        @transaction()
        def hold_lock_inside_outer_unit_of_work() -> None:
            # Outer unit of work is open; depth > 0 once nested code runs.
            assert int(getattr(g, "transaction_depth", 0) or 0) >= 1
            with DistributedLock("ns-outer", a=1, b=2) as key:
                observed["key"] = key
                # Another connection must see the committed lock row now.
                observed["while_held"] = _get_lock(key, other)

        hold_lock_inside_outer_unit_of_work()

    assert observed["while_held"] is not None
    assert isinstance(observed["while_held"]["value"], str)
    assert _get_lock(observed["key"], other) is None


def test_distributed_lock_uses_redis_when_configured() -> None:
    """Test that DistributedLock uses Redis backend when configured."""
    mock_redis = MagicMock()
    mock_redis.set.return_value = True  # Lock acquired

    # Use patch.object to patch on already-imported modules
    with (
        patch.object(acquire_module, "get_redis_client", return_value=mock_redis),
        patch.object(release_module, "get_redis_client", return_value=mock_redis),
    ):
        with DistributedLock("test_redis", key="value") as lock_key:
            assert lock_key is not None
            # Verify SET NX EX was called
            mock_redis.set.assert_called_once()
            call_args = mock_redis.set.call_args
            assert call_args.kwargs["nx"] is True
            assert "ex" in call_args.kwargs

        # Release is compare-and-delete so an expired/reacquired lock is safe.
        mock_redis.eval.assert_called_once()


def test_distributed_lock_redis_already_taken() -> None:
    """Test Redis lock fails when already held."""
    mock_redis = MagicMock()
    mock_redis.set.return_value = None  # Lock not acquired (already taken)

    with patch.object(acquire_module, "get_redis_client", return_value=mock_redis):
        with pytest.raises(AcquireDistributedLockFailedException):
            with DistributedLock("test_redis", key="value"):
                pass


def test_distributed_lock_redis_connection_error() -> None:
    """Test Redis connection error raises exception (fail fast)."""
    import redis

    mock_redis = MagicMock()
    mock_redis.set.side_effect = redis.RedisError("Connection failed")

    with patch.object(acquire_module, "get_redis_client", return_value=mock_redis):
        with pytest.raises(AcquireDistributedLockFailedException):
            with DistributedLock("test_redis", key="value"):
                pass


def test_distributed_lock_custom_ttl() -> None:
    """Test Redis lock with custom TTL."""
    mock_redis = MagicMock()
    mock_redis.set.return_value = True

    with (
        patch.object(acquire_module, "get_redis_client", return_value=mock_redis),
        patch.object(release_module, "get_redis_client", return_value=mock_redis),
    ):
        with DistributedLock("test", ttl_seconds=60, key="value"):
            call_args = mock_redis.set.call_args
            assert call_args.kwargs["ex"] == 60  # Custom TTL


def test_distributed_lock_default_ttl(app_context: None) -> None:
    """Test Redis lock uses default TTL when not specified."""
    from axbi.commands.distributed_lock.base import get_default_lock_ttl

    mock_redis = MagicMock()
    mock_redis.set.return_value = True

    with (
        patch.object(acquire_module, "get_redis_client", return_value=mock_redis),
        patch.object(release_module, "get_redis_client", return_value=mock_redis),
    ):
        with DistributedLock("test", key="value"):
            call_args = mock_redis.set.call_args
            assert call_args.kwargs["ex"] == get_default_lock_ttl()


def test_distributed_lock_fallback_to_kv_when_redis_not_configured() -> None:
    """Test falls back to KV lock when Redis not configured."""
    session = _get_other_session()
    test_key = get_key("test_fallback", key="value")

    with (
        patch.object(acquire_module, "get_redis_client", return_value=None),
        patch.object(release_module, "get_redis_client", return_value=None),
    ):
        with freeze_time("2021-01-01"):
            # When Redis is not configured, should use KV backend
            with DistributedLock("test_fallback", key="value") as lock_key:
                assert lock_key == test_key
                # Verify lock exists in KV store
                lock_value = _get_lock(test_key, session)
                assert isinstance(lock_value["value"], str)
                assert lock_value["value"]

            # Lock should be released
            assert _get_lock(test_key, session) is None

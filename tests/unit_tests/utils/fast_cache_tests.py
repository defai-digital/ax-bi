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

# pylint: disable=import-outside-toplevel, unused-argument

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_app() -> MagicMock:
    """Create a mock Flask app with configurable settings."""
    app = MagicMock()
    app.config = {
        "FAST_CACHE_ENABLED": True,
        "FAST_CACHE_KEY_PREFIX": "fc:",
        "CACHE_DEFAULT_TIMEOUT": 86400,
    }
    return app


def test_set_fast_cache_disabled(mock_app: MagicMock) -> None:
    """When FAST_CACHE_ENABLED is False, no Redis write should occur."""
    from superset.utils.fast_cache import set_fast_cache

    mock_app.config["FAST_CACHE_ENABLED"] = False

    with (
        patch("superset.utils.fast_cache.current_app", mock_app),
        patch("superset.utils.fast_cache._get_redis_client") as mock_get_client,
    ):
        set_fast_cache("test-key", '{"result":[]}')
        mock_get_client.assert_not_called()


def test_set_fast_cache_writes_to_redis(mock_app: MagicMock) -> None:
    """When enabled, set_fast_cache should write JSON to Redis with TTL."""
    from superset.utils.fast_cache import set_fast_cache

    mock_redis = MagicMock()
    mock_app.config["FAST_CACHE_ENABLED"] = True

    with (
        patch("superset.utils.fast_cache.current_app", mock_app),
        patch("superset.utils.fast_cache._get_redis_client", return_value=mock_redis),
    ):
        set_fast_cache("abc123", '{"result":[{"data":[]}]}', timeout=3600)
        mock_redis.set.assert_called_once_with(
            "fc:abc123", '{"result":[{"data":[]}]}', ex=3600
        )


def test_set_fast_cache_uses_default_timeout(mock_app: MagicMock) -> None:
    """When no timeout is provided, CACHE_DEFAULT_TIMEOUT is used."""
    from superset.utils.fast_cache import set_fast_cache

    mock_redis = MagicMock()

    with (
        patch("superset.utils.fast_cache.current_app", mock_app),
        patch("superset.utils.fast_cache._get_redis_client", return_value=mock_redis),
    ):
        set_fast_cache("key1", '{"data":true}')
        mock_redis.set.assert_called_once_with("fc:key1", '{"data":true}', ex=86400)


def test_set_fast_cache_empty_key(mock_app: MagicMock) -> None:
    """An empty cache key should be silently ignored."""
    from superset.utils.fast_cache import set_fast_cache

    mock_redis = MagicMock()

    with (
        patch("superset.utils.fast_cache.current_app", mock_app),
        patch("superset.utils.fast_cache._get_redis_client", return_value=mock_redis),
    ):
        set_fast_cache("", '{"data":true}')
        mock_redis.set.assert_not_called()


def test_set_fast_cache_no_redis_client(mock_app: MagicMock) -> None:
    """When no Redis client is available, write should be silently skipped."""
    from superset.utils.fast_cache import set_fast_cache

    with (
        patch("superset.utils.fast_cache.current_app", mock_app),
        patch("superset.utils.fast_cache._get_redis_client", return_value=None),
    ):
        # Should not raise
        set_fast_cache("key1", '{"data":true}')


def test_set_fast_cache_redis_error(mock_app: MagicMock) -> None:
    """Redis errors should be caught and logged, not propagated."""
    from superset.utils.fast_cache import set_fast_cache

    mock_redis = MagicMock()
    mock_redis.set.side_effect = ConnectionError("Redis down")

    with (
        patch("superset.utils.fast_cache.current_app", mock_app),
        patch("superset.utils.fast_cache._get_redis_client", return_value=mock_redis),
    ):
        # Should not raise
        set_fast_cache("key1", '{"data":true}')


def test_get_fast_cache_hit(mock_app: MagicMock) -> None:
    """When a value exists in Redis, it should be returned as a string."""
    from superset.utils.fast_cache import get_fast_cache

    mock_redis = MagicMock()
    mock_redis.get.return_value = b'{"result":[{"data":[]}]}'

    with (
        patch("superset.utils.fast_cache.current_app", mock_app),
        patch("superset.utils.fast_cache._get_redis_client", return_value=mock_redis),
    ):
        result = get_fast_cache("abc123")
        assert result == '{"result":[{"data":[]}]}'
        mock_redis.get.assert_called_once_with("fc:abc123")


def test_get_fast_cache_miss(mock_app: MagicMock) -> None:
    """When no value exists in Redis, None should be returned."""
    from superset.utils.fast_cache import get_fast_cache

    mock_redis = MagicMock()
    mock_redis.get.return_value = None

    with (
        patch("superset.utils.fast_cache.current_app", mock_app),
        patch("superset.utils.fast_cache._get_redis_client", return_value=mock_redis),
    ):
        result = get_fast_cache("missing-key")
        assert result is None


def test_get_fast_cache_disabled(mock_app: MagicMock) -> None:
    """When disabled, get_fast_cache should return None immediately."""
    from superset.utils.fast_cache import get_fast_cache

    mock_app.config["FAST_CACHE_ENABLED"] = False

    with patch("superset.utils.fast_cache.current_app", mock_app):
        result = get_fast_cache("any-key")
        assert result is None


def test_get_fast_cache_string_value(mock_app: MagicMock) -> None:
    """Redis returning a string (not bytes) should be handled correctly."""
    from superset.utils.fast_cache import get_fast_cache

    mock_redis = MagicMock()
    mock_redis.get.return_value = '{"result":[]}'

    with (
        patch("superset.utils.fast_cache.current_app", mock_app),
        patch("superset.utils.fast_cache._get_redis_client", return_value=mock_redis),
    ):
        result = get_fast_cache("key1")
        assert result == '{"result":[]}'


def test_custom_key_prefix(mock_app: MagicMock) -> None:
    """Custom key prefixes should be applied correctly."""
    from superset.utils.fast_cache import get_fast_cache, set_fast_cache

    mock_redis = MagicMock()
    mock_app.config["FAST_CACHE_KEY_PREFIX"] = "custom:"

    with (
        patch("superset.utils.fast_cache.current_app", mock_app),
        patch("superset.utils.fast_cache._get_redis_client", return_value=mock_redis),
    ):
        set_fast_cache("key1", '{"data":1}')
        mock_redis.set.assert_called_once_with("custom:key1", '{"data":1}', ex=86400)

    mock_redis.get.return_value = b'{"data":1}'
    with (
        patch("superset.utils.fast_cache.current_app", mock_app),
        patch("superset.utils.fast_cache._get_redis_client", return_value=mock_redis),
    ):
        get_fast_cache("key1")
        mock_redis.get.assert_called_with("custom:key1")

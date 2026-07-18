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
"""Unit tests for MCP rate limiting (middleware + factory)."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastmcp.exceptions import ToolError

from axbi.mcp_service.middleware import (
    _tool_call_arguments,
    create_rate_limit_middleware,
    InMemoryRateLimiter,
    LoggingMiddleware,
    RateLimitMiddleware,
    RedisRateLimiter,
)


class _FakeCache:
    """Minimal Flask-Caching-like backend with atomic add/inc semantics."""

    def __init__(self) -> None:
        self.store: dict[str, int] = {}
        self.timeouts: dict[str, int | None] = {}

    def add(self, key: str, value: int, timeout: int | None = None) -> bool:
        if key in self.store:
            return False
        self.store[key] = value
        self.timeouts[key] = timeout
        return True

    def inc(self, key: str, delta: int = 1) -> int:
        self.store[key] = int(self.store.get(key, 0)) + delta
        return self.store[key]

    def get(self, key: str) -> int | None:
        return self.store.get(key)

    def set(self, key: str, value: int, timeout: int | None = None) -> bool:
        self.store[key] = value
        self.timeouts[key] = timeout
        return True


def _make_redis_limiter(cache: _FakeCache) -> RedisRateLimiter:
    with patch("axbi.extensions.cache_manager") as cm:
        cm.cache = cache
        return RedisRateLimiter()


def test_redis_limiter_allows_up_to_limit_then_blocks() -> None:
    cache = _FakeCache()
    limiter = _make_redis_limiter(cache)

    # Exactly `limit` requests are allowed, the next one is blocked.
    results = [
        limiter.is_rate_limited("user:1:t", limit=3, window=60) for _ in range(4)
    ]
    blocked = [is_limited for is_limited, _ in results]
    assert blocked == [False, False, False, True]


def test_redis_limiter_anchors_ttl_once_and_does_not_extend() -> None:
    cache = _FakeCache()
    limiter = _make_redis_limiter(cache)

    for _ in range(3):
        limiter.is_rate_limited("user:1:t", limit=10, window=60)

    # A single bucket key holds the counter, and its TTL equals the window —
    # anchored once on creation, never re-set to a later expiry.
    assert len(cache.store) == 1
    (only_key,) = cache.store
    assert cache.store[only_key] == 3
    assert cache.timeouts[only_key] == 60


def test_redis_limiter_fails_open_on_cache_error() -> None:
    cache = MagicMock()
    cache.add.side_effect = RuntimeError("redis down")
    limiter = _make_redis_limiter(cache)

    is_limited, info = limiter.is_rate_limited("k", limit=1, window=60)
    assert is_limited is False
    assert info["remaining"] == 1


def test_redis_limiter_falls_back_when_no_atomic_inc() -> None:
    cache = _FakeCache()
    # Simulate a backend without atomic inc.
    cache.inc = MagicMock(side_effect=NotImplementedError)  # type: ignore[method-assign]
    limiter = _make_redis_limiter(cache)

    results = [limiter.is_rate_limited("k", limit=2, window=60) for _ in range(3)]
    assert [is_limited for is_limited, _ in results] == [False, False, True]


def test_redis_limiter_no_inc_fallback_does_not_extend_past_window() -> None:
    """Without atomic inc, set must use remaining window TTL, not a full refresh.

    Re-setting timeout=window on every hit under steady traffic never lets the
    fixed window expire (permanent lockout / sliding soft-limit).
    """
    cache = _FakeCache()
    cache.inc = MagicMock(side_effect=NotImplementedError)  # type: ignore[method-assign]
    limiter = _make_redis_limiter(cache)

    window = 60
    for _ in range(5):
        limiter.is_rate_limited("k", limit=10, window=window)

    assert len(cache.store) == 1
    (only_key,) = cache.store
    assert cache.store[only_key] == 5
    # TTL must be at most the window (remaining seconds until bucket end).
    assert cache.timeouts[only_key] is not None
    assert 1 <= int(cache.timeouts[only_key] or 0) <= window


def test_in_memory_limiter_sliding_window() -> None:
    limiter = InMemoryRateLimiter()
    results = [limiter.is_rate_limited("k", limit=2, window=60) for _ in range(3)]
    assert [is_limited for is_limited, _ in results] == [False, False, True]


def test_in_memory_limiter_reset_time_is_in_the_future_when_limited() -> None:
    """When limited, reset_time must be after now (not equal to now).

    Clients use reset_time - now as retry delay. A zero delay encourages
    tight retry loops and misrepresents the sliding window.
    """
    import time

    limiter = InMemoryRateLimiter()
    window = 60
    limit = 2
    for _ in range(limit):
        limited, _ = limiter.is_rate_limited("k", limit=limit, window=window)
        assert limited is False

    limited, info = limiter.is_rate_limited("k", limit=limit, window=window)
    assert limited is True
    # Oldest request ages out after ~window seconds; allow small clock skew.
    assert info["reset_time"] - int(time.time()) > 0
    assert info["reset_time"] <= int(time.time()) + window


def _ctx(
    name: str,
    params: dict[str, object] | None = None,
    *,
    use_arguments: bool = True,
) -> SimpleNamespace:
    """Build a middleware context.

    Real FastMCP ``CallToolRequestParams`` expose tool args on ``.arguments``.
    When *use_arguments* is False, only the legacy ``.params`` stub is set
    (compat path for older mocks).
    """
    payload = params or {}
    if use_arguments:
        message = SimpleNamespace(name=name, arguments=payload)
    else:
        message = SimpleNamespace(name=name, params=payload)
    return SimpleNamespace(
        message=message,
        method="tools/call",
        metadata=None,
        session=None,
    )


def test_key_uses_expensive_limit_for_expensive_tool() -> None:
    mw = RateLimitMiddleware()
    with (
        patch("axbi.mcp_service.middleware.get_user_id", return_value=None),
        patch(
            "axbi.mcp_service.middleware._principal_from_access_token",
            return_value=None,
        ),
    ):
        key, limit = mw._get_rate_limit_key(_ctx("generate_chart"))
    assert limit == mw.expensive_rpm
    assert key.startswith("expensive:anonymous:generate_chart")


def test_key_uses_user_limit_for_known_principal() -> None:
    mw = RateLimitMiddleware()
    with (
        patch("axbi.mcp_service.middleware.get_user_id", return_value=None),
        patch(
            "axbi.mcp_service.middleware._principal_from_access_token",
            return_value="jwt:alice",
        ),
    ):
        key, limit = mw._get_rate_limit_key(_ctx("list_charts"))
    assert limit == mw.user_rpm
    assert key == "user:jwt:alice:list_charts"


def test_key_resolves_real_tool_under_tool_search_proxy() -> None:
    mw = RateLimitMiddleware()
    # Client called the call_tool proxy; the real tool is expensive.
    # Protocol field is ``arguments`` (FastMCP CallToolRequestParams).
    ctx = _ctx("call_tool", {"name": "get_chart_data"}, use_arguments=True)
    with (
        patch("axbi.mcp_service.middleware.get_user_id", return_value=None),
        patch(
            "axbi.mcp_service.middleware._principal_from_access_token",
            return_value=None,
        ),
    ):
        key, limit = mw._get_rate_limit_key(ctx)
    assert limit == mw.expensive_rpm
    assert key.endswith(":get_chart_data")


def test_key_resolves_tool_from_legacy_params_stub() -> None:
    """Legacy mocks that set ``.params`` still resolve the proxied tool name."""
    mw = RateLimitMiddleware()
    ctx = _ctx("call_tool", {"name": "get_chart_data"}, use_arguments=False)
    with (
        patch("axbi.mcp_service.middleware.get_user_id", return_value=None),
        patch(
            "axbi.mcp_service.middleware._principal_from_access_token",
            return_value=None,
        ),
    ):
        key, limit = mw._get_rate_limit_key(ctx)
    assert limit == mw.expensive_rpm
    assert key.endswith(":get_chart_data")


@pytest.mark.asyncio
async def test_middleware_raises_tool_error_when_limited() -> None:
    mw = RateLimitMiddleware(default_requests_per_minute=1)

    async def call_next(_ctx: SimpleNamespace) -> str:
        return "ok"

    with (
        patch("axbi.mcp_service.middleware.get_user_id", return_value=None),
        patch(
            "axbi.mcp_service.middleware._principal_from_access_token",
            return_value=None,
        ),
        patch("axbi.mcp_service.middleware.mcp_event_log"),
    ):
        ctx = _ctx("list_charts")
        first = await mw.on_call_tool(ctx, call_next)
        assert first == "ok"
        with pytest.raises(ToolError):
            await mw.on_call_tool(ctx, call_next)


def test_tool_call_arguments_prefers_protocol_arguments_field() -> None:
    """MCP CallToolRequestParams uses ``arguments``, not ``params``."""
    message = SimpleNamespace(
        name="list_charts",
        arguments={"dashboard_id": 9, "name": "get_chart_data"},
        params={"dashboard_id": 1},  # stale/legacy should lose
    )
    assert _tool_call_arguments(message) == {
        "dashboard_id": 9,
        "name": "get_chart_data",
    }


def test_logging_extracts_entity_ids_from_arguments() -> None:
    mw = LoggingMiddleware()
    ctx = SimpleNamespace(
        message=SimpleNamespace(
            name="get_chart_data",
            arguments={
                "dashboard_id": 3,
                "chart_id": 4,
                "dataset_id": 5,
            },
        ),
        metadata=None,
        session=None,
    )
    with patch("axbi.mcp_service.middleware.get_user_id", return_value=None):
        _agent, _user, dashboard_id, slice_id, dataset_id, params = (
            mw._extract_context_info(ctx)
        )
    assert dashboard_id == 3
    assert slice_id == 4
    assert dataset_id == 5
    assert params["dashboard_id"] == 3


def test_factory_returns_none_when_disabled() -> None:
    flask_app = SimpleNamespace(config={"MCP_RATE_LIMIT_CONFIG": {"enabled": False}})
    with patch(
        "axbi.mcp_service.flask_singleton.get_flask_app", return_value=flask_app
    ):
        assert create_rate_limit_middleware() is None


def test_factory_builds_middleware_when_enabled() -> None:
    flask_app = SimpleNamespace(
        config={
            "MCP_RATE_LIMIT_CONFIG": {
                "enabled": True,
                "default_requests_per_minute": 7,
                "per_user_requests_per_minute": 9,
                "expensive_tool_requests_per_minute": 2,
                "expensive_tools": ["generate_chart"],
            }
        }
    )
    with patch(
        "axbi.mcp_service.flask_singleton.get_flask_app", return_value=flask_app
    ):
        mw = create_rate_limit_middleware()
    assert isinstance(mw, RateLimitMiddleware)
    assert mw.default_rpm == 7
    assert mw.user_rpm == 9
    assert mw.expensive_rpm == 2
    assert mw.expensive_tools == {"generate_chart"}

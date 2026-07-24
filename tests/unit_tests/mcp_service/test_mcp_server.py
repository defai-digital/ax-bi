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

"""Tests for MCP server transport and EventStore creation."""

import asyncio
import contextlib
from typing import Any, cast
from unittest.mock import MagicMock, patch

import httpx
import pytest
from fastmcp import FastMCP
from fastmcp.server.auth.providers.jwt import StaticTokenVerifier
from starlette.routing import Mount, Route


async def _endpoint() -> None:
    """Minimal Starlette endpoint used to construct route fixtures."""


def test_http_transport_app_combines_streamable_http_and_legacy_sse() -> None:
    """GET SSE and POST streamable HTTP routes coexist on /mcp."""
    from axbi.mcp_service.server import _create_http_transport_app

    streamable_app = MagicMock()
    streamable_app.routes = [
        Route("/mcp", _endpoint, methods=["POST", "DELETE"]),
        Route("/health", _endpoint, methods=["GET"]),
    ]
    legacy_sse_app = MagicMock()
    legacy_sse_app.routes = [
        Route("/mcp", _endpoint, methods=["GET"]),
        Mount("/messages", app=MagicMock()),
        Route("/health", _endpoint, methods=["GET"]),
    ]
    mcp_instance = MagicMock()
    mcp_instance.http_app.side_effect = [streamable_app, legacy_sse_app]
    middleware = [MagicMock()]

    result = _create_http_transport_app(
        mcp_instance,
        event_store=None,
        middleware=middleware,
    )

    assert result is streamable_app
    assert [
        (route.path, frozenset(getattr(route, "methods", None) or ()))
        for route in result.routes
    ] == [
        ("/mcp", frozenset({"POST", "DELETE"})),
        ("/health", frozenset({"GET", "HEAD"})),
        ("/mcp", frozenset({"GET", "HEAD"})),
        ("/messages", frozenset()),
    ]
    assert result.state.legacy_sse_enabled is True
    assert mcp_instance.http_app.call_args_list == [
        (
            (),
            {
                "path": "/mcp",
                "transport": "streamable-http",
                "event_store": None,
                "stateless_http": True,
                "middleware": middleware,
            },
        ),
        (
            (),
            {
                "path": "/mcp",
                "transport": "sse",
                "middleware": middleware,
            },
        ),
    ]


def test_http_transport_app_disables_process_local_sse_with_event_store() -> None:
    """Multi-pod mode does not expose an SSE session that cannot cross pods."""
    from axbi.mcp_service.server import _create_http_transport_app

    streamable_app = MagicMock()
    streamable_app.routes = [
        Route("/mcp", _endpoint, methods=["POST", "DELETE"]),
    ]
    mcp_instance = MagicMock()
    mcp_instance.http_app.return_value = streamable_app
    event_store = MagicMock()

    result = _create_http_transport_app(
        mcp_instance,
        event_store=event_store,
        middleware=[],
    )

    assert result is streamable_app
    assert result.state.legacy_sse_enabled is False
    mcp_instance.http_app.assert_called_once_with(
        path="/mcp",
        transport="streamable-http",
        event_store=event_store,
        stateless_http=True,
        middleware=[],
    )


def test_http_transport_app_uses_streamable_lifespan_owner() -> None:
    """The combined app is the streamable app, so FastMCP starts only once."""
    from axbi.mcp_service.server import _create_http_transport_app

    streamable_app = MagicMock()
    streamable_app.routes = []
    legacy_sse_app = MagicMock()
    legacy_sse_app.routes = []
    mcp_instance = MagicMock()
    mcp_instance.http_app.side_effect = [streamable_app, legacy_sse_app]

    result = _create_http_transport_app(
        mcp_instance,
        event_store=None,
        middleware=[],
    )

    assert result is streamable_app


@pytest.mark.asyncio
async def test_legacy_sse_get_starts_event_stream() -> None:
    """An authenticated legacy GET /mcp handshake starts an SSE response."""
    from axbi.mcp_service.server import _create_http_transport_app

    auth = StaticTokenVerifier(
        tokens={
            "test-token": {
                "client_id": "transport-test",
                "scopes": [],
            }
        }
    )
    mcp_instance = FastMCP("dual-transport-test", auth=auth)
    app = _create_http_transport_app(
        mcp_instance,
        event_store=None,
        middleware=[],
    )
    response_started = asyncio.Event()
    sent_messages: list[dict[str, Any]] = []

    async def receive() -> dict[str, Any]:
        await asyncio.Future()
        raise AssertionError("unreachable")

    async def send(message: dict[str, Any]) -> None:
        sent_messages.append(message)
        if message["type"] == "http.response.start":
            response_started.set()

    scope: dict[str, Any] = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/mcp",
        "raw_path": b"/mcp",
        "query_string": b"",
        "root_path": "",
        "headers": [
            (b"accept", b"text/event-stream"),
            (b"authorization", b"Bearer test-token"),
        ],
        "client": ("127.0.0.1", 12345),
        "server": ("127.0.0.1", 31421),
    }

    async with app.router.lifespan_context(app):
        request_task = asyncio.create_task(app(scope, receive, send))
        try:
            await asyncio.wait_for(response_started.wait(), timeout=1)
        finally:
            request_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await request_task

    start = next(
        message for message in sent_messages if message["type"] == "http.response.start"
    )
    assert start["status"] == 200
    headers = dict(cast(list[tuple[bytes, bytes]], start["headers"]))
    assert headers[b"content-type"].startswith(b"text/event-stream")


@pytest.mark.asyncio
async def test_streamable_http_initialize_still_uses_post() -> None:
    """Adding the SSE GET route does not displace streamable HTTP POST."""
    from axbi.mcp_service.server import _create_http_transport_app

    mcp_instance = FastMCP("dual-transport-test")
    app = _create_http_transport_app(
        mcp_instance,
        event_store=None,
        middleware=[],
    )
    transport = httpx.ASGITransport(app=app)

    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://127.0.0.1:31421",
        ) as client:
            response = await client.post(
                "/mcp",
                headers={
                    "Accept": "application/json, text/event-stream",
                    "Content-Type": "application/json",
                },
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2025-03-26",
                        "capabilities": {},
                        "clientInfo": {
                            "name": "transport-test",
                            "version": "1.0",
                        },
                    },
                },
            )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert '"serverInfo":{"name":"dual-transport-test"' in response.text


def test_create_event_store_returns_none_when_no_redis_url():
    """EventStore returns None when no Redis URL configured (single-pod mode)."""
    config = {"CACHE_REDIS_URL": None}

    from axbi.mcp_service.server import create_event_store

    result = create_event_store(config)

    assert result is None


def test_create_event_store_returns_none_when_empty_config():
    """EventStore returns None when config has no CACHE_REDIS_URL."""
    config = {}

    from axbi.mcp_service.server import create_event_store

    result = create_event_store(config)

    assert result is None


def test_create_event_store_creates_event_store_with_redis():
    """EventStore is created with Redis backend when URL is configured."""
    config = {
        "CACHE_REDIS_URL": "redis://localhost:6379/0",
        "event_store_max_events": 50,
        "event_store_ttl": 1800,
    }

    mock_redis_store = MagicMock()
    mock_event_store = MagicMock()

    with patch(
        "axbi.mcp_service.server._create_redis_store",
        return_value=mock_redis_store,
    ) as mock_create_store:
        with patch(
            "fastmcp.server.event_store.EventStore",
            return_value=mock_event_store,
        ) as mock_event_store_class:
            from axbi.mcp_service.server import create_event_store

            result = create_event_store(config)

            # Verify EventStore was created
            assert result is mock_event_store
            # Verify _create_redis_store was called with prefix wrapper
            mock_create_store.assert_called_once_with(
                config, prefix="mcp_events_", wrap=True
            )
            # Verify EventStore was initialized with correct params
            mock_event_store_class.assert_called_once_with(
                storage=mock_redis_store,
                max_events_per_stream=50,
                ttl=1800,
            )


def test_create_event_store_uses_default_config_values():
    """EventStore uses default values when not specified in config."""
    config = {
        "CACHE_REDIS_URL": "redis://localhost:6379/0",
    }

    mock_redis_store = MagicMock()
    mock_event_store = MagicMock()

    with patch(
        "axbi.mcp_service.server._create_redis_store",
        return_value=mock_redis_store,
    ):
        with patch(
            "fastmcp.server.event_store.EventStore",
            return_value=mock_event_store,
        ) as mock_event_store_class:
            from axbi.mcp_service.server import create_event_store

            result = create_event_store(config)

            assert result is mock_event_store
            # Verify defaults are used
            mock_event_store_class.assert_called_once_with(
                storage=mock_redis_store,
                max_events_per_stream=100,  # default
                ttl=3600,  # default
            )


def test_suppress_third_party_warnings():
    """Third-party deprecation warnings filters are installed."""
    import re
    import warnings

    from axbi.mcp_service.server import _suppress_third_party_warnings

    _suppress_third_party_warnings()

    # Verify marshmallow DeprecationWarning filter is installed
    marshmallow_filters = [
        f
        for f in warnings.filters
        if f[0] == "ignore"
        and f[2] is DeprecationWarning
        and isinstance(f[3], re.Pattern)
        and f[3].pattern == r"marshmallow\..*"
    ]
    assert len(marshmallow_filters) >= 1, (
        "Expected marshmallow DeprecationWarning filter"
    )

    # Verify google FutureWarning filter is installed
    google_filters = [
        f
        for f in warnings.filters
        if f[0] == "ignore"
        and f[2] is FutureWarning
        and isinstance(f[3], re.Pattern)
        and f[3].pattern == r"google\..*"
    ]
    assert len(google_filters) >= 1, "Expected google FutureWarning filter"


def test_create_event_store_returns_none_when_redis_store_fails():
    """EventStore returns None when Redis store creation fails."""
    config = {
        "CACHE_REDIS_URL": "redis://localhost:6379/0",
    }

    with patch(
        "axbi.mcp_service.server._create_redis_store",
        return_value=None,  # Simulates Redis store creation failure
    ):
        from axbi.mcp_service.server import create_event_store

        result = create_event_store(config)

        assert result is None


def test_create_auth_provider_uses_default_factory_for_mcp_api_key_only() -> None:
    """MCP_API_KEY_ENABLED=True should install auth even when FAB API keys are off."""
    from axbi.mcp_service.server import _create_auth_provider

    flask_app = MagicMock()
    flask_app.config.get.side_effect = lambda key, default=None: {
        "MCP_AUTH_FACTORY": None,
        "MCP_AUTH_ENABLED": False,
        "MCP_API_KEY_ENABLED": True,
        "FAB_API_KEY_ENABLED": False,
    }.get(key, default)
    auth_provider = MagicMock()

    with patch(
        "axbi.mcp_service.mcp_config.create_default_mcp_auth_factory",
        return_value=auth_provider,
    ) as create_default_mcp_auth_factory:
        result = _create_auth_provider(flask_app)

    assert result is auth_provider
    create_default_mcp_auth_factory.assert_called_once_with(flask_app)


def test_create_auth_provider_propagates_auth_config_error() -> None:
    """A fatal auth config error must propagate, not fall through to no auth.

    The default factory raises MCPAuthConfigError for an unusable auth
    configuration. _create_auth_provider must re-raise it so the service fails
    to start instead of silently returning None (which would run unauthenticated).
    """
    from axbi.mcp_service.mcp_config import MCPAuthConfigError
    from axbi.mcp_service.server import _create_auth_provider

    flask_app = MagicMock()
    flask_app.config.get.side_effect = lambda key, default=None: {
        "MCP_AUTH_FACTORY": None,
        "MCP_AUTH_ENABLED": True,
        "MCP_API_KEY_ENABLED": False,
        "FAB_API_KEY_ENABLED": False,
    }.get(key, default)

    with patch(
        "axbi.mcp_service.mcp_config.create_default_mcp_auth_factory",
        side_effect=MCPAuthConfigError("MCP_JWT_AUDIENCE must be set"),
    ):
        with pytest.raises(MCPAuthConfigError):
            _create_auth_provider(flask_app)


def test_create_auth_provider_fails_closed_on_unexpected_error() -> None:
    """Unexpected factory errors must not start an unauthenticated server."""
    from axbi.mcp_service.server import _create_auth_provider

    flask_app = MagicMock()
    flask_app.config.get.side_effect = lambda key, default=None: {
        "MCP_AUTH_FACTORY": None,
        "MCP_AUTH_ENABLED": True,
        "MCP_API_KEY_ENABLED": False,
        "FAB_API_KEY_ENABLED": False,
    }.get(key, default)

    with patch(
        "axbi.mcp_service.mcp_config.create_default_mcp_auth_factory",
        side_effect=RuntimeError("boom"),
    ):
        with pytest.raises(RuntimeError, match="Refusing to start"):
            _create_auth_provider(flask_app)

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

from unittest.mock import MagicMock

import pytest
import requests

from superset.runtime_modernization.ax_services import (
    AxServicesClient,
    AxServicesConfig,
)

TEST_INTERNAL_TOKEN = "-".join(("token", "123"))


def make_response(
    *,
    ok: bool = True,
    status_code: int = 200,
    payload: dict[str, object] | None = None,
) -> MagicMock:
    """Build a minimal requests response test double."""

    response = MagicMock()
    response.ok = ok
    response.status_code = status_code
    response.json.return_value = payload or {}
    return response


def test_ax_services_config_reads_mapping() -> None:
    """Sidecar config is built from Superset config keys."""

    config = AxServicesConfig.from_mapping(
        {
            "AX_SERVICES_BASE_URL": "http://ax-services.local/",
            "AX_SERVICES_TIMEOUT_SECONDS": "3.5",
            "AX_SERVICES_INTERNAL_TOKEN": TEST_INTERNAL_TOKEN,
        }
    )

    assert config.base_url == "http://ax-services.local"
    assert config.timeout_seconds == 3.5
    assert config.internal_token == TEST_INTERNAL_TOKEN


def test_health_calls_ax_services_with_request_id_and_token() -> None:
    """Health requests include timeout, request ID, and bearer token."""

    session = MagicMock()
    session.get.return_value = make_response(payload={"status": "ok"})
    client = AxServicesClient(
        AxServicesConfig(
            base_url="http://ax-services.local",
            timeout_seconds=1.5,
            internal_token=TEST_INTERNAL_TOKEN,
        ),
        session=session,
    )

    result = client.health(request_id="request-abc")

    assert result.ok is True
    assert result.status_code == 200
    assert result.payload == {"status": "ok"}
    session.get.assert_called_once_with(
        "http://ax-services.local/health",
        headers={
            "authorization": "Bearer token-123",
            "x-request-id": "request-abc",
        },
        timeout=1.5,
    )


def test_ready_returns_unready_response_payload() -> None:
    """Readiness calls preserve non-2xx status and JSON payload."""

    session = MagicMock()
    session.get.return_value = make_response(
        ok=False,
        status_code=503,
        payload={"status": "not_ready"},
    )
    client = AxServicesClient(AxServicesConfig(), session=session)

    result = client.ready()

    assert result.ok is False
    assert result.status_code == 503
    assert result.payload == {"status": "not_ready"}


def test_metadata_calls_ax_services_metadata_endpoint() -> None:
    """Metadata requests use the sidecar Superset metadata probe endpoint."""

    session = MagicMock()
    session.get.return_value = make_response(
        payload={"dependencies": {"supersetMetadata": {"ok": True}}}
    )
    client = AxServicesClient(AxServicesConfig(), session=session)

    result = client.metadata(request_id="request-metadata")

    assert result.ok is True
    assert result.payload == {"dependencies": {"supersetMetadata": {"ok": True}}}
    session.get.assert_called_once_with(
        "http://127.0.0.1:5010/metadata",
        headers={"x-request-id": "request-metadata"},
        timeout=2.0,
    )


def test_metrics_calls_ax_services_metrics_endpoint() -> None:
    """Metrics requests use the sidecar runtime metrics endpoint."""

    session = MagicMock()
    session.get.return_value = make_response(payload={"requests": {"total": 3}})
    client = AxServicesClient(AxServicesConfig(), session=session)

    result = client.metrics(request_id="request-metrics")

    assert result.ok is True
    assert result.payload == {"requests": {"total": 3}}
    session.get.assert_called_once_with(
        "http://127.0.0.1:5010/metrics",
        headers={"x-request-id": "request-metrics"},
        timeout=2.0,
    )


def test_asset_search_posts_to_ax_services_asset_search_endpoint() -> None:
    """Asset search requests use the sidecar TypeScript search endpoint."""

    session = MagicMock()
    session.post.return_value = make_response(payload={"assets": []})
    client = AxServicesClient(AxServicesConfig(), session=session)

    result = client.asset_search(
        {
            "contractVersion": "asset-search.v1",
            "query": "sales",
            "assetTypes": ["dataset"],
            "includeCertifiedOnly": False,
            "limit": 10,
        },
        request_id="request-search",
    )

    assert result.ok is True
    assert result.payload == {"assets": []}
    session.post.assert_called_once_with(
        "http://127.0.0.1:5010/mcp/assets/search",
        json={
            "contractVersion": "asset-search.v1",
            "query": "sales",
            "assetTypes": ["dataset"],
            "includeCertifiedOnly": False,
            "limit": 10,
        },
        headers={
            "content-type": "application/json",
            "x-request-id": "request-search",
        },
        timeout=2.0,
    )


def test_post_json_sends_payload() -> None:
    """POST helpers send JSON payloads to future sidecar candidate paths."""

    session = MagicMock()
    session.post.return_value = make_response(payload={"accepted": True})
    client = AxServicesClient(AxServicesConfig(), session=session)

    result = client.post_json(
        "/runtime/v1/candidate",
        {"operation": "plan_dashboard"},
        request_id="request-abc",
    )

    assert result.ok is True
    assert result.payload == {"accepted": True}
    session.post.assert_called_once_with(
        "http://127.0.0.1:5010/runtime/v1/candidate",
        json={"operation": "plan_dashboard"},
        headers={
            "content-type": "application/json",
            "x-request-id": "request-abc",
        },
        timeout=2.0,
    )


def test_request_exception_returns_error_response() -> None:
    """Network failures return an error envelope instead of raising."""

    session = MagicMock()
    session.get.side_effect = requests.RequestException("connection failed")
    client = AxServicesClient(AxServicesConfig(), session=session)

    result = client.health()

    assert result.ok is False
    assert result.status_code is None
    assert result.error == "connection failed"


def test_invalid_path_raises() -> None:
    """Sidecar paths must be absolute to avoid ambiguous URL construction."""

    client = AxServicesClient(AxServicesConfig())

    with pytest.raises(ValueError, match="path must start"):
        client.get_json("health")

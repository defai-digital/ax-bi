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

from axbi.runtime_modernization.ax_services import (
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
    """Sidecar config is built from AxBI config keys."""

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
    """Metadata requests use the sidecar AxBI metadata probe endpoint."""

    session = MagicMock()
    session.get.return_value = make_response(
        payload={"dependencies": {"axbiMetadata": {"ok": True}}}
    )
    client = AxServicesClient(AxServicesConfig(), session=session)

    result = client.metadata(request_id="request-metadata")

    assert result.ok is True
    assert result.payload == {"dependencies": {"axbiMetadata": {"ok": True}}}
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


def test_list_dashboards_posts_to_ax_services_dashboard_list_endpoint() -> None:
    """Dashboard list requests use the sidecar TypeScript list endpoint."""

    session = MagicMock()
    session.post.return_value = make_response(payload={"dashboards": []})
    client = AxServicesClient(AxServicesConfig(), session=session)

    result = client.list_dashboards(
        {
            "contractVersion": "dashboard-list.v1",
            "filters": [],
            "selectColumns": ["id", "dashboard_title"],
            "orderDirection": "asc",
            "page": 1,
            "pageSize": 10,
            "createdByMe": False,
            "ownedByMe": False,
        },
        request_id="request-dashboards",
    )

    assert result.ok is True
    assert result.payload == {"dashboards": []}
    session.post.assert_called_once_with(
        "http://127.0.0.1:5010/mcp/dashboards/list",
        json={
            "contractVersion": "dashboard-list.v1",
            "filters": [],
            "selectColumns": ["id", "dashboard_title"],
            "orderDirection": "asc",
            "page": 1,
            "pageSize": 10,
            "createdByMe": False,
            "ownedByMe": False,
        },
        headers={
            "content-type": "application/json",
            "x-request-id": "request-dashboards",
        },
        timeout=2.0,
    )


def test_list_charts_posts_to_ax_services_chart_list_endpoint() -> None:
    """Chart list requests use the sidecar TypeScript list endpoint."""

    session = MagicMock()
    session.post.return_value = make_response(payload={"charts": []})
    client = AxServicesClient(AxServicesConfig(), session=session)

    result = client.list_charts(
        {
            "contractVersion": "chart-list.v1",
            "filters": [],
            "selectColumns": ["id", "slice_name"],
            "orderDirection": "asc",
            "page": 1,
            "pageSize": 10,
            "createdByMe": False,
            "ownedByMe": False,
        },
        request_id="request-charts",
    )

    assert result.ok is True
    assert result.payload == {"charts": []}
    session.post.assert_called_once_with(
        "http://127.0.0.1:5010/mcp/charts/list",
        json={
            "contractVersion": "chart-list.v1",
            "filters": [],
            "selectColumns": ["id", "slice_name"],
            "orderDirection": "asc",
            "page": 1,
            "pageSize": 10,
            "createdByMe": False,
            "ownedByMe": False,
        },
        headers={
            "content-type": "application/json",
            "x-request-id": "request-charts",
        },
        timeout=2.0,
    )


def test_list_databases_posts_to_ax_services_database_list_endpoint() -> None:
    """Database list requests use the sidecar TypeScript list endpoint."""

    session = MagicMock()
    session.post.return_value = make_response(payload={"databases": []})
    client = AxServicesClient(AxServicesConfig(), session=session)

    result = client.list_databases(
        {
            "contractVersion": "database-list.v1",
            "filters": [],
            "selectColumns": ["id", "database_name"],
            "orderDirection": "asc",
            "page": 1,
            "pageSize": 10,
            "createdByMe": False,
        },
        request_id="request-databases",
    )

    assert result.ok is True
    assert result.payload == {"databases": []}
    session.post.assert_called_once_with(
        "http://127.0.0.1:5010/mcp/databases/list",
        json={
            "contractVersion": "database-list.v1",
            "filters": [],
            "selectColumns": ["id", "database_name"],
            "orderDirection": "asc",
            "page": 1,
            "pageSize": 10,
            "createdByMe": False,
        },
        headers={
            "content-type": "application/json",
            "x-request-id": "request-databases",
        },
        timeout=2.0,
    )


def test_list_datasets_posts_to_ax_services_dataset_list_endpoint() -> None:
    """Dataset list requests use the sidecar TypeScript list endpoint."""

    session = MagicMock()
    session.post.return_value = make_response(payload={"datasets": []})
    client = AxServicesClient(AxServicesConfig(), session=session)

    result = client.list_datasets(
        {
            "contractVersion": "dataset-list.v1",
            "filters": [],
            "selectColumns": ["id", "table_name"],
            "orderDirection": "asc",
            "page": 1,
            "pageSize": 10,
            "createdByMe": False,
            "ownedByMe": False,
        },
        request_id="request-datasets",
    )

    assert result.ok is True
    assert result.payload == {"datasets": []}
    session.post.assert_called_once_with(
        "http://127.0.0.1:5010/mcp/datasets/list",
        json={
            "contractVersion": "dataset-list.v1",
            "filters": [],
            "selectColumns": ["id", "table_name"],
            "orderDirection": "asc",
            "page": 1,
            "pageSize": 10,
            "createdByMe": False,
            "ownedByMe": False,
        },
        headers={
            "content-type": "application/json",
            "x-request-id": "request-datasets",
        },
        timeout=2.0,
    )


def test_list_annotation_layers_posts_to_ax_services_annotation_layer_endpoint() -> (
    None
):
    """Annotation layer list requests use the sidecar TypeScript list endpoint."""

    session = MagicMock()
    session.post.return_value = make_response(payload={"annotationLayers": []})
    client = AxServicesClient(AxServicesConfig(), session=session)

    result = client.list_annotation_layers(
        {
            "contractVersion": "annotation-layer-list.v1",
            "filters": [],
            "selectColumns": ["id", "name"],
            "orderDirection": "asc",
            "page": 1,
            "pageSize": 10,
        },
        request_id="request-annotation-layers",
    )

    assert result.ok is True
    assert result.payload == {"annotationLayers": []}
    session.post.assert_called_once_with(
        "http://127.0.0.1:5010/mcp/annotation-layers/list",
        json={
            "contractVersion": "annotation-layer-list.v1",
            "filters": [],
            "selectColumns": ["id", "name"],
            "orderDirection": "asc",
            "page": 1,
            "pageSize": 10,
        },
        headers={
            "content-type": "application/json",
            "x-request-id": "request-annotation-layers",
        },
        timeout=2.0,
    )


def test_list_annotations_posts_to_ax_services_annotation_list_endpoint() -> None:
    """Annotation list requests use the sidecar TypeScript list endpoint."""

    session = MagicMock()
    session.post.return_value = make_response(payload={"annotations": []})
    client = AxServicesClient(AxServicesConfig(), session=session)

    result = client.list_annotations(
        {
            "contractVersion": "annotation-list.v1",
            "layerId": 5,
            "filters": [],
            "selectColumns": ["id", "short_descr"],
            "orderDirection": "asc",
            "page": 1,
            "pageSize": 10,
        },
        request_id="request-annotations",
    )

    assert result.ok is True
    assert result.payload == {"annotations": []}
    session.post.assert_called_once_with(
        "http://127.0.0.1:5010/mcp/annotations/list",
        json={
            "contractVersion": "annotation-list.v1",
            "layerId": 5,
            "filters": [],
            "selectColumns": ["id", "short_descr"],
            "orderDirection": "asc",
            "page": 1,
            "pageSize": 10,
        },
        headers={
            "content-type": "application/json",
            "x-request-id": "request-annotations",
        },
        timeout=2.0,
    )


def test_list_queries_posts_to_ax_services_query_list_endpoint() -> None:
    """Query list requests use the sidecar TypeScript list endpoint."""

    session = MagicMock()
    session.post.return_value = make_response(payload={"queries": []})
    client = AxServicesClient(AxServicesConfig(), session=session)

    result = client.list_queries(
        {
            "contractVersion": "query-list.v1",
            "filters": [],
            "selectColumns": ["id", "status"],
            "orderDirection": "desc",
            "page": 1,
            "pageSize": 25,
        },
        request_id="request-queries",
    )

    assert result.ok is True
    assert result.payload == {"queries": []}
    session.post.assert_called_once_with(
        "http://127.0.0.1:5010/mcp/queries/list",
        json={
            "contractVersion": "query-list.v1",
            "filters": [],
            "selectColumns": ["id", "status"],
            "orderDirection": "desc",
            "page": 1,
            "pageSize": 25,
        },
        headers={
            "content-type": "application/json",
            "x-request-id": "request-queries",
        },
        timeout=2.0,
    )


def test_list_saved_queries_posts_to_ax_services_saved_query_list_endpoint() -> None:
    """Saved query list requests use the sidecar TypeScript list endpoint."""

    session = MagicMock()
    session.post.return_value = make_response(payload={"savedQueries": []})
    client = AxServicesClient(AxServicesConfig(), session=session)

    result = client.list_saved_queries(
        {
            "contractVersion": "saved-query-list.v1",
            "filters": [],
            "selectColumns": ["id", "label"],
            "orderDirection": "asc",
            "page": 1,
            "pageSize": 10,
        },
        request_id="request-saved-queries",
    )

    assert result.ok is True
    assert result.payload == {"savedQueries": []}
    session.post.assert_called_once_with(
        "http://127.0.0.1:5010/mcp/saved-queries/list",
        json={
            "contractVersion": "saved-query-list.v1",
            "filters": [],
            "selectColumns": ["id", "label"],
            "orderDirection": "asc",
            "page": 1,
            "pageSize": 10,
        },
        headers={
            "content-type": "application/json",
            "x-request-id": "request-saved-queries",
        },
        timeout=2.0,
    )


def test_list_tags_posts_to_ax_services_tag_list_endpoint() -> None:
    """Tag list requests use the sidecar TypeScript list endpoint."""

    session = MagicMock()
    session.post.return_value = make_response(payload={"tags": []})
    client = AxServicesClient(AxServicesConfig(), session=session)

    result = client.list_tags(
        {
            "contractVersion": "tag-list.v1",
            "filters": [],
            "selectColumns": ["id", "name"],
            "orderDirection": "asc",
            "page": 1,
            "pageSize": 10,
        },
        request_id="request-tags",
    )

    assert result.ok is True
    assert result.payload == {"tags": []}
    session.post.assert_called_once_with(
        "http://127.0.0.1:5010/mcp/tags/list",
        json={
            "contractVersion": "tag-list.v1",
            "filters": [],
            "selectColumns": ["id", "name"],
            "orderDirection": "asc",
            "page": 1,
            "pageSize": 10,
        },
        headers={
            "content-type": "application/json",
            "x-request-id": "request-tags",
        },
        timeout=2.0,
    )


def test_list_reports_posts_to_ax_services_report_list_endpoint() -> None:
    """Report list requests use the sidecar TypeScript list endpoint."""

    session = MagicMock()
    session.post.return_value = make_response(payload={"reports": []})
    client = AxServicesClient(AxServicesConfig(), session=session)

    result = client.list_reports(
        {
            "contractVersion": "report-list.v1",
            "filters": [],
            "selectColumns": ["id", "name"],
            "orderDirection": "asc",
            "page": 1,
            "pageSize": 10,
        },
        request_id="request-reports",
    )

    assert result.ok is True
    assert result.payload == {"reports": []}
    session.post.assert_called_once_with(
        "http://127.0.0.1:5010/mcp/reports/list",
        json={
            "contractVersion": "report-list.v1",
            "filters": [],
            "selectColumns": ["id", "name"],
            "orderDirection": "asc",
            "page": 1,
            "pageSize": 10,
        },
        headers={
            "content-type": "application/json",
            "x-request-id": "request-reports",
        },
        timeout=2.0,
    )


def test_list_roles_posts_to_ax_services_role_list_endpoint() -> None:
    """Role list requests use the sidecar TypeScript list endpoint."""

    session = MagicMock()
    session.post.return_value = make_response(payload={"roles": []})
    client = AxServicesClient(AxServicesConfig(), session=session)

    result = client.list_roles(
        {
            "contractVersion": "role-list.v1",
            "filters": [],
            "selectColumns": ["id", "name"],
            "orderDirection": "asc",
            "page": 1,
            "pageSize": 10,
        },
        request_id="request-roles",
    )

    assert result.ok is True
    assert result.payload == {"roles": []}
    session.post.assert_called_once_with(
        "http://127.0.0.1:5010/mcp/roles/list",
        json={
            "contractVersion": "role-list.v1",
            "filters": [],
            "selectColumns": ["id", "name"],
            "orderDirection": "asc",
            "page": 1,
            "pageSize": 10,
        },
        headers={
            "content-type": "application/json",
            "x-request-id": "request-roles",
        },
        timeout=2.0,
    )


def test_list_rls_filters_posts_to_ax_services_rls_filter_list_endpoint() -> None:
    """RLS filter list requests use the sidecar TypeScript list endpoint."""

    session = MagicMock()
    session.post.return_value = make_response(payload={"rlsFilters": []})
    client = AxServicesClient(AxServicesConfig(), session=session)

    result = client.list_rls_filters(
        {
            "contractVersion": "rls-list.v1",
            "filters": [],
            "selectColumns": ["id", "name", "filter_type"],
            "orderDirection": "asc",
            "page": 1,
            "pageSize": 10,
        },
        request_id="request-rls",
    )

    assert result.ok is True
    assert result.payload == {"rlsFilters": []}
    session.post.assert_called_once_with(
        "http://127.0.0.1:5010/mcp/rls-filters/list",
        json={
            "contractVersion": "rls-list.v1",
            "filters": [],
            "selectColumns": ["id", "name", "filter_type"],
            "orderDirection": "asc",
            "page": 1,
            "pageSize": 10,
        },
        headers={
            "content-type": "application/json",
            "x-request-id": "request-rls",
        },
        timeout=2.0,
    )


def test_list_tasks_posts_to_ax_services_task_list_endpoint() -> None:
    """Task list requests use the sidecar TypeScript list endpoint."""

    session = MagicMock()
    session.post.return_value = make_response(payload={"tasks": []})
    client = AxServicesClient(AxServicesConfig(), session=session)

    result = client.list_tasks(
        {
            "contractVersion": "task-list.v1",
            "filters": [],
            "selectColumns": ["id", "task_name"],
            "orderDirection": "asc",
            "page": 1,
            "pageSize": 10,
        },
        request_id="request-tasks",
    )

    assert result.ok is True
    assert result.payload == {"tasks": []}
    session.post.assert_called_once_with(
        "http://127.0.0.1:5010/mcp/tasks/list",
        json={
            "contractVersion": "task-list.v1",
            "filters": [],
            "selectColumns": ["id", "task_name"],
            "orderDirection": "asc",
            "page": 1,
            "pageSize": 10,
        },
        headers={
            "content-type": "application/json",
            "x-request-id": "request-tasks",
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

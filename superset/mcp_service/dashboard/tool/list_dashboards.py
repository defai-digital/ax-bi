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

"""
List dashboards FastMCP tool (Advanced with metadata cache control)

This module contains the FastMCP tool for listing dashboards using
advanced filtering with clear, unambiguous request schema and metadata cache control.
"""

import logging
from typing import Any, TYPE_CHECKING

from fastmcp import Context
from flask import current_app
from superset_core.mcp.decorators import tool, ToolAnnotations

if TYPE_CHECKING:
    from superset.models.dashboard import Dashboard

from superset import is_feature_enabled
from superset.mcp_service.dashboard.schemas import (
    DashboardFilter,
    DashboardInfo,
    DashboardList,
    ListDashboardsRequest,
    serialize_dashboard_object,
)
from superset.mcp_service.mcp_core import (
    ModelListCore,
    request_or_default,
    to_zero_based_page,
)
from superset.mcp_service.system.schemas import PaginationInfo
from superset.mcp_service.utils import sanitize_for_llm_context
from superset.mcp_service.utils.logging_utils import mcp_event_log_context
from superset.mcp_service.utils.response_utils import (
    dump_model_with_select_columns,
    finalize_list_response,
)
from superset.runtime_modernization.ax_services import (
    AxServicesClient,
    AxServicesConfig,
    AxServicesResponse,
)
from superset.runtime_modernization.measurement import measure_runtime_candidate
from superset.runtime_modernization.shadow import (
    execute_with_shadow,
    ShadowMismatchReport,
)

logger = logging.getLogger(__name__)

# Minimal defaults for reduced token usage - users can request more via select_columns
DEFAULT_DASHBOARD_COLUMNS = [
    "id",
    "dashboard_title",
    "slug",
    "description",
    "certified_by",
    "certification_details",
    "url",
    "changed_on",
    "changed_on_humanized",
]

SORTABLE_DASHBOARD_COLUMNS = [
    "id",
    "dashboard_title",
    "slug",
    "published",
    "changed_on",
    "created_on",
]

_DEFAULT_LIST_DASHBOARDS_REQUEST = ListDashboardsRequest()
_DASHBOARD_LIST_CONTRACT_VERSION = "dashboard-list.v1"


def _dashboard_list_request_payload(request: ListDashboardsRequest) -> dict[str, Any]:
    """Build an ax-services dashboard list request payload."""

    return {
        "contractVersion": _DASHBOARD_LIST_CONTRACT_VERSION,
        "filters": [filter_.model_dump(mode="json") for filter_ in request.filters],
        "selectColumns": list(request.select_columns),
        "search": request.search,
        "orderColumn": request.order_column,
        "orderDirection": request.order_direction,
        "page": request.page,
        "pageSize": request.page_size,
        "createdByMe": request.created_by_me,
        "ownedByMe": request.owned_by_me,
    }


def _ax_services_dashboard_list_candidate(
    request: ListDashboardsRequest,
) -> AxServicesResponse:
    """Run the TypeScript sidecar dashboard list candidate."""

    client = AxServicesClient(AxServicesConfig.from_mapping(current_app.config))
    return client.list_dashboards(_dashboard_list_request_payload(request))


def _dashboard_info_from_ax_services(payload: dict[str, Any]) -> DashboardInfo | None:
    """Convert one valid ax-services dashboard item to the MCP dashboard schema."""

    dashboard_id = payload.get("id")
    if not isinstance(dashboard_id, int):
        return None

    dashboard = DashboardInfo(
        id=dashboard_id,
        dashboard_title=_optional_string(payload.get("dashboardTitle")),
        slug=payload.get("slug") if isinstance(payload.get("slug"), str) else None,
        description=_optional_string(payload.get("description")),
        certified_by=_optional_string(payload.get("certifiedBy")),
        certification_details=_optional_string(payload.get("certificationDetails")),
        published=payload.get("published")
        if isinstance(payload.get("published"), bool)
        else None,
        uuid=payload.get("uuid") if isinstance(payload.get("uuid"), str) else None,
        url=payload.get("url") if isinstance(payload.get("url"), str) else None,
        changed_on=payload.get("changedOn")
        if isinstance(payload.get("changedOn"), str)
        else None,
        changed_on_humanized=payload.get("changedOnHumanized")
        if isinstance(payload.get("changedOnHumanized"), str)
        else None,
    )
    return _sanitize_ax_services_dashboard_info(dashboard)


def _optional_string(value: Any) -> str | None:
    """Return a string value or None."""

    return value if isinstance(value, str) else None


def _sanitize_ax_services_dashboard_info(dashboard: DashboardInfo) -> DashboardInfo:
    """Apply MCP LLM-context sanitization to sidecar dashboard fields."""

    payload = dashboard.model_dump(mode="python")
    for field_name in (
        "dashboard_title",
        "description",
        "certified_by",
        "certification_details",
    ):
        payload[field_name] = sanitize_for_llm_context(
            payload.get(field_name),
            field_path=(field_name,),
        )
    return DashboardInfo(**payload)


def _dashboard_list_from_ax_services_response(
    response: AxServicesResponse,
) -> dict[str, Any] | None:
    """Convert a valid ax-services dashboard list response to the MCP schema."""

    payload = response.payload or {}
    if (
        not response.ok
        or payload.get("contractVersion") != _DASHBOARD_LIST_CONTRACT_VERSION
    ):
        return None

    raw_dashboards = payload.get("dashboards")
    if not isinstance(raw_dashboards, list):
        return None

    dashboards = []
    for raw_dashboard in raw_dashboards:
        if not isinstance(raw_dashboard, dict):
            return None
        dashboard = _dashboard_info_from_ax_services(raw_dashboard)
        if dashboard is None:
            return None
        dashboards.append(dashboard)

    count = payload.get("count")
    total_count = payload.get("totalCount")
    page = payload.get("page")
    page_size = payload.get("pageSize")
    total_pages = payload.get("totalPages")
    has_next = payload.get("hasNext")
    has_previous = payload.get("hasPrevious")
    columns_requested = payload.get("columnsRequested")
    columns_loaded = payload.get("columnsLoaded")
    if (
        not isinstance(count, int)
        or not isinstance(total_count, int)
        or not isinstance(page, int)
        or not isinstance(page_size, int)
        or not isinstance(total_pages, int)
        or not isinstance(has_next, bool)
        or not isinstance(has_previous, bool)
        or not _is_string_list(columns_requested)
        or not _is_string_list(columns_loaded)
    ):
        return None

    dashboard_list = DashboardList(
        dashboards=dashboards,
        count=count,
        total_count=total_count,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        has_next=has_next,
        has_previous=has_previous,
        columns_requested=columns_requested,
        columns_loaded=columns_loaded,
        columns_available=[],
        sortable_columns=SORTABLE_DASHBOARD_COLUMNS,
        filters_applied=[],
        pagination=PaginationInfo(
            page=page,
            page_size=page_size,
            total_count=total_count,
            total_pages=total_pages,
            has_next=has_next,
            has_previous=has_previous,
        ),
    )
    return dump_model_with_select_columns(dashboard_list, columns_requested)


def _is_string_list(value: Any) -> bool:
    """Return whether a value is a list of strings."""

    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def _dashboard_keys_from_mcp_response(response: dict[str, Any]) -> list[int]:
    """Return dashboard IDs from an MCP dashboard list response."""

    dashboards = response.get("dashboards")
    if not isinstance(dashboards, list):
        return []
    return [
        dashboard["id"]
        for dashboard in dashboards
        if isinstance(dashboard, dict) and isinstance(dashboard.get("id"), int)
    ]


def _dashboard_keys_from_ax_services_response(
    response: AxServicesResponse,
) -> list[int]:
    """Return dashboard IDs from an ax-services dashboard list response."""

    payload = response.payload or {}
    dashboards = payload.get("dashboards") if isinstance(payload, dict) else None
    if not isinstance(dashboards, list):
        return []
    return [
        dashboard["id"]
        for dashboard in dashboards
        if isinstance(dashboard, dict) and isinstance(dashboard.get("id"), int)
    ]


def _dashboard_list_shadow_matches(
    authoritative: dict[str, Any],
    candidate: AxServicesResponse,
) -> bool:
    """Compare Python and TypeScript dashboard list outputs by ID order."""

    return candidate.ok and _dashboard_keys_from_mcp_response(
        authoritative
    ) == _dashboard_keys_from_ax_services_response(candidate)


def _summarize_dashboard_list_response(response: dict[str, Any]) -> dict[str, object]:
    """Summarize Python dashboard list results for shadow mismatch reports."""

    return {
        "count": len(_dashboard_keys_from_mcp_response(response)),
        "ids": _dashboard_keys_from_mcp_response(response),
    }


def _summarize_ax_services_dashboard_list_response(
    response: AxServicesResponse,
) -> dict[str, object]:
    """Summarize ax-services dashboard list results for shadow mismatch reports."""

    payload = response.payload or {}
    return {
        "ok": response.ok,
        "status_code": response.status_code,
        "contract_version": payload.get("contractVersion")
        if isinstance(payload, dict)
        else None,
        "count": len(_dashboard_keys_from_ax_services_response(response)),
        "ids": _dashboard_keys_from_ax_services_response(response),
        "error": response.error,
    }


def _report_dashboard_list_shadow_mismatch(report: ShadowMismatchReport) -> None:
    """Log a compact dashboard list shadow mismatch report."""

    logger.warning(
        "Runtime modernization dashboard list shadow mismatch: %s",
        report.to_dict(),
    )


def _dashboard_list_shadow_enabled() -> bool:
    """Return whether dashboard listing should shadow through ax-services."""

    return is_feature_enabled("RUNTIME_SHADOW_EXECUTION") and is_feature_enabled(
        "TS_MCP_ORCHESTRATION"
    )


def _dashboard_list_serving_enabled() -> bool:
    """Return whether dashboard listing should be served through ax-services."""

    return is_feature_enabled("TS_MCP_ORCHESTRATION") and is_feature_enabled(
        "TS_DASHBOARD_LIST_SERVING"
    )


def _record_dashboard_list_metric(metric: str) -> None:
    """Record a dashboard-list migration metric."""

    current_app.config["STATS_LOGGER"].incr(
        f"runtime_modernization.mcp_orchestration.list_dashboards.{metric}"
    )


@tool(
    tags=["core"],
    class_permission_name="Dashboard",
    annotations=ToolAnnotations(
        title="List dashboards",
        readOnlyHint=True,
        destructiveHint=False,
    ),
)
async def list_dashboards(
    request: ListDashboardsRequest | None = None,
    ctx: Context = None,
) -> DashboardList | dict[str, Any]:
    """List dashboards with filtering and search. Returns dashboard metadata
    including title, slug, URL, and last modified time. Use select_columns to
    request additional fields.

    **IMPORTANT**: All parameters must be wrapped in a ``request`` object.
    Do NOT pass ``search``, ``page``, ``page_size``, etc. as top-level
    keyword arguments — they will be rejected. Use the ``request`` wrapper::

        # Correct usage
        list_dashboards(request={"search": "sales", "page": 1, "page_size": 10})
        list_dashboards(request={"filters": [{"col": "dashboard_title", "opr": "sw", "value": "exec"}]})
        list_dashboards()  # no arguments returns first page with defaults

        # Wrong — causes pydantic validation errors
        list_dashboards(search="sales", page=1)  # DO NOT DO THIS

    Valid filter columns for ``filters[].col``:
        ``dashboard_title``, ``published``, ``favorite``,
        ``created_by_fk``, ``changed_by_fk``

    Sortable columns for ``order_column``:
        ``id``, ``dashboard_title``, ``slug``, ``published``,
        ``changed_on``, ``created_on``

    To filter by a person (e.g. "dashboards Maxime is working on"), do NOT pass
    the name as the search parameter — search matches titles and slugs only.
    Instead, call find_users to resolve the name to a user ID, then pass it as
    a filter: filters=[{"col": "created_by_fk", "opr": "eq", "value": <id>}]
    (or "changed_by_fk" for "last modified by").
    """
    request = request_or_default(request, _DEFAULT_LIST_DASHBOARDS_REQUEST)

    with measure_runtime_candidate(
        "mcp_orchestration",
        "list_dashboards",
        current_app.config["STATS_LOGGER"],
    ):
        if _dashboard_list_serving_enabled():
            candidate_response = _ax_services_dashboard_list_candidate(request)
            candidate_dashboards = _dashboard_list_from_ax_services_response(
                candidate_response,
            )
            if candidate_dashboards is not None:
                _record_dashboard_list_metric("served_candidate")
                return candidate_dashboards

            _record_dashboard_list_metric("fallback")
            return await _list_dashboards_python(request, ctx)

        python_response = await _list_dashboards_python(request, ctx)
        return execute_with_shadow(
            area="mcp_orchestration",
            operation="list_dashboards",
            authoritative=lambda: python_response,
            candidate=lambda: _ax_services_dashboard_list_candidate(request),
            compare=_dashboard_list_shadow_matches,
            stats_logger=current_app.config["STATS_LOGGER"],
            shadow_enabled=_dashboard_list_shadow_enabled(),
            report_mismatch=_report_dashboard_list_shadow_mismatch,
            summarize_authoritative=_summarize_dashboard_list_response,
            summarize_candidate=_summarize_ax_services_dashboard_list_response,
        )


async def _list_dashboards_python(
    request: ListDashboardsRequest,
    ctx: Context,
) -> dict[str, Any]:
    """Run the authoritative Python dashboard list path."""

    await ctx.info(
        "Listing dashboards: page=%s, page_size=%s, search=%s"
        % (
            request.page,
            request.page_size,
            request.search,
        )
    )
    await ctx.debug(
        "Dashboard listing filters: filters=%s, order_column=%s, order_direction=%s"
        % (
            len(request.filters),
            request.order_column,
            request.order_direction,
        )
    )

    from superset.daos.dashboard import DashboardDAO
    from superset.mcp_service.common.schema_discovery import (
        DASHBOARD_SORTABLE_COLUMNS,
        get_all_column_names,
        get_dashboard_columns,
    )

    all_columns = get_all_column_names(get_dashboard_columns())

    def _serialize_dashboard(
        obj: "Dashboard | None", cols: list[str] | None
    ) -> DashboardInfo | None:
        """Serialize dashboard object (field filtering handled by model_serializer)."""
        return serialize_dashboard_object(obj)

    tool = ModelListCore(
        dao_class=DashboardDAO,
        output_schema=DashboardInfo,
        item_serializer=_serialize_dashboard,
        filter_type=DashboardFilter,
        default_columns=DEFAULT_DASHBOARD_COLUMNS,
        search_columns=[
            "dashboard_title",
            "slug",
            "uuid",
        ],
        list_field_name="dashboards",
        output_list_schema=DashboardList,
        all_columns=all_columns,
        sortable_columns=DASHBOARD_SORTABLE_COLUMNS,
        logger=logger,
    )

    with mcp_event_log_context(action="mcp.list_dashboards.query"):
        result = tool.run_tool(
            filters=request.filters,
            search=request.search,
            select_columns=request.select_columns,
            order_column=request.order_column,
            order_direction=request.order_direction,
            page=to_zero_based_page(request.page),
            page_size=request.page_size,
            created_by_me=request.created_by_me,
            owned_by_me=request.owned_by_me,
        )
    return await finalize_list_response(result, "dashboards", "Dashboards", ctx)

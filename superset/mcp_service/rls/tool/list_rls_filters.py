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
List RLS filters FastMCP tool.
"""

import logging
from typing import Any

from fastmcp import Context
from flask import current_app
from superset_core.mcp.decorators import tool, ToolAnnotations

from superset import is_feature_enabled
from superset.mcp_service.mcp_core import (
    ModelListCore,
    request_or_default,
    to_zero_based_page,
)
from superset.mcp_service.privacy import USER_DIRECTORY_FIELDS
from superset.mcp_service.rls.schemas import (
    ALL_RLS_COLUMNS,
    DEFAULT_RLS_COLUMNS,
    ListRlsFiltersRequest,
    RlsColumnFilter,
    RlsFilterError,
    RlsFilterInfo,
    RlsFilterList,
    serialize_rls_filter_object,
    SORTABLE_RLS_COLUMNS,
)
from superset.mcp_service.system.schemas import PaginationInfo
from superset.mcp_service.utils.logging_utils import mcp_event_log_context
from superset.mcp_service.utils.response_utils import dump_model_with_select_columns
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

_DEFAULT_LIST_RLS_FILTERS_REQUEST = ListRlsFiltersRequest()
_RLS_LIST_CONTRACT_VERSION = "rls-list.v1"


def _rls_list_request_payload(request: ListRlsFiltersRequest) -> dict[str, Any]:
    """Build an ax-services RLS filter list request payload."""

    return {
        "contractVersion": _RLS_LIST_CONTRACT_VERSION,
        "filters": [filter_.model_dump(mode="json") for filter_ in request.filters],
        "selectColumns": list(request.select_columns),
        "search": request.search,
        "orderColumn": request.order_column,
        "orderDirection": request.order_direction,
        "page": request.page,
        "pageSize": request.page_size,
    }


def _ax_services_rls_list_candidate(
    request: ListRlsFiltersRequest,
) -> AxServicesResponse:
    """Run the TypeScript sidecar RLS filter list candidate."""

    client = AxServicesClient(AxServicesConfig.from_mapping(current_app.config))
    return client.list_rls_filters(_rls_list_request_payload(request))


def _optional_string(value: Any) -> str | None:
    """Return a string value or None."""

    return value if isinstance(value, str) else None


def _optional_integer(value: Any) -> int | None:
    """Return an integer value, excluding booleans."""

    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _rls_table_ref_from_ax_services(payload: dict[str, Any]) -> dict[str, Any] | None:
    """Convert one valid ax-services RLS table ref to the MCP schema."""

    table_ref = {
        "id": _optional_integer(payload.get("id")),
        "table_name": _optional_string(payload.get("tableName")),
    }
    return table_ref if any(value is not None for value in table_ref.values()) else None


def _rls_role_ref_from_ax_services(payload: dict[str, Any]) -> dict[str, Any] | None:
    """Convert one valid ax-services RLS role ref to the MCP schema."""

    role_ref = {
        "id": _optional_integer(payload.get("id")),
        "name": _optional_string(payload.get("name")),
    }
    return role_ref if any(value is not None for value in role_ref.values()) else None


def _rls_filter_from_ax_services(payload: dict[str, Any]) -> RlsFilterInfo | None:
    """Convert one valid ax-services RLS filter item to the MCP schema."""

    filter_id = payload.get("id")
    if not isinstance(filter_id, int):
        return None

    raw_tables = payload.get("tables")
    if raw_tables is not None and not isinstance(raw_tables, list):
        return None
    raw_roles = payload.get("roles")
    if raw_roles is not None and not isinstance(raw_roles, list):
        return None

    tables = []
    for raw_table in raw_tables or []:
        if not isinstance(raw_table, dict):
            return None
        table = _rls_table_ref_from_ax_services(raw_table)
        if table is None:
            return None
        tables.append(table)

    roles = []
    for raw_role in raw_roles or []:
        if not isinstance(raw_role, dict):
            return None
        role = _rls_role_ref_from_ax_services(raw_role)
        if role is None:
            return None
        roles.append(role)

    return RlsFilterInfo.model_validate(
        {
            "id": filter_id,
            "name": _optional_string(payload.get("name")),
            "filter_type": _optional_string(payload.get("filterType")),
            "tables": tables if raw_tables is not None else None,
            "roles": roles if raw_roles is not None else None,
            "clause": _optional_string(payload.get("clause")),
            "group_key": _optional_string(payload.get("groupKey")),
            "changed_on": _optional_string(payload.get("changedOn")),
        }
    )


def _is_string_list(value: Any) -> bool:
    """Return whether a value is a list of strings."""

    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def _rls_list_from_ax_services_response(
    response: AxServicesResponse,
) -> dict[str, Any] | None:
    """Convert a valid ax-services RLS filter list response to the MCP schema."""

    payload = response.payload or {}
    if not response.ok or payload.get("contractVersion") != _RLS_LIST_CONTRACT_VERSION:
        return None
    if payload.get("warnings"):
        return None

    raw_rls_filters = payload.get("rlsFilters")
    if not isinstance(raw_rls_filters, list):
        return None

    rls_filters = []
    for raw_filter in raw_rls_filters:
        if not isinstance(raw_filter, dict):
            return None
        rls_filter = _rls_filter_from_ax_services(raw_filter)
        if rls_filter is None:
            return None
        rls_filters.append(rls_filter)

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

    rls_list = RlsFilterList(
        rls_filters=rls_filters,
        count=count,
        total_count=total_count,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        has_next=has_next,
        has_previous=has_previous,
        columns_requested=columns_requested,
        columns_loaded=columns_loaded,
        columns_available=ALL_RLS_COLUMNS,
        sortable_columns=SORTABLE_RLS_COLUMNS,
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
    return dump_model_with_select_columns(
        rls_list,
        columns_requested,
        by_alias=True,
    )


def _rls_keys_from_mcp_response(response: dict[str, Any]) -> list[int]:
    """Return RLS filter IDs from an MCP RLS filter list response."""

    rls_filters = response.get("rls_filters")
    if not isinstance(rls_filters, list):
        return []
    return [
        rls_filter["id"]
        for rls_filter in rls_filters
        if isinstance(rls_filter, dict) and isinstance(rls_filter.get("id"), int)
    ]


def _rls_keys_from_ax_services_response(response: AxServicesResponse) -> list[int]:
    """Return RLS filter IDs from an ax-services RLS filter list response."""

    payload = response.payload or {}
    rls_filters = payload.get("rlsFilters") if isinstance(payload, dict) else None
    if not isinstance(rls_filters, list):
        return []
    return [
        rls_filter["id"]
        for rls_filter in rls_filters
        if isinstance(rls_filter, dict) and isinstance(rls_filter.get("id"), int)
    ]


def _rls_list_shadow_matches(
    authoritative: dict[str, Any],
    candidate: AxServicesResponse,
) -> bool:
    """Compare Python and TypeScript RLS filter list outputs by ID order."""

    return candidate.ok and _rls_keys_from_mcp_response(
        authoritative
    ) == _rls_keys_from_ax_services_response(candidate)


def _summarize_rls_list_response(response: dict[str, Any]) -> dict[str, object]:
    """Summarize Python RLS filter list results for shadow mismatch reports."""

    return {
        "count": len(_rls_keys_from_mcp_response(response)),
        "ids": _rls_keys_from_mcp_response(response),
    }


def _summarize_ax_services_rls_list_response(
    response: AxServicesResponse,
) -> dict[str, object]:
    """Summarize ax-services RLS filter list results for shadow mismatch reports."""

    payload = response.payload or {}
    return {
        "ok": response.ok,
        "status_code": response.status_code,
        "contract_version": payload.get("contractVersion")
        if isinstance(payload, dict)
        else None,
        "count": len(_rls_keys_from_ax_services_response(response)),
        "ids": _rls_keys_from_ax_services_response(response),
        "error": response.error,
    }


def _rls_list_shadow_mismatch(report: ShadowMismatchReport) -> None:
    """Log a compact RLS filter list shadow mismatch report."""

    logger.warning(
        "Runtime modernization RLS filter list shadow mismatch: %s",
        report.to_dict(),
    )


def _rls_list_shadow_enabled() -> bool:
    """Return whether RLS filter listing should shadow through ax-services."""

    return is_feature_enabled("RUNTIME_SHADOW_EXECUTION") and is_feature_enabled(
        "TS_MCP_ORCHESTRATION"
    )


def _rls_list_serving_enabled() -> bool:
    """Return whether RLS filter listing should be served through ax-services."""

    return is_feature_enabled("TS_MCP_ORCHESTRATION") and is_feature_enabled(
        "TS_RLS_FILTER_LIST_SERVING"
    )


def _record_rls_list_metric(metric: str) -> None:
    """Record an RLS-filter-list migration metric."""

    current_app.config["STATS_LOGGER"].incr(
        f"runtime_modernization.mcp_orchestration.list_rls_filters.{metric}"
    )


@tool(
    tags=["core"],
    class_permission_name="Row Level Security",
    annotations=ToolAnnotations(
        title="List RLS filters",
        readOnlyHint=True,
        destructiveHint=False,
    ),
)
async def list_rls_filters(
    request: ListRlsFiltersRequest | None = None,
    ctx: Context | None = None,
) -> RlsFilterList | RlsFilterError | dict[str, Any]:
    """List row level security filters. Requires admin access.

    Returns RLS filter metadata including name, filter type, tables, roles, and clause.

    Sortable columns for order_column: id, name, filter_type, changed_on
    """
    if ctx is None:
        raise RuntimeError("FastMCP context is required for list_rls_filters")

    request = request_or_default(request, _DEFAULT_LIST_RLS_FILTERS_REQUEST)

    with measure_runtime_candidate(
        "mcp_orchestration",
        "list_rls_filters",
        current_app.config["STATS_LOGGER"],
    ):
        if _rls_list_serving_enabled():
            candidate_response = _ax_services_rls_list_candidate(request)
            candidate_rls_filters = _rls_list_from_ax_services_response(
                candidate_response
            )
            if candidate_rls_filters is not None:
                _record_rls_list_metric("served_candidate")
                return candidate_rls_filters

            _record_rls_list_metric("fallback")
            return await _list_rls_filters_python(request, ctx)

        python_response = await _list_rls_filters_python(request, ctx)
        return execute_with_shadow(
            area="mcp_orchestration",
            operation="list_rls_filters",
            authoritative=lambda: python_response,
            candidate=lambda: _ax_services_rls_list_candidate(request),
            compare=_rls_list_shadow_matches,
            stats_logger=current_app.config["STATS_LOGGER"],
            shadow_enabled=_rls_list_shadow_enabled(),
            report_mismatch=_rls_list_shadow_mismatch,
            summarize_authoritative=_summarize_rls_list_response,
            summarize_candidate=_summarize_ax_services_rls_list_response,
        )


async def _list_rls_filters_python(
    request: ListRlsFiltersRequest,
    ctx: Context,
) -> dict[str, Any]:
    """Run the authoritative Python RLS filter list path."""

    await ctx.info(
        "Listing RLS filters: page=%s, page_size=%s, search=%s"
        % (request.page, request.page_size, request.search)
    )

    try:
        from superset.daos.security import RLSDAO

        def _serialize_rls_filter(obj: object, cols: list[str]) -> RlsFilterInfo | None:
            return serialize_rls_filter_object(obj)

        list_tool = ModelListCore(
            dao_class=RLSDAO,
            output_schema=RlsFilterInfo,
            item_serializer=_serialize_rls_filter,
            filter_type=RlsColumnFilter,
            default_columns=DEFAULT_RLS_COLUMNS,
            search_columns=["name"],
            list_field_name="rls_filters",
            output_list_schema=RlsFilterList,
            all_columns=ALL_RLS_COLUMNS,
            sortable_columns=SORTABLE_RLS_COLUMNS,
            logger=logger,
        )

        # Strip USER_DIRECTORY_FIELDS (e.g. 'roles') before handing off to
        # run_tool, which would raise ValueError if all requested columns are
        # privacy-filtered. Roles are restored in the model_dump context below.
        run_select_columns: list[str] | None = None
        if request.select_columns:
            filtered = [
                c for c in request.select_columns if c not in USER_DIRECTORY_FIELDS
            ]
            run_select_columns = filtered or None

        with mcp_event_log_context(action="mcp.list_rls_filters.query"):
            result = list_tool.run_tool(
                filters=request.filters,
                search=request.search,
                select_columns=run_select_columns,
                order_column=request.order_column,
                order_direction=request.order_direction,
                page=to_zero_based_page(request.page),
                page_size=request.page_size,
            )

        await ctx.info(
            "RLS filters listed: count=%s, total_count=%s"
            % (len(result.rls_filters), result.total_count)
        )

        # Build column selection using ALL_RLS_COLUMNS as the source of truth,
        # bypassing the USER_DIRECTORY_FIELDS privacy filter applied by
        # ModelListCore. 'roles' in an RLS filter is which roles the filter
        # applies to — core filter data — not user-directory metadata (like
        # dashboard.roles, which exposes who has access to the resource).
        if request.select_columns:
            columns_to_filter = [
                c for c in request.select_columns if c in ALL_RLS_COLUMNS
            ]
            if not columns_to_filter:
                columns_to_filter = list(DEFAULT_RLS_COLUMNS)
        else:
            columns_to_filter = list(DEFAULT_RLS_COLUMNS)

        with mcp_event_log_context(action="mcp.list_rls_filters.serialization"):
            return dump_model_with_select_columns(result, columns_to_filter)

    except Exception as e:
        await ctx.error(
            "RLS filter listing failed: error=%s, error_type=%s"
            % (str(e), type(e).__name__)
        )
        raise

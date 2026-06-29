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

"""List roles FastMCP tool."""

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
from superset.mcp_service.role.schemas import (
    DEFAULT_ROLE_COLUMNS,
    ListRolesRequest,
    ROLE_ALL_COLUMNS,
    ROLE_SORTABLE_COLUMNS,
    RoleError,
    RoleFilter,
    RoleInfo,
    RoleList,
    serialize_role_object,
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

_DEFAULT_LIST_ROLES_REQUEST = ListRolesRequest()
_ROLE_LIST_CONTRACT_VERSION = "role-list.v1"


def _role_list_request_payload(request: ListRolesRequest) -> dict[str, Any]:
    """Build an ax-services role list request payload."""

    return {
        "contractVersion": _ROLE_LIST_CONTRACT_VERSION,
        "filters": [filter_.model_dump(mode="json") for filter_ in request.filters],
        "selectColumns": list(request.select_columns),
        "search": request.search,
        "orderColumn": request.order_column,
        "orderDirection": request.order_direction,
        "page": request.page,
        "pageSize": request.page_size,
    }


def _ax_services_role_list_candidate(
    request: ListRolesRequest,
) -> AxServicesResponse:
    """Run the TypeScript sidecar role list candidate."""

    client = AxServicesClient(AxServicesConfig.from_mapping(current_app.config))
    return client.list_roles(_role_list_request_payload(request))


def _optional_string(value: Any) -> str | None:
    """Return a string value or None."""

    return value if isinstance(value, str) else None


def _role_info_from_ax_services(payload: dict[str, Any]) -> RoleInfo | None:
    """Convert one valid ax-services role item to the MCP schema."""

    role_id = payload.get("id")
    if not isinstance(role_id, int):
        return None

    return RoleInfo(
        id=role_id,
        name=sanitize_for_llm_context(
            _optional_string(payload.get("name")),
            field_path=("name",),
        ),
    )


def _is_string_list(value: Any) -> bool:
    """Return whether a value is a list of strings."""

    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def _role_list_from_ax_services_response(
    response: AxServicesResponse,
) -> dict[str, Any] | None:
    """Convert a valid ax-services role list response to the MCP schema."""

    payload = response.payload or {}
    if not response.ok or payload.get("contractVersion") != _ROLE_LIST_CONTRACT_VERSION:
        return None

    raw_roles = payload.get("roles")
    if not isinstance(raw_roles, list):
        return None

    roles = []
    for raw_role in raw_roles:
        if not isinstance(raw_role, dict):
            return None
        role = _role_info_from_ax_services(raw_role)
        if role is None:
            return None
        roles.append(role)

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

    role_list = RoleList(
        roles=roles,
        count=count,
        total_count=total_count,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        has_next=has_next,
        has_previous=has_previous,
        columns_requested=columns_requested,
        columns_loaded=columns_loaded,
        columns_available=ROLE_ALL_COLUMNS,
        sortable_columns=ROLE_SORTABLE_COLUMNS,
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
    return dump_model_with_select_columns(role_list, columns_requested)


def _role_keys_from_mcp_response(response: dict[str, Any]) -> list[int]:
    """Return role IDs from an MCP role list response."""

    roles = response.get("roles")
    if not isinstance(roles, list):
        return []
    return [
        role["id"]
        for role in roles
        if isinstance(role, dict) and isinstance(role.get("id"), int)
    ]


def _role_keys_from_ax_services_response(response: AxServicesResponse) -> list[int]:
    """Return role IDs from an ax-services role list response."""

    payload = response.payload or {}
    roles = payload.get("roles") if isinstance(payload, dict) else None
    if not isinstance(roles, list):
        return []
    return [
        role["id"]
        for role in roles
        if isinstance(role, dict) and isinstance(role.get("id"), int)
    ]


def _role_list_shadow_matches(
    authoritative: dict[str, Any],
    candidate: AxServicesResponse,
) -> bool:
    """Compare Python and TypeScript role list outputs by ID order."""

    return candidate.ok and _role_keys_from_mcp_response(
        authoritative
    ) == _role_keys_from_ax_services_response(candidate)


def _summarize_role_list_response(response: dict[str, Any]) -> dict[str, object]:
    """Summarize Python role list results for shadow mismatch reports."""

    return {
        "count": len(_role_keys_from_mcp_response(response)),
        "ids": _role_keys_from_mcp_response(response),
    }


def _summarize_ax_services_role_list_response(
    response: AxServicesResponse,
) -> dict[str, object]:
    """Summarize ax-services role list results for shadow mismatch reports."""

    payload = response.payload or {}
    return {
        "ok": response.ok,
        "status_code": response.status_code,
        "contract_version": payload.get("contractVersion")
        if isinstance(payload, dict)
        else None,
        "count": len(_role_keys_from_ax_services_response(response)),
        "ids": _role_keys_from_ax_services_response(response),
        "error": response.error,
    }


def _role_list_shadow_mismatch(report: ShadowMismatchReport) -> None:
    """Log a compact role list shadow mismatch report."""

    logger.warning(
        "Runtime modernization role list shadow mismatch: %s",
        report.to_dict(),
    )


def _role_list_shadow_enabled() -> bool:
    """Return whether role listing should shadow through ax-services."""

    return is_feature_enabled("RUNTIME_SHADOW_EXECUTION") and is_feature_enabled(
        "TS_MCP_ORCHESTRATION"
    )


def _role_list_serving_enabled() -> bool:
    """Return whether role listing should be served through ax-services."""

    return is_feature_enabled("TS_MCP_ORCHESTRATION") and is_feature_enabled(
        "TS_ROLE_LIST_SERVING"
    )


def _record_role_list_metric(metric: str) -> None:
    """Record a role-list migration metric."""

    current_app.config["STATS_LOGGER"].incr(
        f"runtime_modernization.mcp_orchestration.list_roles.{metric}"
    )


@tool(
    tags=["core"],
    class_permission_name="Role",
    annotations=ToolAnnotations(
        title="List roles",
        readOnlyHint=True,
        destructiveHint=False,
    ),
)
async def list_roles(
    request: ListRolesRequest | None = None,
    ctx: Context | None = None,
) -> RoleList | RoleError | dict[str, Any]:
    """List roles with filtering and search. Admin only.

    Returns role metadata including id and name.

    Sortable columns for order_column: id, name
    """
    if ctx is None:
        raise RuntimeError("FastMCP context is required for list_roles")

    request = request_or_default(request, _DEFAULT_LIST_ROLES_REQUEST)

    with measure_runtime_candidate(
        "mcp_orchestration",
        "list_roles",
        current_app.config["STATS_LOGGER"],
    ):
        if _role_list_serving_enabled():
            candidate_response = _ax_services_role_list_candidate(request)
            candidate_roles = _role_list_from_ax_services_response(candidate_response)
            if candidate_roles is not None:
                _record_role_list_metric("served_candidate")
                return candidate_roles

            _record_role_list_metric("fallback")
            return await _list_roles_python(request, ctx)

        python_response = await _list_roles_python(request, ctx)
        return execute_with_shadow(
            area="mcp_orchestration",
            operation="list_roles",
            authoritative=lambda: python_response,
            candidate=lambda: _ax_services_role_list_candidate(request),
            compare=_role_list_shadow_matches,
            stats_logger=current_app.config["STATS_LOGGER"],
            shadow_enabled=_role_list_shadow_enabled(),
            report_mismatch=_role_list_shadow_mismatch,
            summarize_authoritative=_summarize_role_list_response,
            summarize_candidate=_summarize_ax_services_role_list_response,
        )


async def _list_roles_python(
    request: ListRolesRequest,
    ctx: Context | None,
) -> dict[str, Any]:
    """Run the authoritative Python role list path."""

    if ctx is not None:
        await ctx.info(
            "Listing roles: page=%s, page_size=%s, search=%s"
            % (request.page, request.page_size, request.search)
        )
        await ctx.debug(
            "Role listing parameters: filters=%s, order_column=%s, order_direction=%s"
            % (request.filters, request.order_column, request.order_direction)
        )

    try:
        from superset.daos.role import RoleDAO

        def _serialize_role(obj: Any, _cols: list[str] | None) -> RoleInfo | None:
            return serialize_role_object(obj)

        list_tool = ModelListCore(
            dao_class=RoleDAO,
            output_schema=RoleInfo,
            item_serializer=_serialize_role,
            filter_type=RoleFilter,
            default_columns=DEFAULT_ROLE_COLUMNS,
            search_columns=["name"],
            list_field_name="roles",
            output_list_schema=RoleList,
            all_columns=ROLE_ALL_COLUMNS,
            sortable_columns=ROLE_SORTABLE_COLUMNS,
            logger=logger,
        )

        with mcp_event_log_context(action="mcp.list_roles.query"):
            result = list_tool.run_tool(
                filters=request.filters,
                search=request.search,
                select_columns=request.select_columns,
                order_column=request.order_column or "id",
                order_direction=request.order_direction,
                page=to_zero_based_page(request.page),
                page_size=request.page_size,
            )

        return await finalize_list_response(result, "roles", "Roles", ctx)

    except Exception as e:
        if ctx is not None:
            await ctx.error(
                "Role listing failed: page=%s, page_size=%s, error=%s, error_type=%s"
                % (request.page, request.page_size, str(e), type(e).__name__)
            )
        raise

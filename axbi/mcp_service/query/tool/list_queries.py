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
List queries FastMCP tool

This module contains the FastMCP tool for listing SQL query history
with filtering, search, and pagination.
"""

import logging
from typing import Any

from axbi_core.mcp.decorators import tool, ToolAnnotations
from fastmcp import Context
from flask import current_app

from axbi import is_feature_enabled
from axbi.mcp_service.mcp_core import (
    ModelListCore,
    request_or_default,
    to_zero_based_page,
)
from axbi.mcp_service.query.schemas import (
    ALL_QUERY_COLUMNS,
    DEFAULT_QUERY_COLUMNS,
    ListQueriesRequest,
    QueryError,
    QueryFilter,
    QueryInfo,
    QueryList,
    serialize_query_object,
    SORTABLE_QUERY_COLUMNS,
)
from axbi.mcp_service.system.schemas import PaginationInfo
from axbi.mcp_service.utils.logging_utils import mcp_event_log_context
from axbi.mcp_service.utils.response_utils import (
    dump_model_with_select_columns,
    finalize_list_response,
)
from axbi.runtime_modernization.ax_services import (
    AxServicesClient,
    AxServicesConfig,
    AxServicesResponse,
)
from axbi.runtime_modernization.measurement import measure_runtime_candidate
from axbi.runtime_modernization.shadow import (
    execute_with_shadow,
    ShadowMismatchReport,
)

logger = logging.getLogger(__name__)

_DEFAULT_LIST_QUERIES_REQUEST = ListQueriesRequest()
_QUERY_LIST_CONTRACT_VERSION = "query-list.v1"


def _query_list_request_payload(request: ListQueriesRequest) -> dict[str, Any]:
    """Build an ax-services query list request payload."""

    return {
        "contractVersion": _QUERY_LIST_CONTRACT_VERSION,
        "filters": [filter_.model_dump(mode="json") for filter_ in request.filters],
        "selectColumns": list(request.select_columns),
        "search": request.search,
        "orderColumn": request.order_column,
        "orderDirection": request.order_direction,
        "page": request.page,
        "pageSize": request.page_size,
    }


def _ax_services_query_list_candidate(
    request: ListQueriesRequest,
) -> AxServicesResponse:
    """Run the TypeScript sidecar query list candidate."""

    client = AxServicesClient(AxServicesConfig.from_mapping(current_app.config))
    return client.list_queries(_query_list_request_payload(request))


def _optional_string(value: Any) -> str | None:
    """Return a string value or None."""

    return value if isinstance(value, str) else None


def _optional_number(value: Any) -> int | float | None:
    """Return an int or float value, excluding booleans."""

    return (
        value
        if isinstance(value, int | float) and not isinstance(value, bool)
        else None
    )


def _optional_integer(value: Any) -> int | None:
    """Return an integer value, excluding booleans."""

    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _query_info_from_ax_services(payload: dict[str, Any]) -> QueryInfo | None:
    """Convert one valid ax-services query item to the MCP schema."""

    query_id = payload.get("id")
    if not isinstance(query_id, int):
        return None

    return QueryInfo.model_validate(
        {
            "id": query_id,
            "sql": _optional_string(payload.get("sql")),
            "executed_sql": _optional_string(payload.get("executedSql")),
            "status": _optional_string(payload.get("status")),
            "start_time": _optional_number(payload.get("startTime")),
            "end_time": _optional_number(payload.get("endTime")),
            "rows": _optional_integer(payload.get("rows")),
            "database_id": _optional_integer(payload.get("databaseId")),
            "schema": _optional_string(payload.get("schema")),
            "catalog": _optional_string(payload.get("catalog")),
            "tab_name": _optional_string(payload.get("tabName")),
            "error_message": _optional_string(payload.get("errorMessage")),
            "client_id": _optional_string(payload.get("clientId")),
            "limit": _optional_integer(payload.get("limit")),
            "progress": _optional_integer(payload.get("progress")),
            "changed_on": _optional_string(payload.get("changedOn")),
            "user_id": _optional_integer(payload.get("userId")),
        }
    )


def _is_string_list(value: Any) -> bool:
    """Return whether a value is a list of strings."""

    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def _query_list_from_ax_services_response(
    response: AxServicesResponse,
) -> dict[str, Any] | None:
    """Convert a valid ax-services query list response to the MCP schema."""

    payload = response.payload or {}
    if (
        not response.ok
        or payload.get("contractVersion") != _QUERY_LIST_CONTRACT_VERSION
    ):
        return None
    if payload.get("warnings"):
        return None

    raw_queries = payload.get("queries")
    if not isinstance(raw_queries, list):
        return None

    queries = []
    for raw_query in raw_queries:
        if not isinstance(raw_query, dict):
            return None
        query = _query_info_from_ax_services(raw_query)
        if query is None:
            return None
        queries.append(query)

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

    query_list = QueryList(
        queries=queries,
        count=count,
        total_count=total_count,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        has_next=has_next,
        has_previous=has_previous,
        columns_requested=columns_requested,
        columns_loaded=columns_loaded,
        columns_available=ALL_QUERY_COLUMNS,
        sortable_columns=SORTABLE_QUERY_COLUMNS,
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
        query_list,
        columns_requested,
        by_alias=True,
    )


def _query_keys_from_mcp_response(response: dict[str, Any]) -> list[int]:
    """Return query IDs from an MCP query list response."""

    queries = response.get("queries")
    if not isinstance(queries, list):
        return []
    return [
        query["id"]
        for query in queries
        if isinstance(query, dict) and isinstance(query.get("id"), int)
    ]


def _query_keys_from_ax_services_response(response: AxServicesResponse) -> list[int]:
    """Return query IDs from an ax-services query list response."""

    payload = response.payload or {}
    queries = payload.get("queries") if isinstance(payload, dict) else None
    if not isinstance(queries, list):
        return []
    return [
        query["id"]
        for query in queries
        if isinstance(query, dict) and isinstance(query.get("id"), int)
    ]


def _query_list_shadow_matches(
    authoritative: dict[str, Any],
    candidate: AxServicesResponse,
) -> bool:
    """Compare Python and TypeScript query list outputs by ID order."""

    return (
        "queries" in authoritative
        and candidate.ok
        and _query_keys_from_mcp_response(authoritative)
        == _query_keys_from_ax_services_response(candidate)
    )


def _summarize_query_list_response(response: dict[str, Any]) -> dict[str, object]:
    """Summarize Python query list results for shadow mismatch reports."""

    return {
        "count": len(_query_keys_from_mcp_response(response)),
        "ids": _query_keys_from_mcp_response(response),
    }


def _summarize_ax_services_query_list_response(
    response: AxServicesResponse,
) -> dict[str, object]:
    """Summarize ax-services query list results for shadow mismatch reports."""

    payload = response.payload or {}
    return {
        "ok": response.ok,
        "status_code": response.status_code,
        "contract_version": payload.get("contractVersion")
        if isinstance(payload, dict)
        else None,
        "count": len(_query_keys_from_ax_services_response(response)),
        "ids": _query_keys_from_ax_services_response(response),
        "error": response.error,
    }


def _query_list_shadow_mismatch(report: ShadowMismatchReport) -> None:
    """Log a compact query list shadow mismatch report."""

    logger.warning(
        "Runtime modernization query list shadow mismatch: %s",
        report.to_dict(),
    )


def _query_list_shadow_enabled() -> bool:
    """Return whether query listing should shadow through ax-services."""

    return is_feature_enabled("RUNTIME_SHADOW_EXECUTION") and is_feature_enabled(
        "TS_MCP_ORCHESTRATION"
    )


def _query_list_serving_enabled() -> bool:
    """Return whether query listing should be served through ax-services."""

    return is_feature_enabled("TS_MCP_ORCHESTRATION") and is_feature_enabled(
        "TS_QUERY_LIST_SERVING"
    )


def _record_query_list_metric(metric: str) -> None:
    """Record a query-list migration metric."""

    current_app.config["STATS_LOGGER"].incr(
        f"runtime_modernization.mcp_orchestration.list_queries.{metric}"
    )


@tool(
    tags=["core"],
    class_permission_name="Query",
    annotations=ToolAnnotations(
        title="List queries",
        readOnlyHint=True,
        destructiveHint=False,
    ),
)
async def list_queries(
    request: ListQueriesRequest | None = None,
    ctx: Context | None = None,
) -> QueryList | QueryError | dict[str, Any]:
    """List SQL query history with filtering and search.

    Returns recent queries executed by the current user (or all queries for
    admins), including SQL text, status, timing, and database information.
    Results are ordered by changed_on descending by default (start_time is not
    always populated for all query records).

    Sortable columns for order_column: id, start_time, end_time, status,
    database_id, changed_on
    """
    if ctx is None:
        raise RuntimeError("FastMCP context is required for list_queries")

    request = request_or_default(request, _DEFAULT_LIST_QUERIES_REQUEST)

    with measure_runtime_candidate(
        "mcp_orchestration",
        "list_queries",
        current_app.config["STATS_LOGGER"],
    ):
        if _query_list_serving_enabled():
            candidate_response = _ax_services_query_list_candidate(request)
            candidate_queries = _query_list_from_ax_services_response(
                candidate_response
            )
            if candidate_queries is not None:
                _record_query_list_metric("served_candidate")
                return candidate_queries

            _record_query_list_metric("fallback")
            return await _list_queries_python(request, ctx)

        python_response = await _list_queries_python(request, ctx)
        return execute_with_shadow(
            area="mcp_orchestration",
            operation="list_queries",
            authoritative=lambda: python_response,
            candidate=lambda: _ax_services_query_list_candidate(request),
            compare=_query_list_shadow_matches,
            stats_logger=current_app.config["STATS_LOGGER"],
            shadow_enabled=_query_list_shadow_enabled(),
            report_mismatch=_query_list_shadow_mismatch,
            summarize_authoritative=_summarize_query_list_response,
            summarize_candidate=_summarize_ax_services_query_list_response,
        )


async def _list_queries_python(
    request: ListQueriesRequest,
    ctx: Context,
) -> dict[str, Any]:
    """Run the authoritative Python query list path."""

    await ctx.info(
        f"Listing queries: page={request.page}, "
        f"page_size={request.page_size}, search={request.search}"
    )
    await ctx.debug(
        f"Query listing parameters: filters={request.filters}, "
        f"order_column={request.order_column}, "
        f"order_direction={request.order_direction}, "
        f"select_columns={request.select_columns}"
    )

    try:
        from axbi.daos.query import QueryDAO

        def _serialize_query(obj: object, cols: list[str] | None) -> QueryInfo | None:
            return serialize_query_object(obj)

        list_tool = ModelListCore(
            dao_class=QueryDAO,
            output_schema=QueryInfo,
            item_serializer=_serialize_query,
            filter_type=QueryFilter,
            default_columns=DEFAULT_QUERY_COLUMNS,
            search_columns=["tab_name", "sql"],
            list_field_name="queries",
            output_list_schema=QueryList,
            all_columns=ALL_QUERY_COLUMNS,
            sortable_columns=SORTABLE_QUERY_COLUMNS,
            logger=logger,
        )

        with mcp_event_log_context(action="mcp.list_queries.query"):
            result = list_tool.run_tool(
                filters=request.filters,
                search=request.search,
                select_columns=request.select_columns,
                order_column=request.order_column or "changed_on",
                order_direction=request.order_direction,
                page=to_zero_based_page(request.page),
                page_size=request.page_size,
            )

        return await finalize_list_response(
            result, "queries", "Queries", ctx, by_alias=True
        )

    except Exception as e:
        await ctx.error(
            f"Query listing failed: page={request.page}, "
            f"page_size={request.page_size}, error={str(e)}, "
            f"error_type={type(e).__name__}"
        )
        raise

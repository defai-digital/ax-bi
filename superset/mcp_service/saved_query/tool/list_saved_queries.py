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
List saved queries FastMCP tool

This module contains the FastMCP tool for listing saved SQL queries
with filtering, search, and pagination.
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
from superset.mcp_service.saved_query.schemas import (
    ALL_SAVED_QUERY_COLUMNS,
    DEFAULT_SAVED_QUERY_COLUMNS,
    ListSavedQueriesRequest,
    SavedQueryError,
    SavedQueryFilter,
    SavedQueryInfo,
    SavedQueryList,
    serialize_saved_query_object,
    SORTABLE_SAVED_QUERY_COLUMNS,
)
from superset.mcp_service.system.schemas import PaginationInfo
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

_DEFAULT_LIST_SAVED_QUERIES_REQUEST = ListSavedQueriesRequest()
_SAVED_QUERY_LIST_CONTRACT_VERSION = "saved-query-list.v1"


def _saved_query_list_request_payload(
    request: ListSavedQueriesRequest,
) -> dict[str, Any]:
    """Build an ax-services saved query list request payload."""

    return {
        "contractVersion": _SAVED_QUERY_LIST_CONTRACT_VERSION,
        "filters": [filter_.model_dump(mode="json") for filter_ in request.filters],
        "selectColumns": list(request.select_columns),
        "search": request.search,
        "orderColumn": request.order_column,
        "orderDirection": request.order_direction,
        "page": request.page,
        "pageSize": request.page_size,
    }


def _ax_services_saved_query_list_candidate(
    request: ListSavedQueriesRequest,
) -> AxServicesResponse:
    """Run the TypeScript sidecar saved query list candidate."""

    client = AxServicesClient(AxServicesConfig.from_mapping(current_app.config))
    return client.list_saved_queries(_saved_query_list_request_payload(request))


def _optional_string(value: Any) -> str | None:
    """Return a string value or None."""

    return value if isinstance(value, str) else None


def _optional_int(value: Any) -> int | None:
    """Return an int value or None."""

    return value if isinstance(value, int) else None


def _saved_query_info_from_ax_services(
    payload: dict[str, Any],
) -> SavedQueryInfo | None:
    """Convert one valid ax-services saved query item to the MCP schema."""

    saved_query_id = payload.get("id")
    if not isinstance(saved_query_id, int):
        return None

    return SavedQueryInfo(
        id=saved_query_id,
        uuid=_optional_string(payload.get("uuid")),
        label=_optional_string(payload.get("label")),
        sql=_optional_string(payload.get("sql")),
        db_id=_optional_int(payload.get("dbId")),
        schema=_optional_string(payload.get("schema")),
        catalog=_optional_string(payload.get("catalog")),
        description=_optional_string(payload.get("description")),
        changed_on=_optional_string(payload.get("changedOn")),
        created_on=_optional_string(payload.get("createdOn")),
        last_run=_optional_string(payload.get("lastRun")),
    )


def _is_string_list(value: Any) -> bool:
    """Return whether a value is a list of strings."""

    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def _saved_query_list_from_ax_services_response(
    response: AxServicesResponse,
) -> dict[str, Any] | None:
    """Convert a valid ax-services saved query list response to the MCP schema."""

    payload = response.payload or {}
    if (
        not response.ok
        or payload.get("contractVersion") != _SAVED_QUERY_LIST_CONTRACT_VERSION
    ):
        return None

    raw_saved_queries = payload.get("savedQueries")
    if not isinstance(raw_saved_queries, list):
        return None

    saved_queries = []
    for raw_saved_query in raw_saved_queries:
        if not isinstance(raw_saved_query, dict):
            return None
        saved_query = _saved_query_info_from_ax_services(raw_saved_query)
        if saved_query is None:
            return None
        saved_queries.append(saved_query)

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

    saved_query_list = SavedQueryList(
        saved_queries=saved_queries,
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
        sortable_columns=SORTABLE_SAVED_QUERY_COLUMNS,
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
        saved_query_list,
        columns_requested,
        by_alias=True,
    )


def _saved_query_keys_from_mcp_response(response: dict[str, Any]) -> list[int]:
    """Return saved query IDs from an MCP saved query list response."""

    saved_queries = response.get("saved_queries")
    if not isinstance(saved_queries, list):
        return []
    return [
        saved_query["id"]
        for saved_query in saved_queries
        if isinstance(saved_query, dict) and isinstance(saved_query.get("id"), int)
    ]


def _saved_query_keys_from_ax_services_response(
    response: AxServicesResponse,
) -> list[int]:
    """Return saved query IDs from an ax-services saved query list response."""

    payload = response.payload or {}
    saved_queries = payload.get("savedQueries") if isinstance(payload, dict) else None
    if not isinstance(saved_queries, list):
        return []
    return [
        saved_query["id"]
        for saved_query in saved_queries
        if isinstance(saved_query, dict) and isinstance(saved_query.get("id"), int)
    ]


def _saved_query_list_shadow_matches(
    authoritative: dict[str, Any],
    candidate: AxServicesResponse,
) -> bool:
    """Compare Python and TypeScript saved query list outputs by ID order."""

    return candidate.ok and _saved_query_keys_from_mcp_response(
        authoritative
    ) == _saved_query_keys_from_ax_services_response(candidate)


def _summarize_saved_query_list_response(
    response: dict[str, Any],
) -> dict[str, object]:
    """Summarize Python saved query list results for shadow mismatch reports."""

    return {
        "count": len(_saved_query_keys_from_mcp_response(response)),
        "ids": _saved_query_keys_from_mcp_response(response),
    }


def _summarize_ax_services_saved_query_list_response(
    response: AxServicesResponse,
) -> dict[str, object]:
    """Summarize ax-services saved query results for shadow mismatch reports."""

    payload = response.payload or {}
    return {
        "ok": response.ok,
        "status_code": response.status_code,
        "contract_version": payload.get("contractVersion")
        if isinstance(payload, dict)
        else None,
        "count": len(_saved_query_keys_from_ax_services_response(response)),
        "ids": _saved_query_keys_from_ax_services_response(response),
        "error": response.error,
    }


def _report_saved_query_list_shadow_mismatch(report: ShadowMismatchReport) -> None:
    """Log a compact saved query list shadow mismatch report."""

    logger.warning(
        "Runtime modernization saved query list shadow mismatch: %s",
        report.to_dict(),
    )


def _saved_query_list_shadow_enabled() -> bool:
    """Return whether saved query listing should shadow through ax-services."""

    return is_feature_enabled("RUNTIME_SHADOW_EXECUTION") and is_feature_enabled(
        "TS_MCP_ORCHESTRATION"
    )


def _saved_query_list_serving_enabled() -> bool:
    """Return whether saved query listing should be served through ax-services."""

    return is_feature_enabled("TS_MCP_ORCHESTRATION") and is_feature_enabled(
        "TS_SAVED_QUERY_LIST_SERVING"
    )


def _record_saved_query_list_metric(metric: str) -> None:
    """Record a saved-query-list migration metric."""

    current_app.config["STATS_LOGGER"].incr(
        f"runtime_modernization.mcp_orchestration.list_saved_queries.{metric}"
    )


@tool(
    tags=["core"],
    class_permission_name="SavedQuery",
    annotations=ToolAnnotations(
        title="List saved queries",
        readOnlyHint=True,
        destructiveHint=False,
    ),
)
async def list_saved_queries(
    request: ListSavedQueriesRequest | None = None,
    ctx: Context | None = None,
) -> SavedQueryList | SavedQueryError | dict[str, Any]:
    """List saved SQL queries with filtering and search.

    Returns saved queries owned by the current user, including label, SQL,
    database ID, and schema.

    Sortable columns for order_column: id, label, db_id, schema,
    changed_on, created_on
    """
    if ctx is None:
        raise RuntimeError("FastMCP context is required for list_saved_queries")

    request = request_or_default(request, _DEFAULT_LIST_SAVED_QUERIES_REQUEST)

    with measure_runtime_candidate(
        "mcp_orchestration",
        "list_saved_queries",
        current_app.config["STATS_LOGGER"],
    ):
        if _saved_query_list_serving_enabled():
            candidate_response = _ax_services_saved_query_list_candidate(request)
            candidate_saved_queries = _saved_query_list_from_ax_services_response(
                candidate_response,
            )
            if candidate_saved_queries is not None:
                _record_saved_query_list_metric("served_candidate")
                return candidate_saved_queries

            _record_saved_query_list_metric("fallback")
            return await _list_saved_queries_python(request, ctx)

        python_response = await _list_saved_queries_python(request, ctx)
        return execute_with_shadow(
            area="mcp_orchestration",
            operation="list_saved_queries",
            authoritative=lambda: python_response,
            candidate=lambda: _ax_services_saved_query_list_candidate(request),
            compare=_saved_query_list_shadow_matches,
            stats_logger=current_app.config["STATS_LOGGER"],
            shadow_enabled=_saved_query_list_shadow_enabled(),
            report_mismatch=_report_saved_query_list_shadow_mismatch,
            summarize_authoritative=_summarize_saved_query_list_response,
            summarize_candidate=_summarize_ax_services_saved_query_list_response,
        )


async def _list_saved_queries_python(
    request: ListSavedQueriesRequest,
    ctx: Context,
) -> dict[str, Any]:
    """Run the authoritative Python saved query list path."""

    await ctx.info(
        f"Listing saved queries: page={request.page}, "
        f"page_size={request.page_size}, search={request.search}"
    )
    await ctx.debug(
        f"Saved query listing parameters: filters={request.filters}, "
        f"order_column={request.order_column}, "
        f"order_direction={request.order_direction}, "
        f"select_columns={request.select_columns}"
    )

    try:
        from superset.daos.query import SavedQueryDAO

        def _serialize_saved_query(
            obj: object, cols: list[str] | None
        ) -> SavedQueryInfo | None:
            return serialize_saved_query_object(obj)

        list_tool = ModelListCore(
            dao_class=SavedQueryDAO,
            output_schema=SavedQueryInfo,
            item_serializer=_serialize_saved_query,
            filter_type=SavedQueryFilter,
            default_columns=DEFAULT_SAVED_QUERY_COLUMNS,
            search_columns=["label", "description", "sql"],
            list_field_name="saved_queries",
            output_list_schema=SavedQueryList,
            all_columns=ALL_SAVED_QUERY_COLUMNS,
            sortable_columns=SORTABLE_SAVED_QUERY_COLUMNS,
            logger=logger,
        )

        with mcp_event_log_context(action="mcp.list_saved_queries.query"):
            result = list_tool.run_tool(
                filters=request.filters,
                search=request.search,
                select_columns=request.select_columns,
                order_column=request.order_column,
                order_direction=request.order_direction,
                page=to_zero_based_page(request.page),
                page_size=request.page_size,
            )

        return await finalize_list_response(
            result, "saved_queries", "Saved queries", ctx, by_alias=True
        )

    except Exception as e:
        await ctx.error(
            f"Saved query listing failed: page={request.page}, "
            f"page_size={request.page_size}, error={str(e)}, "
            f"error_type={type(e).__name__}"
        )
        raise

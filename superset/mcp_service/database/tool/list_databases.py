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
List databases FastMCP tool (Advanced with metadata cache control)

This module contains the FastMCP tool for listing databases using
advanced filtering with clear, unambiguous request schema and metadata cache control.
"""

import logging
from typing import Any, TYPE_CHECKING

from fastmcp import Context
from flask import current_app
from superset_core.mcp.decorators import tool, ToolAnnotations

if TYPE_CHECKING:
    from superset.models.core import Database

from superset import is_feature_enabled
from superset.mcp_service.database.schemas import (
    DatabaseError,
    DatabaseFilter,
    DatabaseInfo,
    DatabaseList,
    ListDatabasesRequest,
    serialize_database_object,
)
from superset.mcp_service.mcp_core import (
    ModelListCore,
    request_or_default,
    to_zero_based_page,
)
from superset.mcp_service.privacy import (
    DATA_MODEL_METADATA_ERROR_TYPE,
    requires_data_model_metadata_access,
    user_can_view_data_model_metadata,
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

_DEFAULT_LIST_DATABASES_REQUEST = ListDatabasesRequest()
_DATABASE_LIST_CONTRACT_VERSION = "database-list.v1"
_SORTABLE_DATABASE_COLUMNS = ["id", "database_name", "changed_on", "created_on"]


def _database_list_request_payload(request: ListDatabasesRequest) -> dict[str, Any]:
    """Build an ax-services database list request payload."""

    return {
        "contractVersion": _DATABASE_LIST_CONTRACT_VERSION,
        "filters": [filter_.model_dump(mode="json") for filter_ in request.filters],
        "selectColumns": list(request.select_columns),
        "search": request.search,
        "orderColumn": request.order_column,
        "orderDirection": request.order_direction,
        "page": request.page,
        "pageSize": request.page_size,
        "createdByMe": request.created_by_me,
    }


def _ax_services_database_list_candidate(
    request: ListDatabasesRequest,
) -> AxServicesResponse:
    """Run the TypeScript sidecar database list candidate."""

    client = AxServicesClient(AxServicesConfig.from_mapping(current_app.config))
    return client.list_databases(_database_list_request_payload(request))


def _optional_string(value: Any) -> str | None:
    """Return a string value or None."""

    return value if isinstance(value, str) else None


def _optional_bool(value: Any) -> bool | None:
    """Return a bool value or None."""

    return value if isinstance(value, bool) else None


def _optional_int(value: Any) -> int | None:
    """Return an int value or None."""

    return value if isinstance(value, int) else None


def _optional_dict(value: Any) -> dict[str, Any] | None:
    """Return a dict value or None."""

    return value if isinstance(value, dict) else None


def _database_info_from_ax_services(payload: dict[str, Any]) -> DatabaseInfo | None:
    """Convert one valid ax-services database item to the MCP database schema."""

    database_id = payload.get("id")
    if not isinstance(database_id, int):
        return None

    return DatabaseInfo(
        id=database_id,
        uuid=_optional_string(payload.get("uuid")),
        database_name=_optional_string(payload.get("databaseName")),
        backend=_optional_string(payload.get("backend")),
        expose_in_sqllab=_optional_bool(payload.get("exposeInSqllab")),
        allow_ctas=_optional_bool(payload.get("allowCtas")),
        allow_cvas=_optional_bool(payload.get("allowCvas")),
        allow_dml=_optional_bool(payload.get("allowDml")),
        allow_file_upload=_optional_bool(payload.get("allowFileUpload")),
        allow_run_async=_optional_bool(payload.get("allowRunAsync")),
        cache_timeout=_optional_int(payload.get("cacheTimeout")),
        configuration_method=_optional_string(payload.get("configurationMethod")),
        force_ctas_schema=_optional_string(payload.get("forceCtasSchema")),
        impersonate_user=_optional_bool(payload.get("impersonateUser")),
        is_managed_externally=_optional_bool(payload.get("isManagedExternally")),
        external_url=_optional_string(payload.get("externalUrl")),
        extra=_optional_dict(payload.get("extra")),
        changed_on=_optional_string(payload.get("changedOn")),
        changed_on_humanized=_optional_string(payload.get("changedOnHumanized")),
        created_on=_optional_string(payload.get("createdOn")),
        created_on_humanized=_optional_string(payload.get("createdOnHumanized")),
    )


def _is_string_list(value: Any) -> bool:
    """Return whether a value is a list of strings."""

    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def _database_list_from_ax_services_response(
    response: AxServicesResponse,
) -> dict[str, Any] | None:
    """Convert a valid ax-services database list response to the MCP schema."""

    payload = response.payload or {}
    if (
        not response.ok
        or payload.get("contractVersion") != _DATABASE_LIST_CONTRACT_VERSION
    ):
        return None

    raw_databases = payload.get("databases")
    if not isinstance(raw_databases, list):
        return None

    databases = []
    for raw_database in raw_databases:
        if not isinstance(raw_database, dict):
            return None
        database = _database_info_from_ax_services(raw_database)
        if database is None:
            return None
        databases.append(database)

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

    database_list = DatabaseList(
        databases=databases,
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
        sortable_columns=_SORTABLE_DATABASE_COLUMNS,
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
    return dump_model_with_select_columns(database_list, columns_requested)


def _database_keys_from_mcp_response(response: dict[str, Any]) -> list[int]:
    """Return database IDs from an MCP database list response."""

    databases = response.get("databases")
    if not isinstance(databases, list):
        return []
    return [
        database["id"]
        for database in databases
        if isinstance(database, dict) and isinstance(database.get("id"), int)
    ]


def _database_keys_from_ax_services_response(
    response: AxServicesResponse,
) -> list[int]:
    """Return database IDs from an ax-services database list response."""

    payload = response.payload or {}
    databases = payload.get("databases") if isinstance(payload, dict) else None
    if not isinstance(databases, list):
        return []
    return [
        database["id"]
        for database in databases
        if isinstance(database, dict) and isinstance(database.get("id"), int)
    ]


def _database_list_shadow_matches(
    authoritative: dict[str, Any],
    candidate: AxServicesResponse,
) -> bool:
    """Compare Python and TypeScript database list outputs by ID order."""

    return candidate.ok and _database_keys_from_mcp_response(
        authoritative
    ) == _database_keys_from_ax_services_response(candidate)


def _summarize_database_list_response(response: dict[str, Any]) -> dict[str, object]:
    """Summarize Python database list results for shadow mismatch reports."""

    return {
        "count": len(_database_keys_from_mcp_response(response)),
        "ids": _database_keys_from_mcp_response(response),
    }


def _summarize_ax_services_database_list_response(
    response: AxServicesResponse,
) -> dict[str, object]:
    """Summarize ax-services database list results for shadow mismatch reports."""

    payload = response.payload or {}
    return {
        "ok": response.ok,
        "status_code": response.status_code,
        "contract_version": payload.get("contractVersion")
        if isinstance(payload, dict)
        else None,
        "count": len(_database_keys_from_ax_services_response(response)),
        "ids": _database_keys_from_ax_services_response(response),
        "error": response.error,
    }


def _report_database_list_shadow_mismatch(report: ShadowMismatchReport) -> None:
    """Log a compact database list shadow mismatch report."""

    logger.warning(
        "Runtime modernization database list shadow mismatch: %s",
        report.to_dict(),
    )


def _database_list_shadow_enabled() -> bool:
    """Return whether database listing should shadow through ax-services."""

    return is_feature_enabled("RUNTIME_SHADOW_EXECUTION") and is_feature_enabled(
        "TS_MCP_ORCHESTRATION"
    )


def _database_list_serving_enabled() -> bool:
    """Return whether database listing should be served through ax-services."""

    return is_feature_enabled("TS_MCP_ORCHESTRATION") and is_feature_enabled(
        "TS_DATABASE_LIST_SERVING"
    )


def _record_database_list_metric(metric: str) -> None:
    """Record a database-list migration metric."""

    current_app.config["STATS_LOGGER"].incr(
        f"runtime_modernization.mcp_orchestration.list_databases.{metric}"
    )


@tool(
    tags=["core"],
    class_permission_name="Database",
    annotations=ToolAnnotations(
        title="List databases",
        readOnlyHint=True,
        destructiveHint=False,
    ),
)
@requires_data_model_metadata_access
async def list_databases(
    request: ListDatabasesRequest | None = None,
    ctx: Context | None = None,
) -> DatabaseList | DatabaseError | dict[str, Any]:
    """List database connections with filtering and search.

    Returns database metadata including name, backend type, and permissions.

    Sortable columns for order_column: id, database_name, changed_on,
    created_on
    """
    if ctx is None:
        raise RuntimeError("FastMCP context is required for list_databases")

    request = request_or_default(request, _DEFAULT_LIST_DATABASES_REQUEST)

    await ctx.info(
        "Listing databases: page=%s, page_size=%s, search=%s"
        % (
            request.page,
            request.page_size,
            request.search,
        )
    )
    await ctx.debug(
        "Database listing parameters: filters=%s, order_column=%s, "
        "order_direction=%s, select_columns=%s"
        % (
            request.filters,
            request.order_column,
            request.order_direction,
            request.select_columns,
        )
    )
    await ctx.debug(
        "Metadata cache settings: use_cache=%s, refresh_metadata=%s, force_refresh=%s"
        % (
            request.use_cache,
            request.refresh_metadata,
            request.force_refresh,
        )
    )

    if not user_can_view_data_model_metadata():
        await ctx.warning("Database listing blocked by data-model privacy controls")
        return DatabaseError.create(
            error="You don't have permission to access database details for your role.",
            error_type=DATA_MODEL_METADATA_ERROR_TYPE,
        )

    with measure_runtime_candidate(
        "mcp_orchestration",
        "list_databases",
        current_app.config["STATS_LOGGER"],
    ):
        if _database_list_serving_enabled():
            candidate_response = _ax_services_database_list_candidate(request)
            candidate_databases = _database_list_from_ax_services_response(
                candidate_response,
            )
            if candidate_databases is not None:
                _record_database_list_metric("served_candidate")
                return candidate_databases

            _record_database_list_metric("fallback")
            return await _list_databases_python(request, ctx)

        python_response = await _list_databases_python(request, ctx)
        return execute_with_shadow(
            area="mcp_orchestration",
            operation="list_databases",
            authoritative=lambda: python_response,
            candidate=lambda: _ax_services_database_list_candidate(request),
            compare=_database_list_shadow_matches,
            stats_logger=current_app.config["STATS_LOGGER"],
            shadow_enabled=_database_list_shadow_enabled(),
            report_mismatch=_report_database_list_shadow_mismatch,
            summarize_authoritative=_summarize_database_list_response,
            summarize_candidate=_summarize_ax_services_database_list_response,
        )


async def _list_databases_python(
    request: ListDatabasesRequest,
    ctx: Context,
) -> dict[str, Any]:
    """Run the authoritative Python database list path."""

    try:
        from superset.daos.database import DatabaseDAO
        from superset.mcp_service.common.schema_discovery import (
            DATABASE_DEFAULT_COLUMNS,
            DATABASE_SORTABLE_COLUMNS,
            get_all_column_names,
            get_database_columns,
        )

        # Get all column names dynamically from the model
        all_columns = get_all_column_names(get_database_columns())

        def _serialize_database(
            obj: "Database | None", cols: list[str] | None
        ) -> DatabaseInfo | None:
            """Serialize database (filtering via model_serializer)."""
            return serialize_database_object(obj)

        # Create tool with standard serialization
        list_tool = ModelListCore(
            dao_class=DatabaseDAO,
            output_schema=DatabaseInfo,
            item_serializer=_serialize_database,
            filter_type=DatabaseFilter,
            default_columns=DATABASE_DEFAULT_COLUMNS,
            search_columns=["database_name"],
            list_field_name="databases",
            output_list_schema=DatabaseList,
            all_columns=all_columns,
            sortable_columns=DATABASE_SORTABLE_COLUMNS,
            logger=logger,
        )

        with mcp_event_log_context(action="mcp.list_databases.query"):
            result = list_tool.run_tool(
                filters=request.filters,
                search=request.search,
                select_columns=request.select_columns,
                order_column=request.order_column,
                order_direction=request.order_direction,
                page=to_zero_based_page(request.page),
                page_size=request.page_size,
                created_by_me=request.created_by_me,
            )

        return await finalize_list_response(result, "databases", "Databases", ctx)

    except Exception as e:
        await ctx.error(
            "Database listing failed: page=%s, page_size=%s, error=%s, error_type=%s"
            % (
                request.page,
                request.page_size,
                str(e),
                type(e).__name__,
            )
        )
        raise

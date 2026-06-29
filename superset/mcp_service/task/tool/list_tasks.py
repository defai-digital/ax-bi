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

"""List tasks MCP tool."""

import logging
from typing import Any

from fastmcp import Context
from flask import current_app
from superset_core.mcp.decorators import tool, ToolAnnotations

from superset import is_feature_enabled
from superset.daos.tasks import TaskDAO
from superset.mcp_service.mcp_core import (
    ModelListCore,
    request_or_default,
    to_zero_based_page,
)
from superset.mcp_service.system.schemas import PaginationInfo
from superset.mcp_service.task.schemas import (
    ALL_TASK_COLUMNS,
    DEFAULT_TASK_COLUMNS,
    ListTasksRequest,
    serialize_task_object,
    TASK_SORTABLE_COLUMNS,
    TaskColumnFilter,
    TaskError,
    TaskInfo,
    TaskList,
)
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

_DEFAULT_LIST_TASKS_REQUEST = ListTasksRequest()
_TASK_LIST_CONTRACT_VERSION = "task-list.v1"


def _task_list_request_payload(request: ListTasksRequest) -> dict[str, Any]:
    """Build an ax-services task list request payload."""

    return {
        "contractVersion": _TASK_LIST_CONTRACT_VERSION,
        "filters": [filter_.model_dump(mode="json") for filter_ in request.filters],
        "selectColumns": list(request.select_columns),
        "search": request.search,
        "orderColumn": request.order_column,
        "orderDirection": request.order_direction,
        "page": request.page,
        "pageSize": request.page_size,
    }


def _ax_services_task_list_candidate(request: ListTasksRequest) -> AxServicesResponse:
    """Run the TypeScript sidecar task list candidate."""

    client = AxServicesClient(AxServicesConfig.from_mapping(current_app.config))
    return client.list_tasks(_task_list_request_payload(request))


def _optional_string(value: Any) -> str | None:
    """Return a string value or None."""

    return value if isinstance(value, str) else None


def _task_info_from_ax_services(payload: dict[str, Any]) -> TaskInfo | None:
    """Convert one valid ax-services task item to the MCP schema."""

    task_id = payload.get("id")
    if not isinstance(task_id, int):
        return None

    task = TaskInfo(
        id=task_id,
        uuid=_optional_string(payload.get("uuid")),
        task_type=_optional_string(payload.get("taskType")),
        task_key=_optional_string(payload.get("taskKey")),
        task_name=_optional_string(payload.get("taskName")),
        status=_optional_string(payload.get("status")),
        scope=_optional_string(payload.get("scope")),
        changed_on=_optional_string(payload.get("changedOn")),
        created_on=_optional_string(payload.get("createdOn")),
    )
    task_payload = task.model_dump(mode="python")
    for field_name in ("task_key", "task_name"):
        task_payload[field_name] = sanitize_for_llm_context(
            task_payload.get(field_name),
            field_path=(field_name,),
        )
    return TaskInfo(**task_payload)


def _is_string_list(value: Any) -> bool:
    """Return whether a value is a list of strings."""

    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def _task_list_from_ax_services_response(
    response: AxServicesResponse,
) -> dict[str, Any] | None:
    """Convert a valid ax-services task list response to the MCP schema."""

    payload = response.payload or {}
    if not response.ok or payload.get("contractVersion") != _TASK_LIST_CONTRACT_VERSION:
        return None

    raw_tasks = payload.get("tasks")
    if not isinstance(raw_tasks, list):
        return None

    tasks = []
    for raw_task in raw_tasks:
        if not isinstance(raw_task, dict):
            return None
        task = _task_info_from_ax_services(raw_task)
        if task is None:
            return None
        tasks.append(task)

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

    task_list = TaskList(
        tasks=tasks,
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
        sortable_columns=TASK_SORTABLE_COLUMNS,
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
    return dump_model_with_select_columns(task_list, columns_requested)


def _task_keys_from_mcp_response(response: dict[str, Any]) -> list[int]:
    """Return task IDs from an MCP task list response."""

    tasks = response.get("tasks")
    if not isinstance(tasks, list):
        return []
    return [
        task["id"]
        for task in tasks
        if isinstance(task, dict) and isinstance(task.get("id"), int)
    ]


def _task_keys_from_ax_services_response(response: AxServicesResponse) -> list[int]:
    """Return task IDs from an ax-services task list response."""

    payload = response.payload or {}
    tasks = payload.get("tasks") if isinstance(payload, dict) else None
    if not isinstance(tasks, list):
        return []
    return [
        task["id"]
        for task in tasks
        if isinstance(task, dict) and isinstance(task.get("id"), int)
    ]


def _task_list_shadow_matches(
    authoritative: dict[str, Any],
    candidate: AxServicesResponse,
) -> bool:
    """Compare Python and TypeScript task list outputs by ID order."""

    return candidate.ok and _task_keys_from_mcp_response(
        authoritative
    ) == _task_keys_from_ax_services_response(candidate)


def _summarize_task_list_response(response: dict[str, Any]) -> dict[str, object]:
    """Summarize Python task list results for shadow mismatch reports."""

    return {
        "count": len(_task_keys_from_mcp_response(response)),
        "ids": _task_keys_from_mcp_response(response),
    }


def _summarize_ax_services_task_list_response(
    response: AxServicesResponse,
) -> dict[str, object]:
    """Summarize ax-services task list results for shadow mismatch reports."""

    payload = response.payload or {}
    return {
        "ok": response.ok,
        "status_code": response.status_code,
        "contract_version": payload.get("contractVersion")
        if isinstance(payload, dict)
        else None,
        "count": len(_task_keys_from_ax_services_response(response)),
        "ids": _task_keys_from_ax_services_response(response),
        "error": response.error,
    }


def _task_list_shadow_mismatch(report: ShadowMismatchReport) -> None:
    """Log a compact task list shadow mismatch report."""

    logger.warning(
        "Runtime modernization task list shadow mismatch: %s",
        report.to_dict(),
    )


def _task_list_shadow_enabled() -> bool:
    """Return whether task listing should shadow through ax-services."""

    return is_feature_enabled("RUNTIME_SHADOW_EXECUTION") and is_feature_enabled(
        "TS_MCP_ORCHESTRATION"
    )


def _task_list_serving_enabled() -> bool:
    """Return whether task listing should be served through ax-services."""

    return is_feature_enabled("TS_MCP_ORCHESTRATION") and is_feature_enabled(
        "TS_TASK_LIST_SERVING"
    )


def _record_task_list_metric(metric: str) -> None:
    """Record a task-list migration metric."""

    current_app.config["STATS_LOGGER"].incr(
        f"runtime_modernization.mcp_orchestration.list_tasks.{metric}"
    )


@tool(
    tags=["core"],
    class_permission_name="Task",
    annotations=ToolAnnotations(
        title="List tasks",
        readOnlyHint=True,
        destructiveHint=False,
    ),
)
async def list_tasks(
    request: ListTasksRequest | None = None,
    ctx: Context | None = None,
) -> TaskList | TaskError | dict[str, Any]:
    """List async tasks with filtering and pagination.

    Returns tasks visible to the current user. Non-admin users only see tasks
    they are subscribed to (task creators are auto-subscribed). Admins see all
    tasks.

    Sortable columns for order_column: task_type, scope, status, created_on, changed_on, started_at, ended_at
    Filter columns: task_type, status, scope
    Search columns (via search=): task_type, task_key, task_name, status, scope

    Common task_type values: sql_execution, thumbnail, report
    Common status values: pending, in_progress, success, failure, aborted
    Common scope values: private, shared, system
    """
    if ctx is None:
        raise RuntimeError("FastMCP context is required for list_tasks")

    request = request_or_default(request, _DEFAULT_LIST_TASKS_REQUEST)

    with measure_runtime_candidate(
        "mcp_orchestration",
        "list_tasks",
        current_app.config["STATS_LOGGER"],
    ):
        if _task_list_serving_enabled():
            candidate_response = _ax_services_task_list_candidate(request)
            candidate_tasks = _task_list_from_ax_services_response(candidate_response)
            if candidate_tasks is not None:
                _record_task_list_metric("served_candidate")
                return candidate_tasks

            _record_task_list_metric("fallback")
            return await _list_tasks_python(request, ctx)

        python_response = await _list_tasks_python(request, ctx)
        return execute_with_shadow(
            area="mcp_orchestration",
            operation="list_tasks",
            authoritative=lambda: python_response,
            candidate=lambda: _ax_services_task_list_candidate(request),
            compare=_task_list_shadow_matches,
            stats_logger=current_app.config["STATS_LOGGER"],
            shadow_enabled=_task_list_shadow_enabled(),
            report_mismatch=_task_list_shadow_mismatch,
            summarize_authoritative=_summarize_task_list_response,
            summarize_candidate=_summarize_ax_services_task_list_response,
        )


async def _list_tasks_python(
    request: ListTasksRequest,
    ctx: Context,
) -> dict[str, Any]:
    """Run the authoritative Python task list path."""

    await ctx.info(
        "Listing tasks: page=%s, page_size=%s" % (request.page, request.page_size)
    )
    await ctx.debug(
        "Task parameters: filters=%s, order_column=%s, order_direction=%s"
        % (request.filters, request.order_column, request.order_direction)
    )

    try:

        def _serialize(obj: object, cols: list[str] | None) -> TaskInfo | None:
            return serialize_task_object(obj)

        # TaskDAO.base_filter = TaskFilter automatically scopes results:
        # non-admins only see their subscribed tasks; admins see all.
        list_tool = ModelListCore(
            dao_class=TaskDAO,
            output_schema=TaskInfo,
            item_serializer=_serialize,
            filter_type=TaskColumnFilter,
            default_columns=DEFAULT_TASK_COLUMNS,
            search_columns=["task_type", "task_key", "task_name", "status", "scope"],
            list_field_name="tasks",
            output_list_schema=TaskList,
            all_columns=ALL_TASK_COLUMNS,
            sortable_columns=TASK_SORTABLE_COLUMNS,
            logger=logger,
        )

        with mcp_event_log_context(action="mcp.list_tasks.query"):
            result = list_tool.run_tool(
                filters=request.filters,
                search=request.search,
                select_columns=request.select_columns,
                order_column=request.order_column or "created_on",
                order_direction=request.order_direction,
                page=to_zero_based_page(request.page),
                page_size=request.page_size,
            )

        return await finalize_list_response(result, "tasks", "Tasks", ctx)

    except Exception as e:
        await ctx.error(
            "Task listing failed: page=%s, error=%s, error_type=%s"
            % (request.page, str(e), type(e).__name__)
        )
        raise

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

from fastmcp import Context
from superset_core.mcp.decorators import tool, ToolAnnotations

from superset.daos.tasks import TaskDAO
from superset.mcp_service.mcp_core import (
    ModelListCore,
    request_or_default,
    to_zero_based_page,
)
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
from superset.mcp_service.utils.logging_utils import mcp_event_log_context
from superset.mcp_service.utils.response_utils import finalize_list_response

logger = logging.getLogger(__name__)

_DEFAULT_LIST_TASKS_REQUEST = ListTasksRequest()


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
) -> TaskList | TaskError:
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

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

from fastmcp import Context
from superset_core.mcp.decorators import tool, ToolAnnotations

from superset.mcp_service.mcp_core import (
    ModelListCore,
    request_or_default,
    to_zero_based_page,
)
from superset.mcp_service.query.schemas import (
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
from superset.mcp_service.utils.logging_utils import mcp_event_log_context
from superset.mcp_service.utils.response_utils import finalize_list_response

logger = logging.getLogger(__name__)

_DEFAULT_LIST_QUERIES_REQUEST = ListQueriesRequest()


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
) -> QueryList | QueryError:
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

    await ctx.info(
        "Listing queries: page=%s, page_size=%s, search=%s"
        % (
            request.page,
            request.page_size,
            request.search,
        )
    )
    await ctx.debug(
        "Query listing parameters: filters=%s, order_column=%s, "
        "order_direction=%s, select_columns=%s"
        % (
            request.filters,
            request.order_column,
            request.order_direction,
            request.select_columns,
        )
    )

    try:
        from superset.daos.query import QueryDAO

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
            "Query listing failed: page=%s, page_size=%s, error=%s, error_type=%s"
            % (
                request.page,
                request.page_size,
                str(e),
                type(e).__name__,
            )
        )
        raise

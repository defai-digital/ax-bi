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
from typing import TYPE_CHECKING

from fastmcp import Context
from superset_core.mcp.decorators import tool, ToolAnnotations

if TYPE_CHECKING:
    from superset.models.core import Database

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
from superset.mcp_service.utils.logging_utils import mcp_event_log_context
from superset.mcp_service.utils.response_utils import finalize_list_response

logger = logging.getLogger(__name__)

_DEFAULT_LIST_DATABASES_REQUEST = ListDatabasesRequest()


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
) -> DatabaseList | DatabaseError:
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

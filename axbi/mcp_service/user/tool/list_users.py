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

"""List users FastMCP tool."""

import logging
from typing import Any

from axbi_core.mcp.decorators import tool, ToolAnnotations
from fastmcp import Context

from axbi.mcp_service.mcp_core import (
    ModelListCore,
    request_or_default,
    to_zero_based_page,
)
from axbi.mcp_service.privacy import user_can_view_data_model_metadata
from axbi.mcp_service.user.schemas import (
    DEFAULT_USER_COLUMNS,
    ListUsersRequest,
    serialize_user_object,
    USER_ALL_COLUMNS,
    USER_SORTABLE_COLUMNS,
    UserError,
    UserFilter,
    UserInfo,
    UserList,
)
from axbi.mcp_service.utils.logging_utils import mcp_event_log_context
from axbi.mcp_service.utils.response_utils import finalize_list_response

logger = logging.getLogger(__name__)

_DEFAULT_LIST_USERS_REQUEST = ListUsersRequest()


@tool(
    tags=["core"],
    class_permission_name="User",
    annotations=ToolAnnotations(
        title="List users",
        readOnlyHint=True,
        destructiveHint=False,
    ),
)
async def list_users(
    request: ListUsersRequest | None = None,
    ctx: Context | None = None,
) -> UserList | UserError:
    """List users with filtering and search. Admin only.

    Returns user metadata. Sensitive fields (email, roles) are only included
    when the caller has data model metadata access.

    Sortable columns for order_column: id, username, first_name, last_name,
    active, changed_on
    """
    if ctx is None:
        raise RuntimeError("FastMCP context is required for list_users")

    request = request_or_default(request, _DEFAULT_LIST_USERS_REQUEST)

    await ctx.info(
        f"Listing users: page={request.page}, page_size={request.page_size}, "
        f"search={request.search}"
    )
    await ctx.debug(
        f"User listing parameters: filters={request.filters}, "
        f"order_column={request.order_column}, "
        f"order_direction={request.order_direction}"
    )

    try:
        from axbi.daos.user import UserDAO

        can_view_sensitive = user_can_view_data_model_metadata()

        if not can_view_sensitive:
            await ctx.debug(
                "Sensitive fields (email, roles) will be redacted for this caller"
            )

        def _serialize_user(obj: Any, cols: list[str] | None) -> UserInfo | None:
            # Only load the roles relationship when it is in the loaded column set.
            # USER_DIRECTORY_FIELDS always strips roles in list context, so this
            # avoids a per-user N+1 lazy-load.
            include_roles = "roles" in (cols or [])
            return serialize_user_object(
                obj, include_sensitive=can_view_sensitive, include_roles=include_roles
            )

        list_tool = ModelListCore(
            dao_class=UserDAO,
            output_schema=UserInfo,
            item_serializer=_serialize_user,
            filter_type=UserFilter,
            default_columns=DEFAULT_USER_COLUMNS,
            search_columns=["username", "first_name", "last_name"],
            list_field_name="users",
            output_list_schema=UserList,
            all_columns=USER_ALL_COLUMNS,
            sortable_columns=USER_SORTABLE_COLUMNS,
            logger=logger,
        )

        with mcp_event_log_context(action="mcp.list_users.query"):
            result = list_tool.run_tool(
                filters=request.filters,
                search=request.search,
                select_columns=request.select_columns,
                order_column=request.order_column or "id",
                order_direction=request.order_direction,
                page=to_zero_based_page(request.page),
                page_size=request.page_size,
            )

        return await finalize_list_response(result, "users", "Users", ctx)

    except Exception as e:
        await ctx.error(
            f"User listing failed: page={request.page}, "
            f"page_size={request.page_size}, error={str(e)}, "
            f"error_type={type(e).__name__}"
        )
        raise

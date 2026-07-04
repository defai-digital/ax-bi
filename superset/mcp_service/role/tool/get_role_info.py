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

"""Get role info FastMCP tool."""

import logging

from fastmcp import Context
from superset_core.mcp.decorators import tool, ToolAnnotations

from superset.mcp_service.mcp_core import ModelGetInfoCore
from superset.mcp_service.role.schemas import (
    GetRoleInfoRequest,
    RoleError,
    RoleInfo,
    serialize_role_object,
)
from superset.mcp_service.utils.logging_utils import mcp_event_log_context

logger = logging.getLogger(__name__)


@tool(
    tags=["discovery"],
    class_permission_name="Role",
    annotations=ToolAnnotations(
        title="Get role info",
        readOnlyHint=True,
        destructiveHint=False,
    ),
)
async def get_role_info(
    request: GetRoleInfoRequest, ctx: Context
) -> RoleInfo | RoleError:
    """Get role details by ID. Admin only.

    Returns role metadata including id and name.

    Example usage:
    ```json
    {
        "identifier": 1
    }
    ```
    """
    await ctx.info(f"Retrieving role information: identifier={request.identifier}")

    try:
        from superset.daos.role import RoleDAO

        def _serializer(obj: object) -> RoleInfo | None:
            return serialize_role_object(obj, include_permissions=True)

        with mcp_event_log_context(action="mcp.get_role_info.lookup"):
            get_tool = ModelGetInfoCore(
                dao_class=RoleDAO,
                output_schema=RoleInfo,
                error_schema=RoleError,
                serializer=_serializer,
                supports_slug=False,
                logger=logger,
            )
            result = get_tool.run_tool(request.identifier)

        if isinstance(result, RoleInfo):
            await ctx.info(
                "Role information retrieved successfully: "
                f"role_id={result.id}, name={result.name}"
            )
        else:
            await ctx.warning(
                f"Role retrieval failed: error_type={result.error_type}, "
                f"error={result.error}"
            )

        return result

    except Exception as e:
        await ctx.error(
            "Role information retrieval failed: "
            f"identifier={request.identifier}, error={str(e)}, "
            f"error_type={type(e).__name__}"
        )
        raise

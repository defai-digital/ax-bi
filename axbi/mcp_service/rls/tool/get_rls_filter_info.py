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
Get RLS filter info FastMCP tool.
"""

import logging

from axbi_core.mcp.decorators import tool, ToolAnnotations
from fastmcp import Context

from axbi.mcp_service.mcp_core import ModelGetInfoCore
from axbi.mcp_service.rls.schemas import (
    GetRlsFilterInfoRequest,
    RlsFilterError,
    RlsFilterInfo,
    serialize_rls_filter_object,
)
from axbi.mcp_service.utils.logging_utils import mcp_event_log_context

logger = logging.getLogger(__name__)


@tool(
    tags=["discovery"],
    class_permission_name="Row Level Security",
    annotations=ToolAnnotations(
        title="Get RLS filter info",
        readOnlyHint=True,
        destructiveHint=False,
    ),
)
async def get_rls_filter_info(
    request: GetRlsFilterInfoRequest, ctx: Context
) -> RlsFilterInfo | RlsFilterError:
    """Get row level security filter details by ID. Requires admin access.

    Returns full RLS filter configuration including name, type, tables, roles,
    and clause.

    Example usage:
    ```json
    {"identifier": 1}
    ```
    """
    await ctx.info(
        f"Retrieving RLS filter information: identifier={request.identifier}"
    )

    try:
        from axbi.daos.security import RLSDAO

        with mcp_event_log_context(action="mcp.get_rls_filter_info.lookup"):
            get_tool = ModelGetInfoCore(
                dao_class=RLSDAO,
                output_schema=RlsFilterInfo,
                error_schema=RlsFilterError,
                serializer=serialize_rls_filter_object,
                supports_slug=False,
                logger=logger,
            )
            result = get_tool.run_tool(request.identifier)

        if isinstance(result, RlsFilterInfo):
            await ctx.info(f"RLS filter retrieved: id={result.id}, name={result.name}")
        else:
            await ctx.warning(
                f"RLS filter retrieval failed: error_type={result.error_type}, "
                f"error={result.error}"
            )

        return result

    except Exception as e:
        await ctx.error(
            f"RLS filter info retrieval failed: identifier={request.identifier}, "
            f"error={str(e)}"
        )
        return RlsFilterError.create(
            error=f"Failed to get RLS filter info: {str(e)}",
            error_type="InternalError",
        )

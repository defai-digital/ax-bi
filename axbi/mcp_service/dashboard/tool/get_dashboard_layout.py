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
Get dashboard layout FastMCP tool

Companion to get_dashboard_info: returns the parsed dashboard layout
(tabs and chart positions) extracted from position_json. Use this
when get_dashboard_info's omitted_fields hint indicates position_json
was stripped and structured layout data is needed for analysis.
"""

import logging

from axbi_core.mcp.decorators import tool, ToolAnnotations
from fastmcp import Context

from axbi.mcp_service.dashboard.schemas import (
    dashboard_layout_serializer,
    DashboardError,
    DashboardLayout,
    GetDashboardLayoutRequest,
)
from axbi.mcp_service.mcp_core import ModelGetInfoCore
from axbi.mcp_service.utils.logging_utils import mcp_event_log_context

logger = logging.getLogger(__name__)


@tool(
    tags=["discovery"],
    class_permission_name="Dashboard",
    annotations=ToolAnnotations(
        title="Get dashboard layout",
        readOnlyHint=True,
        destructiveHint=False,
    ),
)
async def get_dashboard_layout(
    request: GetDashboardLayoutRequest, ctx: Context
) -> DashboardLayout | DashboardError:
    """
    Get parsed dashboard layout by ID, UUID, or slug.

    Returns the tabs and chart positions extracted from the dashboard's
    position_json. get_dashboard_info omits position_json to keep responses
    small; call this tool when you need the structured layout (e.g. to
    explain which charts live under which tab, or to locate a chart by
    its parent tab).

    Example usage:
    ```json
    {
        "identifier": 123
    }
    ```
    """
    await ctx.info(f"Retrieving dashboard layout: identifier={request.identifier}")

    try:
        from axbi.daos.dashboard import DashboardDAO

        # No eager loading: the layout serializer only reads position_json
        # (plus id/title/uuid), so Dashboard.slices is never accessed.
        with mcp_event_log_context(action="mcp.get_dashboard_layout.lookup"):
            core = ModelGetInfoCore(
                dao_class=DashboardDAO,
                output_schema=DashboardLayout,
                error_schema=DashboardError,
                serializer=dashboard_layout_serializer,
                supports_slug=True,
                logger=logger,
            )
            result = core.run_tool(request.identifier)

        if isinstance(result, DashboardLayout):
            await ctx.info(
                f"Dashboard layout retrieved: id={result.id}, "
                f"tab_count={len(result.tabs)}, chart_count={len(result.charts)}, "
                f"has_layout={result.has_layout}"
            )
        else:
            await ctx.warning(
                f"Dashboard layout retrieval failed: error_type={result.error_type}, "
                f"error={result.error}"
            )

        return result

    except Exception as e:
        await ctx.error(
            "Dashboard layout retrieval failed: "
            f"identifier={request.identifier}, error={str(e)}, "
            f"error_type={type(e).__name__}"
        )
        return DashboardError.create(
            error=f"Failed to get dashboard layout: {str(e)}",
            error_type="InternalError",
        )

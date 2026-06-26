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
List dashboards FastMCP tool (Advanced with metadata cache control)

This module contains the FastMCP tool for listing dashboards using
advanced filtering with clear, unambiguous request schema and metadata cache control.
"""

import logging
from typing import TYPE_CHECKING

from fastmcp import Context
from superset_core.mcp.decorators import tool, ToolAnnotations

if TYPE_CHECKING:
    from superset.models.dashboard import Dashboard

from superset.mcp_service.dashboard.schemas import (
    DashboardFilter,
    DashboardInfo,
    DashboardList,
    ListDashboardsRequest,
    serialize_dashboard_object,
)
from superset.mcp_service.mcp_core import (
    ModelListCore,
    request_or_default,
    to_zero_based_page,
)
from superset.mcp_service.utils.logging_utils import mcp_event_log_context
from superset.mcp_service.utils.response_utils import finalize_list_response

logger = logging.getLogger(__name__)

# Minimal defaults for reduced token usage - users can request more via select_columns
DEFAULT_DASHBOARD_COLUMNS = [
    "id",
    "dashboard_title",
    "slug",
    "description",
    "certified_by",
    "certification_details",
    "url",
    "changed_on",
    "changed_on_humanized",
]

SORTABLE_DASHBOARD_COLUMNS = [
    "id",
    "dashboard_title",
    "slug",
    "published",
    "changed_on",
    "created_on",
]

_DEFAULT_LIST_DASHBOARDS_REQUEST = ListDashboardsRequest()


@tool(
    tags=["core"],
    class_permission_name="Dashboard",
    annotations=ToolAnnotations(
        title="List dashboards",
        readOnlyHint=True,
        destructiveHint=False,
    ),
)
async def list_dashboards(
    request: ListDashboardsRequest | None = None,
    ctx: Context = None,
) -> DashboardList:
    """List dashboards with filtering and search. Returns dashboard metadata
    including title, slug, URL, and last modified time. Use select_columns to
    request additional fields.

    **IMPORTANT**: All parameters must be wrapped in a ``request`` object.
    Do NOT pass ``search``, ``page``, ``page_size``, etc. as top-level
    keyword arguments — they will be rejected. Use the ``request`` wrapper::

        # Correct usage
        list_dashboards(request={"search": "sales", "page": 1, "page_size": 10})
        list_dashboards(request={"filters": [{"col": "dashboard_title", "opr": "sw", "value": "exec"}]})
        list_dashboards()  # no arguments returns first page with defaults

        # Wrong — causes pydantic validation errors
        list_dashboards(search="sales", page=1)  # DO NOT DO THIS

    Valid filter columns for ``filters[].col``:
        ``dashboard_title``, ``published``, ``favorite``,
        ``created_by_fk``, ``changed_by_fk``

    Sortable columns for ``order_column``:
        ``id``, ``dashboard_title``, ``slug``, ``published``,
        ``changed_on``, ``created_on``

    To filter by a person (e.g. "dashboards Maxime is working on"), do NOT pass
    the name as the search parameter — search matches titles and slugs only.
    Instead, call find_users to resolve the name to a user ID, then pass it as
    a filter: filters=[{"col": "created_by_fk", "opr": "eq", "value": <id>}]
    (or "changed_by_fk" for "last modified by").
    """
    request = request_or_default(request, _DEFAULT_LIST_DASHBOARDS_REQUEST)
    await ctx.info(
        "Listing dashboards: page=%s, page_size=%s, search=%s"
        % (
            request.page,
            request.page_size,
            request.search,
        )
    )
    await ctx.debug(
        "Dashboard listing filters: filters=%s, order_column=%s, order_direction=%s"
        % (
            len(request.filters),
            request.order_column,
            request.order_direction,
        )
    )

    from superset.daos.dashboard import DashboardDAO
    from superset.mcp_service.common.schema_discovery import (
        DASHBOARD_SORTABLE_COLUMNS,
        get_all_column_names,
        get_dashboard_columns,
    )

    # Get all column names dynamically from the model
    all_columns = get_all_column_names(get_dashboard_columns())

    def _serialize_dashboard(
        obj: "Dashboard | None", cols: list[str] | None
    ) -> DashboardInfo | None:
        """Serialize dashboard object (field filtering handled by model_serializer)."""
        return serialize_dashboard_object(obj)

    tool = ModelListCore(
        dao_class=DashboardDAO,
        output_schema=DashboardInfo,
        item_serializer=_serialize_dashboard,
        filter_type=DashboardFilter,
        default_columns=DEFAULT_DASHBOARD_COLUMNS,
        search_columns=[
            "dashboard_title",
            "slug",
            "uuid",
        ],
        list_field_name="dashboards",
        output_list_schema=DashboardList,
        all_columns=all_columns,
        sortable_columns=DASHBOARD_SORTABLE_COLUMNS,
        logger=logger,
    )

    with mcp_event_log_context(action="mcp.list_dashboards.query"):
        result = tool.run_tool(
            filters=request.filters,
            search=request.search,
            select_columns=request.select_columns,
            order_column=request.order_column,
            order_direction=request.order_direction,
            page=to_zero_based_page(request.page),
            page_size=request.page_size,
            created_by_me=request.created_by_me,
            owned_by_me=request.owned_by_me,
        )
    return await finalize_list_response(result, "dashboards", "Dashboards", ctx)

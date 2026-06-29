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
MCP tool: list_charts (advanced filtering with metadata cache control)
"""

import logging
from typing import cast, TYPE_CHECKING

from fastmcp import Context
from flask import current_app
from superset_core.mcp.decorators import tool, ToolAnnotations

if TYPE_CHECKING:
    from superset.models.slice import Slice

from superset.mcp_service.chart.schemas import (
    ChartError,
    ChartFilter,
    ChartInfo,
    ChartLike,
    ChartList,
    ListChartsRequest,
    serialize_chart_object,
)
from superset.mcp_service.mcp_core import (
    ModelListCore,
    request_or_default,
    to_zero_based_page,
)
from superset.mcp_service.privacy import (
    DATA_MODEL_METADATA_ERROR_TYPE,
    remove_chart_data_model_columns,
    request_uses_chart_data_model_filter,
    user_can_view_data_model_metadata,
)
from superset.mcp_service.utils.logging_utils import mcp_event_log_context
from superset.mcp_service.utils.response_utils import finalize_list_response
from superset.runtime_modernization.measurement import measure_runtime_candidate

logger = logging.getLogger(__name__)

# Minimal defaults for reduced token usage - users can request more via select_columns
DEFAULT_CHART_COLUMNS = [
    "id",
    "slice_name",
    "viz_type",
    "description",
    "certified_by",
    "certification_details",
    "url",
    "changed_on",
    "changed_on_humanized",
]

SORTABLE_CHART_COLUMNS = [
    "id",
    "slice_name",
    "viz_type",
    "description",
    "changed_on",
    "created_on",
]

_DEFAULT_LIST_CHARTS_REQUEST = ListChartsRequest()


@tool(
    tags=["core"],
    class_permission_name="Chart",
    annotations=ToolAnnotations(
        title="List charts",
        readOnlyHint=True,
        destructiveHint=False,
    ),
)
async def list_charts(
    request: ListChartsRequest | None = None,
    ctx: Context = None,
) -> ChartList | ChartError:
    """List charts with filtering and search.

    Returns chart metadata including id, name, viz_type, URL, and last
    modified time.

    **IMPORTANT**: All parameters must be wrapped in a ``request`` object.
    Do NOT pass ``search``, ``page``, ``page_size``, etc. as top-level
    keyword arguments — they will be rejected. Use the ``request`` wrapper::

        # Correct usage
        list_charts(request={"search": "revenue", "page": 1, "page_size": 10})
        list_charts(request={"filters": [{"col": "slice_name", "opr": "sw", "value": "sales"}]})
        list_charts()  # no arguments returns first page with defaults

        # Wrong — causes pydantic validation errors
        list_charts(search="revenue", page=1)  # DO NOT DO THIS

    Valid filter columns for ``filters[].col``:
        ``slice_name``, ``viz_type``, ``datasource_name``,
        ``created_by_fk``, ``changed_by_fk``

    Sortable columns for ``order_column``:
        ``id``, ``slice_name``, ``viz_type``, ``description``,
        ``changed_on``, ``created_on``

    To filter by a person, call find_users to resolve the name to a user ID,
    then pass it as a filter: filters=[{"col": "created_by_fk", "opr": "eq",
    "value": <id>}] (or "changed_by_fk"). Do not pass the name as search.
    """
    request = request_or_default(request, _DEFAULT_LIST_CHARTS_REQUEST)
    await ctx.info(
        "Listing charts: page=%s, page_size=%s, search=%s"
        % (
            request.page,
            request.page_size,
            request.search,
        )
    )
    await ctx.debug(
        "Chart listing filters: filters=%s, order_column=%s, order_direction=%s"
        % (
            len(request.filters),
            request.order_column,
            request.order_direction,
        )
    )

    from superset.daos.chart import ChartDAO
    from superset.mcp_service.common.schema_discovery import (
        CHART_SORTABLE_COLUMNS,
        get_all_column_names,
        get_chart_columns,
    )

    can_view_data_model_metadata = user_can_view_data_model_metadata()
    if not can_view_data_model_metadata and request_uses_chart_data_model_filter(
        request.filters
    ):
        return ChartError(
            error=(
                "You don't have permission to access underlying dataset or "
                "database details for your role."
            ),
            error_type=DATA_MODEL_METADATA_ERROR_TYPE,
        )

    # Get all column names dynamically from the model
    all_columns = get_all_column_names(get_chart_columns())
    sortable_columns = CHART_SORTABLE_COLUMNS
    select_columns = request.select_columns
    if not can_view_data_model_metadata:
        all_columns = remove_chart_data_model_columns(all_columns)
        sortable_columns = remove_chart_data_model_columns(sortable_columns)
        select_columns = remove_chart_data_model_columns(select_columns)

    def _serialize_chart(
        obj: "Slice | None", cols: list[str] | None
    ) -> ChartInfo | None:
        """Serialize chart object (field filtering handled by model_serializer)."""
        return serialize_chart_object(cast(ChartLike | None, obj))

    tool = ModelListCore(
        dao_class=ChartDAO,
        output_schema=ChartInfo,
        item_serializer=_serialize_chart,
        filter_type=ChartFilter,
        default_columns=DEFAULT_CHART_COLUMNS,
        search_columns=[
            "slice_name",
            "description",
        ],
        list_field_name="charts",
        output_list_schema=ChartList,
        all_columns=all_columns,
        sortable_columns=sortable_columns,
        logger=logger,
    )

    with measure_runtime_candidate(
        "mcp_orchestration",
        "list_charts",
        current_app.config["STATS_LOGGER"],
    ):
        try:
            with mcp_event_log_context(action="mcp.list_charts.query"):
                result = tool.run_tool(
                    filters=request.filters,
                    search=request.search,
                    select_columns=select_columns,
                    order_column=request.order_column,
                    order_direction=request.order_direction,
                    page=to_zero_based_page(request.page),
                    page_size=request.page_size,
                    created_by_me=request.created_by_me,
                    owned_by_me=request.owned_by_me,
                )
            return await finalize_list_response(result, "charts", "Charts", ctx)
        except Exception as e:
            await ctx.error("Failed to list charts: %s" % (str(e),))
            raise

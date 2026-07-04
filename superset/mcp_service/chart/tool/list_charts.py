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
from typing import Any, cast, TYPE_CHECKING

from fastmcp import Context
from flask import current_app
from superset_core.mcp.decorators import tool, ToolAnnotations

if TYPE_CHECKING:
    from superset.models.slice import Slice

from superset import is_feature_enabled
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
from superset.mcp_service.system.schemas import PaginationInfo
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
_CHART_LIST_CONTRACT_VERSION = "chart-list.v1"


def _chart_list_request_payload(request: ListChartsRequest) -> dict[str, Any]:
    """Build an ax-services chart list request payload."""

    return {
        "contractVersion": _CHART_LIST_CONTRACT_VERSION,
        "filters": [filter_.model_dump(mode="json") for filter_ in request.filters],
        "selectColumns": list(request.select_columns),
        "search": request.search,
        "orderColumn": request.order_column,
        "orderDirection": request.order_direction,
        "page": request.page,
        "pageSize": request.page_size,
        "createdByMe": request.created_by_me,
        "ownedByMe": request.owned_by_me,
    }


def _ax_services_chart_list_candidate(
    request: ListChartsRequest,
) -> AxServicesResponse:
    """Run the TypeScript sidecar chart list candidate."""

    client = AxServicesClient(AxServicesConfig.from_mapping(current_app.config))
    return client.list_charts(_chart_list_request_payload(request))


def _optional_string(value: Any) -> str | None:
    """Return a string value or None."""

    return value if isinstance(value, str) else None


def _chart_info_from_ax_services(payload: dict[str, Any]) -> ChartInfo | None:
    """Convert one valid ax-services chart item to the MCP chart schema."""

    chart_id = payload.get("id")
    if not isinstance(chart_id, int):
        return None

    chart = ChartInfo(
        id=chart_id,
        slice_name=_optional_string(payload.get("sliceName")),
        viz_type=_optional_string(payload.get("vizType")),
        description=_optional_string(payload.get("description")),
        certified_by=_optional_string(payload.get("certifiedBy")),
        certification_details=_optional_string(payload.get("certificationDetails")),
        uuid=_optional_string(payload.get("uuid")),
        url=_optional_string(payload.get("url")),
        changed_on=_optional_string(payload.get("changedOn")),
        changed_on_humanized=_optional_string(payload.get("changedOnHumanized")),
    )
    return _sanitize_ax_services_chart_info(chart)


def _sanitize_ax_services_chart_info(chart: ChartInfo) -> ChartInfo:
    """Apply MCP LLM-context sanitization to sidecar chart fields."""

    payload = chart.model_dump(mode="python")
    for field_name in (
        "slice_name",
        "description",
        "certified_by",
        "certification_details",
    ):
        payload[field_name] = sanitize_for_llm_context(
            payload.get(field_name),
            field_path=(field_name,),
        )
    return ChartInfo(**payload)


def _is_string_list(value: Any) -> bool:
    """Return whether a value is a list of strings."""

    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def _chart_list_from_ax_services_response(
    response: AxServicesResponse,
) -> dict[str, Any] | None:
    """Convert a valid ax-services chart list response to the MCP schema."""

    payload = response.payload or {}
    if (
        not response.ok
        or payload.get("contractVersion") != _CHART_LIST_CONTRACT_VERSION
    ):
        return None

    raw_charts = payload.get("charts")
    if not isinstance(raw_charts, list):
        return None

    charts = []
    for raw_chart in raw_charts:
        if not isinstance(raw_chart, dict):
            return None
        chart = _chart_info_from_ax_services(raw_chart)
        if chart is None:
            return None
        charts.append(chart)

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

    chart_list = ChartList(
        charts=charts,
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
        sortable_columns=SORTABLE_CHART_COLUMNS,
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
    return dump_model_with_select_columns(chart_list, columns_requested)


def _chart_keys_from_mcp_response(response: dict[str, Any]) -> list[int]:
    """Return chart IDs from an MCP chart list response."""

    charts = response.get("charts")
    if not isinstance(charts, list):
        return []
    return [
        chart["id"]
        for chart in charts
        if isinstance(chart, dict) and isinstance(chart.get("id"), int)
    ]


def _chart_keys_from_ax_services_response(response: AxServicesResponse) -> list[int]:
    """Return chart IDs from an ax-services chart list response."""

    payload = response.payload or {}
    charts = payload.get("charts") if isinstance(payload, dict) else None
    if not isinstance(charts, list):
        return []
    return [
        chart["id"]
        for chart in charts
        if isinstance(chart, dict) and isinstance(chart.get("id"), int)
    ]


def _chart_list_shadow_matches(
    authoritative: dict[str, Any],
    candidate: AxServicesResponse,
) -> bool:
    """Compare Python and TypeScript chart list outputs by ID order."""

    return candidate.ok and _chart_keys_from_mcp_response(
        authoritative
    ) == _chart_keys_from_ax_services_response(candidate)


def _summarize_chart_list_response(response: dict[str, Any]) -> dict[str, object]:
    """Summarize Python chart list results for shadow mismatch reports."""

    return {
        "count": len(_chart_keys_from_mcp_response(response)),
        "ids": _chart_keys_from_mcp_response(response),
    }


def _summarize_ax_services_chart_list_response(
    response: AxServicesResponse,
) -> dict[str, object]:
    """Summarize ax-services chart list results for shadow mismatch reports."""

    payload = response.payload or {}
    return {
        "ok": response.ok,
        "status_code": response.status_code,
        "contract_version": payload.get("contractVersion")
        if isinstance(payload, dict)
        else None,
        "count": len(_chart_keys_from_ax_services_response(response)),
        "ids": _chart_keys_from_ax_services_response(response),
        "error": response.error,
    }


def _report_chart_list_shadow_mismatch(report: ShadowMismatchReport) -> None:
    """Log a compact chart list shadow mismatch report."""

    logger.warning(
        "Runtime modernization chart list shadow mismatch: %s",
        report.to_dict(),
    )


def _chart_list_shadow_enabled() -> bool:
    """Return whether chart listing should shadow through ax-services."""

    return is_feature_enabled("RUNTIME_SHADOW_EXECUTION") and is_feature_enabled(
        "TS_MCP_ORCHESTRATION"
    )


def _chart_list_serving_enabled() -> bool:
    """Return whether chart listing should be served through ax-services."""

    return is_feature_enabled("TS_MCP_ORCHESTRATION") and is_feature_enabled(
        "TS_CHART_LIST_SERVING"
    )


def _record_chart_list_metric(metric: str) -> None:
    """Record a chart-list migration metric."""

    current_app.config["STATS_LOGGER"].incr(
        f"runtime_modernization.mcp_orchestration.list_charts.{metric}"
    )


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
) -> ChartList | ChartError | dict[str, Any]:
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

    sidecar_request = request
    if not can_view_data_model_metadata:
        sidecar_request = request.model_copy(
            update={
                "select_columns": remove_chart_data_model_columns(
                    request.select_columns
                ),
            },
        )

    with measure_runtime_candidate(
        "mcp_orchestration",
        "list_charts",
        current_app.config["STATS_LOGGER"],
    ):
        if _chart_list_serving_enabled():
            candidate_response = _ax_services_chart_list_candidate(sidecar_request)
            candidate_charts = _chart_list_from_ax_services_response(
                candidate_response,
            )
            if candidate_charts is not None:
                _record_chart_list_metric("served_candidate")
                return candidate_charts

            _record_chart_list_metric("fallback")
            return await _list_charts_python(
                request,
                ctx,
                can_view_data_model_metadata,
            )

        python_response = await _list_charts_python(
            request,
            ctx,
            can_view_data_model_metadata,
        )
        return execute_with_shadow(
            area="mcp_orchestration",
            operation="list_charts",
            authoritative=lambda: python_response,
            candidate=lambda: _ax_services_chart_list_candidate(sidecar_request),
            compare=_chart_list_shadow_matches,
            stats_logger=current_app.config["STATS_LOGGER"],
            shadow_enabled=_chart_list_shadow_enabled(),
            report_mismatch=_report_chart_list_shadow_mismatch,
            summarize_authoritative=_summarize_chart_list_response,
            summarize_candidate=_summarize_ax_services_chart_list_response,
        )


async def _list_charts_python(
    request: ListChartsRequest,
    ctx: Context,
    can_view_data_model_metadata: bool,
) -> dict[str, Any]:
    """Run the authoritative Python chart list path."""

    await ctx.info(
        f"Listing charts: page={request.page}, "
        f"page_size={request.page_size}, search={request.search}"
    )
    await ctx.debug(
        f"Chart listing filters: filters={len(request.filters)}, "
        f"order_column={request.order_column}, "
        f"order_direction={request.order_direction}"
    )

    from superset.daos.chart import ChartDAO
    from superset.mcp_service.common.schema_discovery import (
        CHART_SORTABLE_COLUMNS,
        get_all_column_names,
        get_chart_columns,
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
        await ctx.error(f"Failed to list charts: {str(e)}")
        raise

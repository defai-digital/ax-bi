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
MCP tool: suggest_chart_improvements

Analyze an existing chart's configuration and data, then suggest
improvements for better visualization or readability.
"""

import logging
from typing import Any

from fastmcp import Context
from superset_core.mcp.decorators import tool, ToolAnnotations

from superset.mcp_service.ai.provider_factory import get_llm_provider
from superset.mcp_service.ai.schemas import (
    SuggestChartImprovementsRequest,
    SuggestChartImprovementsResponse,
)
from superset.mcp_service.utils.logging_utils import mcp_event_log_context

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Heuristic analysis when no LLM is configured
# ---------------------------------------------------------------------------

# Chart types considered sub-optimal for certain data shapes
_HIGH_CARDINALITY_PIE_LIMIT = 10
_TABLE_TYPES = {"table", "pivot_table", "pivot_table_v2", "ag-grid-table"}
_TIME_SERIES_TYPES = {
    "echarts_timeseries_line",
    "echarts_timeseries_bar",
    "echarts_timeseries_area",
    "mixed_timeseries",
}


def _heuristic_analysis(  # noqa: C901
    chart_config: dict[str, Any],
    data_sample: dict[str, Any] | None,
    goal: str | None,
) -> SuggestChartImprovementsResponse:
    """Rule-based chart improvement suggestions."""
    viz_type = chart_config.get("viz_type", "")
    warnings: list[str] = []
    suggestions: list[dict[str, Any]] = []

    # Check for pie chart with too many categories
    if viz_type == "pie" and data_sample:
        row_count = len(data_sample.get("data", []))
        if row_count > _HIGH_CARDINALITY_PIE_LIMIT:
            suggestions.append(
                {
                    "reason": (
                        f"Pie chart has {row_count} slices which is hard to read. "
                        "Consider using a bar chart for better comparison."
                    ),
                    "config_changes": {"chart_type": "xy", "kind": "bar"},
                    "preview_config": None,
                }
            )

    # Check for table when a chart might be more insightful
    if viz_type in _TABLE_TYPES and not goal:
        suggestions.append(
            {
                "reason": (
                    "Tables show raw numbers but charts reveal patterns faster. "
                    "Consider adding a complementary bar or line chart."
                ),
                "config_changes": {},
                "preview_config": None,
            }
        )

    # Check for big_number without trendline
    if viz_type in ("big_number", "big_number_total"):
        form_data = chart_config.get("form_data", chart_config)
        if not form_data.get("comparison_type"):
            suggestions.append(
                {
                    "reason": (
                        "Big Number charts are more insightful with a trendline "
                        "to show how the metric changes over time."
                    ),
                    "config_changes": {
                        "chart_type": "big_number",
                        "show_trendline": True,
                    },
                    "preview_config": None,
                }
            )

    # Check for missing time grain on time series
    if viz_type in _TIME_SERIES_TYPES:
        form_data = chart_config.get("form_data", chart_config)
        if not form_data.get("time_grain_sqla"):
            suggestions.append(
                {
                    "reason": (
                        "No time grain specified. Setting an appropriate time grain "
                        "(e.g. P1M for monthly) can improve readability."
                    ),
                    "config_changes": {"time_grain_sqla": "P1M"},
                    "preview_config": None,
                }
            )

    # General suggestion: color palette
    if viz_type and viz_type not in _TABLE_TYPES:
        form_data = chart_config.get("form_data", chart_config)
        if not form_data.get("color_scheme"):
            suggestions.append(
                {
                    "reason": (
                        "Applying a consistent color scheme improves readability "
                        "and accessibility."
                    ),
                    "config_changes": {"color_scheme": "supersetColors"},
                    "preview_config": None,
                }
            )

    # Goal-specific suggestions
    if goal:
        goal_lower = goal.lower()
        if "read" in goal_lower or "clear" in goal_lower:
            suggestions.append(
                {
                    "reason": (
                        "For better readability, consider adding data labels, "
                        "simplifying axis labels, or reducing the number of series."
                    ),
                    "config_changes": {"show_value": True},
                    "preview_config": None,
                }
            )
        if "trend" in goal_lower:
            if viz_type not in _TIME_SERIES_TYPES:
                suggestions.append(
                    {
                        "reason": (
                            "For trend analysis, a time series line chart is "
                            "usually the most effective visualization."
                        ),
                        "config_changes": {
                            "chart_type": "xy",
                            "kind": "line",
                        },
                        "preview_config": None,
                    }
                )

    current_analysis = (
        f"Chart type: {viz_type or 'unknown'}. "
        f"Analyzed {'with data sample' if data_sample else 'config only'}."
    )

    return SuggestChartImprovementsResponse(
        current_analysis=current_analysis,
        suggestions=suggestions,
        warnings=warnings,
    )


# ---------------------------------------------------------------------------
# LLM-powered analysis
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """You are a data visualization expert. Analyze the given chart
configuration and data sample, then suggest improvements.

Return JSON with this structure:
{
  "current_analysis": "Brief analysis of the current chart",
  "suggestions": [
    {
      "reason": "Why this improves the chart",
      "config_changes": {"key": "value"}
    }
  ]
}

Config change keys should be valid generate_chart parameters:
- chart_type: xy, big_number, pie, table, pivot_table, mixed_timeseries
- kind (for xy): line, bar, area, scatter
- color_scheme: supersetColors, d3Category10, etc.
- show_value: true (data labels)
- time_grain_sqla: P1H, P1D, P1W, P1M, P1Y
- show_trendline: true (for big_number)
- donut: true (for pie -> donut)
- aggregate: SUM, AVG, COUNT, etc.
"""


async def _llm_analysis(
    chart_config: dict[str, Any],
    data_sample: dict[str, Any] | None,
    goal: str | None,
) -> SuggestChartImprovementsResponse | None:
    """LLM-powered chart improvement suggestions. Returns None if no provider."""
    try:
        provider = get_llm_provider()
    except Exception:  # noqa: BLE001
        return None

    user_msg_parts = [
        f"Chart config: {json_dumps_compact(chart_config)}",
    ]
    if data_sample:
        user_msg_parts.append(f"Data sample: {json_dumps_compact(data_sample)}")
    if goal:
        user_msg_parts.append(f"User goal: {goal}")

    user_msg = "\n".join(user_msg_parts)

    try:
        result = await provider.complete_json(
            system_prompt=_SYSTEM_PROMPT,
            user_prompt=user_msg,
            response_schema=SuggestChartImprovementsResponse,
            metadata={"tool": "suggest_chart_improvements"},
        )
        return SuggestChartImprovementsResponse(
            current_analysis=result.get("current_analysis", ""),
            suggestions=result.get("suggestions", []),
            warnings=[],
        )
    except NotImplementedError:
        return None
    except Exception as e:  # noqa: BLE001
        logger.warning("LLM analysis failed, falling back to heuristic: %s", e)
        return None


def json_dumps_compact(obj: Any) -> str:
    """Compact JSON serialization for LLM prompts."""
    from superset.utils import json as sjson

    try:
        return sjson.dumps(obj)
    except Exception:  # noqa: BLE001
        return str(obj)


# ---------------------------------------------------------------------------
# Tool definition
# ---------------------------------------------------------------------------


@tool(
    tags=["core", "ai"],
    class_permission_name="Chart",
    annotations=ToolAnnotations(
        title="Suggest chart improvements",
        readOnlyHint=True,
        destructiveHint=False,
    ),
)
async def suggest_chart_improvements(
    request: SuggestChartImprovementsRequest,
    ctx: Context,
) -> dict[str, Any]:
    """Analyze a chart and suggest visualization improvements.

    Examines the chart's configuration, data shape, and optionally its data
    sample to produce actionable improvement suggestions. Each suggestion
    includes a reason and config changes that can be applied via update_chart.

    Set goal for targeted advice (e.g. "Make this easier to read",
    "Show trends more clearly"). Omit goal for general improvements.

    Example:
    ```json
    {
        "chart_id": 42,
        "goal": "Show trends more clearly"
    }
    ```
    """
    chart_id = request.chart_id
    goal = request.goal

    with mcp_event_log_context(action="mcp.suggest_chart_improvements.fetch"):
        # Fetch chart info
        from superset import db
        from superset.models.slice import Slice

        if isinstance(chart_id, str):
            chart = db.session.query(Slice).filter(Slice.uuid == chart_id).first()
        else:
            chart = db.session.get(Slice, int(chart_id))

        if not chart:
            return SuggestChartImprovementsResponse(
                current_analysis="",
                suggestions=[],
                warnings=[f"Chart {chart_id} not found."],
            ).model_dump()

        # Build chart config from params
        chart_config: dict[str, Any] = {
            "viz_type": chart.viz_type or "",
            "slice_name": chart.slice_name or "",
        }

        # Try to extract form_data
        try:
            from superset.utils import json as sjson

            if chart.params:
                form_data = sjson.loads(chart.params)
                chart_config["form_data"] = form_data
        except Exception:  # noqa: BLE001
            logger.debug("Could not parse chart params", exc_info=True)

        # Try to get a small data sample for richer analysis
        data_sample: dict[str, Any] | None = None
        try:
            from superset.mcp_service.chart.tool.get_chart_data import (
                get_chart_data,
                GetChartDataRequest,
            )

            data_request = GetChartDataRequest(identifier=chart.id, row_limit=20)
            data_result = await get_chart_data(data_request, ctx)
            if hasattr(data_result, "model_dump"):
                data_sample = data_result.model_dump()
            elif isinstance(data_result, dict):
                data_sample = data_result
        except Exception:  # noqa: BLE001
            # Data sample is optional; proceed without it
            logger.debug("Could not fetch chart data sample", exc_info=True)

    # Try LLM analysis first, fall back to heuristic
    llm_result = await _llm_analysis(chart_config, data_sample, goal)
    if llm_result is not None:
        return llm_result.model_dump()

    heuristic_result = _heuristic_analysis(chart_config, data_sample, goal)
    return heuristic_result.model_dump()

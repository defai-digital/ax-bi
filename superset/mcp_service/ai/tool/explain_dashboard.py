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
"""MCP tool: explain_dashboard

Summarizes and critiques an existing dashboard, optionally answering
specific questions grounded in the dashboard's charts and data.
"""

from __future__ import annotations

import logging
from typing import Any

from superset_core.mcp.decorators import tool, ToolAnnotations

try:
    from fastmcp import Context
except ModuleNotFoundError:
    Context = Any

from superset.mcp_service.ai.schemas import (
    ExplainDashboardRequest,
    ExplainDashboardResponse,
)
from superset.mcp_service.privacy import (
    requires_data_model_metadata_access,
    user_can_view_data_model_metadata,
)
from superset.mcp_service.utils.logging_utils import mcp_event_log_context

logger = logging.getLogger(__name__)


def _gather_dashboard_context(
    dashboard_id: int | str,
) -> tuple[dict[str, Any] | None, list[dict[str, Any]], list[str]]:
    """Gather dashboard metadata and chart summaries.

    Returns:
        Tuple of (dashboard_info_dict, chart_summaries, warnings).
    """
    warnings: list[str] = []

    from sqlalchemy.orm import subqueryload

    from superset.daos.dashboard import DashboardDAO
    from superset.models.dashboard import Dashboard
    from superset.models.slice import Slice

    dashboard = DashboardDAO.find_by_id(
        dashboard_id,
        query_options=[
            subqueryload(Dashboard.slices).subqueryload(Slice.tags),
        ],
    )

    if not dashboard:
        warnings.append(f"Dashboard {dashboard_id} not found or not accessible.")
        return None, [], warnings

    # Build dashboard info
    from superset.mcp_service.dashboard.schemas import serialize_dashboard_object

    dash_info = serialize_dashboard_object(dashboard)
    dash_dict = dash_info.model_dump(mode="json")

    # Build chart summaries
    chart_summaries: list[dict[str, Any]] = []
    for chart in getattr(dashboard, "slices", []) or []:
        chart_summary: dict[str, Any] = {
            "id": getattr(chart, "id", None),
            "name": getattr(chart, "slice_name", None),
            "viz_type": getattr(chart, "viz_type", None),
            "description": getattr(chart, "description", None),
            "datasource_name": getattr(chart, "datasource_name", None),
        }
        chart_summaries.append(chart_summary)

    return dash_dict, chart_summaries, warnings


def _build_overview_summary(
    dash_info: dict[str, Any],
    chart_summaries: list[dict[str, Any]],
) -> tuple[str, list[dict[str, Any]], list[str]]:
    """Build an overview summary of the dashboard."""
    title = dash_info.get("dashboard_title", "Untitled")
    chart_count = len(chart_summaries)

    # Group charts by viz_type
    viz_groups: dict[str, list[str]] = {}
    for c in chart_summaries:
        vt = c.get("viz_type", "unknown") or "unknown"
        viz_groups.setdefault(vt, []).append(c.get("name", f"Chart {c.get('id')}"))

    # Build summary text
    parts = [f"Dashboard '{title}' contains {chart_count} chart(s)."]
    if description := dash_info.get("description") or "":
        parts.append(f"Description: {description}")

    if viz_groups:
        group_parts = []
        for vt, names in viz_groups.items():
            group_parts.append(f"{len(names)} {vt.replace('_', ' ')}")
        parts.append(f"Chart types: {', '.join(group_parts)}.")

    # Key metrics from chart names
    key_metrics: list[dict[str, Any]] = []
    for c in chart_summaries:
        if c.get("viz_type") and "big_number" in c["viz_type"]:
            key_metrics.append(
                {
                    "name": c.get("name", ""),
                    "type": "KPI",
                    "chart_id": c.get("id"),
                }
            )

    # Caveats
    caveats: list[str] = []
    if chart_count == 0:
        caveats.append("This dashboard has no charts.")
    if not dash_info.get("published"):
        caveats.append("This dashboard is not published.")

    return " ".join(parts), key_metrics, caveats


def _build_follow_up_suggestions(
    chart_summaries: list[dict[str, Any]],
) -> list[str]:
    """Generate follow-up suggestions based on dashboard content."""
    suggestions: list[str] = []
    viz_types = {c.get("viz_type", "") for c in chart_summaries}

    if not any("big_number" in vt for vt in viz_types if vt):
        suggestions.append("Add a big number chart for key KPI headlines.")
    if not any("table" in vt for vt in viz_types if vt):
        suggestions.append("Add a table chart for detailed data inspection.")
    if len(chart_summaries) < 3:
        suggestions.append(
            "Consider adding more chart perspectives for a comprehensive view."
        )
    suggestions.append("Use update_chart to modify any chart's configuration.")
    suggestions.append(
        "Use create_chart_from_intent to add new charts from a description."
    )

    return suggestions


@tool(
    tags=["discovery", "ai"],
    class_permission_name="Dashboard",
    annotations=ToolAnnotations(
        title="Explain dashboard",
        readOnlyHint=True,
        destructiveHint=False,
    ),
)
@requires_data_model_metadata_access
async def explain_dashboard(
    request: ExplainDashboardRequest, ctx: Context
) -> dict[str, Any]:
    """Summarize and explain an existing dashboard.

    Returns an overview summary, key metrics, caveats, and follow-up
    suggestions. When a specific question is provided, attempts to answer
    it using the dashboard's chart data.

    IMPORTANT FOR LLM CLIENTS:
    - Use this to understand what a dashboard shows before making changes
    - The overview includes chart types, count, and key metrics
    - Follow-up suggestions help guide next actions
    - Caveats flag potential issues (unpublished, empty, etc.)

    Example usage:
    ```json
    {
        "dashboard_id": 42,
        "scope": "overview"
    }
    ```

    Ask a specific question:
    ```json
    {
        "dashboard_id": 42,
        "question": "What are the key revenue metrics shown?",
        "scope": "data"
    }
    ```
    """
    await ctx.info(
        f"Explaining dashboard: id={request.dashboard_id}, scope={request.scope}, "
        f"question={request.question[:50] if request.question else None}"
    )

    if not user_can_view_data_model_metadata():
        await ctx.warning("Dashboard explanation blocked by privacy controls")
        return ExplainDashboardResponse(
            warnings=["You don't have permission to access dashboard metadata."],
        ).model_dump()

    # Gather dashboard context
    with mcp_event_log_context(action="mcp.explain_dashboard.gather"):
        dash_info, chart_summaries, warnings = _gather_dashboard_context(
            request.dashboard_id
        )

    if dash_info is None:
        return ExplainDashboardResponse(
            warnings=warnings,
            summary="Dashboard not found.",
        ).model_dump()

    # Build explanation
    with mcp_event_log_context(action="mcp.explain_dashboard.explain"):
        summary, key_metrics, caveats = _build_overview_summary(
            dash_info, chart_summaries
        )

        # If a specific question is asked, try to enrich the answer
        if request.question:
            # Try LLM first
            try:
                from superset.mcp_service.ai.provider_factory import get_llm_provider

                provider = get_llm_provider()
                system_prompt = (
                    "You are a data analyst. Given a dashboard's metadata and chart "
                    "summaries, answer the user's question concisely. If the answer "
                    "cannot be determined from the available information, say so."
                )
                dash_context = (
                    f"Dashboard: {dash_info.get('dashboard_title', 'Untitled')}\n"
                    f"Description: {dash_info.get('description', 'N/A')}\n"
                    f"Charts: {chart_summaries}\n"
                    f"Native filters: {dash_info.get('native_filters', [])}"
                )
                user_prompt = (
                    f"Context:\n{dash_context}\n\nQuestion: {request.question}"
                )

                from pydantic import BaseModel, Field

                class AnswerResponse(BaseModel):
                    answer: str = Field(description="Answer to the question")
                    confidence: float = Field(default=0.5, ge=0.0, le=1.0)

                result = provider.complete_json(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    response_schema=AnswerResponse,
                    metadata={
                        "action": "explain_dashboard",
                        "question": request.question[:200],
                    },
                )
                if hasattr(result, "answer"):
                    summary = result.answer
                elif isinstance(result, dict) and "answer" in result:
                    summary = result["answer"]
            except NotImplementedError:
                # No LLM provider — answer from metadata only
                summary = (
                    f"{summary}\n\n"
                    f"Regarding your question '{request.question}': "
                    f"Without an LLM provider configured, I can only report "
                    f"the dashboard metadata shown above. Configure "
                    f"GENAI_LLM_PROVIDER_CONFIG for question answering."
                )
            except Exception as e:
                warnings.append(f"LLM question answering failed ({e}).")

    # Build follow-up suggestions
    follow_ups = _build_follow_up_suggestions(chart_summaries)

    await ctx.info(
        f"Dashboard explained: id={request.dashboard_id}, charts={len(chart_summaries)}"
    )

    return ExplainDashboardResponse(
        summary=summary,
        source_charts=chart_summaries,
        key_metrics=key_metrics,
        caveats=caveats,
        follow_up_suggestions=follow_ups,
        warnings=warnings,
    ).model_dump()

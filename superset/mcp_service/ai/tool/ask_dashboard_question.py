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
"""MCP tool: ask_dashboard_question

Dashboard-scoped Q&A that answers questions grounded in a dashboard's
charts and datasets. Optionally generates a follow-up chart to
visualize the answer.
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
    AskDashboardQuestionRequest,
    AskDashboardQuestionResponse,
)
from superset.mcp_service.privacy import (
    requires_data_model_metadata_access,
    user_can_view_data_model_metadata,
)
from superset.mcp_service.utils.logging_utils import mcp_event_log_context

logger = logging.getLogger(__name__)


def _get_chart_sample_data(chart: Any) -> dict[str, Any] | None:
    """Get a compact data sample from a chart's query context.

    Uses the chart's form_data to execute a lightweight query with a
    small row limit. Returns None if the query fails or the chart has
    no usable form_data.
    """
    try:
        from superset.utils import json

        params_str = getattr(chart, "params", None)
        if not params_str:
            return None

        form_data = (
            json.loads(params_str) if isinstance(params_str, str) else params_str
        )
        datasource_id = form_data.get("datasource_id") or getattr(
            chart, "datasource_id", None
        )
        if not datasource_id:
            return None

        from superset.commands.chart.data.get_data_command import ChartDataCommand
        from superset.mcp_service.chart.chart_helpers import (
            build_query_context_from_form_data,
        )

        query_context = build_query_context_from_form_data(
            form_data, chart=chart, row_limit=10
        )
        if not query_context:
            return None

        command = ChartDataCommand(query_context)
        command.validate()
        result = command.run()

        if not result or "queries" not in result or len(result["queries"]) == 0:
            return None

        query_result = result["queries"][0]
        data = query_result.get("data", [])
        colnames = query_result.get("colnames", [])

        return {"columns": colnames, "data": data[:10]}
    except Exception:
        logger.debug(
            "Could not sample data for chart %s",
            getattr(chart, "id", "?"),
            exc_info=True,
        )
        return None


def _gather_chart_data_context(
    dashboard_id: int | str,
    chart_ids: list[int] | None = None,
) -> tuple[
    dict[str, Any] | None,
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[str],
]:
    """Gather dashboard and chart data context for answering questions.

    Returns:
        Tuple of (dashboard_info, chart_metadata_list, chart_data_samples, warnings).
    """
    warnings: list[str] = []

    from sqlalchemy.orm import subqueryload

    from superset.daos.dashboard import DashboardDAO
    from superset.models.dashboard import Dashboard
    from superset.models.slice import Slice

    dashboard = DashboardDAO.find_by_id(
        dashboard_id,
        query_options=[subqueryload(Dashboard.slices).subqueryload(Slice.tags)],
    )

    if not dashboard:
        warnings.append(f"Dashboard {dashboard_id} not found or not accessible.")
        return None, [], [], warnings

    from superset.mcp_service.dashboard.schemas import serialize_dashboard_object

    dash_info = serialize_dashboard_object(dashboard)
    dash_dict = dash_info.model_dump(mode="json")

    # Build chart metadata
    chart_metadata: list[dict[str, Any]] = []
    charts_to_query = getattr(dashboard, "slices", []) or []

    if chart_ids:
        charts_to_query = [c for c in charts_to_query if c.id in chart_ids]

    for chart in charts_to_query:
        chart_metadata.append(
            {
                "id": chart.id,
                "name": getattr(chart, "slice_name", ""),
                "viz_type": getattr(chart, "viz_type", ""),
                "description": getattr(chart, "description", None),
                "datasource_id": getattr(chart, "datasource_id", None),
                "datasource_name": getattr(chart, "datasource_name", None),
            }
        )

    # Gather sample data from a subset of charts (up to 3 to limit latency)
    chart_data_samples: list[dict[str, Any]] = []
    for chart in charts_to_query[:3]:
        sample = _get_chart_sample_data(chart)
        if sample:
            chart_data_samples.append(
                {
                    "chart_id": chart.id,
                    "chart_name": getattr(chart, "slice_name", ""),
                    "data": sample,
                }
            )

    return dash_dict, chart_metadata, chart_data_samples, warnings


def _answer_with_llm(  # noqa: C901
    question: str,
    dash_info: dict[str, Any],
    chart_metadata: list[dict[str, Any]],
    chart_data_samples: list[dict[str, Any]],
) -> tuple[str, float, list[str], list[str]]:
    """Use the LLM to answer a question grounded in dashboard data.

    Returns:
        Tuple of (answer, confidence, caveats, suggested_next_questions).
    """
    caveats: list[str] = []
    suggested: list[str] = []

    try:
        from pydantic import BaseModel, Field

        from superset.mcp_service.ai.provider_factory import get_llm_provider

        provider = get_llm_provider()

        class AnswerResponse(BaseModel):
            answer: str = Field(description="Concise answer grounded in the data")
            confidence: float = Field(default=0.5, ge=0.0, le=1.0)
            caveats: list[str] = Field(
                default_factory=list,
                description="Limitations or assumptions in the answer",
            )
            suggested_next_questions: list[str] = Field(
                default_factory=list,
                description="2-3 natural follow-up questions the user might ask",
            )

        system_prompt = (
            "You are a data analyst embedded in a BI dashboard. Answer the "
            "user's question using ONLY the dashboard data provided below. "
            "If the data doesn't contain enough information, say so explicitly. "
            "Cite specific chart names and values when possible. "
            "Suggest 2-3 natural follow-up questions."
        )

        # Build compact context
        context_parts = [
            f"Dashboard: {dash_info.get('dashboard_title', 'Untitled')}",
        ]
        if desc := dash_info.get("description"):
            context_parts.append(f"Description: {desc}")

        if chart_metadata:
            context_parts.append(f"Charts ({len(chart_metadata)}):")
            for cm in chart_metadata[:10]:
                context_parts.append(
                    f"  - {cm['name']} ({cm['viz_type']}): {cm.get('description', '')}"
                )

        if chart_data_samples:
            context_parts.append("\nChart data samples:")
            for sample in chart_data_samples[:3]:
                context_parts.append(
                    f"\n  Chart '{sample['chart_name']}' (id={sample['chart_id']}):"
                )
                # Compact data representation
                data = sample.get("data", {})
                if isinstance(data, dict):
                    columns = data.get("columns", [])
                    rows = data.get("data", [])[:5]
                    if columns:
                        context_parts.append(f"    Columns: {columns}")
                    for row in rows:
                        context_parts.append(f"    {row}")

        user_prompt = (
            "Context:\n" + "\n".join(context_parts) + f"\n\nQuestion: {question}"
        )

        result = provider.complete_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_schema=AnswerResponse,
            metadata={
                "action": "ask_dashboard_question",
                "question": question[:200],
            },
        )

        if hasattr(result, "answer"):
            return (
                result.answer,
                result.confidence,
                result.caveats if hasattr(result, "caveats") else [],
                result.suggested_next_questions
                if hasattr(result, "suggested_next_questions")
                else [],
            )
        elif isinstance(result, dict):
            return (
                result.get("answer", ""),
                result.get("confidence", 0.5),
                result.get("caveats", []),
                result.get("suggested_next_questions", []),
            )

    except NotImplementedError:
        caveats.append(
            "No LLM provider configured. "
            "Configure GENAI_LLM_PROVIDER_CONFIG for question answering."
        )
    except Exception as e:
        logger.warning("LLM question answering failed: %s", e, exc_info=True)
        caveats.append(f"LLM processing failed: {e}")

    # Fallback: metadata-only answer
    title = dash_info.get("dashboard_title", "Untitled")
    chart_count = len(chart_metadata)
    answer = (
        f"Dashboard '{title}' has {chart_count} chart(s). "
        f"Without an LLM provider, I cannot answer specific data questions. "
        f"Configure GENAI_LLM_PROVIDER_CONFIG to enable data-driven answers."
    )
    return answer, 0.2, caveats, suggested


@tool(
    tags=["discovery", "ai"],
    class_permission_name="Dashboard",
    annotations=ToolAnnotations(
        title="Ask dashboard question",
        readOnlyHint=False,
        destructiveHint=False,
    ),
)
@requires_data_model_metadata_access
async def ask_dashboard_question(
    request: AskDashboardQuestionRequest, ctx: Context
) -> dict[str, Any]:
    """Ask a question about a dashboard's data and get a grounded answer.

    Answers natural language questions using the dashboard's actual chart
    data. Optionally generates a follow-up chart to visualize the answer.

    IMPORTANT FOR LLM CLIENTS:
    - Use this for dashboard-scoped Q&A (Phase 4: Dashboard Agent)
    - Answers are grounded in the dashboard's actual chart data
    - Set generate_follow_up_chart=True to create a new chart for the answer
    - Returns caveats and suggested next questions

    Example usage:
    ```json
    {
        "dashboard_id": 42,
        "question": "What was the top-performing region last quarter?"
    }
    ```

    With follow-up chart generation:
    ```json
    {
        "dashboard_id": 42,
        "question": "Show me the monthly trend of the top metric",
        "generate_follow_up_chart": true
    }
    ```
    """
    await ctx.info(
        "Asking dashboard question: id=%s, question='%s', follow_up_chart=%s"
        % (
            request.dashboard_id,
            request.question[:80],
            request.generate_follow_up_chart,
        )
    )

    if not user_can_view_data_model_metadata():
        await ctx.warning("Dashboard Q&A blocked by privacy controls")
        return AskDashboardQuestionResponse(
            warnings=["You don't have permission to access dashboard metadata."],
        ).model_dump()

    all_warnings: list[str] = []

    # Step 1: Gather dashboard context
    with mcp_event_log_context(action="mcp.ask_dashboard_question.gather"):
        dash_info, chart_metadata, chart_data_samples, gather_warnings = (
            _gather_chart_data_context(
                request.dashboard_id,
                request.chart_ids or None,
            )
        )
    all_warnings.extend(gather_warnings)

    if dash_info is None:
        return AskDashboardQuestionResponse(
            answer="Dashboard not found.",
            warnings=all_warnings,
        ).model_dump()

    sources = [
        {"chart_id": cm["id"], "name": cm["name"], "viz_type": cm["viz_type"]}
        for cm in chart_metadata
    ]

    # Step 2: Answer the question
    with mcp_event_log_context(action="mcp.ask_dashboard_question.answer"):
        answer, confidence, caveats, suggested = _answer_with_llm(
            request.question,
            dash_info,
            chart_metadata,
            chart_data_samples,
        )

    # Step 3: Optionally generate a follow-up chart
    follow_up_chart = None
    if request.generate_follow_up_chart and chart_metadata:
        await ctx.report_progress(3, 3, "Generating follow-up chart")
        try:
            # Use the first chart's dataset as the source
            source_ds_id = None
            for cm in chart_metadata:
                if cm.get("datasource_id"):
                    source_ds_id = cm["datasource_id"]
                    break

            from superset.mcp_service.ai.schemas import (
                CreateChartFromIntentRequest,
            )
            from superset.mcp_service.ai.tool.create_chart_from_intent import (
                create_chart_from_intent,
            )

            chart_req = CreateChartFromIntentRequest(
                prompt=request.question,
                dataset_id=source_ds_id,
                save_chart=True,
            )
            chart_result = await create_chart_from_intent(chart_req, ctx)

            if isinstance(chart_result, str):
                from superset.utils import json as superset_json

                chart_result = superset_json.loads(chart_result)

            follow_up_chart = chart_result.get("chart")

        except Exception as e:
            logger.warning("Follow-up chart generation failed: %s", e, exc_info=True)
            all_warnings.append(f"Follow-up chart generation failed: {e}")

    await ctx.info(
        "Dashboard question answered: id=%s, confidence=%.2f, sources=%d"
        % (request.dashboard_id, confidence, len(sources))
    )

    return AskDashboardQuestionResponse(
        answer=answer,
        confidence=confidence,
        sources=sources,
        follow_up_chart=follow_up_chart,
        caveats=caveats,
        suggested_next_questions=suggested,
        warnings=all_warnings,
    ).model_dump()

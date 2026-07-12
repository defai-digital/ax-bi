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
"""MCP tool: prompt_to_dashboard

Single-call orchestrator that chains the full prompt-to-dashboard pipeline:
plan_dashboard -> create_chart_from_intent (per chart) -> compose_dashboard.

This is the primary entry point for MCP clients that want to go from a
natural language prompt to a complete dashboard in one call, without
manually chaining 5+ tool invocations.
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any

from axbi_core.mcp.decorators import tool, ToolAnnotations

try:
    from fastmcp import Context
except ModuleNotFoundError:
    Context = Any

from axbi.mcp_service.ai.schemas import (
    ComposeDashboardRequest,
    CreateChartFromIntentRequest,
    DashboardPlanFull,
    DashboardPlanRequest,
    PromptToDashboardChartSummary,
    PromptToDashboardRequest,
    PromptToDashboardResponse,
    WorkflowStepStatus,
)
from axbi.mcp_service.privacy import (
    requires_data_model_metadata_access,
    user_can_view_data_model_metadata,
)
from axbi.mcp_service.utils.logging_utils import mcp_event_log_context

logger = logging.getLogger(__name__)


def _record_artifact(
    artifact_type: str,
    artifact_id: int,
    prompt: str,
    plan_id: str | None,
    tool_chain: list[str],
    source_dataset_ids: list[int],
    confidence: float,
    validation_summary: str = "",
) -> None:
    """Record an AI-generated artifact for audit trail.

    Silently degrades if the model table is unavailable so the main
    flow never depends on the audit table existing.
    """
    try:
        from flask import g

        from axbi import db
        from axbi.models.ai import AIGeneratedArtifact
        from axbi.utils import json as axbi_json

        record = AIGeneratedArtifact()
        record.uuid = uuid.uuid4()
        record.artifact_type = artifact_type
        record.artifact_id = artifact_id
        record.principal_user_id = getattr(g.user, "id", None)
        record.source_prompt = prompt[:2000]
        # Store plan_id and intent summary as JSON in normalized_intent
        record.normalized_intent = axbi_json.dumps(
            {"prompt_excerpt": prompt[:200], "plan_id": plan_id or ""}
        )
        record.llm_provider = ""
        record.llm_model = ""
        record.tool_chain = axbi_json.dumps(tool_chain)
        record.source_asset_refs = axbi_json.dumps(source_dataset_ids)
        record.validation_summary = validation_summary
        record.confidence_score = confidence

        db.session.add(record)
        db.session.commit()  # pylint: disable=consider-using-transaction
    except Exception:
        logger.debug("AI artifact audit recording unavailable", exc_info=True)


@tool(
    tags=["mutate", "ai"],
    class_permission_name="Dashboard",
    feature_flags=["GENAI_BI", "GENAI_BI_MCP_TOOLS", "GENAI_PROMPT_TO_DASHBOARD"],
    annotations=ToolAnnotations(
        title="Prompt to dashboard",
        readOnlyHint=False,
        destructiveHint=False,
    ),
)
@requires_data_model_metadata_access
async def prompt_to_dashboard(  # noqa: C901
    request: PromptToDashboardRequest, ctx: Context
) -> dict[str, Any]:
    """Create a complete dashboard from a natural language prompt in one call.

    This is the single-call orchestrator for the prompt-to-dashboard pipeline.
    It chains three steps internally:
    1. plan_dashboard - discover datasets and build a chart plan
    2. create_chart_from_intent - generate each chart from the plan
    3. compose_dashboard - assemble charts into a dashboard with layout

    IMPORTANT FOR LLM CLIENTS:
    - This is the simplest way to create a dashboard from a prompt
    - Dashboard is created as draft by default (draft=True)
    - Charts are saved permanently by default (save_charts=True)
    - Returns the dashboard URL, plan, chart summaries, and lineage

    Example usage:
    ```json
    {
        "prompt": "Create an executive sales dashboard with revenue trends",
        "max_charts": 6,
        "draft": true
    }
    ```

    Pin to specific datasets:
    ```json
    {
        "prompt": "Show customer retention and churn analysis",
        "dataset_ids": [42, 55],
        "max_charts": 4
    }
    ```
    """
    start_time = time.time()
    await ctx.info(
        f"Prompt-to-dashboard: prompt='{request.prompt[:80]}', "
        f"datasets={request.dataset_ids}, max_charts={request.max_charts}"
    )

    if not user_can_view_data_model_metadata():
        await ctx.warning("Prompt-to-dashboard blocked by privacy controls")
        return PromptToDashboardResponse(
            error="You don't have permission to access dataset metadata.",
        ).model_dump()

    if not request.dry_run and not request.save_charts:
        return PromptToDashboardResponse(
            error=(
                "save_charts=False cannot compose a dashboard. Use dry_run=True "
                "to validate preview-only chart intents."
            ),
        ).model_dump()

    all_warnings: list[str] = []
    chart_summaries: list[PromptToDashboardChartSummary] = []
    chart_ids: list[int] = []
    successful_chart_count = 0
    failed_chart_count = 0
    tool_chain = ["prompt_to_dashboard"]
    steps: list[WorkflowStepStatus] = []

    # ------------------------------------------------------------------
    # Step 1: Plan the dashboard
    # ------------------------------------------------------------------
    await ctx.report_progress(1, 4, "Planning dashboard")
    plan_started = time.time()
    with mcp_event_log_context(action="mcp.prompt_to_dashboard.plan"):
        from axbi.mcp_service.ai.tool.plan_dashboard import plan_dashboard

        plan_request = DashboardPlanRequest(
            prompt=request.prompt,
            dataset_candidates=request.dataset_ids,
            constraints={"max_charts": request.max_charts},
        )
        plan_result = await plan_dashboard(plan_request, ctx)

    if isinstance(plan_result, str):
        from axbi.utils import json as axbi_json

        plan_result = axbi_json.loads(plan_result)

    plan_data = plan_result.get("plan", {})
    plan_warnings = plan_result.get("warnings", [])
    all_warnings.extend(plan_warnings)

    if not plan_data:
        duration = int((time.time() - start_time) * 1000)
        steps.append(
            WorkflowStepStatus(
                name="plan",
                status="failed",
                detail="No plan produced",
                duration_ms=int((time.time() - plan_started) * 1000),
            )
        )
        return PromptToDashboardResponse(
            error="Dashboard planning failed. No plan produced.",
            warnings=all_warnings,
            total_duration_ms=duration,
            status="failed",
            steps=steps,
        ).model_dump()

    # Reconstruct plan into DashboardPlanFull for compose_dashboard
    try:
        plan_full = DashboardPlanFull.model_validate(plan_data)
    except Exception:
        logger.warning("Plan validation failed; building minimal plan", exc_info=True)
        plan_full = DashboardPlanFull(
            plan_id=plan_data.get("plan_id", str(uuid.uuid4())),
            title=plan_data.get("title", "Dashboard"),
            description=request.prompt[:200],
            datasets=plan_data.get("datasets", []),
            chart_intents=plan_data.get("chart_intents", []),
            global_filters=plan_data.get("global_filters", []),
            assumptions=plan_data.get("assumptions", []),
            clarifying_questions=plan_data.get("clarifying_questions", []),
            confidence=plan_data.get("confidence", 0.0),
        )

    tool_chain.append("plan_dashboard")
    steps.append(
        WorkflowStepStatus(
            name="plan",
            status="succeeded",
            detail=(
                f"title='{plan_full.title}', charts={len(plan_full.chart_intents)}, "
                f"confidence={plan_full.confidence:.2f}"
            ),
            duration_ms=int((time.time() - plan_started) * 1000),
        )
    )
    await ctx.info(
        f"Plan ready: title='{plan_full.title}', "
        f"charts={len(plan_full.chart_intents)}, confidence={plan_full.confidence:.2f}"
    )

    # Confidence / empty-plan gate: fail loudly instead of composing junk
    from axbi.mcp_service.ai.grounding_utils import plan_should_block_compose

    should_block, block_reason = plan_should_block_compose(
        plan_full.confidence,
        len(plan_full.chart_intents),
        plan_full.clarifying_questions,
        min_confidence=request.min_confidence,
        force=request.force,
    )
    # dry_run still returns the plan for review even when blocked from compose
    if should_block and not request.dry_run:
        duration = int((time.time() - start_time) * 1000)
        await ctx.warning(f"Prompt-to-dashboard blocked: {block_reason}")
        steps.append(
            WorkflowStepStatus(
                name="confidence_gate",
                status="failed",
                detail=block_reason,
            )
        )
        steps.append(
            WorkflowStepStatus(
                name="generate_charts",
                status="skipped",
                detail="Blocked by confidence gate",
            )
        )
        steps.append(
            WorkflowStepStatus(
                name="compose",
                status="skipped",
                detail="Blocked by confidence gate",
            )
        )
        return PromptToDashboardResponse(
            plan=_safe_plan_for_response(plan_full),
            charts=[],
            warnings=all_warnings
            + [
                block_reason,
                "No charts or dashboard were created. "
                "Answer clarifying questions, pin dataset_ids, improve dataset "
                "metrics/descriptions, or retry with force=true.",
            ],
            error=f"Plan confidence gate: {block_reason}",
            total_duration_ms=duration,
            status="blocked",
            steps=steps,
        ).model_dump()
    if should_block and request.dry_run:
        all_warnings.append(f"Would block compose without force: {block_reason}")
        steps.append(
            WorkflowStepStatus(
                name="confidence_gate",
                status="failed",
                detail=f"Would block: {block_reason}",
            )
        )
    else:
        steps.append(
            WorkflowStepStatus(
                name="confidence_gate",
                status="succeeded",
                detail=f"confidence={plan_full.confidence:.2f}",
            )
        )

    # ------------------------------------------------------------------
    # Step 2: Generate each chart from its intent
    # ------------------------------------------------------------------
    await ctx.report_progress(2, 4, "Generating charts from intents")
    charts_started = time.time()
    source_dataset_ids: set[int] = set()

    for idx, intent in enumerate(plan_full.chart_intents):
        chart_purpose = intent.purpose or f"Chart {idx + 1}"
        await ctx.report_progress(
            2,
            4,
            f"Generating chart {idx + 1}/{len(plan_full.chart_intents)}: "
            f"{chart_purpose}",
        )

        # Build prompt from the chart intent. Prefer structured fields so
        # create_chart_from_intent does not re-parse natural language.
        intent_prompt = _build_intent_prompt(intent, request.prompt)
        dataset_id = intent.dataset_id or None

        if isinstance(dataset_id, int):
            source_dataset_ids.add(dataset_id)

        try:
            from axbi.mcp_service.ai.tool.create_chart_from_intent import (
                create_chart_from_intent,
            )

            chart_req = CreateChartFromIntentRequest(
                prompt=intent_prompt,
                dataset_id=dataset_id,
                save_chart=request.save_charts and not request.dry_run,
                chart_type=getattr(intent, "chart_type", None) or None,
                metrics=list(getattr(intent, "metrics", None) or []),
                dimensions=list(getattr(intent, "dimensions", None) or []),
                filters=list(getattr(intent, "filters", None) or []),
                time_range=getattr(intent, "time_range", None),
            )
            chart_result = await create_chart_from_intent(chart_req, ctx)

            if isinstance(chart_result, str):
                from axbi.utils import json as axbi_json

                chart_result = axbi_json.loads(chart_result)

            chart_data = chart_result.get("chart")
            chart_id = chart_data.get("id") if chart_data else None
            chart_name = (
                chart_data.get("slice_name", "")
                if chart_data
                else chart_result.get("chart_name", "")
            )
            chart_type = chart_result.get("chart_type_selected", "")
            chart_confidence = chart_result.get("confidence", 0.0)
            chart_preview = chart_result.get("preview_url")
            chart_warnings = chart_result.get("warnings", [])
            chart_succeeded = bool(chart_result.get("success"))

            chart_status = "succeeded" if chart_succeeded else "failed"
            chart_summaries.append(
                PromptToDashboardChartSummary(
                    chart_id=chart_id,
                    chart_name=chart_name,
                    chart_type=chart_type,
                    purpose=chart_purpose,
                    confidence=chart_confidence,
                    preview_url=chart_preview,
                    warnings=chart_warnings,
                    status=chart_status,
                )
            )

            if chart_succeeded:
                successful_chart_count += 1
            else:
                failed_chart_count += 1

            if chart_id:
                chart_ids.append(chart_id)
                tool_chain.append(f"create_chart_from_intent[{chart_id}]")
            elif not chart_succeeded:
                all_warnings.append(
                    f"Chart '{chart_purpose}' could not be generated: "
                    + "; ".join(chart_warnings[:2])
                )

        except Exception as e:
            logger.warning(
                "Chart generation failed for intent '%s': %s",
                chart_purpose,
                e,
                exc_info=True,
            )
            all_warnings.append(f"Chart '{chart_purpose}' failed: {e}")
            failed_chart_count += 1
            chart_summaries.append(
                PromptToDashboardChartSummary(
                    chart_name="",
                    chart_type="",
                    purpose=chart_purpose,
                    confidence=0.0,
                    warnings=[f"Generation failed: {e}"],
                    status="failed",
                )
            )

    if successful_chart_count and failed_chart_count:
        chart_step_status: str = "succeeded"
        chart_step_detail = (
            f"partial: {successful_chart_count} succeeded, {failed_chart_count} failed"
        )
    elif successful_chart_count:
        chart_step_status = "succeeded"
        chart_step_detail = f"{successful_chart_count} succeeded"
    else:
        chart_step_status = "failed"
        chart_step_detail = f"{failed_chart_count} failed"
    steps.append(
        WorkflowStepStatus(
            name="generate_charts",
            status=chart_step_status,
            detail=chart_step_detail,
            duration_ms=int((time.time() - charts_started) * 1000),
        )
    )

    if request.dry_run:
        duration = int((time.time() - start_time) * 1000)
        steps.append(
            WorkflowStepStatus(
                name="compose",
                status="skipped",
                detail="dry_run=true",
            )
        )
        if not successful_chart_count:
            return PromptToDashboardResponse(
                plan=_safe_plan_for_response(plan_full),
                charts=chart_summaries,
                error="No chart previews were successfully generated.",
                warnings=all_warnings,
                total_duration_ms=duration,
                status="failed",
                steps=steps,
                charts_succeeded=successful_chart_count,
                charts_failed=failed_chart_count,
            ).model_dump()
        return PromptToDashboardResponse(
            plan=_safe_plan_for_response(plan_full),
            charts=chart_summaries,
            layout_summary=(
                f"Dry run validated {successful_chart_count} chart preview(s); "
                "no charts or dashboard were created."
            ),
            warnings=all_warnings,
            total_duration_ms=duration,
            status="dry_run",
            steps=steps,
            charts_succeeded=successful_chart_count,
            charts_failed=failed_chart_count,
        ).model_dump()

    if not chart_ids:
        duration = int((time.time() - start_time) * 1000)
        steps.append(
            WorkflowStepStatus(
                name="compose",
                status="skipped",
                detail="No successful charts to compose",
            )
        )
        return PromptToDashboardResponse(
            plan=_safe_plan_for_response(plan_full),
            charts=chart_summaries,
            error="No charts were successfully generated. "
            "Try rephrasing the prompt or specifying dataset_ids.",
            warnings=all_warnings,
            total_duration_ms=duration,
            status="failed",
            steps=steps,
            charts_succeeded=successful_chart_count,
            charts_failed=failed_chart_count,
        ).model_dump()

    # ------------------------------------------------------------------
    # Step 3: Compose the dashboard
    # ------------------------------------------------------------------
    await ctx.report_progress(3, 4, "Composing dashboard")
    tool_chain.append("compose_dashboard")
    compose_started = time.time()

    with mcp_event_log_context(action="mcp.prompt_to_dashboard.compose"):
        from axbi.mcp_service.ai.tool.compose_dashboard import compose_dashboard

        compose_req = ComposeDashboardRequest(
            plan=plan_full,
            chart_ids=chart_ids,
            draft=request.draft,
        )
        compose_result = await compose_dashboard(compose_req, ctx)

    if isinstance(compose_result, str):
        from axbi.utils import json as axbi_json

        compose_result = axbi_json.loads(compose_result)

    compose_error = compose_result.get("error")
    dashboard_data = compose_result.get("dashboard")
    dashboard_url = compose_result.get("dashboard_url")
    layout_summary = compose_result.get("layout_summary", "")
    lineage = compose_result.get("lineage")

    if compose_error:
        duration = int((time.time() - start_time) * 1000)
        steps.append(
            WorkflowStepStatus(
                name="compose",
                status="failed",
                detail=str(compose_error),
                duration_ms=int((time.time() - compose_started) * 1000),
            )
        )
        return PromptToDashboardResponse(
            plan=_safe_plan_for_response(plan_full),
            charts=chart_summaries,
            error=f"Dashboard composition failed: {compose_error}",
            warnings=all_warnings,
            total_duration_ms=duration,
            status="failed",
            steps=steps,
            charts_succeeded=successful_chart_count,
            charts_failed=failed_chart_count,
        ).model_dump()

    dashboard_id = dashboard_data.get("id") if dashboard_data else None
    steps.append(
        WorkflowStepStatus(
            name="compose",
            status="succeeded",
            detail=f"dashboard_id={dashboard_id}",
            duration_ms=int((time.time() - compose_started) * 1000),
        )
    )

    # ------------------------------------------------------------------
    # Step 4: Record audit trail and build response
    # ------------------------------------------------------------------
    await ctx.report_progress(4, 4, "Recording audit trail")

    if dashboard_data and dashboard_data.get("id"):
        _record_artifact(
            artifact_type="dashboard",
            artifact_id=dashboard_data["id"],
            prompt=request.prompt,
            plan_id=plan_full.plan_id,
            tool_chain=tool_chain,
            source_dataset_ids=list(source_dataset_ids),
            confidence=plan_full.confidence,
            validation_summary=(
                f"{successful_chart_count} charts generated, "
                f"{failed_chart_count} failed"
            ),
        )

    duration = int((time.time() - start_time) * 1000)
    workflow_status = "partial" if failed_chart_count else "completed"
    if failed_chart_count:
        all_warnings.append(
            f"Partial success: {failed_chart_count} chart(s) failed; "
            f"dashboard composed with {successful_chart_count} chart(s)."
        )

    await ctx.info(
        f"Prompt-to-dashboard complete: "
        f"dashboard_id={dashboard_data.get('id') if dashboard_data else None}, "
        f"charts={len(chart_ids)}, status={workflow_status}, duration={duration}ms"
    )

    return PromptToDashboardResponse(
        dashboard=dashboard_data,
        dashboard_url=dashboard_url,
        plan=_safe_plan_for_response(plan_full),
        charts=chart_summaries,
        layout_summary=layout_summary,
        lineage=lineage,
        warnings=all_warnings,
        error=None,
        total_duration_ms=duration,
        status=workflow_status,
        steps=steps,
        charts_succeeded=successful_chart_count,
        charts_failed=failed_chart_count,
    ).model_dump()


def _build_intent_prompt(  # noqa: C901
    intent: Any, dashboard_prompt: str
) -> str:
    """Build a create_chart_from_intent prompt from a chart intent.

    Combines the intent's purpose, metrics, dimensions, filters, and
    time range into a natural language prompt that the intent mapper
    can resolve.
    """
    parts: list[str] = []

    if purpose := getattr(intent, "purpose", "") or "":
        parts.append(purpose)

    if metrics := getattr(intent, "metrics", []) or []:
        parts.append(f"using metrics: {', '.join(str(m) for m in metrics)}")

    if dimensions := getattr(intent, "dimensions", []) or []:
        parts.append(f"broken down by {', '.join(str(d) for d in dimensions)}")

    if time_range := getattr(intent, "time_range", None):
        parts.append(f"for {time_range}")

    if filters := getattr(intent, "filters", []) or []:
        filter_parts = []
        for f in filters:
            if isinstance(f, dict):
                col = f.get("column", "")
                val = f.get("value", "")
                op = f.get("operator", "eq")
                filter_parts.append(f"{col} {op} {val}")
        if filter_parts:
            parts.append(f"filtered by {', '.join(filter_parts)}")

    if chart_type := getattr(intent, "chart_type", ""):
        parts.append(f"as a {chart_type} chart")

    if parts:
        return ". ".join(parts)

    # Fallback: use the dashboard prompt
    return dashboard_prompt


def _safe_plan_for_response(plan_full: DashboardPlanFull) -> Any:
    """Build a DashboardPlan suitable for the response (without forward refs)."""
    from axbi.mcp_service.ai.schemas import DashboardPlan, DashboardPlanSection

    return DashboardPlan(
        plan_id=plan_full.plan_id,
        title=plan_full.title,
        description=plan_full.description,
        datasets=plan_full.datasets,
        chart_intents=plan_full.chart_intents,
        global_filters=plan_full.global_filters,
        sections=[
            DashboardPlanSection(
                title="Charts",
                chart_intents=[ci.model_dump() for ci in plan_full.chart_intents],
            )
        ],
        layout_hints=plan_full.layout_hints,
        assumptions=plan_full.assumptions,
        clarifying_questions=plan_full.clarifying_questions,
        confidence=plan_full.confidence,
    )

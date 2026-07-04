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
"""MCP tool: evaluate_ai_answer

Evaluation harness for prompt-to-dashboard. Records the prompt, expected
result, actual result, and computed scores into the ``ai_evaluation_runs``
table so that the GenAI BI pipeline can be regression-tested across model
or prompt changes.
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any

from pydantic import BaseModel, Field
from superset_core.mcp.decorators import tool, ToolAnnotations

try:
    from fastmcp import Context
except ModuleNotFoundError:
    Context = Any

from superset.mcp_service.ai.schemas import (
    PromptToDashboardRequest,
)
from superset.mcp_service.privacy import (
    requires_data_model_metadata_access,
    user_can_view_data_model_metadata,
)
from superset.mcp_service.utils.logging_utils import mcp_event_log_context

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class EvalExpectedResult(BaseModel):
    """Expected result specification for evaluation."""

    chart_count: int | None = Field(
        default=None,
        description="Expected number of charts (or None to skip this check).",
    )
    chart_types: list[str] | None = Field(
        default=None,
        description="Expected chart types (order-independent subset check).",
    )
    dataset_count: int | None = Field(
        default=None,
        description="Expected number of distinct datasets used.",
    )
    title_keywords: list[str] | None = Field(
        default=None,
        description="Keywords that must appear in the dashboard title.",
    )
    has_filters: bool | None = Field(
        default=None,
        description="Whether the dashboard should have global filters.",
    )
    min_confidence: float | None = Field(
        default=None,
        description="Minimum acceptable confidence score.",
    )


class EvalScore(BaseModel):
    """A single evaluation score dimension."""

    dimension: str = Field(description="Scoring dimension name")
    score: float = Field(
        description="Score from 0.0 (fail) to 1.0 (pass)", ge=0.0, le=1.0
    )
    detail: str = Field(default="", description="Human-readable explanation")


class EvaluateAIAnswerRequest(BaseModel):
    """Request schema for evaluate_ai_answer."""

    prompt: str = Field(
        description="The natural language prompt to evaluate.",
    )
    expected: EvalExpectedResult = Field(
        description="Expected result specification.",
    )
    dataset_ids: list[int] = Field(
        default_factory=list,
        description="Optional: pin to specific dataset IDs.",
    )
    max_charts: int = Field(
        default=6,
        ge=1,
        le=12,
        description="Maximum charts to generate.",
    )
    record_run: bool = Field(
        default=True,
        description="Whether to persist the evaluation run to the database.",
    )


class EvaluateAIAnswerResponse(BaseModel):
    """Response schema for evaluate_ai_answer."""

    eval_id: str = Field(default="", description="Unique evaluation run ID.")
    passed: bool = Field(description="Overall pass/fail.")
    scores: list[EvalScore] = Field(default_factory=list)
    overall_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Weighted average score across dimensions.",
    )
    actual: dict[str, Any] = Field(
        default_factory=dict,
        description="Actual result from prompt_to_dashboard.",
    )
    expected: dict[str, Any] = Field(
        default_factory=dict,
        description="Expected result specification used.",
    )
    duration_ms: int = Field(default=0)
    warnings: list[str] = Field(default_factory=list)
    error: str | None = Field(default=None)


# ---------------------------------------------------------------------------
# Scoring helpers
# ---------------------------------------------------------------------------


def _score_chart_count(expected: int | None, actual: int) -> EvalScore:
    """Score whether the chart count matches."""
    if expected is None:
        return EvalScore(
            dimension="chart_count", score=1.0, detail="Skipped (not specified)."
        )
    diff = abs(expected - actual)
    if diff == 0:
        return EvalScore(
            dimension="chart_count",
            score=1.0,
            detail=f"Exact match: {actual} chart(s).",
        )
    # Partial credit: 1 chart off = 0.5, 2+ off = 0.0
    score = max(0.0, 1.0 - diff * 0.5)
    return EvalScore(
        dimension="chart_count",
        score=score,
        detail=f"Expected {expected}, got {actual}.",
    )


def _score_chart_types(
    expected: list[str] | None, actual_types: list[str]
) -> EvalScore:
    """Score whether expected chart types are present."""
    if expected is None:
        return EvalScore(
            dimension="chart_types", score=1.0, detail="Skipped (not specified)."
        )
    if not expected:
        return EvalScore(
            dimension="chart_types", score=1.0, detail="No types expected."
        )
    actual_lower = {t.lower() for t in actual_types}
    matches = sum(1 for e in expected if e.lower() in actual_lower)
    score = matches / len(expected) if expected else 0.0
    return EvalScore(
        dimension="chart_types",
        score=score,
        detail=f"{matches}/{len(expected)} expected types found in {actual_types}.",
    )


def _score_dataset_count(expected: int | None, actual: int) -> EvalScore:
    """Score whether the dataset count matches."""
    if expected is None:
        return EvalScore(
            dimension="dataset_count", score=1.0, detail="Skipped (not specified)."
        )
    score = 1.0 if expected == actual else max(0.0, 1.0 - abs(expected - actual) * 0.5)
    return EvalScore(
        dimension="dataset_count",
        score=score,
        detail=f"Expected {expected}, got {actual}.",
    )


def _score_title_keywords(expected: list[str] | None, title: str) -> EvalScore:
    """Score whether title contains expected keywords."""
    if expected is None:
        return EvalScore(
            dimension="title_keywords", score=1.0, detail="Skipped (not specified)."
        )
    if not expected:
        return EvalScore(
            dimension="title_keywords", score=1.0, detail="No keywords expected."
        )
    title_lower = title.lower()
    matches = sum(1 for kw in expected if kw.lower() in title_lower)
    score = matches / len(expected)
    return EvalScore(
        dimension="title_keywords",
        score=score,
        detail=f"{matches}/{len(expected)} keywords found in '{title}'.",
    )


def _score_has_filters(expected: bool | None, actual_count: int) -> EvalScore:
    """Score whether filters are present/absent as expected."""
    if expected is None:
        return EvalScore(
            dimension="has_filters", score=1.0, detail="Skipped (not specified)."
        )
    if expected == (has_filters := actual_count > 0):
        return EvalScore(
            dimension="has_filters",
            score=1.0,
            detail=f"{'Has' if has_filters else 'No'} filters, as expected.",
        )
    return EvalScore(
        dimension="has_filters",
        score=0.0,
        detail=f"Expected filters={expected}, got {actual_count} filter(s).",
    )


def _score_confidence(min_confidence: float | None, actual: float) -> EvalScore:
    """Score whether confidence meets the minimum threshold."""
    if min_confidence is None:
        return EvalScore(
            dimension="confidence", score=1.0, detail="Skipped (not specified)."
        )
    if actual >= min_confidence:
        return EvalScore(
            dimension="confidence",
            score=1.0,
            detail=f"Confidence {actual:.2f} >= {min_confidence:.2f}.",
        )
    # Partial credit proportional to how close
    score = actual / min_confidence if min_confidence > 0 else 0.0
    return EvalScore(
        dimension="confidence",
        score=min(score, 1.0),
        detail=f"Confidence {actual:.2f} < {min_confidence:.2f}.",
    )


def _record_eval_run(
    eval_id: str,
    prompt: str,
    expected: dict[str, Any],
    actual: dict[str, Any],
    scores: list[dict[str, Any]],
    model: str,
) -> None:
    """Persist the evaluation run to ai_evaluation_runs.

    Silently degrades if the table doesn't exist yet.
    """
    try:
        from superset import db
        from superset.models.ai import AIEvaluationRun
        from superset.utils import json as superset_json

        record = AIEvaluationRun()
        record.uuid = uuid.UUID(eval_id) if len(eval_id) == 36 else uuid.uuid4()
        record.prompt = prompt[:4000]
        record.expected_result = superset_json.dumps(expected)
        record.actual_result = superset_json.dumps(actual)
        record.scores = superset_json.dumps(scores)
        record.model = model
        record.tool_versions = superset_json.dumps(
            {"prompt_to_dashboard": "1.0", "evaluate_ai_answer": "1.0"}
        )

        db.session.add(record)
        db.session.commit()  # pylint: disable=consider-using-transaction
    except Exception:
        logger.debug("Evaluation run recording unavailable", exc_info=True)


# ---------------------------------------------------------------------------
# Tool
# ---------------------------------------------------------------------------


@tool(
    tags=["ai", "eval"],
    class_permission_name="Dashboard",
    annotations=ToolAnnotations(
        title="Evaluate AI answer",
        readOnlyHint=False,
        destructiveHint=False,
    ),
)
@requires_data_model_metadata_access
async def evaluate_ai_answer(  # noqa: C901
    request: EvaluateAIAnswerRequest, ctx: Context
) -> dict[str, Any]:
    """Evaluate the prompt-to-dashboard pipeline against expected results.

    Runs the full prompt_to_dashboard pipeline and scores the output against
    an expected-result specification. Results are persisted to the
    ai_evaluation_runs table for regression tracking.

    IMPORTANT FOR LLM CLIENTS:
    - Use this to regression-test prompt-to-dashboard quality
    - Specify expected chart_count, chart_types, title_keywords, etc.
    - Returns per-dimension scores and an overall pass/fail
    - Set record_run=False to skip persistence (dry run)

    Example usage:
    ```json
    {
        "prompt": "Create a sales dashboard with revenue trends",
        "expected": {
            "chart_count": 4,
            "chart_types": ["echarts_timeseries_line", "big_number"],
            "title_keywords": ["sales"],
            "min_confidence": 0.5
        },
        "max_charts": 6
    }
    ```
    """
    start_time = time.time()
    eval_id = str(uuid.uuid4())
    warnings: list[str] = []

    await ctx.info(
        "Evaluating AI answer: eval_id=%s, prompt='%s'" % (eval_id, request.prompt[:80])
    )

    if not user_can_view_data_model_metadata():
        await ctx.warning("Evaluation blocked by privacy controls")
        return EvaluateAIAnswerResponse(
            eval_id=eval_id,
            passed=False,
            error="You don't have permission to access dataset metadata.",
        ).model_dump()

    # Step 1: Run the pipeline
    await ctx.report_progress(1, 3, "Running prompt-to-dashboard pipeline")

    actual_result: dict[str, Any] = {}
    pipeline_error: str | None = None

    with mcp_event_log_context(action="mcp.evaluate_ai_answer.pipeline"):
        try:
            from superset.mcp_service.ai.tool.prompt_to_dashboard import (
                prompt_to_dashboard,
            )

            pipeline_req = PromptToDashboardRequest(
                prompt=request.prompt,
                dataset_ids=request.dataset_ids,
                max_charts=request.max_charts,
                draft=True,
                save_charts=False,  # Don't persist test charts
            )
            pipeline_result = await prompt_to_dashboard(pipeline_req, ctx)

            if isinstance(pipeline_result, str):
                from superset.utils import json as superset_json

                pipeline_result = superset_json.loads(pipeline_result)

            actual_result = pipeline_result
            pipeline_error = pipeline_result.get("error")

        except Exception as e:
            logger.warning("Pipeline execution failed: %s", e, exc_info=True)
            pipeline_error = str(e)

    if pipeline_error:
        warnings.append(f"Pipeline error: {pipeline_error}")

    # Step 2: Score the result
    await ctx.report_progress(2, 3, "Scoring results")

    charts = actual_result.get("charts", [])
    plan = actual_result.get("plan") or {}
    chart_types = [c.get("chart_type", "") for c in charts if c.get("chart_type")]
    dashboard = actual_result.get("dashboard") or {}
    title = dashboard.get("title", plan.get("title", ""))
    datasets = plan.get("datasets", [])
    filters = plan.get("global_filters", [])
    confidence = plan.get("confidence", 0.0)

    scores = [
        _score_chart_count(request.expected.chart_count, len(charts)),
        _score_chart_types(request.expected.chart_types, chart_types),
        _score_dataset_count(request.expected.dataset_count, len(datasets)),
        _score_title_keywords(request.expected.title_keywords, title),
        _score_has_filters(request.expected.has_filters, len(filters)),
        _score_confidence(request.expected.min_confidence, confidence),
    ]

    # Overall score: weighted average (equal weights for now)
    active_scores = [s.score for s in scores if s.detail and "Skipped" not in s.detail]
    overall_score = sum(active_scores) / len(active_scores) if active_scores else 1.0
    passed = overall_score >= 0.7 and pipeline_error is None

    actual_summary = {
        "chart_count": len(charts),
        "chart_types": chart_types,
        "dataset_count": len(datasets),
        "title": title,
        "filter_count": len(filters),
        "confidence": confidence,
        "dashboard_id": dashboard.get("id"),
        "pipeline_error": pipeline_error,
    }

    expected_dict = request.expected.model_dump()

    # Step 3: Record the run
    await ctx.report_progress(3, 3, "Recording evaluation run")

    if request.record_run:
        with mcp_event_log_context(action="mcp.evaluate_ai_answer.record"):
            _record_eval_run(
                eval_id=eval_id,
                prompt=request.prompt,
                expected=expected_dict,
                actual=actual_summary,
                scores=[s.model_dump() for s in scores],
                model="",  # LLM model is not known at this level
            )

    duration = int((time.time() - start_time) * 1000)

    await ctx.info(
        "Evaluation complete: eval_id=%s, passed=%s, score=%.2f, duration=%dms"
        % (eval_id, passed, overall_score, duration)
    )

    return EvaluateAIAnswerResponse(
        eval_id=eval_id,
        passed=passed,
        scores=scores,
        overall_score=overall_score,
        actual=actual_summary,
        expected=expected_dict,
        duration_ms=duration,
        warnings=warnings,
        error=pipeline_error,
    ).model_dump()

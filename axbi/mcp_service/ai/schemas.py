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
"""Pydantic schemas for GenAI BI MCP tool contracts.

These schemas define the request/response structures for the
AI-powered MCP tools. They serve as both validation contracts
and documentation for the tool interfaces.
"""

from __future__ import annotations

import uuid
from typing import Any, cast, Literal

from pydantic import BaseModel, Field, field_validator

from axbi.mcp_service.utils.sanitization import escape_llm_context_delimiters


def _escape_optional_text(v: str | None) -> str | None:
    """Escape MCP context delimiters in optional text."""
    if v is None:
        return None
    return cast(str, escape_llm_context_delimiters(v))


def _escape_text_list(v: list[str]) -> list[str]:
    """Escape MCP context delimiters in a list of text values."""
    return cast(list[str], escape_llm_context_delimiters(v))


def _escape_metadata_dict(v: dict[str, Any]) -> dict[str, Any]:
    """Escape MCP context delimiters in metadata dictionaries."""
    return cast(dict[str, Any], escape_llm_context_delimiters(v))


# ---------------------------------------------------------------------------
# search_business_assets
# ---------------------------------------------------------------------------


class AssetSearchRequest(BaseModel):
    """Request schema for search_business_assets."""

    query: str = Field(description="Natural language search query")
    asset_types: list[str] = Field(
        default_factory=list,
        description="Asset types to include: dataset, chart, dashboard, metric",
    )
    include_certified_only: bool = Field(
        default=False,
        description="Only return certified assets",
    )
    limit: int = Field(default=10, ge=1, le=100)


class AssetResult(BaseModel):
    """Single asset in search results."""

    asset_type: str
    id: int
    uuid: str
    name: str
    description: str | None = None
    certified: bool = False
    relevance_score: float | None = None
    relevance_reason: str | None = None
    owners: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)

    @field_validator(
        "asset_type",
        "uuid",
        "name",
        "description",
        "relevance_reason",
    )
    @classmethod
    def escape_text_field(cls, v: str | None) -> str | None:
        """Escape MCP context delimiters in asset metadata."""
        return _escape_optional_text(v)

    @field_validator("owners", "tags")
    @classmethod
    def escape_text_list(cls, v: list[str]) -> list[str]:
        """Escape MCP context delimiters in asset metadata lists."""
        return _escape_text_list(v)


class AssetSearchResponse(BaseModel):
    """Response schema for search_business_assets."""

    assets: list[AssetResult] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    @field_validator("warnings")
    @classmethod
    def escape_warnings(cls, v: list[str]) -> list[str]:
        """Escape MCP context delimiters in warning text."""
        return _escape_text_list(v)


# ---------------------------------------------------------------------------
# describe_dataset_for_ai
# ---------------------------------------------------------------------------


class DatasetDescriptionRequest(BaseModel):
    """Request schema for describe_dataset_for_ai."""

    dataset_id: int
    include_sample_values: bool = Field(default=False)
    include_usage_stats: bool = Field(default=True)


class ColumnDescription(BaseModel):
    """AI-ready description of a dataset column."""

    name: str
    type: str
    description: str | None = None
    aliases: list[str] = Field(default_factory=list)
    is_dimension: bool = False
    sample_values: list[str] = Field(
        default_factory=list,
        description=(
            "Bounded sample values when GENAI_LLM_ALLOW_BOUNDED_SAMPLES is "
            "enabled and the client requests them; empty otherwise."
        ),
    )

    @field_validator("name", "type", "description")
    @classmethod
    def escape_text_field(cls, v: str | None) -> str | None:
        """Escape MCP context delimiters in column metadata."""
        return _escape_optional_text(v)

    @field_validator("aliases", "sample_values")
    @classmethod
    def escape_aliases(cls, v: list[str]) -> list[str]:
        """Escape MCP context delimiters in semantic aliases / samples."""
        return _escape_text_list(v)


class MetricDescription(BaseModel):
    """AI-ready description of a saved metric."""

    name: str
    expression: str
    description: str | None = None

    @field_validator("name", "expression", "description")
    @classmethod
    def escape_text_field(cls, v: str | None) -> str | None:
        """Escape MCP context delimiters in metric metadata."""
        return _escape_optional_text(v)


class DatasetDescription(BaseModel):
    """AI-ready description of a dataset."""

    id: int
    name: str
    description: str | None = None
    certified: bool = False
    main_time_column: str | None = None
    columns: list[ColumnDescription] = Field(default_factory=list)
    metrics: list[MetricDescription] = Field(default_factory=list)
    privacy: dict[str, Any] = Field(default_factory=dict)
    grounding: dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Governed semantic contract summary: measures, glossary, "
            "instructions, policies, and time columns when available."
        ),
    )

    @field_validator("name", "description", "main_time_column")
    @classmethod
    def escape_text_field(cls, v: str | None) -> str | None:
        """Escape MCP context delimiters in dataset metadata."""
        return _escape_optional_text(v)

    @field_validator("privacy", "grounding")
    @classmethod
    def escape_privacy_metadata(cls, v: dict[str, Any]) -> dict[str, Any]:
        """Escape MCP context delimiters in privacy/grounding metadata."""
        return _escape_metadata_dict(v)


class DatasetDescriptionResponse(BaseModel):
    """Response schema for describe_dataset_for_ai."""

    dataset: DatasetDescription
    warnings: list[str] = Field(default_factory=list)

    @field_validator("warnings")
    @classmethod
    def escape_warnings(cls, v: list[str]) -> list[str]:
        """Escape MCP context delimiters in warning text."""
        return _escape_text_list(v)


# ---------------------------------------------------------------------------
# plan_dashboard
# ---------------------------------------------------------------------------


class DashboardPlanRequest(BaseModel):
    """Request schema for plan_dashboard."""

    prompt: str
    dataset_candidates: list[int] = Field(default_factory=list)
    constraints: dict[str, Any] = Field(default_factory=dict)


class DashboardPlanSection(BaseModel):
    """A section within a dashboard plan."""

    title: str
    chart_intents: list[dict[str, Any]] = Field(default_factory=list)


class DashboardPlan(BaseModel):
    """Structured dashboard plan from the planner.

    Carries the full planning context including chart intents, datasets,
    confidence, assumptions, and clarifying questions so downstream tools
    (compose_dashboard, validate_chart) can reason about the plan.
    """

    plan_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique plan session ID for lineage tracking",
    )
    title: str
    description: str = Field(
        default="", description="Dashboard description / business goal"
    )
    datasets: list[dict[str, Any]] = Field(
        default_factory=list, description="Datasets discovered"
    )
    sections: list[DashboardPlanSection] = Field(default_factory=list)
    chart_intents: list[ChartIntentDetail] = Field(
        default_factory=list, description="Chart specifications"
    )
    global_filters: list[dict[str, Any]] = Field(
        default_factory=list, description="Global filter specs"
    )
    layout_hints: dict[str, Any] = Field(
        default_factory=dict, description="Layout suggestions"
    )
    assumptions: list[str] = Field(default_factory=list, description="Assumptions made")
    clarifying_questions: list[str] = Field(
        default_factory=list, description="Questions for the user"
    )
    confidence: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Overall confidence score"
    )


class ChartIntentDetail(BaseModel):
    """Detailed intent for a single chart within a dashboard plan."""

    purpose: str = Field(description="What this chart should show")
    chart_type: str = Field(
        description="Suggested chart type (e.g. 'xy', 'big_number', 'table', 'pie')"
    )
    dataset_id: int | str = Field(description="Dataset ID to use")
    metrics: list[str] = Field(
        default_factory=list, description="Metric names or expressions"
    )
    dimensions: list[str] = Field(
        default_factory=list, description="Dimension column names"
    )
    filters: list[dict[str, Any]] = Field(
        default_factory=list, description="Filter specifications"
    )
    time_range: str | None = Field(
        default=None, description="Time range (e.g. 'Last 90 days')"
    )


# Resolve forward references: DashboardPlan references ChartIntentDetail
# which is defined above, but the annotation was a string under
# ``from __future__ import annotations``. Rebuild after both are defined.
DashboardPlan.model_rebuild()


class DashboardPlanFull(BaseModel):
    """Full dashboard plan from the planner (internal LLM working model)."""

    plan_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique plan session ID for lineage tracking",
    )
    title: str = Field(description="Dashboard title")
    description: str = Field(
        default="", description="Dashboard description / business goal"
    )
    datasets: list[dict[str, Any]] = Field(
        default_factory=list, description="Datasets discovered"
    )
    chart_intents: list[ChartIntentDetail] = Field(
        default_factory=list, description="Chart specifications"
    )
    global_filters: list[dict[str, Any]] = Field(
        default_factory=list, description="Global filter specs"
    )
    layout_hints: dict[str, Any] = Field(
        default_factory=dict, description="Layout suggestions"
    )
    assumptions: list[str] = Field(default_factory=list, description="Assumptions made")
    clarifying_questions: list[str] = Field(
        default_factory=list, description="Questions for the user"
    )
    confidence: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Overall confidence score"
    )


class DashboardPlanResponse(BaseModel):
    """Response schema for plan_dashboard."""

    plan: DashboardPlan
    warnings: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# create_chart_from_intent
# ---------------------------------------------------------------------------


class CreateChartFromIntentRequest(BaseModel):
    """Request schema for create_chart_from_intent."""

    prompt: str = Field(
        description="What the user wants to visualize, in plain English. "
        "Example: 'Show me monthly revenue trend for the last year'"
    )
    dataset_id: int | str | None = Field(
        default=None,
        description="Optional: pin to a specific dataset ID. "
        "When omitted, the best dataset is discovered automatically.",
    )
    save_chart: bool = Field(
        default=True,
        description=(
            "Whether to save the chart permanently (True) or preview only (False)"
        ),
    )
    max_preview_rows: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="Maximum rows for preview data",
    )
    # Structured fields from plan_dashboard chart intents. When present, the
    # tool builds chart config deterministically instead of re-parsing NL.
    chart_type: str | None = Field(
        default=None,
        description=(
            "Optional structured chart type from a plan intent "
            "(xy, big_number, table, pie, pivot_table). Prefer this over "
            "embedding chart type only in the prompt."
        ),
    )
    metrics: list[str] = Field(
        default_factory=list,
        description="Optional metric names from a plan intent",
    )
    dimensions: list[str] = Field(
        default_factory=list,
        description="Optional dimension column names from a plan intent",
    )
    filters: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Optional structured filters from a plan intent",
    )
    time_range: str | None = Field(
        default=None,
        description="Optional time range (e.g. 'Last 90 days')",
    )
    kind: str | None = Field(
        default=None,
        description="Optional xy kind: line, bar, area, scatter",
    )


class CreateChartFromIntentResponse(BaseModel):
    """Response schema for create_chart_from_intent."""

    chart: dict[str, Any] | None = Field(
        default=None,
        description=(
            "Created chart metadata (id, name, viz_type, url), or None on failure"
        ),
    )
    chart_name: str = Field(
        default="",
        description="Generated chart name, including for preview-only charts.",
    )
    form_data: dict[str, Any] | None = Field(
        default=None,
        description="Validated AxBI form data for a preview or saved chart.",
    )
    success: bool = Field(
        default=False,
        description="Whether the chart intent produced a valid chart or preview.",
    )
    dataset_used: dict[str, Any] | None = Field(
        default=None,
        description="Dataset that was selected (id, name)",
    )
    chart_type_selected: str = Field(
        default="",
        description="Chart type that was chosen (e.g. 'echarts_timeseries_line')",
    )
    explanation: str = Field(
        default="",
        description="Why this chart type, these metrics, and dimensions were selected",
    )
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Confidence score (0-1) for the intent mapping",
    )
    warnings: list[str] = Field(default_factory=list)
    preview_url: str | None = Field(
        default=None,
        description="URL to preview the chart interactively",
    )
    alternatives: list[str] = Field(
        default_factory=list,
        description="Suggested alternative visualizations the user might prefer",
    )


# ---------------------------------------------------------------------------
# compose_dashboard
# ---------------------------------------------------------------------------


class NarrativeBlock(BaseModel):
    """A text/narrative block to include in a dashboard."""

    content: str = Field(description="Markdown or plain text content")
    position: str = Field(
        default="after",
        description="Where to place relative to charts: 'before', 'after', 'between'",
    )


class ComposeDashboardRequest(BaseModel):
    """Request schema for compose_dashboard."""

    plan: DashboardPlanFull = Field(
        description="The dashboard plan (from plan_dashboard response)",
    )
    chart_ids: list[int] = Field(
        description=(
            "Chart IDs created for this dashboard (from create_chart_from_intent calls)"
        ),
        min_length=1,
    )
    draft: bool = Field(
        default=True,
        description=(
            "Create as draft (unpublished). Set to False to publish immediately."
        ),
    )
    narrative_blocks: list[NarrativeBlock] | None = Field(
        default=None,
        description="Optional text blocks to include in the dashboard",
    )


class ComposeDashboardResponse(BaseModel):
    """Response schema for compose_dashboard."""

    dashboard: dict[str, Any] | None = Field(
        default=None,
        description="Created dashboard metadata (id, title, url)",
    )
    dashboard_url: str | None = Field(default=None)
    layout_summary: str = Field(
        default="",
        description="Human-readable summary of the dashboard layout",
    )
    lineage: dict[str, Any] | None = Field(
        default=None,
        description=(
            "AI lineage metadata (plan_id, tool_chain, source_datasets, confidence)"
        ),
    )
    warnings: list[str] = Field(default_factory=list)
    error: str | None = Field(default=None)


# ---------------------------------------------------------------------------
# explain_dashboard
# ---------------------------------------------------------------------------


class ExplainDashboardRequest(BaseModel):
    """Request schema for explain_dashboard."""

    dashboard_id: int | str = Field(
        description="Dashboard ID, UUID, or slug to explain",
    )
    question: str | None = Field(
        default=None,
        description="Optional specific question about the dashboard. "
        "When omitted, returns an overview summary.",
    )
    scope: Literal["overview", "chart", "data"] = Field(
        default="overview",
        description="Scope of the explanation: 'overview' for summary, "
        "'chart' for chart-level detail, 'data' for data analysis",
    )


class ExplainDashboardResponse(BaseModel):
    """Response schema for explain_dashboard."""

    summary: str = Field(
        default="", description="Dashboard summary or answer to question"
    )
    source_charts: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Charts referenced in the explanation",
    )
    key_metrics: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Key metrics found across the dashboard's charts",
    )
    caveats: list[str] = Field(
        default_factory=list,
        description="Caveats or limitations to be aware of",
    )
    follow_up_suggestions: list[str] = Field(
        default_factory=list,
        description="Suggested follow-up questions or actions",
    )
    warnings: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# suggest_chart_improvements
# ---------------------------------------------------------------------------


class ChartSuggestion(BaseModel):
    """A single chart improvement suggestion."""

    reason: str = Field(description="Why this change would improve the chart")
    config_changes: dict[str, Any] = Field(
        default_factory=dict,
        description="Config patch to apply via update_chart",
    )
    preview_config: dict[str, Any] | None = Field(
        default=None,
        description="Full config for generating a preview with generate_chart",
    )


class SuggestChartImprovementsRequest(BaseModel):
    """Request schema for suggest_chart_improvements."""

    chart_id: int | str = Field(
        description="Chart ID or UUID to analyze",
    )
    goal: str | None = Field(
        default=None,
        description=(
            "Optional improvement goal "
            "(e.g. 'Make this easier to read', "
            "'Show trends more clearly'). "
            "When omitted, general improvements are suggested."
        ),
    )


class SuggestChartImprovementsResponse(BaseModel):
    """Response schema for suggest_chart_improvements."""

    current_analysis: str = Field(
        default="",
        description="Analysis of the current chart configuration",
    )
    suggestions: list[ChartSuggestion] = Field(
        default_factory=list,
        description="Improvement suggestions ranked by impact",
    )
    warnings: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# validate_chart
# ---------------------------------------------------------------------------


class ValidateChartRequest(BaseModel):
    """Request schema for validate_chart."""

    dataset_id: int = Field(description="Dataset ID to validate the config against")
    config: dict[str, Any] = Field(
        description=(
            "Chart configuration dict (same shape as GenerateChartRequest.config)"
        ),
    )


class ValidateChartResponse(BaseModel):
    """Response schema for validate_chart."""

    is_valid: bool = Field(description="Whether the chart config is valid")
    errors: list[str] = Field(
        default_factory=list, description="Validation error messages"
    )
    warnings: list[str] = Field(
        default_factory=list, description="Non-blocking warnings"
    )
    normalized_config: dict[str, Any] | None = Field(
        default=None,
        description="Normalized config after column name correction (if valid)",
    )


# ---------------------------------------------------------------------------
# prompt_to_dashboard (single-call orchestrator)
# ---------------------------------------------------------------------------


class PromptToDashboardRequest(BaseModel):
    """Request schema for prompt_to_dashboard single-call orchestrator."""

    prompt: str = Field(
        description="Natural language description of the dashboard to create. "
        "Example: 'Create an executive sales dashboard with revenue trends "
        "by region, top products, and quarterly KPIs.'"
    )
    dataset_ids: list[int] = Field(
        default_factory=list,
        description="Optional: pin to specific dataset IDs. "
        "When empty, datasets are auto-discovered from the prompt.",
    )
    plan: DashboardPlan | None = Field(
        default=None,
        description=(
            "Optional reviewed plan to execute. When supplied, the orchestrator "
            "validates and uses it without planning again."
        ),
    )
    max_charts: int = Field(
        default=6,
        ge=1,
        le=12,
        description="Maximum number of charts to generate.",
    )
    draft: bool = Field(
        default=True,
        description="Create as draft (unpublished). Set False to publish.",
    )
    save_charts: bool = Field(
        default=True,
        description="Save individual charts permanently.",
    )
    dry_run: bool = Field(
        default=False,
        description=(
            "Validate the plan and chart previews without creating charts or a "
            "dashboard."
        ),
    )
    min_confidence: float = Field(
        default=0.25,
        ge=0.0,
        le=1.0,
        description=(
            "Minimum plan confidence required before creating charts/dashboard. "
            "Below this threshold the tool returns the plan and clarifying "
            "questions without mutations (unless force=true)."
        ),
    )
    force: bool = Field(
        default=False,
        description=(
            "Bypass the low-confidence gate and create artifacts even when "
            "plan confidence is below min_confidence."
        ),
    )


class PromptToDashboardChartSummary(BaseModel):
    """Summary of a single chart generated by the orchestrator."""

    chart_id: int | None = None
    chart_name: str = ""
    chart_type: str = ""
    purpose: str = ""
    confidence: float = 0.0
    preview_url: str | None = None
    warnings: list[str] = Field(default_factory=list)
    status: Literal["succeeded", "failed", "skipped"] = Field(
        default="succeeded",
        description="Per-chart generation outcome",
    )


class WorkflowStepStatus(BaseModel):
    """One step in the prompt-to-dashboard workflow."""

    name: str = Field(description="Step name, e.g. plan, generate_charts, compose")
    status: Literal["pending", "running", "succeeded", "failed", "skipped"] = "pending"
    detail: str = Field(default="", description="Human-readable step detail")
    duration_ms: int = Field(default=0)


class PromptToDashboardResponse(BaseModel):
    """Response schema for prompt_to_dashboard single-call orchestrator."""

    dashboard: dict[str, Any] | None = Field(
        default=None,
        description="Created dashboard metadata (id, title, url)",
    )
    dashboard_url: str | None = None
    plan: DashboardPlan | None = Field(
        default=None,
        description="The dashboard plan that was generated",
    )
    charts: list[PromptToDashboardChartSummary] = Field(
        default_factory=list,
        description="Individual chart summaries",
    )
    layout_summary: str = Field(
        default="",
        description="Human-readable summary of the dashboard layout",
    )
    lineage: dict[str, Any] | None = Field(
        default=None,
        description="AI lineage metadata for audit trail",
    )
    warnings: list[str] = Field(default_factory=list)
    error: str | None = Field(default=None)
    total_duration_ms: int = Field(
        default=0,
        description="Total orchestration time in milliseconds",
    )
    status: Literal[
        "completed",
        "partial",
        "blocked",
        "failed",
        "dry_run",
    ] = Field(
        default="failed",
        description=(
            "Workflow outcome: completed (all charts + dashboard), "
            "partial (some charts failed but dashboard composed), "
            "blocked (confidence gate), failed, or dry_run"
        ),
    )
    steps: list[WorkflowStepStatus] = Field(
        default_factory=list,
        description="Ordered workflow step statuses for agent observability",
    )
    charts_succeeded: int = Field(default=0)
    charts_failed: int = Field(default=0)


# ---------------------------------------------------------------------------
# ask_dashboard_question (dashboard-scoped follow-up Q&A)
# ---------------------------------------------------------------------------


class AskDashboardQuestionRequest(BaseModel):
    """Request schema for ask_dashboard_question."""

    dashboard_id: int | str = Field(
        description="Dashboard ID, UUID, or slug to query.",
    )
    question: str = Field(
        description="Natural language question about the dashboard's data. "
        "Example: 'What was the top-performing region last quarter?'"
    )
    chart_ids: list[int] = Field(
        default_factory=list,
        description="Optional: scope the question to specific charts.",
    )
    generate_follow_up_chart: bool = Field(
        default=False,
        description="When True, attempt to create a chart answering the question.",
    )


class AskDashboardQuestionResponse(BaseModel):
    """Response schema for ask_dashboard_question."""

    answer: str = Field(
        default="",
        description="Answer to the question grounded in dashboard data.",
    )
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Confidence in the answer.",
    )
    sources: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Charts/datasets used to answer the question.",
    )
    follow_up_chart: dict[str, Any] | None = Field(
        default=None,
        description="Generated follow-up chart if requested.",
    )
    caveats: list[str] = Field(
        default_factory=list,
        description="Caveats or limitations of the answer.",
    )
    suggested_next_questions: list[str] = Field(
        default_factory=list,
        description="Suggested follow-up questions.",
    )
    warnings: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# AIGeneratedArtifact (audit trail)
# ---------------------------------------------------------------------------


class AIGeneratedArtifactRecord(BaseModel):
    """Audit record for an AI-generated artifact."""

    uuid: str = ""
    artifact_type: str = Field(description="Type: chart, dashboard, dataset, report")
    artifact_id: int = Field(description="ID of the generated artifact")
    principal_user_id: int | None = Field(
        default=None, description="User who triggered generation"
    )
    source_prompt: str = Field(default="", description="Original user prompt")
    normalized_intent: str = Field(default="", description="Normalized intent summary")
    llm_provider: str = Field(default="", description="LLM provider used")
    llm_model: str = Field(default="", description="LLM model used")
    tool_chain: list[str] = Field(
        default_factory=list, description="Sequence of tools called"
    )
    source_asset_refs: list[int] = Field(
        default_factory=list, description="Dataset IDs used"
    )
    validation_summary: str = Field(
        default="", description="Summary of validation results"
    )
    confidence_score: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Overall confidence"
    )
    plan_id: str | None = Field(default=None, description="Dashboard plan session ID")
    created_on: str | None = None


# ---------------------------------------------------------------------------
# suggest_semantic_enrichment
# ---------------------------------------------------------------------------


class SemanticEnrichmentRequest(BaseModel):
    """Request schema for suggest_semantic_enrichment."""

    dataset_id: int = Field(description="Dataset to analyze for draft enrichments")
    focus: str | None = Field(
        default=None,
        description="Optional focus (e.g. 'synonyms for revenue metrics')",
    )

    @field_validator("focus")
    @classmethod
    def escape_focus(cls, v: str | None) -> str | None:
        """Escape MCP context delimiters in optional focus text."""
        return _escape_optional_text(v)


class SemanticEnrichmentSuggestion(BaseModel):
    """A single draft semantic enrichment (not auto-applied)."""

    object_type: Literal["dataset", "column", "metric"]
    object_name: str
    suggestion_type: Literal["description", "synonym", "relationship"]
    value: str
    related_object: str | None = None
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    rationale: str = ""

    @field_validator("object_name", "value", "related_object", "rationale")
    @classmethod
    def escape_text_field(cls, v: str | None) -> str | None:
        """Escape MCP context delimiters in suggestion text."""
        return _escape_optional_text(v)


class SemanticEnrichmentResponse(BaseModel):
    """Response schema for suggest_semantic_enrichment."""

    suggestions: list[SemanticEnrichmentSuggestion] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    used_llm: bool = False
    provider_type: str | None = None
    model: str | None = None
    draft_only: bool = Field(
        default=True,
        description="Suggestions are drafts; certified fields require human approval.",
    )

    @field_validator("warnings")
    @classmethod
    def escape_warnings(cls, v: list[str]) -> list[str]:
        """Escape MCP context delimiters in warning text."""
        return _escape_text_list(v)

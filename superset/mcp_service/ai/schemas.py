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

from typing import Any, cast, Literal

from pydantic import BaseModel, Field, field_validator

from superset.mcp_service.utils.sanitization import escape_llm_context_delimiters


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

    @field_validator("name", "type", "description")
    @classmethod
    def escape_text_field(cls, v: str | None) -> str | None:
        """Escape MCP context delimiters in column metadata."""
        return _escape_optional_text(v)

    @field_validator("aliases")
    @classmethod
    def escape_aliases(cls, v: list[str]) -> list[str]:
        """Escape MCP context delimiters in semantic aliases."""
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

    @field_validator("name", "description", "main_time_column")
    @classmethod
    def escape_text_field(cls, v: str | None) -> str | None:
        """Escape MCP context delimiters in dataset metadata."""
        return _escape_optional_text(v)

    @field_validator("privacy")
    @classmethod
    def escape_privacy_metadata(cls, v: dict[str, Any]) -> dict[str, Any]:
        """Escape MCP context delimiters in privacy metadata."""
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
    """Structured dashboard plan from the planner."""

    title: str
    business_goal: str | None = None
    global_filters: list[dict[str, Any]] = Field(default_factory=list)
    sections: list[DashboardPlanSection] = Field(default_factory=list)


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


class DashboardPlanFull(BaseModel):
    """Full dashboard plan from the planner."""

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


class CreateChartFromIntentResponse(BaseModel):
    """Response schema for create_chart_from_intent."""

    chart: dict[str, Any] | None = Field(
        default=None,
        description=(
            "Created chart metadata (id, name, viz_type, url), or None on failure"
        ),
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

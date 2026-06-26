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

from typing import Any

from pydantic import BaseModel, Field

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


class AssetSearchResponse(BaseModel):
    """Response schema for search_business_assets."""

    assets: list[AssetResult] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


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


class MetricDescription(BaseModel):
    """AI-ready description of a saved metric."""

    name: str
    expression: str
    description: str | None = None


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


class DatasetDescriptionResponse(BaseModel):
    """Response schema for describe_dataset_for_ai."""

    dataset: DatasetDescription
    warnings: list[str] = Field(default_factory=list)


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


class DashboardPlanResponse(BaseModel):
    """Response schema for plan_dashboard."""

    plan: DashboardPlan
    warnings: list[str] = Field(default_factory=list)

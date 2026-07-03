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
"""MCP tool: upload_and_plan

Convenience tool that uploads a file and produces a dashboard plan in
a single call — no manual chaining required. The file is uploaded to the
auto-provisioned DuckDB, then plan_dashboard is invoked with the new
dataset pinned, returning a full plan (chart intents, dataset selections,
global filters, layout hints) that the caller can review.

After reviewing the plan, the caller can:
- Call ``prompt_to_dashboard`` with ``dataset_ids=[<id>]`` to create the
  dashboard, OR
- Call ``create_chart_from_intent`` for individual charts and then
  ``compose_dashboard`` to assemble them.
"""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, Field
from superset_core.mcp.decorators import tool, ToolAnnotations

try:
    from fastmcp import Context
except ModuleNotFoundError:
    Context = Any

from superset.mcp_service.ai.schemas import (
    DashboardPlan,
    DashboardPlanFull,
    DashboardPlanSection,
)
from superset.mcp_service.privacy import (
    requires_data_model_metadata_access,
    user_can_view_data_model_metadata,
)
from superset.mcp_service.utils.logging_utils import mcp_event_log_context

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------


class UploadAndPlanRequest(BaseModel):
    """Request schema for upload_and_plan convenience tool."""

    file_content: str = Field(
        description="Base64-encoded file content (CSV, Excel, or Parquet)."
    )
    filename: str = Field(
        description="Filename with extension (e.g. 'revenue.xlsx'). "
        "Used to detect file type."
    )
    prompt: str = Field(
        description="Natural language description of the dashboard to plan. "
        "Example: 'Create a revenue dashboard by client and service type.'"
    )
    table_name: str | None = Field(
        default=None,
        description="Optional table name for the uploaded data. "
        "Auto-generated from filename if omitted.",
    )
    sheet_name: str | None = Field(
        default=None,
        description="Excel only: name of the sheet to upload. "
        "If omitted, the first sheet is used.",
    )
    max_charts: int = Field(
        default=6,
        ge=1,
        le=12,
        description="Maximum number of chart intents in the plan.",
    )


class UploadAndPlanResponse(BaseModel):
    """Response schema for upload_and_plan convenience tool."""

    dataset: dict[str, Any] = Field(
        default_factory=dict,
        description="Uploaded dataset info (id, table_name, columns, etc.).",
    )
    plan: DashboardPlan | None = Field(
        default=None,
        description="Dashboard plan with chart intents and dataset metadata.",
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="Warnings or issues encountered during upload/planning.",
    )
    next_steps: str = Field(
        default="",
        description="Instructions for what to call next to create the dashboard.",
    )


# ---------------------------------------------------------------------------
# Tool implementation
# ---------------------------------------------------------------------------


@tool(
    tags=["mutate", "ai"],
    class_permission_name="Dashboard",
    annotations=ToolAnnotations(
        title="Upload and plan",
        readOnlyHint=False,
        destructiveHint=False,
    ),
)
@requires_data_model_metadata_access
async def upload_and_plan(
    request: UploadAndPlanRequest, ctx: Context
) -> dict[str, Any]:
    """Upload a file and produce a dashboard plan in one call.

    Combines two steps into one:
    1. Upload the CSV/Excel/Parquet file to DuckDB (creates a dataset)
    2. Plan a dashboard using the uploaded dataset

    Returns the dataset info and a dashboard plan. The plan is READ-ONLY —
    no charts or dashboards are created. Review the plan, then call
    ``prompt_to_dashboard`` with the dataset ID to create the dashboard.

    IMPORTANT FOR LLM CLIENTS:
    - This is the fastest way to go from a file to a dashboard plan
    - The response includes dataset ID, available sheets, and column info
    - Use the returned dataset ID with prompt_to_dashboard to create

    Example:
    ```json
    {
        "file_content": "<base64>",
        "filename": "revenue.xlsx",
        "prompt": "Create a service revenue dashboard by client"
    }
    ```
    """
    await ctx.info(
        "Upload-and-plan: filename='%s', prompt='%s'"
        % (request.filename, request.prompt[:80])
    )

    if not user_can_view_data_model_metadata():
        await ctx.warning("Upload-and-plan blocked by privacy controls")
        return UploadAndPlanResponse(
            warnings=["You don't have permission to access dataset metadata."],
        ).model_dump()

    all_warnings: list[str] = []

    # ------------------------------------------------------------------
    # Step 1: Upload the file
    # ------------------------------------------------------------------
    await ctx.report_progress(1, 3, "Uploading file")
    with mcp_event_log_context(action="mcp.upload_and_plan.upload"):
        from superset.mcp_service.dataset.tool.upload_file import (
            upload_single_file,
        )

        result = upload_single_file(
            file_content=request.file_content,
            filename=request.filename,
            table_name=request.table_name,
            sheet_name=request.sheet_name,
        )

    # Handle upload error
    from superset.mcp_service.dataset.schemas import DatasetError

    if isinstance(result, DatasetError):
        await ctx.warning(f"Upload failed: {result.error}")
        return UploadAndPlanResponse(
            warnings=[f"Upload failed: {result.error}"],
        ).model_dump()

    # Extract dataset info
    if hasattr(result, "model_dump"):
        ds_dict = result.model_dump()
    elif isinstance(result, dict):
        ds_dict = result
    else:
        ds_dict = {"raw": str(result)}

    ds_id = ds_dict.get("id")
    ds_table = ds_dict.get("table_name", "")
    sheet_names = ds_dict.get("sheet_names", [])

    await ctx.info(
        "File uploaded: dataset_id=%s, table='%s', sheets=%s"
        % (ds_id, ds_table, sheet_names)
    )

    # ------------------------------------------------------------------
    # Step 2: Plan the dashboard
    # ------------------------------------------------------------------
    await ctx.report_progress(2, 3, "Planning dashboard")
    with mcp_event_log_context(action="mcp.upload_and_plan.plan"):
        from superset.mcp_service.ai.tool.plan_dashboard import (
            _build_chart_intents_heuristic,
            _discover_datasets,
            _plan_with_llm,
        )

        datasets = _discover_datasets(
            request.prompt,
            pinned_ids=[ds_id] if ds_id else None,
        )

        if not datasets:
            all_warnings.append(
                "Upload succeeded but dataset not found for planning."
            )
            return UploadAndPlanResponse(
                dataset=ds_dict,
                warnings=all_warnings,
            ).model_dump()

        max_charts = request.max_charts
        llm_result = _plan_with_llm(request.prompt, datasets, max_charts)

        if llm_result is not None:
            plan_full, plan_warnings = llm_result
            all_warnings.extend(plan_warnings)
        else:
            chart_intents = _build_chart_intents_heuristic(
                request.prompt, datasets, max_charts
            )
            all_warnings.append(
                "No LLM provider configured. Plan uses heuristic keyword "
                "matching. Configure GENAI_LLM_PROVIDER_CONFIG for better "
                "results."
            )
            plan_full = DashboardPlanFull(
                title=_derive_title(request.prompt),
                description=request.prompt[:200],
                datasets=datasets,
                chart_intents=chart_intents,
                assumptions=[
                    "Chart types selected based on keyword matching.",
                    "Metrics and dimensions resolved from uploaded dataset.",
                ],
                clarifying_questions=[],
                confidence=0.4,
            )

    # ------------------------------------------------------------------
    # Step 3: Build response
    # ------------------------------------------------------------------
    await ctx.report_progress(3, 3, "Building response")
    response_plan = DashboardPlan(
        plan_id=plan_full.plan_id,
        title=plan_full.title,
        description=plan_full.description,
        datasets=plan_full.datasets,
        chart_intents=plan_full.chart_intents,
        global_filters=plan_full.global_filters,
        sections=[
            DashboardPlanSection(
                title="Charts",
                chart_intents=[
                    ci.model_dump() for ci in plan_full.chart_intents
                ],
            )
        ],
        layout_hints=plan_full.layout_hints,
        assumptions=plan_full.assumptions,
        clarifying_questions=plan_full.clarifying_questions,
        confidence=plan_full.confidence,
    )

    # Build next_steps guidance
    next_steps = (
        f"To create the dashboard, call prompt_to_dashboard with "
        f"prompt='{request.prompt[:80]}...' and dataset_ids=[{ds_id}]. "
    )
    if sheet_names and len(sheet_names) > 1:
        other_sheets = [s for s in sheet_names if s != request.sheet_name]
        if other_sheets:
            next_steps += (
                f"Other sheets available: {', '.join(other_sheets[:3])}. "
                f"Upload again with sheet_name to use a different sheet."
            )

    await ctx.info(
        "Upload-and-plan complete: plan_id=%s, charts=%d, confidence=%.2f"
        % (
            plan_full.plan_id,
            len(plan_full.chart_intents),
            plan_full.confidence,
        )
    )

    return UploadAndPlanResponse(
        dataset=ds_dict,
        plan=response_plan,
        warnings=all_warnings,
        next_steps=next_steps,
    ).model_dump()


def _derive_title(prompt: str) -> str:
    """Derive a dashboard title from the prompt."""
    import re

    words = re.findall(r"[A-Za-z]+", prompt)
    skip = {
        "create", "make", "build", "show", "me",
        "a", "an", "the", "with", "for", "and",
    }
    meaningful = [w for w in words if w.lower() not in skip][:5]
    if meaningful:
        return " ".join(meaningful).title() + " Dashboard"
    return "Dashboard"

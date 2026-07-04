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
"""MCP tool: plan_dashboard

Produces a dashboard plan from a natural language prompt without creating
any artifacts. The plan includes chart intents, dataset selections, global
filters, and layout hints. The user reviews the plan, then calls
create_chart_from_intent for each chart intent, and finally compose_dashboard
to assemble the dashboard.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from superset_core.mcp.decorators import tool, ToolAnnotations

try:
    from fastmcp import Context
except ModuleNotFoundError:
    Context = Any

from superset.mcp_service.ai.asset_search import search_assets
from superset.mcp_service.ai.schemas import (
    ChartIntentDetail,
    DashboardPlan,
    DashboardPlanFull,
    DashboardPlanRequest,
    DashboardPlanResponse,
    DashboardPlanSection,
)
from superset.mcp_service.privacy import (
    requires_data_model_metadata_access,
    user_can_view_data_model_metadata,
)
from superset.mcp_service.utils.logging_utils import mcp_event_log_context

logger = logging.getLogger(__name__)


def _discover_datasets(
    prompt: str,
    pinned_ids: list[int] | None = None,
    limit: int = 5,
) -> list[dict[str, Any]]:
    """Find relevant datasets for the dashboard plan.

    When ``pinned_ids`` are provided, look those up directly.
    Otherwise use asset search to discover candidates.

    Each returned dict includes 'columns' — a list of column metadata
    dicts with 'name', 'type', and 'is_numeric' — so that the planner
    can populate chart intents with meaningful metrics and dimensions.

    Returns:
        List of dicts with 'id', 'name', 'description', 'certified',
        'columns'.
    """
    if pinned_ids:
        from superset.daos.dataset import DatasetDAO

        results = []
        for ds_id in pinned_ids:
            ds = DatasetDAO.find_by_id(ds_id)
            if ds:
                results.append(
                    {
                        "id": ds.id,
                        "name": getattr(ds, "table_name", ""),
                        "description": getattr(ds, "description", None) or "",
                        "certified": bool(getattr(ds, "certified_by", None)),
                        "columns": _extract_columns(ds),
                    }
                )
        return results

    # Auto-discover
    assets = search_assets(
        query=prompt,
        asset_types=["dataset"],
        include_certified_only=False,
        limit=limit,
    )
    results = []
    for a in assets:
        ds_dict: dict[str, Any] = {
            "id": a.id,
            "name": a.name,
            "description": a.description or "",
            "certified": a.certified,
        }
        # Fetch columns for discovered datasets
        from superset.daos.dataset import DatasetDAO

        ds = DatasetDAO.find_by_id(a.id)
        ds_dict["columns"] = _extract_columns(ds) if ds else []
        results.append(ds_dict)
    return results


_NUMERIC_TYPES = frozenset(
    {
        "INT",
        "INTEGER",
        "BIGINT",
        "SMALLINT",
        "TINYINT",
        "FLOAT",
        "DOUBLE",
        "DOUBLE PRECISION",
        "REAL",
        "DECIMAL",
        "NUMERIC",
        "NUMBER",
        "INT64",
        "INT32",
        "INT16",
        "INT8",
        "FLOAT64",
        "FLOAT32",
    }
)


def _extract_columns(ds: Any | None) -> list[dict[str, Any]]:
    """Extract column metadata from a dataset ORM object.

    Returns a compact list of column dicts suitable for LLM context:
    ``[{"name": "revenue", "type": "FLOAT", "is_numeric": True}, ...]``
    """
    if ds is None:
        return []
    columns: list[dict[str, Any]] = []
    for col in getattr(ds, "columns", []) or []:
        col_name = getattr(col, "column_name", "")
        if not col_name:
            continue
        col_type = str(getattr(col, "type", "") or "").upper()
        is_numeric = (
            "NUMERIC" in col_type
            or "FLOAT" in col_type
            or "DOUBLE" in col_type
            or "INT" in col_type
            or "DECIMAL" in col_type
            or col_type in _NUMERIC_TYPES
        )
        is_dttm = (
            bool(getattr(col, "is_dttm", False))
            or "DATE" in col_type
            or "TIME" in col_type
        )
        columns.append(
            {
                "name": col_name,
                "type": col_type or "VARCHAR",
                "is_numeric": is_numeric,
                "is_dttm": is_dttm,
            }
        )
    return columns


def _detect_by_dimension(prompt: str, category_cols: list[str]) -> str:
    """Detect a 'by <category>' grouping from the prompt.

    Returns the matched category column name, or empty string.
    Example: 'revenue by client' -> 'Client' (if 'Client' is a column).

    Matching priority:
    1. Exact match (case-insensitive)
    2. Substring match (keyword is in column name)
    3. Fallback to first category column
    """
    import re

    by_match = re.search(r"\bby\s+(\w+(?:\s+\w+)?)", prompt, re.IGNORECASE)
    if not by_match:
        return ""
    keyword = by_match.group(1).strip().lower()

    # Priority 1: exact match (case-insensitive)
    for cat in category_cols:
        if cat.lower() == keyword:
            return cat

    # Priority 2: keyword appears within column name
    for cat in category_cols:
        if keyword in cat.lower():
            return cat

    # Priority 3: column name appears within keyword
    for cat in category_cols:
        if cat.lower() in keyword:
            return cat

    # Fallback to the first category column
    return category_cols[0] if category_cols else ""


def _build_chart_intents_heuristic(
    prompt: str,
    datasets: list[dict[str, Any]],
    max_charts: int = 6,
) -> list[ChartIntentDetail]:
    """Build chart intents from prompt keywords and dataset metadata.

    This is the heuristic fallback when no LLM provider is configured.
    It creates a reasonable set of chart intents based on common dashboard
    patterns, using actual column names from the dataset metadata when
    available.

    Recognised prompt patterns:
    - trend / monthly / over time  → line chart (xy)
    - top / bottom / ranking      → horizontal bar (ranking)
    - by <category> / by region   → bar chart grouped by that category
    - breakdown / composition     → pie chart
    - kpi / headline / total      → big number
    - multiple numeric columns    → multi-metric comparison bar
    - (always)                    → summary table
    """
    import re

    if not datasets:
        return []

    intents: list[ChartIntentDetail] = []
    primary_ds = datasets[0]
    columns = primary_ds.get("columns", [])

    # Identify useful column categories
    numeric_cols = [c["name"] for c in columns if c.get("is_numeric")]
    dttm_cols = [c["name"] for c in columns if c.get("is_dttm")]
    category_cols = [
        c["name"] for c in columns if not c.get("is_numeric") and not c.get("is_dttm")
    ]

    # Pick the best metric column (first numeric found)
    default_metric = numeric_cols[0] if numeric_cols else ""
    # Pick the best dimension (first category column found)
    default_dimension = category_cols[0] if category_cols else ""
    # Pick the best time column
    default_time_col = dttm_cols[0] if dttm_cols else ""

    # --- Pattern: "by <category>" grouping (e.g. "revenue by client") ---
    by_dimension = _detect_by_dimension(prompt, category_cols)

    if by_dimension:
        metrics = numeric_cols[:3] if len(numeric_cols) <= 6 else [default_metric]
        intents.append(
            ChartIntentDetail(
                purpose=f"Show metrics grouped by {by_dimension}",
                chart_type="xy",
                dataset_id=primary_ds["id"],
                metrics=metrics,
                dimensions=[by_dimension],
            )
        )

    # --- Pattern: trend over time ---
    if re.search(
        r"\b(trend|over time|history|growth|change|monthly|yearly)\b",
        prompt,
        re.IGNORECASE,
    ):
        time_range = "No limit"
        metrics = [default_metric] if default_metric else []
        # For wide-format data (many numeric cols, no datetime col),
        # use all numeric columns as separate series for comparison
        if not default_time_col and len(numeric_cols) >= 3:
            metrics = numeric_cols[:6]
            dims: list[str] = [default_dimension] if default_dimension else []
        else:
            dims = [default_time_col] if default_time_col else []
        intents.append(
            ChartIntentDetail(
                purpose="Show trend over time",
                chart_type="xy",
                dataset_id=primary_ds["id"],
                metrics=metrics,
                dimensions=dims,
                time_range=time_range,
            )
        )

    # --- Pattern: top/bottom ranking ---
    if re.search(
        r"\b(top|bottom|ranking|leaderboard|best|worst)\b", prompt, re.IGNORECASE
    ):
        metrics = [default_metric] if default_metric else []
        dims = [default_dimension] if default_dimension else []
        intents.append(
            ChartIntentDetail(
                purpose="Show top items by key metric",
                chart_type="xy",
                dataset_id=primary_ds["id"],
                metrics=metrics,
                dimensions=dims,
            )
        )

    # --- Pattern: breakdown/composition ---
    if re.search(
        r"\b(breakdown|composition|share|proportion|by category|by region|by type)\b",
        prompt,
        re.IGNORECASE,
    ):
        metrics = [default_metric] if default_metric else []
        dims = (
            [by_dimension or default_dimension]
            if (by_dimension or default_dimension)
            else []
        )
        intents.append(
            ChartIntentDetail(
                purpose="Show breakdown by category",
                chart_type="pie",
                dataset_id=primary_ds["id"],
                metrics=metrics,
                dimensions=dims,
            )
        )

    # --- Pattern: KPI / headline numbers ---
    if re.search(
        r"\b(kpi|headline|total|summary|overview|key metric)\b", prompt, re.IGNORECASE
    ):
        metrics = [default_metric] if default_metric else []
        intents.append(
            ChartIntentDetail(
                purpose="Show key performance indicators",
                chart_type="big_number",
                dataset_id=primary_ds["id"],
                metrics=metrics,
                dimensions=[],
            )
        )

    # Always add a summary table if we have room
    if len(intents) < max_charts:
        intents.append(
            ChartIntentDetail(
                purpose="Detailed data table",
                chart_type="table",
                dataset_id=primary_ds["id"],
                metrics=numeric_cols[:3] if numeric_cols else [],
                dimensions=category_cols[:3] if category_cols else [],
            )
        )

    # If nothing was detected, provide a default set
    if not intents:
        intents = [
            ChartIntentDetail(
                purpose="Key metrics overview",
                chart_type="big_number",
                dataset_id=primary_ds["id"],
                metrics=[default_metric] if default_metric else [],
                dimensions=[],
            ),
            ChartIntentDetail(
                purpose="Breakdown by category",
                chart_type="xy",
                dataset_id=primary_ds["id"],
                metrics=[default_metric] if default_metric else [],
                dimensions=([default_dimension] if default_dimension else []),
            ),
            ChartIntentDetail(
                purpose="Detailed data",
                chart_type="table",
                dataset_id=primary_ds["id"],
                metrics=numeric_cols[:3] if numeric_cols else [],
                dimensions=category_cols[:3] if category_cols else [],
            ),
        ]

    return intents[:max_charts]


def _plan_with_llm(
    prompt: str,
    datasets: list[dict[str, Any]],
    max_charts: int,
) -> tuple[DashboardPlanFull, list[str]] | None:
    """Attempt to plan using the configured LLM provider."""
    warnings: list[str] = []
    try:
        from superset.mcp_service.ai.provider_factory import get_llm_provider

        provider = get_llm_provider()
        # StubLLMProvider raises NotImplementedError on complete_json
        # so this naturally falls through to heuristic

        # Build dataset context for the LLM (includes column metadata)
        ds_context_parts = []
        for d in datasets:
            cols = d.get("columns", [])
            col_str = ""
            if cols:
                col_items = []
                for c in cols[:20]:  # Limit to 20 columns for context
                    type_hint = ""
                    if c.get("is_numeric"):
                        type_hint = " [numeric]"
                    elif c.get("is_dttm"):
                        type_hint = " [datetime]"
                    col_items.append(f"{c['name']}{type_hint}")
                col_str = f"\n  Columns: {', '.join(col_items)}"
            ds_context_parts.append(
                f"- {d['name']} (id={d['id']}, certified={d['certified']}): "
                f"{d['description']}{col_str}"
            )
        ds_context = "\n".join(ds_context_parts)

        system_prompt = (
            "You are a dashboard design expert. Given a user request and available "
            "datasets, produce a dashboard plan. Each chart_intent must specify:\n"
            "- purpose: what the chart shows\n"
            "- chart_type: one of 'xy', 'big_number', 'table', 'pie', 'pivot_table'\n"
            "- dataset_id: from the available datasets\n"
            "- metrics: list of metric names or column names with aggregates\n"
            "- dimensions: list of grouping columns\n"
            "- time_range: optional time range string\n\n"
            "Provide a confidence score (0-1), list assumptions, and ask clarifying "
            "questions if the request is ambiguous."
        )

        user_prompt = (
            f"User request: {prompt}\n\n"
            f"Available datasets:\n{ds_context}\n\n"
            f"Maximum charts: {max_charts}\n\n"
            "Produce a dashboard plan."
        )

        result = provider.complete_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_schema=DashboardPlanFull,
            metadata={"action": "plan_dashboard", "prompt": prompt[:200]},
        )

        if not isinstance(result, DashboardPlanFull):
            result = DashboardPlanFull.model_validate(result)
        return result, warnings

    except NotImplementedError:
        return None
    except Exception as e:
        warnings.append(f"LLM planning failed ({e}). Falling back to heuristic.")
        return None


@tool(
    tags=["discovery", "ai"],
    class_permission_name="Dashboard",
    annotations=ToolAnnotations(
        title="Plan dashboard",
        readOnlyHint=True,
        destructiveHint=False,
    ),
)
@requires_data_model_metadata_access
async def plan_dashboard(request: DashboardPlanRequest, ctx: Context) -> dict[str, Any]:
    """Create a dashboard plan from a natural language prompt.

    Produces a structured plan with chart intents, dataset selections,
    and layout hints WITHOUT creating any artifacts. Review the plan,
    then use create_chart_from_intent for each chart, and compose_dashboard
    to assemble the final dashboard.

    IMPORTANT FOR LLM CLIENTS:
    - This is a READ-ONLY planning tool — nothing is created
    - The plan includes chart_intents that describe what each chart should show
    - After reviewing, create each chart using create_chart_from_intent
    - Then assemble with compose_dashboard

    Example usage:
    ```json
    {
        "prompt": "Create an executive sales dashboard with revenue trends...",
        "constraints": {"max_charts": 6}
    }
    ```
    """
    await ctx.info(
        f"Planning dashboard: prompt='{request.prompt[:80]}', "
        f"datasets={request.dataset_candidates}"
    )

    # Generate a unique plan session ID for lineage tracking
    plan_id = str(uuid.uuid4())

    if not user_can_view_data_model_metadata():
        await ctx.warning("Dashboard planning blocked by privacy controls")
        return DashboardPlanResponse(
            plan=_empty_plan(plan_id),
            warnings=["You don't have permission to access dataset metadata."],
        ).model_dump()

    all_warnings: list[str] = []
    max_charts = int(request.constraints.get("max_charts", 6))

    # Step 1: Discover datasets
    await ctx.report_progress(1, 3, "Discovering datasets")
    with mcp_event_log_context(action="mcp.plan_dashboard.discover"):
        datasets = _discover_datasets(
            request.prompt,
            pinned_ids=request.dataset_candidates or None,
        )

    if not datasets:
        all_warnings.append(
            "No datasets found. Specify dataset_candidates or rephrase the prompt."
        )
        return DashboardPlanResponse(
            plan=_empty_plan(plan_id),
            warnings=all_warnings,
        ).model_dump()

    # Step 2: Build plan (LLM or heuristic)
    await ctx.report_progress(2, 3, "Building dashboard plan")
    with mcp_event_log_context(action="mcp.plan_dashboard.plan"):
        llm_result = _plan_with_llm(request.prompt, datasets, max_charts)

    if llm_result is not None:
        plan, plan_warnings = llm_result
        # Ensure the LLM-returned plan uses our session plan_id
        plan.plan_id = plan_id
        all_warnings.extend(plan_warnings)
    else:
        # Heuristic fallback
        chart_intents = _build_chart_intents_heuristic(
            request.prompt, datasets, max_charts
        )
        all_warnings.append(
            "No LLM provider configured. Plan uses heuristic keyword matching. "
            "Configure GENAI_LLM_PROVIDER_CONFIG for better results."
        )
        plan = DashboardPlanFull(
            plan_id=plan_id,
            title=_derive_title(request.prompt),
            description=request.prompt[:200],
            datasets=datasets,
            chart_intents=chart_intents,
            assumptions=[
                "Chart types selected based on keyword matching.",
                "Metrics and dimensions need to be resolved from dataset metadata.",
            ],
            clarifying_questions=[],
            confidence=0.4,
        )

    # Step 3: Build response
    await ctx.report_progress(3, 3, "Building response")
    # Build the response plan with full planning context
    response_plan = DashboardPlan(
        plan_id=plan_id,
        title=plan.title,
        description=plan.description,
        datasets=plan.datasets,
        chart_intents=plan.chart_intents,
        global_filters=plan.global_filters,
        sections=[
            DashboardPlanSection(
                title="Charts",
                chart_intents=[ci.model_dump() for ci in plan.chart_intents],
            )
        ],
        layout_hints=plan.layout_hints,
        assumptions=plan.assumptions,
        clarifying_questions=plan.clarifying_questions,
        confidence=plan.confidence,
    )

    await ctx.info(
        f"Dashboard plan created: title='{plan.title}', "
        f"charts={len(plan.chart_intents)}, confidence={plan.confidence:.2f}"
    )

    return DashboardPlanResponse(
        plan=response_plan,
        warnings=all_warnings,
    ).model_dump()


def _empty_plan(plan_id: str | None = None) -> DashboardPlan:
    """Return an empty dashboard plan."""
    return DashboardPlan(
        plan_id=plan_id or str(uuid.uuid4()),
        title="Untitled Dashboard",
        sections=[],
    )


def _derive_title(prompt: str) -> str:
    """Derive a dashboard title from the prompt."""
    # Use first few meaningful words
    import re

    words = re.findall(r"[A-Za-z]+", prompt)
    # Skip common filler words
    skip = {
        "create",
        "make",
        "build",
        "show",
        "me",
        "a",
        "an",
        "the",
        "with",
        "for",
        "and",
    }
    meaningful = [w for w in words if w.lower() not in skip][:5]
    if meaningful:
        return " ".join(meaningful).title() + " Dashboard"
    return "Dashboard"

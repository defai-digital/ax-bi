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
"""MCP tool: compose_dashboard

Creates a dashboard from a validated plan and pre-created chart IDs.
Extends the existing generate_dashboard with narrative blocks, smarter
layout, draft mode, and lineage metadata.
"""

from __future__ import annotations

import contextlib
import logging
import uuid
from typing import Any

from sqlalchemy.exc import SQLAlchemyError
from superset_core.mcp.decorators import tool, ToolAnnotations

try:
    from fastmcp import Context
except ModuleNotFoundError:
    Context = Any

from flask import g

from superset.mcp_service.ai.schemas import (
    ComposeDashboardRequest,
    ComposeDashboardResponse,
)
from superset.mcp_service.dashboard.constants import (
    generate_id,
    GRID_COLUMN_COUNT,
    GRID_DEFAULT_CHART_WIDTH,
)
from superset.mcp_service.utils.logging_utils import mcp_event_log_context
from superset.mcp_service.utils.url_utils import get_superset_base_url
from superset.utils import json

logger = logging.getLogger(__name__)

_CHART_HEIGHT = 50


def _build_native_filters(
    global_filters: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Convert plan global_filters into Superset native filter configuration.

    Each filter dict in ``global_filters`` may contain:
    - name (str)
    - filter_type (str): e.g. 'filter_select', 'filter_time', 'filter_range'
    - targets (list[dict]): dataset/column scoping
    - default_value (str | list | None)
    - multi_select (bool)
    - search_all_filters (bool)
    """
    filters: list[dict[str, Any]] = []
    for gf in global_filters:
        if not isinstance(gf, dict):
            continue
        filter_id = str(uuid.uuid4())
        filter_config: dict[str, Any] = {
            "id": filter_id,
            "name": gf.get("name", "Filter"),
            "filterType": gf.get("filter_type", "filter_select"),
            "targets": gf.get("targets", []),
            "defaultDataMask": {},
            "cascadeParentIds": [],
            "scope": {"rootPath": ["ROOT_ID"], "excluded": []},
            "isInstant": True,
        }
        if gf.get("default_value") is not None:
            filter_config["defaultDataMask"] = {
                "filterState": {"value": gf["default_value"]},
            }
        # Optional control values for select filters
        control_values: dict[str, Any] = {"enableEmptyFilter": False}
        if gf.get("multi_select") is not None:
            control_values["multiSelect"] = gf["multi_select"]
        if gf.get("search_all_filters") is not None:
            control_values["searchAllFilters"] = gf["search_all_filters"]
        filter_config["controlValues"] = control_values
        filters.append(filter_config)
    return filters


def _create_smart_layout(  # noqa: C901
    chart_objects: list[Any],
    plan: Any,
    narrative_blocks: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Create a dashboard layout with charts arranged by the plan's hints.

    Places charts in a 2-column grid by default. The first chart in the
    plan gets a full-width row if it's a big_number (KPI header pattern).
    Narrative blocks are rendered as MARKDOWN components between chart rows.
    """
    layout: dict[str, Any] = {}
    row_ids: list[str] = []

    charts_per_row = 2
    idx = 0

    # Insert "before" narrative blocks at the top
    if narrative_blocks:
        for nb in narrative_blocks:
            if nb.get("position") == "before":
                _add_markdown_row(layout, row_ids, nb.get("content", ""))

    while idx < len(chart_objects):
        row_id = generate_id("ROW")
        row_ids.append(row_id)
        column_keys: list[str] = []

        # Big number charts get a full-width row for KPI-style headers
        chart = chart_objects[idx]
        viz_type = getattr(chart, "viz_type", "")
        if "big_number" in viz_type and idx == 0:
            chart_key = f"CHART-{chart.id}"
            col_key = generate_id("COLUMN")
            column_keys.append(col_key)

            layout[chart_key] = {
                "children": [],
                "id": chart_key,
                "meta": {
                    "chartId": chart.id,
                    "height": 30,  # KPIs are shorter
                    "sliceName": chart.slice_name or f"Chart {chart.id}",
                    "uuid": str(chart.uuid) if chart.uuid else f"chart-{chart.id}",
                    "width": GRID_DEFAULT_CHART_WIDTH,
                },
                "parents": ["ROOT_ID", "GRID_ID", row_id, col_key],
                "type": "CHART",
            }
            layout[col_key] = {
                "children": [chart_key],
                "id": col_key,
                "meta": {
                    "background": "BACKGROUND_TRANSPARENT",
                    "width": GRID_COLUMN_COUNT,
                },
                "parents": ["ROOT_ID", "GRID_ID", row_id],
                "type": "COLUMN",
            }
            idx += 1
        else:
            # Standard 2-column layout
            row_charts = chart_objects[idx : idx + charts_per_row]
            col_width = GRID_COLUMN_COUNT // len(row_charts)

            for chart in row_charts:
                chart_key = f"CHART-{chart.id}"
                col_key = generate_id("COLUMN")
                column_keys.append(col_key)

                layout[chart_key] = {
                    "children": [],
                    "id": chart_key,
                    "meta": {
                        "chartId": chart.id,
                        "height": _CHART_HEIGHT,
                        "sliceName": chart.slice_name or f"Chart {chart.id}",
                        "uuid": str(chart.uuid) if chart.uuid else f"chart-{chart.id}",
                        "width": GRID_DEFAULT_CHART_WIDTH,
                    },
                    "parents": ["ROOT_ID", "GRID_ID", row_id, col_key],
                    "type": "CHART",
                }
                layout[col_key] = {
                    "children": [chart_key],
                    "id": col_key,
                    "meta": {
                        "background": "BACKGROUND_TRANSPARENT",
                        "width": col_width,
                    },
                    "parents": ["ROOT_ID", "GRID_ID", row_id],
                    "type": "COLUMN",
                }
            idx += len(row_charts)

        layout[row_id] = {
            "children": column_keys,
            "id": row_id,
            "meta": {"background": "BACKGROUND_TRANSPARENT"},
            "parents": ["ROOT_ID", "GRID_ID"],
            "type": "ROW",
        }

        # Insert "between" narrative blocks after each row of charts
        if narrative_blocks:
            for nb in narrative_blocks:
                if nb.get("position") == "between":
                    _add_markdown_row(layout, row_ids, nb.get("content", ""))

    # Insert "after" narrative blocks at the bottom
    if narrative_blocks:
        for nb in narrative_blocks:
            if nb.get("position") == "after":
                _add_markdown_row(layout, row_ids, nb.get("content", ""))

    layout["GRID_ID"] = {
        "children": row_ids,
        "id": "GRID_ID",
        "parents": ["ROOT_ID"],
        "type": "GRID",
    }
    layout["ROOT_ID"] = {
        "children": ["GRID_ID"],
        "id": "ROOT_ID",
        "type": "ROOT",
    }
    layout["DASHBOARD_VERSION_KEY"] = "v2"

    return layout


def _add_markdown_row(
    layout: dict[str, Any],
    row_ids: list[str],
    content: str,
) -> str:
    """Add a full-width MARKDOWN row to the layout.

    Returns the row_id that was added.
    """
    md_id = generate_id("MARKDOWN")
    col_key = generate_id("COLUMN")
    row_id = generate_id("ROW")
    row_ids.append(row_id)

    layout[md_id] = {
        "children": [],
        "id": md_id,
        "meta": {
            "code": content,
            "height": 20,
            "width": GRID_DEFAULT_CHART_WIDTH,
        },
        "parents": ["ROOT_ID", "GRID_ID", row_id, col_key],
        "type": "MARKDOWN",
    }
    layout[col_key] = {
        "children": [md_id],
        "id": col_key,
        "meta": {
            "background": "BACKGROUND_TRANSPARENT",
            "width": GRID_COLUMN_COUNT,
        },
        "parents": ["ROOT_ID", "GRID_ID", row_id],
        "type": "COLUMN",
    }
    layout[row_id] = {
        "children": [col_key],
        "id": row_id,
        "meta": {"background": "BACKGROUND_TRANSPARENT"},
        "parents": ["ROOT_ID", "GRID_ID"],
        "type": "ROW",
    }
    return row_id


@tool(
    tags=["mutate", "ai"],
    class_permission_name="Dashboard",
    annotations=ToolAnnotations(
        title="Compose dashboard",
        readOnlyHint=False,
        destructiveHint=False,
    ),
)
async def compose_dashboard(  # noqa: C901
    request: ComposeDashboardRequest, ctx: Context
) -> dict[str, Any]:
    """Create a dashboard from a plan and pre-created charts.

    Takes a validated dashboard plan (from plan_dashboard) and chart IDs
    (from create_chart_from_intent calls), then assembles them into a
    dashboard with smart layout.

    IMPORTANT FOR LLM CLIENTS:
    - Create charts FIRST using create_chart_from_intent for each chart intent
    - Then call this tool with the chart IDs and the plan
    - Dashboard is created as draft by default (draft=True)
    - Set draft=False to publish immediately

    Example workflow:
    1. plan_dashboard -> get plan with chart_intents
    2. create_chart_from_intent for each chart intent -> get chart IDs
    3. compose_dashboard(plan=plan, chart_ids=[1, 2, 3]) -> dashboard URL
    """
    await ctx.info(
        f"Composing dashboard: title='{request.plan.title}', "
        f"charts={len(request.chart_ids)}, draft={request.draft}"
    )

    try:
        from superset import db
        from superset.models.slice import Slice

        # Validate charts exist and are accessible
        with mcp_event_log_context(action="mcp.compose_dashboard.validate_charts"):
            chart_objects = (
                db.session.query(Slice)
                .filter(Slice.id.in_(request.chart_ids))
                .order_by(Slice.id)
                .all()
            )
            found_ids = {c.id for c in chart_objects}
            missing = set(request.chart_ids) - found_ids
            if missing:
                return ComposeDashboardResponse(
                    error=f"Charts not found: {sorted(missing)}",
                    warnings=[
                        "Some chart IDs were not found. Only found charts were used."
                    ],
                ).model_dump()

        # Create layout
        with mcp_event_log_context(action="mcp.compose_dashboard.layout"):
            # Convert narrative_blocks to dicts for the layout builder
            nb_dicts: list[dict[str, Any]] | None = None
            if request.narrative_blocks:
                nb_dicts = [
                    {
                        "content": nb.content,
                        "position": nb.position,
                    }
                    for nb in request.narrative_blocks
                ]
            layout = _create_smart_layout(
                chart_objects, request.plan, narrative_blocks=nb_dicts
            )

        # Build native filter configuration from plan global_filters
        native_filters: list[dict[str, Any]] = []
        if request.plan.global_filters:
            with mcp_event_log_context(action="mcp.compose_dashboard.build_filters"):
                native_filters = _build_native_filters(request.plan.global_filters)

        # Build AI lineage metadata for audit trail
        ai_lineage: dict[str, Any] = {
            "plan_id": request.plan.plan_id,
            "source_prompt": request.plan.description or "",
            "tool_chain": [
                "plan_dashboard",
                "create_chart_from_intent",
                "compose_dashboard",
            ],
            "source_datasets": [ds.get("id") for ds in request.plan.datasets],
            "chart_ids": request.chart_ids,
            "confidence": request.plan.confidence,
            "created_by": "mcp_genai",
        }

        # Create dashboard
        from superset.models.dashboard import Dashboard

        with mcp_event_log_context(action="mcp.compose_dashboard.db_write"):
            json_metadata = json.dumps(
                {
                    "filter_scopes": {},
                    "expanded_slices": {},
                    "refresh_frequency": 0,
                    "timed_refresh_immune_slices": [],
                    "color_scheme": None,
                    "label_colors": {},
                    "shared_label_colors": {},
                    "color_scheme_domain": [],
                    "cross_filters_enabled": False,
                    "native_filter_configuration": native_filters,
                    "global_chart_configuration": {
                        "scope": {"rootPath": ["ROOT_ID"], "excluded": []}
                    },
                    "chart_configuration": {},
                    "ai_lineage": ai_lineage,
                }
            )

            dashboard = Dashboard()
            dashboard.dashboard_title = request.plan.title or "Dashboard"
            dashboard.description = request.plan.description or ""
            dashboard.json_metadata = json_metadata
            dashboard.position_json = json.dumps(layout)
            dashboard.published = not request.draft

            # Set owners
            from superset.extensions import security_manager

            current_user = (
                db.session.query(security_manager.user_model)
                .filter_by(id=g.user.id)
                .first()
            )
            if current_user:
                dashboard.owners = [current_user]

            # Attach charts
            fresh_charts = (
                db.session.query(Slice)
                .filter(Slice.id.in_(request.chart_ids))
                .order_by(Slice.id)
                .all()
            )
            dashboard.slices = fresh_charts

            db.session.add(dashboard)
            db.session.commit()  # pylint: disable=consider-using-transaction
            try:
                db.session.refresh(dashboard)
            except SQLAlchemyError:
                logger.warning(
                    "Dashboard %s created but refresh failed",
                    dashboard.id,
                    exc_info=True,
                )

        dashboard_url = f"{get_superset_base_url()}/ax-bi/dashboard/{dashboard.id}/"

        # Build layout summary
        layout_parts = []
        for chart in fresh_charts:
            viz = getattr(chart, "viz_type", "unknown")
            name = getattr(chart, "slice_name", f"Chart {chart.id}")
            layout_parts.append(f"{name} ({viz})")
        layout_summary = f"Dashboard with {len(fresh_charts)} charts: " + ", ".join(
            layout_parts[:5]
        )
        if len(fresh_charts) > 5:
            layout_summary += f" and {len(fresh_charts) - 5} more"

        await ctx.info(f"Dashboard composed: id={dashboard.id}, url={dashboard_url}")

        return ComposeDashboardResponse(
            dashboard={
                "id": dashboard.id,
                "title": dashboard.dashboard_title,
                "url": dashboard_url,
                "published": dashboard.published,
                "chart_count": len(fresh_charts),
            },
            dashboard_url=dashboard_url,
            layout_summary=layout_summary,
            lineage=ai_lineage,
            warnings=[],
        ).model_dump()

    except SQLAlchemyError as e:
        from superset import db

        with contextlib.suppress(SQLAlchemyError):
            db.session.rollback()  # pylint: disable=consider-using-transaction
        logger.error("Dashboard composition failed: %s", e, exc_info=True)
        return ComposeDashboardResponse(
            error=f"Failed to create dashboard: {e}",
        ).model_dump()
    except Exception as e:
        logger.error("Dashboard composition failed: %s", e, exc_info=True)
        return ComposeDashboardResponse(
            error=f"Failed to create dashboard: {e}",
        ).model_dump()

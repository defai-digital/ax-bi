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

import logging
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


def _create_smart_layout(
    chart_objects: list[Any],
    plan: Any,
) -> dict[str, Any]:
    """Create a dashboard layout with charts arranged by the plan's hints.

    Places charts in a 2-column grid by default. The first chart in the
    plan gets a full-width row if it's a big_number (KPI header pattern).
    """
    layout: dict[str, Any] = {}
    row_ids: list[str] = []

    charts_per_row = 2
    idx = 0

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


@tool(
    tags=["mutate", "ai"],
    class_permission_name="Dashboard",
    annotations=ToolAnnotations(
        title="Compose dashboard",
        readOnlyHint=False,
        destructiveHint=False,
    ),
)
async def compose_dashboard(
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
        "Composing dashboard: title='%s', charts=%d, draft=%s"
        % (request.plan.title, len(request.chart_ids), request.draft)
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
            layout = _create_smart_layout(chart_objects, request.plan)

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
                    "native_filter_configuration": [],
                    "global_chart_configuration": {
                        "scope": {"rootPath": ["ROOT_ID"], "excluded": []}
                    },
                    "chart_configuration": {},
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

        dashboard_url = f"{get_superset_base_url()}/superset/dashboard/{dashboard.id}/"

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

        await ctx.info(
            "Dashboard composed: id=%s, url=%s" % (dashboard.id, dashboard_url)
        )

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
            warnings=[],
        ).model_dump()

    except SQLAlchemyError as e:
        from superset import db

        try:
            db.session.rollback()  # pylint: disable=consider-using-transaction
        except SQLAlchemyError:
            pass
        logger.error("Dashboard composition failed: %s", e, exc_info=True)
        return ComposeDashboardResponse(
            error=f"Failed to create dashboard: {e}",
        ).model_dump()
    except Exception as e:
        logger.error("Dashboard composition failed: %s", e, exc_info=True)
        return ComposeDashboardResponse(
            error=f"Failed to create dashboard: {e}",
        ).model_dump()

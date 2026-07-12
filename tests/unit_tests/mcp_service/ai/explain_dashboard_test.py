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
"""Unit tests for the explain_dashboard MCP tool helpers."""

from __future__ import annotations

import sys
import types
from collections.abc import Callable
from typing import Any
from unittest.mock import MagicMock

# ---------------------------------------------------------------------------
# Decorator passthrough
# ---------------------------------------------------------------------------


def _force_passthrough_decorators() -> dict[str, types.ModuleType]:
    def _passthrough_tool(
        func: Callable[..., Any] | None = None,
        **kwargs: Any,
    ) -> Callable[..., Any]:
        del kwargs
        if func is not None:
            return func
        return lambda f: f

    mock_decorators = MagicMock()
    mock_decorators.tool = _passthrough_tool
    mock_decorators.ToolAnnotations = dict

    saved_modules: dict[str, types.ModuleType] = {}
    for key in ("axbi_core.mcp", "axbi_core.mcp.decorators"):
        if key in sys.modules:
            saved_modules[key] = sys.modules[key]

    sys.modules["axbi_core.mcp"] = MagicMock()
    sys.modules["axbi_core.mcp.decorators"] = mock_decorators
    return saved_modules


def _restore_modules(saved_modules: dict[str, types.ModuleType]) -> None:
    for key in list(sys.modules.keys()):
        if key.startswith("axbi_core.mcp"):
            del sys.modules[key]
    sys.modules.update(saved_modules)


_saved = _force_passthrough_decorators()
try:
    from axbi.mcp_service.ai.tool.explain_dashboard import (
        _build_follow_up_suggestions,
        _build_overview_summary,
    )
finally:
    _restore_modules(_saved)


# ---------------------------------------------------------------------------
# _build_overview_summary
# ---------------------------------------------------------------------------


class TestBuildOverviewSummary:
    def test_basic_summary(self) -> None:
        dash_info = {
            "dashboard_title": "Sales Dashboard",
            "description": "Q4 executive summary",
            "published": True,
        }
        charts = [
            {"id": 1, "name": "Revenue", "viz_type": "echarts_timeseries_line"},
            {"id": 2, "name": "Count", "viz_type": "echarts_timeseries_bar"},
        ]
        summary, key_metrics, caveats = _build_overview_summary(dash_info, charts)

        assert "Sales Dashboard" in summary
        assert "2 chart(s)" in summary
        assert "Q4 executive summary" in summary
        assert len(key_metrics) == 0  # No big_number charts
        assert len(caveats) == 0

    def test_big_number_detected_as_kpi(self) -> None:
        dash_info = {
            "dashboard_title": "KPI Dashboard",
            "description": "",
            "published": True,
        }
        charts = [
            {"id": 1, "name": "Total Revenue", "viz_type": "big_number_total"},
            {"id": 2, "name": "Trend", "viz_type": "echarts_timeseries_line"},
        ]
        summary, key_metrics, caveats = _build_overview_summary(dash_info, charts)

        assert len(key_metrics) == 1
        assert key_metrics[0]["name"] == "Total Revenue"
        assert key_metrics[0]["type"] == "KPI"
        assert key_metrics[0]["chart_id"] == 1

    def test_unpublished_caveat(self) -> None:
        dash_info = {
            "dashboard_title": "Draft",
            "description": "",
            "published": False,
        }
        charts = [{"id": 1, "name": "C", "viz_type": "table"}]
        summary, key_metrics, caveats = _build_overview_summary(dash_info, charts)

        assert any("not published" in c.lower() for c in caveats)

    def test_empty_dashboard_caveat(self) -> None:
        dash_info = {
            "dashboard_title": "Empty",
            "description": "",
            "published": True,
        }
        summary, key_metrics, caveats = _build_overview_summary(dash_info, [])

        assert any("no charts" in c.lower() for c in caveats)

    def test_chart_types_in_summary(self) -> None:
        dash_info = {
            "dashboard_title": "Mixed",
            "description": "",
            "published": True,
        }
        charts = [
            {"id": 1, "name": "A", "viz_type": "echarts_timeseries_line"},
            {"id": 2, "name": "B", "viz_type": "echarts_timeseries_line"},
            {"id": 3, "name": "C", "viz_type": "pie"},
        ]
        summary, _, _ = _build_overview_summary(dash_info, charts)

        assert "2 echarts timeseries line" in summary
        assert "1 pie" in summary

    def test_no_description(self) -> None:
        dash_info = {
            "dashboard_title": "NoDesc",
            "description": None,
            "published": True,
        }
        charts = [{"id": 1, "name": "X", "viz_type": "table"}]
        summary, _, _ = _build_overview_summary(dash_info, charts)

        assert "Description:" not in summary

    def test_unknown_viz_type_grouped(self) -> None:
        dash_info = {
            "dashboard_title": "Test",
            "description": "",
            "published": True,
        }
        charts = [{"id": 1, "name": "X", "viz_type": None}]
        summary, _, _ = _build_overview_summary(dash_info, charts)

        assert "1 unknown" in summary


# ---------------------------------------------------------------------------
# _build_follow_up_suggestions
# ---------------------------------------------------------------------------


class TestBuildFollowUpSuggestions:
    def test_suggests_big_number_when_missing(self) -> None:
        charts = [
            {"id": 1, "viz_type": "echarts_timeseries_line"},
        ]
        suggestions = _build_follow_up_suggestions(charts)
        assert any("big number" in s.lower() for s in suggestions)

    def test_suggests_table_when_missing(self) -> None:
        charts = [
            {"id": 1, "viz_type": "big_number_total"},
        ]
        suggestions = _build_follow_up_suggestions(charts)
        assert any("table" in s.lower() for s in suggestions)

    def test_suggests_more_charts_when_few(self) -> None:
        charts = [
            {"id": 1, "viz_type": "big_number_total"},
        ]
        suggestions = _build_follow_up_suggestions(charts)
        assert any(
            "more chart" in s.lower() or "comprehensive" in s.lower()
            for s in suggestions
        )

    def test_no_big_number_suggestion_when_present(self) -> None:
        charts = [
            {"id": 1, "viz_type": "big_number_total"},
            {"id": 2, "viz_type": "table"},
            {"id": 3, "viz_type": "echarts_timeseries_line"},
        ]
        suggestions = _build_follow_up_suggestions(charts)
        assert not any("add a big number" in s.lower() for s in suggestions)

    def test_no_table_suggestion_when_present(self) -> None:
        charts = [
            {"id": 1, "viz_type": "big_number_total"},
            {"id": 2, "viz_type": "table"},
            {"id": 3, "viz_type": "echarts_timeseries_line"},
        ]
        suggestions = _build_follow_up_suggestions(charts)
        assert not any("add a table" in s.lower() for s in suggestions)

    def test_always_suggests_tools(self) -> None:
        charts = [{"id": 1, "viz_type": "table"}]
        suggestions = _build_follow_up_suggestions(charts)
        assert any("update_chart" in s for s in suggestions)
        assert any("create_chart_from_intent" in s for s in suggestions)

    def test_empty_charts(self) -> None:
        suggestions = _build_follow_up_suggestions([])
        # Should suggest everything
        assert any("big number" in s.lower() for s in suggestions)
        assert any("table" in s.lower() for s in suggestions)
        assert any(
            "more chart" in s.lower() or "comprehensive" in s.lower()
            for s in suggestions
        )

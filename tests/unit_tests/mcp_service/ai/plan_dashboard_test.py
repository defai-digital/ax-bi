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
"""Unit tests for the plan_dashboard MCP tool helpers."""

from __future__ import annotations

import sys
import types
from collections.abc import Callable
from typing import Any
from unittest.mock import MagicMock

import pytest


# ---------------------------------------------------------------------------
# Decorator passthrough (same pattern as describe_dataset_test.py)
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
    for key in ("superset_core.mcp", "superset_core.mcp.decorators"):
        if key in sys.modules:
            saved_modules[key] = sys.modules[key]

    sys.modules["superset_core.mcp"] = MagicMock()
    sys.modules["superset_core.mcp.decorators"] = mock_decorators
    return saved_modules


def _restore_modules(saved_modules: dict[str, types.ModuleType]) -> None:
    for key in list(sys.modules.keys()):
        if key.startswith("superset_core.mcp"):
            del sys.modules[key]
    sys.modules.update(saved_modules)


_saved = _force_passthrough_decorators()
try:
    from superset.mcp_service.ai.tool.plan_dashboard import (
        _build_chart_intents_heuristic,
        _derive_title,
        _empty_plan,
    )
finally:
    _restore_modules(_saved)


# ---------------------------------------------------------------------------
# _derive_title
# ---------------------------------------------------------------------------


class TestDeriveTitle:
    def test_basic_prompt(self) -> None:
        title = _derive_title("Create an executive sales dashboard")
        assert "Executive" in title
        assert "Sales" in title
        assert title.endswith("Dashboard")

    def test_filler_words_skipped(self) -> None:
        title = _derive_title("Show me a chart with revenue")
        # 'show', 'me', 'a', 'with' are filler words
        assert "Chart" not in title or "Revenue" in title

    def test_empty_prompt(self) -> None:
        title = _derive_title("")
        assert title == "Dashboard"

    def test_all_filler_words(self) -> None:
        title = _derive_title("create a the for and")
        assert title == "Dashboard"


# ---------------------------------------------------------------------------
# _empty_plan
# ---------------------------------------------------------------------------


class TestEmptyPlan:
    def test_empty_plan_structure(self) -> None:
        plan = _empty_plan()
        assert plan.title == "Untitled Dashboard"
        assert plan.business_goal == ""
        assert plan.sections == []


# ---------------------------------------------------------------------------
# _build_chart_intents_heuristic
# ---------------------------------------------------------------------------


class TestBuildChartIntentsHeuristic:
    def _ds(self, ds_id: int = 1) -> list[dict[str, Any]]:
        return [{"id": ds_id, "name": "test_ds", "description": "", "certified": False}]

    def test_trend_intent(self) -> None:
        intents = _build_chart_intents_heuristic(
            "Show revenue trend over time", self._ds()
        )
        chart_types = [i.chart_type for i in intents]
        assert "xy" in chart_types
        purposes = [i.purpose.lower() for i in intents]
        assert any("trend" in p for p in purposes)

    def test_ranking_intent(self) -> None:
        intents = _build_chart_intents_heuristic(
            "Show top products by revenue", self._ds()
        )
        purposes = [i.purpose.lower() for i in intents]
        assert any("top" in p for p in purposes)

    def test_breakdown_intent(self) -> None:
        intents = _build_chart_intents_heuristic(
            "Show breakdown by category", self._ds()
        )
        chart_types = [i.chart_type for i in intents]
        assert "pie" in chart_types

    def test_kpi_intent(self) -> None:
        intents = _build_chart_intents_heuristic(
            "Show key KPI overview", self._ds()
        )
        chart_types = [i.chart_type for i in intents]
        assert "big_number" in chart_types

    def test_always_adds_summary_table(self) -> None:
        intents = _build_chart_intents_heuristic("Show KPI overview", self._ds())
        chart_types = [i.chart_type for i in intents]
        assert "table" in chart_types

    def test_default_intents_when_no_keywords(self) -> None:
        intents = _build_chart_intents_heuristic("Something", self._ds())
        # When no keywords match, only the always-added summary table remains
        assert len(intents) >= 1
        chart_types = [i.chart_type for i in intents]
        assert "table" in chart_types

    def test_empty_datasets(self) -> None:
        intents = _build_chart_intents_heuristic("Show trend", [])
        assert intents == []

    def test_max_charts_limit(self) -> None:
        intents = _build_chart_intents_heuristic(
            "Show trend top KPI breakdown overview total summary",
            self._ds(),
            max_charts=2,
        )
        assert len(intents) <= 2

    def test_dataset_id_propagated(self) -> None:
        intents = _build_chart_intents_heuristic(
            "Show trend over time", self._ds(ds_id=42)
        )
        for intent in intents:
            assert intent.dataset_id == 42

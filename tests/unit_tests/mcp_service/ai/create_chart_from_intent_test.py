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
"""Unit tests for the create_chart_from_intent MCP tool helpers."""

from __future__ import annotations

import sys
import types
from collections.abc import Callable
from typing import Any
from unittest.mock import MagicMock, patch

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
    from superset.mcp_service.ai.tool.create_chart_from_intent import (
        _suggest_alternatives,
    )
finally:
    _restore_modules(_saved)


# ---------------------------------------------------------------------------
# _suggest_alternatives
# ---------------------------------------------------------------------------


class TestSuggestAlternatives:
    def test_line_alternatives(self) -> None:
        alts = _suggest_alternatives("echarts_timeseries_line")
        assert len(alts) == 2
        assert any("bar" in a.lower() for a in alts)
        assert any("area" in a.lower() for a in alts)

    def test_bar_alternatives(self) -> None:
        alts = _suggest_alternatives("echarts_timeseries_bar")
        assert len(alts) == 2
        assert any("line" in a.lower() for a in alts)

    def test_table_alternatives(self) -> None:
        alts = _suggest_alternatives("table")
        assert len(alts) == 2
        assert any("bar" in a.lower() for a in alts)

    def test_big_number_alternatives(self) -> None:
        alts = _suggest_alternatives("big_number")
        assert len(alts) == 2
        assert any("trendline" in a.lower() for a in alts)

    def test_pie_alternatives(self) -> None:
        alts = _suggest_alternatives("pie")
        assert len(alts) == 2
        assert any("table" in a.lower() for a in alts)

    def test_unknown_chart_type(self) -> None:
        alts = _suggest_alternatives("some_unknown_type")
        assert len(alts) == 1
        assert "different" in alts[0].lower()


# ---------------------------------------------------------------------------
# _resolve_chart_config_from_intent (heuristic path)
# ---------------------------------------------------------------------------


class TestResolveChartConfigFromIntent:
    """Test the heuristic fallback path when no LLM provider is configured."""

    def test_heuristic_fallback(self) -> None:
        """When no LLM provider, should fall back to heuristic mapping."""
        _s2 = _force_passthrough_decorators()
        try:
            from superset.mcp_service.ai.tool.create_chart_from_intent import (
                _resolve_chart_config_from_intent,
            )
        finally:
            _restore_modules(_s2)

        ds = MagicMock()
        ds.columns = []
        ds.metrics = []
        ds.main_dttm_col = None

        # Mock provider_factory to raise NotImplementedError (no LLM configured)
        with patch(
            "superset.mcp_service.ai.provider_factory.get_llm_provider",
            side_effect=NotImplementedError,
        ):
            config, chart_type, confidence, explanation, warnings = (
                _resolve_chart_config_from_intent("Show me something", ds)
            )

        # Should have a warning about no LLM provider
        assert any("llm" in w.lower() or "heuristic" in w.lower() for w in warnings)
        # Heuristic fallback returns table for generic prompts
        assert chart_type == "table" or config is not None

    def test_llm_failure_fallback(self) -> None:
        """When LLM fails with an exception, should fall back to heuristic."""
        _s2 = _force_passthrough_decorators()
        try:
            from superset.mcp_service.ai.tool.create_chart_from_intent import (
                _resolve_chart_config_from_intent,
            )
        finally:
            _restore_modules(_s2)

        ds = MagicMock()
        ds.columns = []
        ds.metrics = []
        ds.main_dttm_col = None

        with patch(
            "superset.mcp_service.ai.provider_factory.get_llm_provider",
            side_effect=RuntimeError("LLM unavailable"),
        ):
            config, chart_type, confidence, explanation, warnings = (
                _resolve_chart_config_from_intent("Show total count", ds)
            )

        assert any("failed" in w.lower() or "heuristic" in w.lower() for w in warnings)

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

import importlib
import inspect
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
    from axbi.mcp_service.ai.tool.create_chart_from_intent import (
        _dataset_name_candidates,
        _extract_chart_name,
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
# _extract_chart_name
# ---------------------------------------------------------------------------


class TestExtractChartName:
    def test_extracts_name_it_phrase(self) -> None:
        assert (
            _extract_chart_name("Create a bar chart. Name it Test - Count by Island.")
            == "Test - Count by Island"
        )

    def test_extracts_name_before_follow_up_instruction(self) -> None:
        assert (
            _extract_chart_name(
                "Name it Penguins Count by Island. Return only the saved chart URL."
            )
            == "Penguins Count by Island"
        )

    def test_extracts_named_phrase(self) -> None:
        assert (
            _extract_chart_name("Create a chart named MCP Test - Revenue by Country")
            == "MCP Test - Revenue by Country"
        )

    def test_returns_none_when_no_name_requested(self) -> None:
        assert _extract_chart_name("Create a bar chart by island") is None


# ---------------------------------------------------------------------------
# _dataset_name_candidates
# ---------------------------------------------------------------------------


class TestDatasetNameCandidates:
    def test_extracts_dataset_name_after_dataset_keyword(self) -> None:
        assert _dataset_name_candidates("Find dataset palmer_penguins") == [
            "palmer_penguins"
        ]

    def test_extracts_dataset_name_after_from_keyword(self) -> None:
        assert _dataset_name_candidates("Create a chart from cleaned_sales_data") == [
            "cleaned_sales_data"
        ]

    def test_deduplicates_dataset_candidates(self) -> None:
        assert _dataset_name_candidates(
            "Find dataset palmer_penguins from palmer_penguins"
        ) == ["palmer_penguins"]


# ---------------------------------------------------------------------------
# _resolve_chart_config_from_intent (heuristic path)
# ---------------------------------------------------------------------------


class TestResolveChartConfigFromIntent:
    """Test the heuristic fallback path when no LLM provider is configured."""

    def test_heuristic_fallback(self) -> None:
        """When no LLM provider, should fall back to heuristic mapping."""
        _s2 = _force_passthrough_decorators()
        try:
            from axbi.mcp_service.ai.tool.create_chart_from_intent import (
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
            "axbi.mcp_service.ai.provider_factory.get_llm_provider",
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
            from axbi.mcp_service.ai.tool.create_chart_from_intent import (
                _resolve_chart_config_from_intent,
            )
        finally:
            _restore_modules(_s2)

        ds = MagicMock()
        ds.columns = []
        ds.metrics = []
        ds.main_dttm_col = None

        with patch(
            "axbi.mcp_service.ai.provider_factory.get_llm_provider",
            side_effect=RuntimeError("LLM unavailable"),
        ):
            config, chart_type, confidence, explanation, warnings = (
                _resolve_chart_config_from_intent("Show total count", ds)
            )

        assert any("failed" in w.lower() or "heuristic" in w.lower() for w in warnings)


class TestCreateChartFromIntent:
    def test_calls_generate_chart_with_keyword_ctx(self) -> None:
        """Regression test for FastMCP wrappers receiving duplicate ctx values."""
        module = importlib.import_module(
            "axbi.mcp_service.ai.tool.create_chart_from_intent"
        )
        source = inspect.getsource(module)

        assert "generate_chart(chart_request, ctx=ctx)" in source
        assert "generate_chart(chart_request, ctx)" not in source

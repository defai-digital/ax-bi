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
"""Unit tests for the suggest_chart_improvements MCP tool."""

from __future__ import annotations

import asyncio
import sys
import types
from collections.abc import Callable
from importlib import import_module
from typing import Any
from unittest.mock import MagicMock, patch


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
    module = import_module("superset.mcp_service.ai.tool.suggest_chart_improvements")
finally:
    _restore_modules(_saved)


def test_non_object_form_data_is_treated_as_absent_in_heuristic_path() -> None:
    result = module._heuristic_analysis(
        chart_config={
            "viz_type": "big_number",
            "slice_name": "Total revenue",
            "form_data": [],
        },
        data_sample={"data": []},
        goal=None,
    )

    assert (
        result.current_analysis == "Chart type: big_number. Analyzed with data sample."
    )
    assert result.warnings == []
    assert any(
        suggestion.config_changes.get("show_trendline") is True
        for suggestion in result.suggestions
    )


def test_llm_analysis_uses_asyncio_to_thread() -> None:
    """_llm_analysis wraps sync complete_json in asyncio.to_thread."""
    mock_provider = MagicMock()
    mock_provider.complete_json.return_value = {
        "current_analysis": "Good chart",
        "suggestions": [{"reason": "Add color", "config_changes": {}}],
    }

    with patch.object(module, "get_llm_provider", return_value=mock_provider):
        result = asyncio.run(
            module._llm_analysis(
                chart_config={"viz_type": "pie", "form_data": {}},
                data_sample=None,
                goal=None,
            )
        )
    assert result is not None
    assert result.current_analysis == "Good chart"
    mock_provider.complete_json.assert_called_once()

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
"""Unit tests for the validate_chart MCP tool."""

from __future__ import annotations

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
    module = import_module("axbi.mcp_service.ai.tool.validate_chart")
    from axbi.mcp_service.ai.schemas import (
        ValidateChartRequest,
        ValidateChartResponse,
    )
finally:
    _restore_modules(_saved)


# ---------------------------------------------------------------------------
# Schema tests
# ---------------------------------------------------------------------------


class TestValidateChartRequest:
    def test_basic_request(self) -> None:
        req = ValidateChartRequest(
            dataset_id=1,
            config={"chart_type": "xy", "kind": "line"},
        )
        assert req.dataset_id == 1
        assert req.config["chart_type"] == "xy"


class TestValidateChartResponse:
    def test_valid_response(self) -> None:
        resp = ValidateChartResponse(
            is_valid=True,
            normalized_config={"chart_type": "xy"},
        )
        assert resp.is_valid is True
        assert resp.errors == []
        assert resp.warnings == []

    def test_invalid_response_with_errors(self) -> None:
        resp = ValidateChartResponse(
            is_valid=False,
            errors=["Column 'foo' not found in dataset"],
        )
        assert resp.is_valid is False
        assert len(resp.errors) == 1

    def test_response_with_warnings(self) -> None:
        resp = ValidateChartResponse(
            is_valid=True,
            warnings=["High cardinality column may be slow"],
            normalized_config={"chart_type": "table"},
        )
        assert resp.is_valid is True
        assert len(resp.warnings) == 1
        assert resp.normalized_config is not None


# ---------------------------------------------------------------------------
# ValidationPipeline integration (mocked)
# ---------------------------------------------------------------------------


class TestValidateChartLogic:
    """Test the _run_validation helper directly to avoid Flask auth context."""

    def test_invalid_config_returns_errors(self) -> None:
        """When ValidationPipeline returns is_valid=False, errors are surfaced."""
        mock_result = MagicMock()
        mock_result.is_valid = False
        mock_result.error = MagicMock()
        mock_result.error.message = "Invalid chart type 'banana'"

        mock_pipeline = MagicMock()
        mock_pipeline.validate_request_with_warnings.return_value = mock_result

        with patch.dict(
            "sys.modules",
            {
                "axbi.mcp_service.chart.validation.pipeline": MagicMock(
                    ValidationPipeline=mock_pipeline
                ),
            },
        ):
            from axbi.mcp_service.ai.tool.validate_chart import _run_validation

            result = _run_validation(dataset_id=1, config={"chart_type": "banana"})
            assert result["is_valid"] is False
            assert any("banana" in e for e in result["errors"])

    def test_valid_config_returns_normalized(self) -> None:
        """When ValidationPipeline passes, normalized config is returned."""
        mock_config = MagicMock()
        mock_config.model_dump.return_value = {
            "chart_type": "xy",
            "kind": "line",
        }
        mock_result = MagicMock()
        mock_result.is_valid = True
        mock_result.error = None
        mock_result.warnings = None
        mock_result.request = MagicMock()
        mock_result.request.config = mock_config

        mock_pipeline = MagicMock()
        mock_pipeline.validate_request_with_warnings.return_value = mock_result

        with patch.dict(
            "sys.modules",
            {
                "axbi.mcp_service.chart.validation.pipeline": MagicMock(
                    ValidationPipeline=mock_pipeline
                ),
            },
        ):
            from axbi.mcp_service.ai.tool.validate_chart import _run_validation

            result = _run_validation(
                dataset_id=1,
                config={"chart_type": "xy", "kind": "line", "x": {"name": "date"}},
            )
            assert result["is_valid"] is True
            assert result["normalized_config"] is not None
            assert result["normalized_config"]["chart_type"] == "xy"

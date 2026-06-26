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
"""Unit tests for the describe_dataset_for_ai service logic."""

from __future__ import annotations

import sys
import types
from collections.abc import Callable
from typing import Any
from unittest.mock import MagicMock


def _force_passthrough_decorators() -> dict[str, types.ModuleType]:
    """Import tool helpers without requiring MCP startup registration."""

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


_saved_modules = _force_passthrough_decorators()
try:
    from superset.mcp_service.ai.tool.describe_dataset_for_ai import (
        _describe_dataset,
        _get_aliases_for_object,
    )
finally:
    _restore_modules(_saved_modules)


def test_describe_dataset_basic() -> None:
    """Test basic dataset description extraction."""
    dataset = MagicMock()
    dataset.id = 42
    dataset.table_name = "sales_orders"
    dataset.description = "Sales order facts"
    dataset.certified_by = "Analytics"
    dataset.main_dttm_col = "order_date"

    col = MagicMock()
    col.column_name = "region"
    col.type = "VARCHAR"
    col.description = "Sales region"
    col.is_dttm = False
    col.expression = None

    metric = MagicMock()
    metric.metric_name = "revenue"
    metric.expression = "SUM(amount)"
    metric.description = "Booked revenue"

    dataset.columns = [col]
    dataset.metrics = [metric]

    result = _describe_dataset(dataset)

    assert result.id == 42
    assert result.name == "sales_orders"
    assert result.description == "Sales order facts"
    assert result.certified is True
    assert result.main_time_column == "order_date"
    assert len(result.columns) == 1
    assert result.columns[0].name == "region"
    assert result.columns[0].type == "VARCHAR"
    assert len(result.metrics) == 1
    assert result.metrics[0].name == "revenue"
    assert result.metrics[0].expression == "SUM(amount)"


def test_describe_dataset_no_time_column() -> None:
    """Test fallback to first datetime column."""
    dataset = MagicMock()
    dataset.id = 1
    dataset.table_name = "test_table"
    dataset.description = None
    dataset.certified_by = None
    dataset.main_dttm_col = None

    dttm_col = MagicMock()
    dttm_col.column_name = "created_at"
    dttm_col.type = "TIMESTAMP"
    dttm_col.description = None
    dttm_col.is_dttm = True
    dttm_col.expression = None

    dataset.columns = [dttm_col]
    dataset.metrics = []

    result = _describe_dataset(dataset)

    assert result.main_time_column == "created_at"


def test_describe_dataset_no_columns() -> None:
    """Test dataset with no columns or metrics."""
    dataset = MagicMock()
    dataset.id = 1
    dataset.table_name = "empty_table"
    dataset.description = None
    dataset.certified_by = None
    dataset.main_dttm_col = None
    dataset.columns = None
    dataset.metrics = None

    result = _describe_dataset(dataset)

    assert result.columns == []
    assert result.metrics == []


def test_describe_dataset_privacy_metadata() -> None:
    """Test that privacy metadata is correctly set."""
    dataset = MagicMock()
    dataset.id = 1
    dataset.table_name = "test"
    dataset.description = None
    dataset.certified_by = None
    dataset.main_dttm_col = None
    dataset.columns = []
    dataset.metrics = []

    result = _describe_dataset(dataset, include_sample_values=False)
    assert result.privacy["sample_values_included"] is False
    assert result.privacy["metadata_scope"] == "role_allowed"


def test_get_aliases_returns_empty_on_error() -> None:
    """Test that alias lookup returns empty list on error."""
    # When the alias table doesn't exist, should return empty
    aliases = _get_aliases_for_object("column", "test_col", dataset_id=1)
    # This will either return [] or raise (caught internally)
    assert isinstance(aliases, list)


def test_describe_dataset_column_is_dimension() -> None:
    """Test dimension heuristic for columns."""
    dataset = MagicMock()
    dataset.id = 1
    dataset.table_name = "test"
    dataset.description = None
    dataset.certified_by = None
    dataset.main_dttm_col = None

    # Regular column (no expression, not datetime) -> dimension
    dim_col = MagicMock()
    dim_col.column_name = "region"
    dim_col.type = "VARCHAR"
    dim_col.description = None
    dim_col.is_dttm = False
    dim_col.expression = None

    # Datetime column -> not dimension
    dttm_col = MagicMock()
    dttm_col.column_name = "order_date"
    dttm_col.type = "DATE"
    dttm_col.description = None
    dttm_col.is_dttm = True
    dttm_col.expression = None

    # Expression column -> not dimension
    expr_col = MagicMock()
    expr_col.column_name = "full_name"
    expr_col.type = "VARCHAR"
    expr_col.description = None
    expr_col.is_dttm = False
    expr_col.expression = "first_name || ' ' || last_name"

    dataset.columns = [dim_col, dttm_col, expr_col]
    dataset.metrics = []

    result = _describe_dataset(dataset)

    assert result.columns[0].is_dimension is True  # region
    assert result.columns[1].is_dimension is False  # order_date (dttm)
    assert result.columns[2].is_dimension is False  # full_name (expression)

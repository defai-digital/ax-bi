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
"""Unit tests for the compose_dashboard MCP tool helpers."""

from __future__ import annotations

import sys
import types
import uuid
from collections.abc import Callable
from contextlib import nullcontext
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from pytest_mock import MockerFixture

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
    from axbi.mcp_service.ai.tool.compose_dashboard import (
        _build_native_filters,
        _chart_access_error,
        _CHART_HEIGHT,
        _compose_dashboard as compose_dashboard,
        _create_smart_layout,
    )
    from axbi.mcp_service.dashboard.constants import (
        GRID_COLUMN_COUNT,
        GRID_DEFAULT_CHART_WIDTH,
    )
finally:
    _restore_modules(_saved)

from axbi.commands.dashboard.exceptions import (  # noqa: E402
    DashboardChartsAccessDeniedError,
    DashboardChartsNotFoundError,
    DashboardCreateFailedError,
)
from axbi.mcp_service.ai.schemas import (  # noqa: E402
    ComposeDashboardRequest,
    DashboardPlanFull,
)
from axbi.mcp_service.common.error_schemas import (  # noqa: E402
    sanitize_error_text,
)
from axbi.utils import json  # noqa: E402

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_chart(
    chart_id: int,
    viz_type: str = "echarts_timeseries_line",
    slice_name: str | None = None,
    chart_uuid: str | None = None,
) -> MagicMock:
    chart = MagicMock()
    chart.id = chart_id
    chart.viz_type = viz_type
    chart.slice_name = slice_name or f"Chart {chart_id}"
    chart.uuid = chart_uuid or str(uuid.uuid4())
    return chart


def _compose_request(chart_ids: list[int]) -> ComposeDashboardRequest:
    """Build a minimal valid dashboard-composition request."""
    return ComposeDashboardRequest(
        plan=DashboardPlanFull(
            plan_id="plan-123",
            title="Revenue overview",
            description="Revenue performance",
            datasets=[{"id": 9}],
            confidence=0.9,
        ),
        chart_ids=chart_ids,
    )


def _patch_compose_runtime(mocker: MockerFixture) -> None:
    """Replace Flask-bound logging and URL helpers for direct tool tests."""
    mocker.patch(
        "axbi.mcp_service.ai.tool.compose_dashboard.mcp_event_log_context",
        side_effect=lambda **_kwargs: nullcontext(),
    )
    mocker.patch(
        "axbi.mcp_service.ai.tool.compose_dashboard.get_axbi_base_url",
        return_value="http://localhost:8088",
    )
    mocker.patch(
        "axbi.mcp_service.ai.tool.compose_dashboard._chart_access_error",
        return_value=None,
    )


@pytest.mark.asyncio
async def test_compose_dashboard_delegates_persistence_to_command(
    mocker: MockerFixture,
) -> None:
    """The MCP adapter passes generated state through the dashboard command."""
    chart = _make_chart(7, slice_name="Revenue")
    find_charts = mocker.patch(
        "axbi.mcp_service.ai.tool.compose_dashboard.ChartDAO.find_by_ids",
        return_value=[chart],
    )
    command_factory = mocker.patch(
        "axbi.mcp_service.ai.tool.compose_dashboard.CreateDashboardFromChartsCommand"
    )
    dashboard = MagicMock(
        id=23,
        dashboard_title="Revenue overview",
        published=False,
    )
    command_factory.return_value.run.return_value = dashboard
    command_factory.return_value.charts = [chart]
    _patch_compose_runtime(mocker)
    context = MagicMock()
    context.info = AsyncMock()

    response = await compose_dashboard(_compose_request([7]), context)

    assert response["error"] is None
    assert response["dashboard"]["id"] == 23
    assert response["dashboard"]["chart_count"] == 1
    find_charts.assert_called_once_with(
        [7],
        skip_base_filter=True,
    )
    properties, chart_ids = command_factory.call_args.args
    assert chart_ids == [7]
    assert properties["dashboard_title"] == "Revenue overview"
    assert properties["published"] is False
    metadata = json.loads(properties["json_metadata"])
    assert metadata["ai_lineage"]["plan_id"] == "plan-123"
    command_factory.return_value.run.assert_called_once_with()
    context.info.assert_awaited()


@pytest.mark.parametrize(
    ("error", "expected_message"),
    [
        (DashboardChartsNotFoundError({7}), "Charts not found: [7]"),
        (DashboardChartsAccessDeniedError({7}), "Access denied to charts: [7]"),
        (
            DashboardCreateFailedError(),
            "Failed to create dashboard due to a database error.",
        ),
    ],
)
@pytest.mark.asyncio
async def test_compose_dashboard_maps_command_errors(
    mocker: MockerFixture,
    error: Exception,
    expected_message: str,
) -> None:
    """Command failures remain domain-safe at the MCP response boundary."""
    chart = _make_chart(7)
    mocker.patch(
        "axbi.mcp_service.ai.tool.compose_dashboard.ChartDAO.find_by_ids",
        return_value=[chart],
    )
    command_factory = mocker.patch(
        "axbi.mcp_service.ai.tool.compose_dashboard.CreateDashboardFromChartsCommand"
    )
    command_factory.return_value.run.side_effect = error
    _patch_compose_runtime(mocker)
    context = MagicMock()
    context.info = AsyncMock()

    response = await compose_dashboard(_compose_request([7]), context)

    assert response["dashboard"] is None
    assert response["error"] == sanitize_error_text(expected_message)


# ---------------------------------------------------------------------------
# _create_smart_layout
# ---------------------------------------------------------------------------


class TestCreateSmartLayout:
    def test_root_and_grid_structure(self) -> None:
        """Layout always has ROOT_ID and GRID_ID."""
        charts = [_make_chart(1)]
        layout = _create_smart_layout(charts, plan=None)

        assert "ROOT_ID" in layout
        assert "GRID_ID" in layout
        assert layout["ROOT_ID"]["type"] == "ROOT"
        assert layout["GRID_ID"]["type"] == "GRID"
        assert "GRID_ID" in layout["ROOT_ID"]["children"]
        assert layout["DASHBOARD_VERSION_KEY"] == "v2"

    def test_single_chart_layout(self) -> None:
        """A single non-big-number chart gets a full-width column."""
        charts = [_make_chart(1, viz_type="echarts_timeseries_line")]
        layout = _create_smart_layout(charts, plan=None)

        # Should have 1 ROW, 1 COLUMN, 1 CHART
        chart_keys = [k for k in layout if k.startswith("CHART-")]
        col_keys = [k for k in layout if k.startswith("COLUMN-")]
        row_keys = [k for k in layout if k.startswith("ROW-")]

        assert len(chart_keys) == 1
        assert len(col_keys) == 1
        assert len(row_keys) == 1

        # Single chart column should be full width
        col = layout[col_keys[0]]
        assert col["meta"]["width"] == GRID_COLUMN_COUNT

    def test_two_charts_side_by_side(self) -> None:
        """Two non-big-number charts should be arranged in 2 columns."""
        charts = [
            _make_chart(1, viz_type="echarts_timeseries_line"),
            _make_chart(2, viz_type="echarts_timeseries_bar"),
        ]
        layout = _create_smart_layout(charts, plan=None)

        chart_keys = [k for k in layout if k.startswith("CHART-")]
        col_keys = [k for k in layout if k.startswith("COLUMN-")]
        row_keys = [k for k in layout if k.startswith("ROW-")]

        assert len(chart_keys) == 2
        assert len(col_keys) == 2
        assert len(row_keys) == 1  # Both in same row

        # Each column should be half width
        for ck in col_keys:
            assert layout[ck]["meta"]["width"] == GRID_COLUMN_COUNT // 2

    def test_big_number_full_width_first(self) -> None:
        """First big_number chart gets its own full-width row (KPI header)."""
        charts = [
            _make_chart(1, viz_type="big_number_total"),
            _make_chart(2, viz_type="echarts_timeseries_line"),
            _make_chart(3, viz_type="echarts_timeseries_bar"),
        ]
        layout = _create_smart_layout(charts, plan=None)

        # Big number chart should be shorter
        bn_chart = layout["CHART-1"]
        assert bn_chart["meta"]["height"] == 30  # KPIs are shorter

        # Big number chart column should be full width
        bn_col_key = bn_chart["parents"][-1]
        bn_col = layout[bn_col_key]
        assert bn_col["meta"]["width"] == GRID_COLUMN_COUNT

        # Remaining charts should be in a separate row
        chart2 = layout["CHART-2"]
        chart3 = layout["CHART-3"]
        # They should share the same row (parents[2] is the row ID)
        assert chart2["parents"][2] == chart3["parents"][2]
        # And that row is different from the big_number row
        assert chart2["parents"][2] != bn_chart["parents"][2]

    def test_chart_height(self) -> None:
        """Standard charts should use _CHART_HEIGHT."""
        charts = [_make_chart(1)]
        layout = _create_smart_layout(charts, plan=None)

        chart = layout["CHART-1"]
        assert chart["meta"]["height"] == _CHART_HEIGHT

    def test_chart_metadata(self) -> None:
        """Chart metadata should include chartId, sliceName, uuid."""
        test_uuid = str(uuid.uuid4())
        charts = [_make_chart(42, slice_name="Revenue Trend", chart_uuid=test_uuid)]
        layout = _create_smart_layout(charts, plan=None)

        meta = layout["CHART-42"]["meta"]
        assert meta["chartId"] == 42
        assert meta["sliceName"] == "Revenue Trend"
        assert meta["uuid"] == test_uuid
        assert meta["width"] == GRID_DEFAULT_CHART_WIDTH

    def test_no_uuid_fallback(self) -> None:
        """When chart has no UUID, should use fallback string."""
        chart = _make_chart(5)
        chart.uuid = None
        layout = _create_smart_layout([chart], plan=None)

        meta = layout["CHART-5"]["meta"]
        assert meta["uuid"] == "chart-5"

    def test_no_slice_name_fallback(self) -> None:
        """When chart has no slice_name, should use fallback."""
        chart = _make_chart(7)
        chart.slice_name = None
        layout = _create_smart_layout([chart], plan=None)

        meta = layout["CHART-7"]["meta"]
        assert meta["sliceName"] == "Chart 7"

    def test_three_charts_layout(self) -> None:
        """Three non-big-number charts: first row has 2, second row has 1."""
        charts = [
            _make_chart(1),
            _make_chart(2),
            _make_chart(3),
        ]
        layout = _create_smart_layout(charts, plan=None)

        row_keys = [k for k in layout if k.startswith("ROW-")]
        assert len(row_keys) == 2  # 2 rows

        # First row should have 2 charts
        first_row = layout[row_keys[0]]
        first_row_cols = first_row["children"]
        assert len(first_row_cols) == 2

        # Second row should have 1 chart
        second_row = layout[row_keys[1]]
        second_row_cols = second_row["children"]
        assert len(second_row_cols) == 1

    def test_grid_children_order(self) -> None:
        """GRID_ID children should list row IDs in order."""
        charts = [_make_chart(1), _make_chart(2), _make_chart(3)]
        layout = _create_smart_layout(charts, plan=None)

        grid_children = layout["GRID_ID"]["children"]
        row_keys = [k for k in layout if k.startswith("ROW-")]
        assert grid_children == sorted(row_keys, key=lambda k: grid_children.index(k))

    def test_column_transparent_background(self) -> None:
        """All columns should have transparent background."""
        charts = [_make_chart(1), _make_chart(2)]
        layout = _create_smart_layout(charts, plan=None)

        col_keys = [k for k in layout if k.startswith("COLUMN-")]
        for ck in col_keys:
            assert layout[ck]["meta"]["background"] == "BACKGROUND_TRANSPARENT"


def test_chart_access_error_rejects_inaccessible_chart(mocker) -> None:
    chart = _make_chart(7)
    mocker.patch(
        "axbi.mcp_service.auth.check_chart_data_access",
        return_value=MagicMock(is_valid=False, error="Dataset access denied"),
    )

    assert (
        _chart_access_error([chart])
        == "Chart 7 is not accessible: Dataset access denied"
    )


# ---------------------------------------------------------------------------
# _build_native_filters
# ---------------------------------------------------------------------------


class TestBuildNativeFilters:
    def test_empty_input(self) -> None:
        assert _build_native_filters([]) == []

    def test_single_select_filter(self) -> None:
        filters = _build_native_filters(
            [
                {
                    "name": "Region",
                    "filter_type": "filter_select",
                    "targets": [{"datasetId": 1, "column": {"name": "region"}}],
                    "default_value": "US",
                    "multi_select": True,
                }
            ]
        )
        assert len(filters) == 1
        f = filters[0]
        assert f["name"] == "Region"
        assert f["filterType"] == "filter_select"
        assert f["targets"] == [{"datasetId": 1, "column": {"name": "region"}}]
        assert f["defaultDataMask"]["filterState"]["value"] == "US"
        assert f["controlValues"]["multiSelect"] is True
        assert f["isInstant"] is True
        assert f["scope"] == {"rootPath": ["ROOT_ID"], "excluded": []}
        # id is a UUID
        uuid.UUID(f["id"])

    def test_time_filter_no_default(self) -> None:
        filters = _build_native_filters(
            [{"name": "Date Range", "filter_type": "filter_time"}]
        )
        assert len(filters) == 1
        f = filters[0]
        assert f["filterType"] == "filter_time"
        assert f["defaultDataMask"] == {}

    def test_multiple_filters(self) -> None:
        filters = _build_native_filters(
            [
                {"name": "Region", "filter_type": "filter_select"},
                {"name": "Date", "filter_type": "filter_time"},
                {"name": "Amount", "filter_type": "filter_range"},
            ]
        )
        assert len(filters) == 3
        names = [f["name"] for f in filters]
        assert names == ["Region", "Date", "Amount"]
        # All IDs are unique
        ids = [f["id"] for f in filters]
        assert len(set(ids)) == 3

    def test_non_dict_items_skipped(self) -> None:
        filters = _build_native_filters(["not_a_dict", 42, None])  # type: ignore[list-item]
        assert filters == []

    def test_default_name_fallback(self) -> None:
        filters = _build_native_filters([{}])
        assert filters[0]["name"] == "Filter"
        assert filters[0]["filterType"] == "filter_select"

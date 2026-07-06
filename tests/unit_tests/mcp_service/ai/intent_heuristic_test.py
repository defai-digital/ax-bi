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
"""Unit tests for the heuristic intent-to-chart mapping fallback."""

from __future__ import annotations

from unittest.mock import MagicMock

from superset.mcp_service.ai.intent_heuristic import (
    _detect_chart_type,
    _find_dimension_from_prompt,
    _find_first_dimension,
    _find_first_metric,
    _find_time_column,
    heuristic_chart_config,
)

# ---------------------------------------------------------------------------
# Helpers to build mock datasets
# ---------------------------------------------------------------------------


def _make_col(
    name: str,
    col_type: str = "VARCHAR",
    is_dttm: bool = False,
) -> MagicMock:
    col = MagicMock()
    col.column_name = name
    col.type = col_type
    col.is_dttm = is_dttm
    return col


def _make_metric(name: str = "count") -> MagicMock:
    m = MagicMock()
    m.metric_name = name
    return m


def _make_dataset(
    columns: list[MagicMock] | None = None,
    metrics: list[MagicMock] | None = None,
    main_dttm_col: str | None = None,
) -> MagicMock:
    ds = MagicMock()
    ds.columns = columns or []
    ds.metrics = metrics or []
    ds.main_dttm_col = main_dttm_col
    return ds


# ---------------------------------------------------------------------------
# _find_time_column
# ---------------------------------------------------------------------------


class TestFindTimeColumn:
    def test_main_dttm_col(self) -> None:
        ds = _make_dataset(main_dttm_col="order_date")
        assert _find_time_column(ds) == "order_date"

    def test_fallback_to_first_datetime_column(self) -> None:
        ds = _make_dataset(
            columns=[
                _make_col("name", "VARCHAR"),
                _make_col("created_at", "TIMESTAMP", is_dttm=True),
            ]
        )
        assert _find_time_column(ds) == "created_at"

    def test_no_time_column(self) -> None:
        ds = _make_dataset(columns=[_make_col("name", "VARCHAR")])
        assert _find_time_column(ds) is None

    def test_no_columns_at_all(self) -> None:
        ds = _make_dataset(columns=None)
        assert _find_time_column(ds) is None


# ---------------------------------------------------------------------------
# _find_first_metric
# ---------------------------------------------------------------------------


class TestFindFirstMetric:
    def test_saved_metric(self) -> None:
        ds = _make_dataset(metrics=[_make_metric("revenue")])
        result = _find_first_metric(ds)
        assert result is not None
        assert result["name"] == "revenue"
        assert result["saved_metric"] is True

    def test_numeric_column_fallback(self) -> None:
        ds = _make_dataset(
            columns=[_make_col("amount", "FLOAT")],
            metrics=[],
        )
        result = _find_first_metric(ds)
        assert result is not None
        assert result["name"] == "amount"
        assert result["aggregate"] == "SUM"

    def test_no_metric_available(self) -> None:
        ds = _make_dataset(
            columns=[_make_col("name", "VARCHAR")],
            metrics=[],
        )
        result = _find_first_metric(ds)
        assert result is None


# ---------------------------------------------------------------------------
# _find_first_dimension
# ---------------------------------------------------------------------------


class TestFindFirstDimension:
    def test_prefers_string_column(self) -> None:
        ds = _make_dataset(
            columns=[
                _make_col("amount", "FLOAT"),
                _make_col("region", "VARCHAR"),
            ]
        )
        assert _find_first_dimension(ds) == "region"

    def test_skips_datetime_columns(self) -> None:
        ds = _make_dataset(
            columns=[
                _make_col("created_at", "TIMESTAMP", is_dttm=True),
                _make_col("category", "TEXT"),
            ]
        )
        assert _find_first_dimension(ds) == "category"

    def test_fallback_to_non_time_column(self) -> None:
        ds = _make_dataset(
            columns=[
                _make_col("created_at", "TIMESTAMP", is_dttm=True),
                _make_col("amount", "FLOAT"),
            ]
        )
        assert _find_first_dimension(ds) == "amount"

    def test_no_dimension(self) -> None:
        ds = _make_dataset(columns=[])
        assert _find_first_dimension(ds) is None


# ---------------------------------------------------------------------------
# _find_dimension_from_prompt
# ---------------------------------------------------------------------------


class TestFindDimensionFromPrompt:
    def test_matches_by_column_name(self) -> None:
        ds = _make_dataset(
            columns=[
                _make_col("species", "VARCHAR"),
                _make_col("island", "VARCHAR"),
            ]
        )
        assert _find_dimension_from_prompt("Show count by island", ds) == "island"

    def test_matches_grouped_by_column_name_with_underscore(self) -> None:
        ds = _make_dataset(
            columns=[
                _make_col("product_line", "VARCHAR"),
                _make_col("country", "VARCHAR"),
            ]
        )
        assert (
            _find_dimension_from_prompt("Bar chart grouped by product line", ds)
            == "product_line"
        )

    def test_returns_none_when_prompt_does_not_name_column(self) -> None:
        ds = _make_dataset(columns=[_make_col("species", "VARCHAR")])
        assert _find_dimension_from_prompt("Show a chart", ds) is None


# ---------------------------------------------------------------------------
# _detect_chart_type
# ---------------------------------------------------------------------------


class TestDetectChartType:
    def test_single_value_keywords(self) -> None:
        ds = _make_dataset()
        chart_type, kind, _ = _detect_chart_type("Show me total revenue", ds)
        assert chart_type == "big_number"
        assert kind == "big_number"

    def test_trend_keywords_with_time_col(self) -> None:
        ds = _make_dataset(main_dttm_col="order_date")
        chart_type, kind, explanation = _detect_chart_type(
            "Show revenue trend over time", ds
        )
        assert chart_type == "xy"
        assert kind == "line"
        assert "order_date" in explanation

    def test_trend_keywords_without_time_col(self) -> None:
        ds = _make_dataset()
        chart_type, kind, _ = _detect_chart_type("Show revenue trend", ds)
        assert chart_type == "xy"
        assert kind == "bar"

    def test_proportion_keywords(self) -> None:
        ds = _make_dataset()
        chart_type, kind, _ = _detect_chart_type("Show share by region", ds)
        assert chart_type == "pie"
        assert kind == "pie"

    def test_table_keywords(self) -> None:
        ds = _make_dataset()
        chart_type, kind, _ = _detect_chart_type("List all rows as a table", ds)
        assert chart_type == "table"
        assert kind == "table"

    def test_comparison_keywords(self) -> None:
        ds = _make_dataset()
        chart_type, kind, _ = _detect_chart_type("Compare sales by region", ds)
        assert chart_type == "xy"
        assert kind == "bar"

    def test_explicit_bar_chart_takes_priority_over_count(self) -> None:
        ds = _make_dataset()
        chart_type, kind, _ = _detect_chart_type(
            "Create a bar chart showing COUNT(*) by island", ds
        )
        assert chart_type == "xy"
        assert kind == "bar"

    def test_default_fallback(self) -> None:
        ds = _make_dataset()
        chart_type, kind, _ = _detect_chart_type("Show me something", ds)
        assert chart_type == "table"
        assert kind == "table"

    def test_priority_single_value_over_trend(self) -> None:
        """Single value keywords take priority over trend keywords."""
        ds = _make_dataset(main_dttm_col="dt")
        chart_type, _, _ = _detect_chart_type("Total count over time", ds)
        assert chart_type == "big_number"


# ---------------------------------------------------------------------------
# heuristic_chart_config
# ---------------------------------------------------------------------------


class TestHeuristicChartConfig:
    def test_big_number_with_trendline(self) -> None:
        ds = _make_dataset(
            metrics=[_make_metric("revenue")],
            main_dttm_col="order_date",
        )
        config, chart_type, confidence, explanation, warnings = heuristic_chart_config(
            "Show total revenue", ds, []
        )
        assert config is not None
        assert config["chart_type"] == "big_number"
        assert config["show_trendline"] is True
        assert config["temporal_column"] == "order_date"
        assert chart_type == "big_number"
        assert confidence == 0.4
        assert "trendline" in explanation.lower()

    def test_big_number_no_metric(self) -> None:
        ds = _make_dataset(
            columns=[_make_col("name", "VARCHAR")],
            metrics=[],
        )
        config, chart_type, confidence, _, warnings = heuristic_chart_config(
            "Show total", ds, []
        )
        assert config is None
        assert chart_type == "big_number"
        assert confidence == 0.1
        assert any("metric" in w.lower() for w in warnings)

    def test_xy_line_chart(self) -> None:
        ds = _make_dataset(
            columns=[
                _make_col("region", "VARCHAR"),
                _make_col("created_at", "TIMESTAMP", is_dttm=True),
            ],
            metrics=[_make_metric("count")],
            main_dttm_col="created_at",
        )
        config, chart_type, confidence, _, warnings = heuristic_chart_config(
            "Show monthly revenue trend", ds, []
        )
        assert config is not None
        assert config["chart_type"] == "xy"
        assert config["kind"] == "line"
        assert config["time_grain"] == "P1M"
        assert chart_type == "echarts_timeseries_line"

    def test_xy_daily_grain(self) -> None:
        ds = _make_dataset(
            metrics=[_make_metric("count")],
            main_dttm_col="dt",
            columns=[_make_col("dt", "TIMESTAMP", is_dttm=True)],
        )
        config, _, _, _, _ = heuristic_chart_config(
            "Show daily trend over time", ds, []
        )
        assert config is not None
        assert config["time_grain"] == "P1D"

    def test_xy_yearly_grain(self) -> None:
        ds = _make_dataset(
            metrics=[_make_metric("count")],
            main_dttm_col="dt",
            columns=[_make_col("dt", "TIMESTAMP", is_dttm=True)],
        )
        config, _, _, _, _ = heuristic_chart_config("Show yearly trend", ds, [])
        assert config is not None
        assert config["time_grain"] == "P1Y"

    def test_xy_no_metric(self) -> None:
        ds = _make_dataset(
            columns=[_make_col("name", "VARCHAR")],
            metrics=[],
            main_dttm_col="dt",
        )
        config, chart_type, confidence, _, warnings = heuristic_chart_config(
            "Show trend over time", ds, []
        )
        assert config is None
        assert confidence == 0.1

    def test_pie_chart(self) -> None:
        ds = _make_dataset(
            columns=[_make_col("region", "VARCHAR")],
            metrics=[_make_metric("revenue")],
        )
        config, chart_type, confidence, _, _ = heuristic_chart_config(
            "Show proportion by region", ds, []
        )
        assert config is not None
        assert config["chart_type"] == "pie"
        assert config["group_by"] == "region"
        assert chart_type == "pie"

    def test_pie_missing_dimension(self) -> None:
        ds = _make_dataset(
            columns=[],
            metrics=[_make_metric("count")],
        )
        config, chart_type, _, _, warnings = heuristic_chart_config(
            "Show breakdown", ds, []
        )
        assert config is None
        assert any("dimension" in w.lower() for w in warnings)

    def test_table_chart(self) -> None:
        ds = _make_dataset(
            columns=[
                _make_col("name", "VARCHAR"),
                _make_col("amount", "FLOAT"),
            ],
        )
        config, chart_type, confidence, _, _ = heuristic_chart_config(
            "List all rows as a table", ds, []
        )
        assert config is not None
        assert config["chart_type"] == "table"
        assert len(config["columns"]) == 2
        # Numeric column should have aggregate
        amount_col = [c for c in config["columns"] if c["name"] == "amount"][0]
        assert amount_col["aggregate"] == "SUM"

    def test_table_no_columns(self) -> None:
        ds = _make_dataset(columns=[])
        config, chart_type, confidence, _, warnings = heuristic_chart_config(
            "Show me a table", ds, []
        )
        assert config is None
        assert any("no columns" in w.lower() for w in warnings)

    def test_comparison_bar_chart(self) -> None:
        ds = _make_dataset(
            columns=[
                _make_col("region", "VARCHAR"),
                _make_col("created_at", "TIMESTAMP", is_dttm=True),
            ],
            metrics=[_make_metric("revenue")],
            main_dttm_col="created_at",
        )
        config, chart_type, _, _, _ = heuristic_chart_config(
            "Compare sales by region", ds, []
        )
        assert config is not None
        assert config["chart_type"] == "xy"
        assert config["kind"] == "bar"
        assert chart_type == "echarts_timeseries_bar"

    def test_explicit_bar_count_uses_requested_dimension(self) -> None:
        ds = _make_dataset(
            columns=[
                _make_col("species", "VARCHAR"),
                _make_col("island", "VARCHAR"),
            ],
            metrics=[_make_metric("count")],
        )
        config, chart_type, _, _, _ = heuristic_chart_config(
            "Create a bar chart showing COUNT(*) by island", ds, []
        )
        assert config is not None
        assert config["chart_type"] == "xy"
        assert config["kind"] == "bar"
        assert config["x"]["name"] == "island"
        assert chart_type == "echarts_timeseries_bar"

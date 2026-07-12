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
"""Unit tests for structured chart intent → generate_chart config mapping."""

from __future__ import annotations

from types import SimpleNamespace

from axbi.mcp_service.ai.structured_intent import (
    chart_config_from_structured_intent,
    has_structured_chart_fields,
    resolve_metric_ref,
)


def _dataset(
    *,
    columns: list[tuple[str, bool]] | None = None,
    metrics: list[str] | None = None,
    main_dttm: str | None = None,
) -> SimpleNamespace:
    col_objs = [
        SimpleNamespace(column_name=name, is_dttm=is_dttm, type="VARCHAR")
        for name, is_dttm in (columns or [])
    ]
    metric_objs = [
        SimpleNamespace(metric_name=name, expression=f"SUM({name})")
        for name in (metrics or [])
    ]
    return SimpleNamespace(
        columns=col_objs,
        metrics=metric_objs,
        main_dttm_col=main_dttm,
        table_name="sales",
        id=1,
    )


def test_has_structured_chart_fields() -> None:
    assert has_structured_chart_fields(["revenue"], ["region"], "xy")
    assert has_structured_chart_fields([], [], "big_number")
    assert has_structured_chart_fields(["m"], [], None)
    assert not has_structured_chart_fields([], [], None)
    assert not has_structured_chart_fields([], [], "  ")


def test_resolve_metric_prefers_saved_metric() -> None:
    ds = _dataset(columns=[("amount", False)], metrics=["revenue", "count"])
    assert resolve_metric_ref("revenue", ds) == {
        "name": "revenue",
        "saved_metric": True,
    }
    assert resolve_metric_ref("amount", ds) == {
        "name": "amount",
        "aggregate": "SUM",
    }


def test_xy_bar_from_metrics_and_dimension() -> None:
    ds = _dataset(
        columns=[("region", False), ("order_date", True)],
        metrics=["revenue"],
        main_dttm="order_date",
    )
    config, chart_type, confidence, explanation, warnings = (
        chart_config_from_structured_intent(
            chart_type="xy",
            metrics=["revenue"],
            dimensions=["region"],
            dataset=ds,
            kind="bar",
        )
    )
    assert config is not None
    assert config["chart_type"] == "xy"
    assert config["kind"] == "bar"
    assert config["x"] == {"name": "region"}
    assert config["y"] == [{"name": "revenue", "saved_metric": True}]
    assert chart_type.startswith("echarts_timeseries_")
    assert confidence >= 0.7
    assert "structured intent" in explanation.lower()
    assert warnings == []


def test_big_number_with_trendline() -> None:
    ds = _dataset(
        columns=[("order_date", True)],
        metrics=["revenue"],
        main_dttm="order_date",
    )
    config, chart_type, confidence, _, _ = chart_config_from_structured_intent(
        chart_type="big_number",
        metrics=["revenue"],
        dimensions=[],
        dataset=ds,
    )
    assert config is not None
    assert config["chart_type"] == "big_number"
    assert config["metric"]["saved_metric"] is True
    assert config["show_trendline"] is True
    assert config["temporal_column"] == "order_date"
    assert chart_type == "big_number"
    assert confidence >= 0.7


def test_pie_requires_metric_and_dimension() -> None:
    ds = _dataset(columns=[("region", False)], metrics=["revenue"])
    config, _, confidence, explanation, _ = chart_config_from_structured_intent(
        chart_type="pie",
        metrics=["revenue"],
        dimensions=[],
        dataset=ds,
    )
    assert config is None
    assert confidence < 0.3
    assert "metric" in explanation.lower() or "dimension" in explanation.lower()


def test_filters_and_time_range_normalized() -> None:
    ds = _dataset(
        columns=[("region", False)],
        metrics=["revenue"],
    )
    config, _, _, _, warnings = chart_config_from_structured_intent(
        chart_type="xy",
        metrics=["revenue"],
        dimensions=["region"],
        filters=[{"column": "region", "operator": "eq", "value": "EMEA"}],
        time_range="Last 90 days",
        dataset=ds,
        kind="bar",
    )
    assert config is not None
    assert config["filters"] == [
        {"column": "region", "op": "=", "value": "EMEA"},
    ]
    # time_range is not a valid generate_chart config field; warn instead
    assert "time_range" not in config
    assert any("Last 90 days" in w for w in warnings)


def test_table_falls_back_to_dimensions_and_metrics() -> None:
    ds = _dataset(
        columns=[("region", False), ("product", False)],
        metrics=["revenue"],
    )
    config, chart_type, _, _, _ = chart_config_from_structured_intent(
        chart_type="table",
        metrics=["revenue"],
        dimensions=["region", "product"],
        dataset=ds,
    )
    assert chart_type == "table"
    assert config is not None
    assert config["columns"][0] == {"name": "region"}
    assert any(c.get("saved_metric") for c in config["columns"])

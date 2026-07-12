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
"""Eval-style smoke tests for plan → structured chart config quality.

These tests do not require a live DB. They score whether common business
prompts produce usable chart intents and valid generate_chart configs.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from axbi.mcp_service.ai.asset_search import _query_tokens, _score_result
from axbi.mcp_service.ai.grounding_utils import plan_should_block_compose
from axbi.mcp_service.ai.structured_intent import chart_config_from_structured_intent
from axbi.mcp_service.ai.tool.plan_dashboard import (
    _build_chart_intents_heuristic,
    _build_global_filters_heuristic,
)


def _sales_dataset_dict() -> dict[str, Any]:
    return {
        "id": 42,
        "name": "sales_orders",
        "description": "Sales order facts with revenue by region",
        "certified": True,
        "metrics": ["revenue", "order_count"],
        "columns": [
            {
                "name": "order_date",
                "type": "DATE",
                "is_numeric": False,
                "is_dttm": True,
            },
            {
                "name": "region",
                "type": "VARCHAR",
                "is_numeric": False,
                "is_dttm": False,
            },
            {
                "name": "product",
                "type": "VARCHAR",
                "is_numeric": False,
                "is_dttm": False,
            },
            {"name": "amount", "type": "FLOAT", "is_numeric": True, "is_dttm": False},
        ],
        "grounding": {
            "measures": [
                {"name": "revenue", "expression": "SUM(amount)", "aliases": ["sales"]}
            ],
            "time_columns": ["order_date"],
            "glossary": {"revenue": ["sales", "bookings"]},
        },
    }


def _dataset_orm() -> SimpleNamespace:
    return SimpleNamespace(
        id=42,
        table_name="sales_orders",
        main_dttm_col="order_date",
        metrics=[
            SimpleNamespace(metric_name="revenue", expression="SUM(amount)"),
            SimpleNamespace(metric_name="order_count", expression="COUNT(*)"),
        ],
        columns=[
            SimpleNamespace(column_name="order_date", type="DATE", is_dttm=True),
            SimpleNamespace(column_name="region", type="VARCHAR", is_dttm=False),
            SimpleNamespace(column_name="product", type="VARCHAR", is_dttm=False),
            SimpleNamespace(column_name="amount", type="FLOAT", is_dttm=False),
        ],
    )


def test_eval_sales_prompt_tokens_rank_sales_dataset() -> None:
    prompt = "Create an executive sales dashboard with revenue trends"
    sales_score = _score_result("sales_orders", "Sales order facts", prompt)
    other_score = _score_result("hr_employees", "People directory", prompt)
    assert "sales" in _query_tokens(prompt)
    assert sales_score > other_score
    assert sales_score >= 0.35


def test_eval_heuristic_plan_prefers_saved_metrics() -> None:
    intents = _build_chart_intents_heuristic(
        "Show revenue trend by region and top products",
        [_sales_dataset_dict()],
        max_charts=6,
    )
    assert intents
    metric_names = {m for intent in intents for m in intent.metrics}
    assert "revenue" in metric_names or "order_count" in metric_names
    # Structured fields present for every intent
    for intent in intents:
        assert intent.dataset_id == 42
        assert intent.chart_type
        assert intent.purpose


def test_eval_structured_intents_compile_to_chart_configs() -> None:
    ds = _dataset_orm()
    intents = _build_chart_intents_heuristic(
        "KPI total revenue trend and breakdown by region",
        [_sales_dataset_dict()],
        max_charts=5,
    )
    compiled = 0
    for intent in intents:
        config, chart_type, confidence, _, warnings = (
            chart_config_from_structured_intent(
                chart_type=intent.chart_type,
                metrics=intent.metrics,
                dimensions=intent.dimensions,
                filters=intent.filters,
                time_range=intent.time_range,
                dataset=ds,
            )
        )
        if config is None:
            continue
        assert "chart_type" in config
        assert confidence >= 0.4
        assert chart_type
        compiled += 1
    assert compiled >= 2


def test_eval_global_filters_include_targets() -> None:
    filters = _build_global_filters_heuristic([_sales_dataset_dict()])
    assert filters
    assert any(f.get("filter_type") == "filter_time" for f in filters)
    for filt in filters:
        assert filt.get("targets")
        assert filt["targets"][0]["datasetId"] == 42


def test_eval_confidence_gate_blocks_empty_intents() -> None:
    block, reason = plan_should_block_compose(0.9, 0, [])
    assert block is True
    assert "intent" in reason.lower()


def test_eval_confidence_gate_allows_reasonable_plan() -> None:
    block, _ = plan_should_block_compose(0.55, 3, [], min_confidence=0.25)
    assert block is False

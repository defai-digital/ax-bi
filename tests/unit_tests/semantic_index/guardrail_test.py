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
"""Tests for the deterministic governance guardrail."""

from __future__ import annotations

from types import SimpleNamespace

from superset.semantic_index.grounding import build_grounding_contract
from superset.semantic_index.guardrail import check_config

_POLICIES = [
    {
        "type": "non_additive",
        "target": "revenue",
        "dimensions": ["region"],
        "reason": "mixed local currencies (LCY)",
        "severity": "block",
    },
    {
        "type": "non_additive",
        "target": "total_revenue",
        "dimensions": ["region"],
        "reason": "mixed local currencies (LCY)",
        "severity": "block",
    },
]


def _contract():
    dataset = SimpleNamespace(
        id=11,
        table_name="service_revenue_2025",
        schema="public",
        description="",
        main_dttm_col="month_date",
        database=None,
        columns=[
            SimpleNamespace(column_name="region", type="TEXT"),
            SimpleNamespace(column_name="client", type="TEXT"),
            SimpleNamespace(column_name="revenue", type="DOUBLE"),
        ],
        metrics=[
            SimpleNamespace(metric_name="total_revenue", expression="SUM(revenue)"),
        ],
    )
    return build_grounding_contract(dataset, policies=_POLICIES)


def test_big_number_summing_across_regions_is_blocked() -> None:
    config = {
        "chart_type": "big_number",
        "metric": {"name": "revenue", "aggregate": "SUM"},
    }
    violations = check_config(config, _contract())
    assert len(violations) == 1
    assert violations[0].target == "revenue"
    assert violations[0].severity == "block"
    assert "region" in violations[0].message


def test_grouping_by_region_is_safe() -> None:
    config = {
        "chart_type": "xy",
        "x": {"name": "region"},
        "y": [{"name": "revenue", "aggregate": "SUM"}],
    }
    assert check_config(config, _contract()) == []


def test_filtering_region_to_single_value_is_safe() -> None:
    config = {
        "chart_type": "xy",
        "x": {"name": "client"},
        "y": [{"name": "total_revenue", "saved_metric": True}],
        "filters": [{"column": "region", "operator": "eq", "value": "AU"}],
    }
    assert check_config(config, _contract()) == []


def test_breakdown_by_client_without_region_is_blocked() -> None:
    config = {
        "chart_type": "xy",
        "x": {"name": "client"},
        "y": [{"name": "total_revenue", "saved_metric": True}],
    }
    violations = check_config(config, _contract())
    assert len(violations) == 1
    assert violations[0].target == "total_revenue"


def test_table_with_region_column_is_safe() -> None:
    config = {
        "chart_type": "table",
        "columns": [{"name": "region"}, {"name": "revenue", "aggregate": "SUM"}],
    }
    assert check_config(config, _contract()) == []


def test_unaffected_measure_is_not_flagged() -> None:
    config = {
        "chart_type": "big_number",
        "metric": {"name": "count", "saved_metric": True},
    }
    assert check_config(config, _contract()) == []


def test_no_policies_means_no_violations() -> None:
    contract = build_grounding_contract(
        SimpleNamespace(id=1, table_name="t", columns=[], metrics=[])
    )
    config = {
        "chart_type": "big_number",
        "metric": {"name": "revenue", "aggregate": "SUM"},
    }
    assert check_config(config, contract) == []

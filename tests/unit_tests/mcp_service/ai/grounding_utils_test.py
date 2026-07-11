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
"""Unit tests for GenAI grounding helpers."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from superset.mcp_service.ai.grounding_utils import (
    enrich_dataset_plan_entry,
    grounding_summary_dict,
    plan_should_block_compose,
    preferred_metric_names,
    resolve_name_via_grounding,
)


def test_plan_should_block_on_empty_intents() -> None:
    block, reason = plan_should_block_compose(0.9, 0, [])
    assert block is True
    assert "no chart intents" in reason.lower()


def test_plan_should_block_on_low_confidence() -> None:
    block, reason = plan_should_block_compose(
        0.1,
        3,
        ["Which dataset?"],
        min_confidence=0.25,
    )
    assert block is True
    assert "0.10" in reason
    assert "Which dataset" in reason


def test_plan_should_not_block_when_force() -> None:
    block, reason = plan_should_block_compose(0.05, 0, [], force=True)
    assert block is False
    assert reason == ""


def test_plan_allows_adequate_confidence() -> None:
    block, _ = plan_should_block_compose(0.5, 2, [], min_confidence=0.25)
    assert block is False


def test_resolve_name_via_grounding_measure_and_alias() -> None:
    contract = SimpleNamespace(
        measures=[
            SimpleNamespace(name="revenue", aliases=["sales", "bookings"]),
        ],
        dimensions=[
            SimpleNamespace(name="region", aliases=["geo", "territory"]),
        ],
        glossary={"customer": ["client", "account"]},
    )
    assert resolve_name_via_grounding("sales", contract, prefer="measure") == "revenue"
    assert (
        resolve_name_via_grounding("territory", contract, prefer="dimension")
        == "region"
    )
    assert resolve_name_via_grounding("client", contract, prefer="any") == "customer"


def test_preferred_metric_names_from_dataset_metrics() -> None:
    ds = SimpleNamespace(
        id=1,
        metrics=[
            SimpleNamespace(metric_name="count"),
            SimpleNamespace(metric_name="revenue"),
        ],
        columns=[],
    )
    with patch(
        "superset.mcp_service.ai.grounding_utils.load_grounding_contract",
        return_value=None,
    ):
        assert preferred_metric_names(ds) == ["count", "revenue"]


def test_enrich_dataset_plan_entry_adds_metrics() -> None:
    ds = SimpleNamespace(
        id=7,
        metrics=[SimpleNamespace(metric_name="revenue")],
        columns=[],
        table_name="sales",
    )
    entry = {"id": 7, "name": "sales", "columns": []}
    with patch(
        "superset.mcp_service.ai.grounding_utils.load_grounding_contract",
        return_value=None,
    ):
        enriched = enrich_dataset_plan_entry(entry, ds)
    assert enriched["metrics"] == ["revenue"]


def test_grounding_summary_dict_compact() -> None:
    contract = SimpleNamespace(
        measures=[
            SimpleNamespace(
                name="revenue",
                expression="SUM(amt)",
                description="Booked",
                aliases=["sales"],
            )
        ],
        dimensions=[
            SimpleNamespace(
                name="region",
                type="STRING",
                is_temporal=False,
                aliases=["geo"],
            )
        ],
        time_columns=["order_date"],
        glossary={"revenue": ["sales"]},
        instructions=["Prefer certified metrics"],
        policies=[{"type": "non_additive", "target": "balance"}],
    )
    summary = grounding_summary_dict(contract)
    assert summary["measures"][0]["name"] == "revenue"
    assert summary["time_columns"] == ["order_date"]
    assert "revenue" in summary["glossary"]

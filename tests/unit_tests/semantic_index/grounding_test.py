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
"""Tests for the grounding contract and governance loaders."""

from __future__ import annotations

from types import SimpleNamespace

from axbi.semantic_index.governance import (
    aliases_for,
    load_dataset_eval_cases,
    load_dataset_instructions,
    load_dataset_policies,
)
from axbi.semantic_index.grounding import build_grounding_contract


def _dataset() -> SimpleNamespace:
    return SimpleNamespace(
        id=11,
        table_name="service_revenue_2025",
        schema="public",
        description="Service revenue by client 2025 (LCY).",
        main_dttm_col="month_date",
        database=SimpleNamespace(database_name="analytics"),
        columns=[
            SimpleNamespace(
                column_name="month_date",
                type="TIMESTAMP",
                description="Revenue month",
                is_dttm=True,
                groupby=False,
                filterable=True,
            ),
            SimpleNamespace(
                column_name="client",
                type="VARCHAR",
                description="Client name",
                is_dttm=False,
                groupby=True,
                filterable=True,
            ),
        ],
        metrics=[
            SimpleNamespace(
                metric_name="total_revenue",
                expression="SUM(revenue)",
                verbose_name="Total Revenue (LCY)",
                description="Booked revenue",
                d3format=",.0f",
            )
        ],
    )


ALIASES = {
    ("metric", "total_revenue"): ["turnover", "營收"],
    ("column", "client"): ["customer", "account"],
}
INSTRUCTIONS = ["Amounts are in LCY; do not sum across regions."]


def test_aliases_for_normalizes_lookup() -> None:
    assert aliases_for(ALIASES, "Metric", "TOTAL_REVENUE") == ["turnover", "營收"]
    assert aliases_for(ALIASES, "column", "missing") == []
    assert aliases_for(None, "column", "client") == []


def test_load_dataset_instructions_from_extra_json() -> None:
    ds = SimpleNamespace(extra='{"ai": {"instructions": ["one", "two"]}}')
    assert load_dataset_instructions(ds) == ["one", "two"]

    ds_dict = SimpleNamespace(extra={"ai": {"instructions": "single"}})
    assert load_dataset_instructions(ds_dict) == ["single"]

    assert load_dataset_instructions(SimpleNamespace(extra=None)) == []
    assert load_dataset_instructions(SimpleNamespace(extra="not json")) == []


def test_load_dataset_policies_from_extra_json() -> None:
    ds = SimpleNamespace(
        extra=(
            '{"ai": {"policies": [{"type": "non_additive", "target": "revenue",'
            ' "dimensions": ["region"]}, "not-a-dict"]}}'
        )
    )
    policies = load_dataset_policies(ds)
    assert len(policies) == 1
    assert policies[0]["target"] == "revenue"

    assert load_dataset_policies(SimpleNamespace(extra=None)) == []


def test_load_dataset_eval_cases_from_extra() -> None:
    ds = SimpleNamespace(
        extra=(
            '{"ai": {"eval_cases": ['
            '{"prompt": "revenue by region", "expect_measure": "total_revenue"},'
            '{"prompt": "  "}, {"no_prompt": 1}]}}'
        )
    )
    cases = load_dataset_eval_cases(ds)
    # blank-prompt and prompt-less entries are dropped
    assert len(cases) == 1
    assert cases[0]["expect_measure"] == "total_revenue"
    assert load_dataset_eval_cases(SimpleNamespace(extra=None)) == []


def test_contract_carries_and_renders_policies() -> None:
    policies = [
        {
            "type": "non_additive",
            "target": "total_revenue",
            "dimensions": ["region"],
            "reason": "mixed LCY",
        }
    ]
    contract = build_grounding_contract(_dataset(), policies=policies)
    assert contract.policies == policies
    md = contract.to_markdown()
    assert "## Policies (enforced)" in md
    assert "Do NOT aggregate 'total_revenue' across region" in md


def test_build_grounding_contract_fields() -> None:
    contract = build_grounding_contract(
        _dataset(), aliases=ALIASES, instructions=INSTRUCTIONS
    )

    assert contract.dataset_name == "service_revenue_2025"
    assert contract.time_columns == ["month_date"]

    measure = next(m for m in contract.measures if m.name == "total_revenue")
    assert measure.expression == "SUM(revenue)"
    assert measure.aliases == ["turnover", "營收"]

    client = next(d for d in contract.dimensions if d.name == "client")
    assert client.groupable
    assert client.filterable
    assert client.aliases == ["customer", "account"]

    assert contract.glossary["total_revenue"] == ["turnover", "營收"]
    assert contract.instructions == INSTRUCTIONS


def test_grounding_contract_markdown_is_promptable() -> None:
    md = build_grounding_contract(
        _dataset(), aliases=ALIASES, instructions=INSTRUCTIONS
    ).to_markdown()

    # Certified measure definition is surfaced verbatim for the LLM to reuse.
    assert "= SUM(revenue)" in md
    # Disambiguation instruction is front and center.
    assert "## Instructions (MUST follow)" in md
    assert "do not sum across regions" in md
    # Synonyms travel with the objects.
    assert "aka turnover" in md
    assert "## Glossary" in md


def test_grounding_contract_to_dict_is_serializable() -> None:
    payload = build_grounding_contract(_dataset(), aliases=ALIASES).to_dict()
    assert payload["dataset_id"] == 11
    assert payload["measures"][0]["name"] == "total_revenue"
    assert payload["time_columns"] == ["month_date"]

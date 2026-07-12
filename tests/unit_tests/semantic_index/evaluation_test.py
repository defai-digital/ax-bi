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
"""Tests for the deterministic semantic-layer evaluation harness."""

from __future__ import annotations

from types import SimpleNamespace

from axbi.semantic_index.evaluation import (
    build_generation_cases,
    build_guardrail_cases,
    evaluate_contract,
    evaluate_generation,
    evaluate_grounding,
    evaluate_guardrail,
    GenerationCase,
)
from axbi.semantic_index.grounding import build_grounding_contract

_POLICIES = [
    {
        "type": "non_additive",
        "target": "total_revenue",
        "dimensions": ["region"],
        "reason": "mixed LCY",
        "severity": "block",
    }
]


def _rich_dataset() -> SimpleNamespace:
    return SimpleNamespace(
        id=11,
        table_name="service_revenue_2025",
        schema="public",
        description="",
        main_dttm_col="month_date",
        database=None,
        columns=[
            SimpleNamespace(
                column_name="region",
                type="TEXT",
                groupby=True,
                filterable=True,
                is_dttm=False,
                description=None,
            ),
            SimpleNamespace(
                column_name="month_date",
                type="TIMESTAMP",
                groupby=True,
                filterable=True,
                is_dttm=True,
                description=None,
            ),
        ],
        metrics=[
            SimpleNamespace(
                metric_name="total_revenue",
                expression="SUM(revenue)",
                verbose_name="",
                d3format=",.0f",
                description=None,
            )
        ],
    )


def _rich_contract():
    return build_grounding_contract(
        _rich_dataset(),
        aliases={("metric", "total_revenue"): ["turnover"]},
        instructions=["Do not sum across regions."],
        policies=_POLICIES,
    )


def test_build_guardrail_cases_from_policy() -> None:
    cases = build_guardrail_cases(_rich_contract())
    # one violating + two safe cases per non_additive policy
    assert len(cases) == 3
    assert sum(1 for c in cases if c.should_block) == 1
    assert sum(1 for c in cases if not c.should_block) == 2


def test_guardrail_scores_perfect_on_enforced_policy() -> None:
    contract = _rich_contract()
    score = evaluate_guardrail(contract, build_guardrail_cases(contract))
    assert score["total"] == 3
    assert score["accuracy"] == 1.0
    assert score["precision"] == 1.0
    assert score["recall"] == 1.0


def test_grounding_maturity_high_for_rich_contract() -> None:
    grounding = evaluate_grounding(_rich_contract())
    assert grounding["maturity_score"] == 1.0
    assert grounding["signals"]["has_policies"] is True
    assert grounding["signals"]["has_time_dimension"] is True


def test_grounding_maturity_low_for_bare_contract() -> None:
    bare = build_grounding_contract(
        SimpleNamespace(id=1, table_name="bare", columns=[], metrics=[])
    )
    grounding = evaluate_grounding(bare)
    assert grounding["maturity_score"] == 0.0
    assert grounding["policy_count"] == 0


def test_evaluate_generation_scores_validity_and_compliance() -> None:
    contract = _rich_contract()  # non_additive total_revenue across region

    def generate(prompt: str):
        if "crash" in prompt:
            raise ValueError("boom")
        if "money" in prompt:  # aggregates across regions -> blocked
            return {"chart_type": "big_number", "metric": {"name": "total_revenue"}}
        if "region" in prompt:  # grouped by region -> compliant
            return {
                "chart_type": "xy",
                "x": {"name": "region"},
                "y": [{"name": "total_revenue"}],
            }
        return None  # invalid

    cases = [
        GenerationCase("total money", expect_chart_type="big_number"),
        GenerationCase(
            "revenue by region",
            expect_chart_type="xy",
            expect_measure="total_revenue",
        ),
        GenerationCase("please crash"),
        GenerationCase("nothing useful"),
    ]
    score = evaluate_generation(cases, generate, contract)

    assert score["total"] == 4
    assert score["valid"] == 2  # big_number + xy are dicts; crash/None are not
    assert score["governance_compliant"] == 1  # big_number is blocked; region is ok
    assert score["intent_match_rate"] == 1.0  # both expectation cases matched


def test_build_generation_cases_from_contract() -> None:
    cases = build_generation_cases(_rich_contract())
    # 'count' is skipped; total_revenue yields a "show" case + a "by region" case
    assert len(cases) == 2
    assert all(c.expect_measure == "total_revenue" for c in cases)
    assert any("region" in c.prompt for c in cases)


def test_generation_case_from_dict() -> None:
    case = GenerationCase.from_dict({"prompt": "x", "expect_chart_type": "pie"})
    assert case.prompt == "x"
    assert case.expect_chart_type == "pie"
    assert case.expect_measure is None


def test_evaluate_contract_report() -> None:
    report = evaluate_contract(_rich_contract())
    assert report.dataset_id == 11
    assert report.guardrail["accuracy"] == 1.0
    assert report.grounding["maturity_score"] == 1.0
    payload = report.to_dict()
    assert payload["dataset_name"] == "service_revenue_2025"
    assert "guardrail" in payload
    assert "grounding" in payload

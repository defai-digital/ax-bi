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
"""Repeatable evaluation for the GenAI BI semantic layer.

You cannot improve what you do not measure. This module scores two things
deterministically (no LLM required):

1. **Guardrail correctness** — for every declared governance policy, auto-derive
   a violating case and safe cases, then verify the guardrail decides each
   correctly (precision/recall). This proves each policy is actually enforced.
2. **Grounding maturity** — how complete the governed data model is (certified
   measures, synonym coverage, instructions, policies, a time dimension), since
   "the data model is the upper bound on AI quality".

Results persist to ``AIEvaluationRun`` so a score can be tracked over time.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from axbi.semantic_index.grounding import GroundingContract
from axbi.semantic_index.guardrail import _config_measures, check_config


@dataclass(frozen=True)
class GuardrailCase:
    """A labeled config the guardrail should accept or reject."""

    name: str
    config: dict[str, Any]
    should_block: bool


@dataclass(frozen=True)
class GenerationCase:
    """A prompt-to-dashboard case with optional expected properties."""

    prompt: str
    expect_chart_type: str | None = None
    expect_measure: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GenerationCase:
        """Build a case from an authored dict (JSON file or dataset extra)."""

        return cls(
            prompt=str(data["prompt"]),
            expect_chart_type=data.get("expect_chart_type"),
            expect_measure=data.get("expect_measure"),
        )


def build_generation_cases(contract: GroundingContract) -> list[GenerationCase]:
    """Auto-derive a minimal golden set from a contract's measures.

    Used when no golden cases are authored, so the eval works out of the box.
    Authored cases (a JSON file or the dataset's ``extra.ai.eval_cases``) are
    preferred — they can encode nuance this heuristic can't.
    """

    dimensions = [d.name for d in contract.dimensions if not d.is_temporal]
    dimension = dimensions[0] if dimensions else None
    cases: list[GenerationCase] = []
    for measure in contract.measures:
        if measure.name == "count":  # the trivial COUNT(*) metric carries no intent
            continue
        label = measure.verbose_name or measure.name
        cases.append(GenerationCase(f"show {label}", expect_measure=measure.name))
        if dimension:
            cases.append(
                GenerationCase(f"{label} by {dimension}", expect_measure=measure.name)
            )
    return cases


def evaluate_generation(
    cases: list[GenerationCase],
    generate_fn: Callable[[str], dict[str, Any] | None],
    contract: GroundingContract,
) -> dict[str, Any]:
    """Score end-to-end prompt-to-dashboard generation.

    ``generate_fn`` maps a prompt to a chart config (dict) using whatever
    generator you plug in — the LLM intent mapper, the heuristic fallback, or a
    scripted stub for tests. Each generated config is scored on three axes:
    it is *valid* (a non-empty dict), *governance-compliant* (no blocking
    guardrail violation), and, when the case declares expectations, an *intent
    match* (right chart type / uses the expected measure). This measures the
    real payoff of the semantic layer: does the pipeline produce correct,
    policy-respecting dashboards?
    """

    total = len(cases)
    valid = compliant = matched = expected = 0
    details: list[dict[str, Any]] = []
    for case in cases:
        error: str | None = None
        config: dict[str, Any] | None = None
        try:
            config = generate_fn(case.prompt)
        except Exception as exc:  # pylint: disable=broad-except
            error = f"{type(exc).__name__}: {exc}"

        is_valid = isinstance(config, dict) and bool(config)
        violations = check_config(config, contract) if is_valid else []
        blocked = [v for v in violations if v.severity == "block"]
        is_compliant = is_valid and not blocked

        has_expectation = bool(case.expect_chart_type or case.expect_measure)
        intent_ok = is_valid
        if isinstance(config, dict) and case.expect_chart_type:
            intent_ok = intent_ok and config.get("chart_type") == case.expect_chart_type
        if isinstance(config, dict) and case.expect_measure:
            intent_ok = intent_ok and case.expect_measure in _config_measures(config)

        valid += int(is_valid)
        compliant += int(is_compliant)
        if has_expectation:
            expected += 1
            matched += int(bool(intent_ok))

        details.append(
            {
                "prompt": case.prompt,
                "valid": is_valid,
                "governance_compliant": is_compliant,
                "blocked_by": [v.message for v in blocked],
                "intent_match": intent_ok if has_expectation else None,
                "error": error,
            }
        )

    return {
        "total": total,
        "valid": valid,
        "governance_compliant": compliant,
        "validity_rate": round(valid / total, 4) if total else 1.0,
        "compliance_rate": round(compliant / total, 4) if total else 1.0,
        "intent_match_rate": round(matched / expected, 4) if expected else None,
        "details": details,
    }


@dataclass(frozen=True)
class EvalReport:
    """Scored evaluation for one dataset's governed semantic layer."""

    dataset_id: int | None
    dataset_name: str
    guardrail: dict[str, Any] = field(default_factory=dict)
    grounding: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset_id": self.dataset_id,
            "dataset_name": self.dataset_name,
            "guardrail": self.guardrail,
            "grounding": self.grounding,
        }


def build_guardrail_cases(contract: GroundingContract) -> list[GuardrailCase]:
    """Auto-derive guardrail test cases from the contract's policies.

    For each ``non_additive`` policy this yields one violating case (aggregate
    the measure with no breakdown/filter) and two safe cases (grouped by the
    dimension, and filtered to a single value). The suite therefore validates
    that every declared policy is genuinely enforceable.
    """

    cases: list[GuardrailCase] = []
    for policy in contract.policies:
        if policy.get("type") != "non_additive":
            continue
        target = str(policy.get("target", "")).strip()
        dimensions = [
            str(d).strip() for d in policy.get("dimensions", []) if str(d).strip()
        ]
        if not target or not dimensions:
            continue
        dimension = dimensions[0]
        cases.append(
            GuardrailCase(
                name=f"block: aggregate '{target}' across '{dimension}'",
                config={
                    "chart_type": "big_number",
                    "metric": {"name": target, "aggregate": "SUM"},
                },
                should_block=True,
            )
        )
        cases.append(
            GuardrailCase(
                name=f"allow: '{target}' grouped by '{dimension}'",
                config={
                    "chart_type": "xy",
                    "x": {"name": dimension},
                    "y": [{"name": target, "aggregate": "SUM"}],
                },
                should_block=False,
            )
        )
        cases.append(
            GuardrailCase(
                name=f"allow: '{target}' filtered to one '{dimension}'",
                config={
                    "chart_type": "big_number",
                    "metric": {"name": target, "aggregate": "SUM"},
                    "filters": [
                        {"column": dimension, "operator": "eq", "value": "_single_"}
                    ],
                },
                should_block=False,
            )
        )
    return cases


def evaluate_guardrail(
    contract: GroundingContract,
    cases: list[GuardrailCase],
) -> dict[str, Any]:
    """Score the guardrail against labeled cases (accuracy/precision/recall)."""

    true_pos = false_pos = true_neg = false_neg = 0
    details: list[dict[str, Any]] = []
    for case in cases:
        predicted_block = bool(check_config(case.config, contract))
        correct = predicted_block == case.should_block
        if case.should_block and predicted_block:
            true_pos += 1
        elif case.should_block and not predicted_block:
            false_neg += 1
        elif not case.should_block and predicted_block:
            false_pos += 1
        else:
            true_neg += 1
        details.append(
            {
                "case": case.name,
                "expected_block": case.should_block,
                "predicted_block": predicted_block,
                "pass": correct,
            }
        )

    total = len(cases)
    passed = true_pos + true_neg
    precision = true_pos / (true_pos + false_pos) if (true_pos + false_pos) else 1.0
    recall = true_pos / (true_pos + false_neg) if (true_pos + false_neg) else 1.0
    accuracy = passed / total if total else 1.0
    return {
        "total": total,
        "passed": passed,
        "accuracy": round(accuracy, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "details": details,
    }


def evaluate_grounding(contract: GroundingContract) -> dict[str, Any]:
    """Score how complete the governed data model is (0..1 maturity)."""

    measures = contract.measures
    dimensions = contract.dimensions
    measures_defined = sum(1 for measure in measures if measure.expression)
    measures_with_alias = sum(1 for measure in measures if measure.aliases)
    dimensions_with_alias = sum(1 for dimension in dimensions if dimension.aliases)
    has_time = any(dimension.is_temporal for dimension in dimensions)

    signals = {
        "all_measures_defined": bool(measures) and measures_defined == len(measures),
        "has_glossary": bool(contract.glossary),
        "has_instructions": bool(contract.instructions),
        "has_policies": bool(contract.policies),
        "has_time_dimension": has_time,
    }
    maturity = round(sum(1 for value in signals.values() if value) / len(signals), 4)
    return {
        "measure_count": len(measures),
        "measures_defined": measures_defined,
        "measures_with_alias": measures_with_alias,
        "dimension_count": len(dimensions),
        "dimensions_with_alias": dimensions_with_alias,
        "glossary_terms": len(contract.glossary),
        "instruction_count": len(contract.instructions),
        "policy_count": len(contract.policies),
        "signals": signals,
        "maturity_score": maturity,
    }


def evaluate_contract(contract: GroundingContract) -> EvalReport:
    """Run the full deterministic evaluation for a grounding contract."""

    cases = build_guardrail_cases(contract)
    return EvalReport(
        dataset_id=contract.dataset_id,
        dataset_name=contract.dataset_name,
        guardrail=evaluate_guardrail(contract, cases),
        grounding=evaluate_grounding(contract),
    )


def persist_evaluation(report: EvalReport, *, model: str = "deterministic-v1") -> None:
    """Persist an evaluation to ``AIEvaluationRun`` (best-effort)."""

    from axbi.extensions import db
    from axbi.models.ai import AIEvaluationRun
    from axbi.utils import json

    try:
        db.session.add(
            AIEvaluationRun(
                prompt=f"governance-eval:dataset:{report.dataset_id}",
                expected_result=json.dumps(
                    {"guardrail_cases": report.guardrail.get("total", 0)}
                ),
                actual_result=json.dumps(report.to_dict()),
                scores=json.dumps(
                    {
                        "guardrail_accuracy": report.guardrail.get("accuracy"),
                        "grounding_maturity": report.grounding.get("maturity_score"),
                    }
                ),
                model=model,
                tool_versions=json.dumps({"guardrail": "1", "grounding": "1"}),
            )
        )
        db.session.commit()
    except Exception:  # pylint: disable=broad-except
        db.session.rollback()

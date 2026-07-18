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
"""Helpers for loading and applying dataset grounding contracts.

Grounding contracts expose certified measures, dimensions, glossary aliases,
and governance policies. Prompt-to-dashboard quality depends on injecting this
context into planning and metric resolution instead of guessing from raw
column names.
"""

from __future__ import annotations

import logging
from typing import Any

from axbi.commands.ai.authoring.confidence import (
    DEFAULT_MIN_PLAN_CONFIDENCE,
    evaluate_compose_gate,
)

logger = logging.getLogger(__name__)


def plan_should_block_compose(
    confidence: float,
    chart_intent_count: int,
    clarifying_questions: list[str] | None,
    *,
    min_confidence: float = DEFAULT_MIN_PLAN_CONFIDENCE,
    force: bool = False,
) -> tuple[bool, str]:
    """Compatibility adapter for the command-owned confidence policy."""
    return evaluate_compose_gate(
        confidence,
        chart_intent_count,
        clarifying_questions,
        min_confidence=min_confidence,
        force=force,
    )


def load_grounding_contract(dataset: Any) -> Any | None:
    """Load a GroundingContract for a dataset ORM object.

    Returns None when the semantic index package or dataset metadata is
    unavailable so callers can degrade gracefully.
    """
    if dataset is None:
        return None
    try:
        from axbi.semantic_index.governance import (
            load_dataset_aliases,
            load_dataset_instructions,
            load_dataset_policies,
        )
        from axbi.semantic_index.grounding import build_grounding_contract

        dataset_id = getattr(dataset, "id", None)
        aliases = load_dataset_aliases(dataset_id) if dataset_id is not None else {}
        return build_grounding_contract(
            dataset,
            aliases=aliases,
            instructions=load_dataset_instructions(dataset),
            policies=load_dataset_policies(dataset),
        )
    except Exception:  # pylint: disable=broad-except
        logger.debug("Grounding contract unavailable", exc_info=True)
        return None


def grounding_summary_dict(contract: Any | None) -> dict[str, Any]:
    """Compact JSON-serializable summary for plan dataset entries."""
    if contract is None:
        return {}
    measures = [
        {
            "name": m.name,
            "expression": m.expression,
            "description": m.description,
            "aliases": list(m.aliases or []),
        }
        for m in (contract.measures or [])[:20]
    ]
    dimensions = [
        {
            "name": d.name,
            "type": d.type,
            "is_temporal": d.is_temporal,
            "aliases": list(d.aliases or []),
        }
        for d in (contract.dimensions or [])[:30]
    ]
    return {
        "measures": measures,
        "time_columns": list(contract.time_columns or []),
        "glossary": {
            k: list(v) for k, v in (contract.glossary or {}).items() if k and v
        },
        "instructions": list(contract.instructions or [])[:10],
        "policies": list(contract.policies or [])[:10],
        "dimensions": dimensions,
    }


def resolve_name_via_grounding(  # noqa: C901
    name: str,
    contract: Any | None,
    *,
    prefer: str = "any",
) -> str | None:
    """Resolve a business term to a canonical measure/dimension name.

    Args:
        name: User or plan-provided term.
        contract: GroundingContract or None.
        prefer: "measure", "dimension", or "any".

    Returns:
        Canonical name if found, else None.
    """
    cleaned = (name or "").strip()
    if not cleaned or contract is None:
        return None
    key = cleaned.lower()

    measures = list(getattr(contract, "measures", None) or [])
    dimensions = list(getattr(contract, "dimensions", None) or [])
    glossary = dict(getattr(contract, "glossary", None) or {})

    def match_measure() -> str | None:
        for measure in measures:
            if measure.name.lower() == key:
                return measure.name
            for alias in measure.aliases or []:
                if str(alias).lower() == key:
                    return measure.name
        return None

    def match_dimension() -> str | None:
        for dimension in dimensions:
            if dimension.name.lower() == key:
                return dimension.name
            for alias in dimension.aliases or []:
                if str(alias).lower() == key:
                    return dimension.name
        return None

    def match_glossary() -> str | None:
        for canonical, synonyms in glossary.items():
            if str(canonical).lower() == key:
                return str(canonical)
            for synonym in synonyms or []:
                if str(synonym).lower() == key:
                    return str(canonical)
        return None

    if prefer == "measure":
        return match_measure() or match_glossary()
    if prefer == "dimension":
        return match_dimension() or match_glossary()
    return match_measure() or match_dimension() or match_glossary()


def preferred_metric_names(dataset: Any, limit: int = 5) -> list[str]:
    """Return preferred metric names: saved metrics / grounding measures first."""
    contract = load_grounding_contract(dataset)
    if contract and contract.measures:
        return [m.name for m in contract.measures if m.name][:limit]

    names: list[str] = []
    for metric in getattr(dataset, "metrics", []) or []:
        name = getattr(metric, "metric_name", None)
        if name:
            names.append(str(name))
    return names[:limit]


def enrich_dataset_plan_entry(
    ds_dict: dict[str, Any], dataset: Any | None
) -> dict[str, Any]:
    """Attach metrics and grounding summary onto a plan dataset dict."""
    enriched = dict(ds_dict)
    if dataset is None:
        return enriched

    metrics = preferred_metric_names(dataset, limit=10)
    if metrics:
        enriched["metrics"] = metrics

    contract = load_grounding_contract(dataset)
    if summary := grounding_summary_dict(contract):
        enriched["grounding"] = summary
        # Prefer grounding measure names for planner heuristics
        if summary.get("measures") and not metrics:
            enriched["metrics"] = [
                m["name"] for m in summary["measures"] if m.get("name")
            ]
    return enriched

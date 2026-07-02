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
"""Deterministic governance guardrail for generated chart configurations.

Prompting an LLM to "follow the rules" is necessary but not sufficient — models
violate in-context instructions, and heuristic fallbacks ignore them entirely.
This module enforces the semantic layer's structured policies *after* a config
is produced, independent of how it was produced.

The primary policy is ``non_additive``: a measure that must not be aggregated
across a set of dimensions (the semantic-layer model for a mixed-currency /
semi-additive measure). An aggregate is safe only if every non-additive
dimension is either a breakdown (so each bucket stays within one value) or
pinned to a single value by a filter; otherwise the aggregate silently combines
incompatible values.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from superset.semantic_index.grounding import GroundingContract

_EQUALITY_OPERATORS = frozenset({"eq", "==", "=", "equals"})


@dataclass(frozen=True)
class GovernanceViolation:
    """A governance policy violated by a generated chart configuration."""

    policy_type: str
    target: str
    message: str
    severity: str = "warn"  # "block" or "warn"


def _collect_names(value: Any, names: set[str]) -> None:
    """Collect ``name`` fields / bare strings from a nested config fragment."""

    if value is None:
        return
    if isinstance(value, str):
        stripped = value.strip()
        if stripped:
            names.add(stripped)
    elif isinstance(value, dict):
        name = value.get("name")
        if isinstance(name, str) and name.strip():
            names.add(name.strip())
    elif isinstance(value, (list, tuple)):
        for item in value:
            _collect_names(item, names)


def _config_measures(config: dict[str, Any]) -> set[str]:
    """Return the measure names that the config aggregates."""

    measures: set[str] = set()
    for key in ("metric", "metrics", "y"):
        _collect_names(config.get(key), measures)
    # Table columns are measures only when they carry an aggregate.
    for column in config.get("columns") or []:
        if (
            isinstance(column, dict)
            and column.get("aggregate")
            and isinstance(column.get("name"), str)
        ):
            measures.add(column["name"].strip())
    return measures


def _config_breakdowns(config: dict[str, Any]) -> set[str]:
    """Return the dimensions the config splits the measure by."""

    breakdowns: set[str] = set()
    for key in ("x", "group_by", "groupby", "dimensions", "series", "breakdown"):
        _collect_names(config.get(key), breakdowns)
    # Table columns without an aggregate act as group-by dimensions.
    for column in config.get("columns") or []:
        if (
            isinstance(column, dict)
            and not column.get("aggregate")
            and isinstance(column.get("name"), str)
        ):
            breakdowns.add(column["name"].strip())
    return breakdowns


def _config_pinned_dimensions(config: dict[str, Any]) -> set[str]:
    """Return dimensions pinned to a single value by an equality/single filter."""

    pinned: set[str] = set()
    for filter_spec in config.get("filters") or []:
        if not isinstance(filter_spec, dict):
            continue
        column = filter_spec.get("column")
        if not isinstance(column, str) or not column.strip():
            continue
        operator = str(filter_spec.get("operator", "")).lower()
        value = filter_spec.get("value")
        if operator in _EQUALITY_OPERATORS:
            pinned.add(column.strip())
        elif operator == "in" and isinstance(value, (list, tuple)) and len(value) == 1:
            pinned.add(column.strip())
    return pinned


def check_config(
    config: dict[str, Any] | None,
    contract: GroundingContract,
) -> list[GovernanceViolation]:
    """Return governance violations in a generated chart configuration."""

    if not config or not contract.policies:
        return []

    measures = _config_measures(config)
    breakdowns = _config_breakdowns(config)
    pinned = _config_pinned_dimensions(config)
    safe_dimensions = breakdowns | pinned

    violations: list[GovernanceViolation] = []
    for policy in contract.policies:
        if policy.get("type") != "non_additive":
            continue
        target = str(policy.get("target", "")).strip()
        if not target or target not in measures:
            continue
        dimensions = {
            str(dimension).strip()
            for dimension in policy.get("dimensions", [])
            if str(dimension).strip()
        }
        unsafe = dimensions - safe_dimensions
        if not unsafe:
            continue
        reason = str(policy.get("reason", "")).strip()
        message = (
            f"Measure '{target}' is aggregated across {sorted(unsafe)} "
            "without grouping by or filtering to a single value"
        )
        if reason:
            message += f" — {reason}"
        message += (
            f". Fix: group by one of {sorted(unsafe)}, or filter it to a single value."
        )
        violations.append(
            GovernanceViolation(
                policy_type="non_additive",
                target=target,
                message=message,
                severity=str(policy.get("severity", "warn")).strip().lower() or "warn",
            )
        )
    return violations

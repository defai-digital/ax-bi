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
"""Loaders for governed context that grounds semantic retrieval.

The research on LLM-powered analytics is consistent: accuracy comes less from
better embeddings and more from feeding the model *governed business meaning*
(synonyms, metric definitions, disambiguation rules). This module loads that
governed context from Superset so it can enrich both the semantic index and the
grounding contract passed to prompt-to-dashboard.
"""

from __future__ import annotations

from typing import Any

from superset.utils import json

# Type alias: (object_type, object_name_lower) -> list of alias strings.
AliasMap = dict[tuple[str, str], list[str]]


def _alias_key(object_type: str | None, object_name: str | None) -> tuple[str, str]:
    """Return the normalized lookup key for an aliased object."""

    return (
        (object_type or "").strip().lower(),
        (object_name or "").strip().lower(),
    )


def load_dataset_aliases(dataset_id: int) -> AliasMap:
    """Load business synonyms for a dataset and its columns/metrics.

    Reads the ``AISemanticAlias`` table (business glossary) in a single query
    and returns a lookup keyed by ``(object_type, object_name)``. Returns an
    empty map if the table has not been migrated yet.
    """

    from superset.extensions import db
    from superset.models.ai import AISemanticAlias

    try:
        rows = (
            db.session.query(AISemanticAlias)
            .filter(
                AISemanticAlias.dataset_id == dataset_id,
                AISemanticAlias.alias.isnot(None),
            )
            .all()
        )
    except Exception:  # pylint: disable=broad-except
        # The alias table may not exist yet (pre-migration); degrade gracefully.
        return {}

    mapping: AliasMap = {}
    for row in rows:
        alias = (row.alias or "").strip()
        if not alias:
            continue
        key = _alias_key(row.object_type, row.object_name)
        bucket = mapping.setdefault(key, [])
        if alias not in bucket:
            bucket.append(alias)
    return mapping


def aliases_for(
    aliases: AliasMap | None,
    object_type: str,
    object_name: str,
) -> list[str]:
    """Return the aliases registered for one object, or an empty list."""

    if not aliases:
        return []
    return list(aliases.get(_alias_key(object_type, object_name), []))


def _ai_meta(dataset: Any) -> dict[str, Any]:
    """Return the ``extra.ai`` governance block for a dataset, or ``{}``."""

    extra = getattr(dataset, "extra", None)
    if not extra:
        return {}
    try:
        parsed = json.loads(extra) if isinstance(extra, str) else extra
    except (ValueError, TypeError):
        return {}
    if not isinstance(parsed, dict):
        return {}
    ai_meta = parsed.get("ai")
    return ai_meta if isinstance(ai_meta, dict) else {}


def load_dataset_instructions(dataset: Any) -> list[str]:
    """Load governance instructions/caveats for a dataset.

    Instructions are authored disambiguation rules (for example, "amounts are in
    local currency; do not sum across regions") stored under the dataset's
    ``extra`` JSON as ``{"ai": {"instructions": [...]}}``. These are the
    highest-signal, lowest-cost grounding a data owner can add.
    """

    instructions = _ai_meta(dataset).get("instructions")
    if isinstance(instructions, str):
        instructions = [instructions]
    if not isinstance(instructions, list):
        return []
    return [str(item).strip() for item in instructions if str(item).strip()]


def load_dataset_policies(dataset: Any) -> list[dict[str, Any]]:
    """Load structured governance policies for a dataset.

    Policies are machine-enforceable rules (unlike free-text instructions),
    stored under ``{"ai": {"policies": [...]}}``. The primary type is
    ``non_additive`` — a measure that must not be aggregated across the listed
    dimensions without grouping by or filtering to a single value (the
    semantic-layer model for a mixed-currency / semi-additive measure). Example::

        {"type": "non_additive", "target": "revenue", "dimensions": ["region"],
         "reason": "mixed local currencies", "severity": "block"}
    """

    policies = _ai_meta(dataset).get("policies")
    if not isinstance(policies, list):
        return []
    return [policy for policy in policies if isinstance(policy, dict)]


def load_dataset_eval_cases(dataset: Any) -> list[dict[str, Any]]:
    """Load authored prompt-to-dashboard evaluation cases for a dataset.

    Golden cases live under ``{"ai": {"eval_cases": [{"prompt": ...,
    "expect_chart_type": ..., "expect_measure": ...}]}}``. They let a data
    owner pin the expected behaviour of the generation pipeline so accuracy can
    be tracked over time (and gated in CI).
    """

    cases = _ai_meta(dataset).get("eval_cases")
    if not isinstance(cases, list):
        return []
    return [
        case
        for case in cases
        if isinstance(case, dict) and str(case.get("prompt", "")).strip()
    ]

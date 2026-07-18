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
"""Transport-neutral confidence policy for dashboard composition."""

from __future__ import annotations

DEFAULT_MIN_PLAN_CONFIDENCE = 0.25


def evaluate_compose_gate(
    confidence: float,
    chart_intent_count: int,
    clarifying_questions: list[str] | None,
    *,
    min_confidence: float = DEFAULT_MIN_PLAN_CONFIDENCE,
    force: bool = False,
) -> tuple[bool, str]:
    """Return whether authoring must stop before chart/dashboard mutation."""
    if force:
        return False, ""
    if chart_intent_count <= 0:
        return (
            True,
            "Plan has no chart intents. Clarify the request or pin dataset_ids.",
        )
    if confidence < min_confidence:
        questions = clarifying_questions or []
        detail = (
            f" Plan confidence {confidence:.2f} is below minimum {min_confidence:.2f}."
        )
        if questions:
            detail += " Clarifying questions: " + "; ".join(questions[:5])
        else:
            detail += (
                " Rephrase the prompt, pin dataset_ids, or set force=true to proceed."
            )
        return True, detail.strip()
    return False, ""


# Compatibility name for callers migrating from the MCP helper module.
plan_should_block_compose = evaluate_compose_gate

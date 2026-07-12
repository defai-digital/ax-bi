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
from __future__ import annotations

from functools import partial
from typing import Any
from uuid import UUID, uuid4

from axbi.commands.ai.exceptions import AIAuditPersistenceError
from axbi.commands.base import BaseCommand
from axbi.daos.ai import AIEvaluationRunDAO, AIGeneratedArtifactDAO
from axbi.models.ai import AIEvaluationRun, AIGeneratedArtifact
from axbi.utils import json
from axbi.utils.core import get_user_id
from axbi.utils.decorators import on_error, transaction

_AI_TOOL_VERSIONS = {
    "prompt_to_dashboard": "1.0",
    "evaluate_ai_answer": "1.0",
}


class RecordAIGeneratedArtifactCommand(BaseCommand):
    """Persist lineage metadata for one AI-generated BI artifact."""

    def __init__(
        self,
        *,
        artifact_type: str,
        artifact_id: int,
        prompt: str,
        plan_id: str | None,
        tool_chain: list[str],
        source_dataset_ids: list[int],
        confidence: float,
        validation_summary: str = "",
    ) -> None:
        self._artifact_type = artifact_type
        self._artifact_id = artifact_id
        self._prompt = prompt
        self._plan_id = plan_id
        self._tool_chain = list(tool_chain)
        self._source_dataset_ids = list(source_dataset_ids)
        self._confidence = confidence
        self._validation_summary = validation_summary

    @transaction(on_error=partial(on_error, reraise=AIAuditPersistenceError))
    def run(self) -> AIGeneratedArtifact:
        """Create the audit record within a rollback-safe transaction."""
        self.validate()
        return AIGeneratedArtifactDAO.create(
            attributes={
                "uuid": uuid4(),
                "artifact_type": self._artifact_type,
                "artifact_id": self._artifact_id,
                "principal_user_id": get_user_id(),
                "source_prompt": self._prompt[:2000],
                "normalized_intent": json.dumps(
                    {
                        "prompt_excerpt": self._prompt[:200],
                        "plan_id": self._plan_id or "",
                    }
                ),
                "llm_provider": "",
                "llm_model": "",
                "tool_chain": json.dumps(self._tool_chain),
                "source_asset_refs": json.dumps(self._source_dataset_ids),
                "validation_summary": self._validation_summary,
                "confidence_score": self._confidence,
            }
        )

    def validate(self) -> None:
        """Validate command inputs supplied by the governed workflow."""
        if not self._artifact_type:
            raise ValueError("artifact_type must not be empty")
        if self._artifact_id < 1:
            raise ValueError("artifact_id must be positive")


class RecordAIEvaluationRunCommand(BaseCommand):
    """Persist one prompt-to-dashboard evaluation result."""

    def __init__(
        self,
        *,
        eval_id: str,
        prompt: str,
        expected: dict[str, Any],
        actual: dict[str, Any],
        scores: list[dict[str, Any]],
        model: str,
    ) -> None:
        self._eval_id = eval_id
        self._prompt = prompt
        self._expected = expected.copy()
        self._actual = actual.copy()
        self._scores = [score.copy() for score in scores]
        self._model = model

    @transaction(on_error=partial(on_error, reraise=AIAuditPersistenceError))
    def run(self) -> AIEvaluationRun:
        """Create the evaluation record within a rollback-safe transaction."""
        self.validate()
        record_id = UUID(self._eval_id) if len(self._eval_id) == 36 else uuid4()
        return AIEvaluationRunDAO.create(
            attributes={
                "uuid": record_id,
                "prompt": self._prompt[:4000],
                "expected_result": json.dumps(self._expected),
                "actual_result": json.dumps(self._actual),
                "scores": json.dumps(self._scores),
                "model": self._model,
                "tool_versions": json.dumps(_AI_TOOL_VERSIONS),
            }
        )

    def validate(self) -> None:
        """Validate command inputs supplied by the evaluation workflow."""
        if not self._prompt:
            raise ValueError("prompt must not be empty")

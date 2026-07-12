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

from unittest.mock import MagicMock
from uuid import UUID, uuid4

import pytest
from pytest_mock import MockerFixture
from sqlalchemy.exc import SQLAlchemyError

from axbi.commands.ai.audit import (
    RecordAIEvaluationRunCommand,
    RecordAIGeneratedArtifactCommand,
)
from axbi.commands.ai.exceptions import AIAuditPersistenceError
from axbi.utils import json


def test_record_generated_artifact_builds_governed_lineage_payload(
    mocker: MockerFixture,
) -> None:
    """Artifact audit serialization and user attribution live in the command."""
    record_id = uuid4()
    mocker.patch("axbi.commands.ai.audit.uuid4", return_value=record_id)
    mocker.patch("axbi.commands.ai.audit.get_user_id", return_value=42)
    record = MagicMock()
    create = mocker.patch(
        "axbi.commands.ai.audit.AIGeneratedArtifactDAO.create",
        return_value=record,
    )
    tool_chain = ["prompt_to_dashboard", "compose_dashboard"]
    source_dataset_ids = [7, 9]
    prompt = "p" * 2200
    command = RecordAIGeneratedArtifactCommand(
        artifact_type="dashboard",
        artifact_id=31,
        prompt=prompt,
        plan_id="plan-1",
        tool_chain=tool_chain,
        source_dataset_ids=source_dataset_ids,
        confidence=0.83,
        validation_summary="validated",
    )
    tool_chain.append("mutated-after-construction")
    source_dataset_ids.append(99)

    result = command.run()

    assert result is record
    attributes = create.call_args.kwargs["attributes"]
    assert attributes["uuid"] == record_id
    assert attributes["artifact_type"] == "dashboard"
    assert attributes["artifact_id"] == 31
    assert attributes["principal_user_id"] == 42
    assert attributes["source_prompt"] == prompt[:2000]
    assert json.loads(attributes["normalized_intent"]) == {
        "prompt_excerpt": prompt[:200],
        "plan_id": "plan-1",
    }
    assert json.loads(attributes["tool_chain"]) == [
        "prompt_to_dashboard",
        "compose_dashboard",
    ]
    assert json.loads(attributes["source_asset_refs"]) == [7, 9]
    assert attributes["validation_summary"] == "validated"
    assert attributes["confidence_score"] == 0.83


def test_record_evaluation_run_preserves_identifier_and_serializes_payload(
    mocker: MockerFixture,
) -> None:
    """Evaluation records keep their workflow ID and stable tool versions."""
    eval_id = uuid4()
    record = MagicMock()
    create = mocker.patch(
        "axbi.commands.ai.audit.AIEvaluationRunDAO.create",
        return_value=record,
    )
    expected = {"chart_count": 3}
    actual = {"chart_count": 2}
    scores = [{"dimension": "chart_count", "score": 0.5}]
    prompt = "evaluate " + "p" * 4200
    command = RecordAIEvaluationRunCommand(
        eval_id=str(eval_id),
        prompt=prompt,
        expected=expected,
        actual=actual,
        scores=scores,
        model="gpt-test",
    )
    expected["mutated"] = True
    actual["mutated"] = True
    scores[0]["score"] = 0.0

    result = command.run()

    assert result is record
    attributes = create.call_args.kwargs["attributes"]
    assert attributes["uuid"] == eval_id
    assert attributes["prompt"] == prompt[:4000]
    assert json.loads(attributes["expected_result"]) == {"chart_count": 3}
    assert json.loads(attributes["actual_result"]) == {"chart_count": 2}
    assert json.loads(attributes["scores"]) == [
        {"dimension": "chart_count", "score": 0.5}
    ]
    assert attributes["model"] == "gpt-test"
    assert json.loads(attributes["tool_versions"]) == {
        "prompt_to_dashboard": "1.0",
        "evaluate_ai_answer": "1.0",
    }


def test_record_evaluation_run_generates_id_for_non_uuid_identifier(
    mocker: MockerFixture,
) -> None:
    """Legacy non-UUID evaluation identifiers retain the generated-ID fallback."""
    generated_id = uuid4()
    mocker.patch("axbi.commands.ai.audit.uuid4", return_value=generated_id)
    create = mocker.patch("axbi.commands.ai.audit.AIEvaluationRunDAO.create")

    RecordAIEvaluationRunCommand(
        eval_id="short-id",
        prompt="Evaluate a dashboard",
        expected={},
        actual={},
        scores=[],
        model="",
    ).run()

    assert create.call_args.kwargs["attributes"]["uuid"] == generated_id


@pytest.mark.parametrize(
    ("dao_target", "command"),
    [
        (
            "axbi.commands.ai.audit.AIGeneratedArtifactDAO.create",
            RecordAIGeneratedArtifactCommand(
                artifact_type="dashboard",
                artifact_id=1,
                prompt="Build a dashboard",
                plan_id=None,
                tool_chain=[],
                source_dataset_ids=[],
                confidence=0.5,
            ),
        ),
        (
            "axbi.commands.ai.audit.AIEvaluationRunDAO.create",
            RecordAIEvaluationRunCommand(
                eval_id=str(UUID(int=1)),
                prompt="Evaluate a dashboard",
                expected={},
                actual={},
                scores=[],
                model="",
            ),
        ),
    ],
)
def test_ai_audit_commands_map_sqlalchemy_failures(
    mocker: MockerFixture,
    dao_target: str,
    command: RecordAIGeneratedArtifactCommand | RecordAIEvaluationRunCommand,
) -> None:
    """Both audit commands roll back and expose one stable persistence error."""
    mocker.patch(dao_target, side_effect=SQLAlchemyError("audit table missing"))

    with pytest.raises(AIAuditPersistenceError) as exc_info:
        command.run()

    assert isinstance(exc_info.value.__cause__, SQLAlchemyError)


@pytest.mark.parametrize(
    ("command", "message"),
    [
        (
            RecordAIGeneratedArtifactCommand(
                artifact_type="",
                artifact_id=1,
                prompt="Build a dashboard",
                plan_id=None,
                tool_chain=[],
                source_dataset_ids=[],
                confidence=0.5,
            ),
            "artifact_type",
        ),
        (
            RecordAIGeneratedArtifactCommand(
                artifact_type="dashboard",
                artifact_id=0,
                prompt="Build a dashboard",
                plan_id=None,
                tool_chain=[],
                source_dataset_ids=[],
                confidence=0.5,
            ),
            "artifact_id",
        ),
        (
            RecordAIEvaluationRunCommand(
                eval_id=str(UUID(int=1)),
                prompt="",
                expected={},
                actual={},
                scores=[],
                model="",
            ),
            "prompt",
        ),
    ],
)
def test_ai_audit_commands_reject_invalid_internal_inputs(
    command: RecordAIGeneratedArtifactCommand | RecordAIEvaluationRunCommand,
    message: str,
) -> None:
    """Invalid internal workflow data never reaches an audit DAO."""
    with pytest.raises(ValueError, match=message):
        command.validate()

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
"""Tests for rollback-safe GenAI audit adapters."""

from pytest_mock import MockerFixture

from axbi.commands.ai.exceptions import AIAuditPersistenceError
from axbi.mcp_service.ai.tool.evaluate_ai_answer import _record_eval_run
from axbi.mcp_service.ai.tool.prompt_to_dashboard import _record_artifact


def test_record_artifact_delegates_to_transactional_command(
    mocker: MockerFixture,
) -> None:
    """The prompt workflow passes audit data without constructing ORM models."""
    command_class = mocker.patch(
        "axbi.mcp_service.ai.tool.prompt_to_dashboard.RecordAIGeneratedArtifactCommand"
    )

    _record_artifact(
        artifact_type="dashboard",
        artifact_id=19,
        prompt="Build an executive dashboard",
        plan_id="plan-19",
        tool_chain=["plan_dashboard", "compose_dashboard"],
        source_dataset_ids=[4, 8],
        confidence=0.77,
        validation_summary="validated",
    )

    command_class.assert_called_once_with(
        artifact_type="dashboard",
        artifact_id=19,
        prompt="Build an executive dashboard",
        plan_id="plan-19",
        tool_chain=["plan_dashboard", "compose_dashboard"],
        source_dataset_ids=[4, 8],
        confidence=0.77,
        validation_summary="validated",
    )
    command_class.return_value.run.assert_called_once_with()


def test_record_artifact_still_degrades_silently_after_command_failure(
    mocker: MockerFixture,
) -> None:
    """Optional lineage failure cannot fail the main dashboard workflow."""
    command_class = mocker.patch(
        "axbi.mcp_service.ai.tool.prompt_to_dashboard.RecordAIGeneratedArtifactCommand"
    )
    command_class.return_value.run.side_effect = AIAuditPersistenceError()
    logger = mocker.patch("axbi.mcp_service.ai.tool.prompt_to_dashboard.logger")

    _record_artifact(
        artifact_type="dashboard",
        artifact_id=19,
        prompt="Build an executive dashboard",
        plan_id=None,
        tool_chain=[],
        source_dataset_ids=[],
        confidence=0.5,
    )

    logger.debug.assert_called_once_with(
        "AI artifact audit recording unavailable",
        exc_info=True,
    )


def test_record_evaluation_delegates_to_transactional_command(
    mocker: MockerFixture,
) -> None:
    """Evaluation workflows delegate serialization and persistence together."""
    command_class = mocker.patch(
        "axbi.mcp_service.ai.tool.evaluate_ai_answer.RecordAIEvaluationRunCommand"
    )

    _record_eval_run(
        eval_id="00000000-0000-0000-0000-000000000019",
        prompt="Evaluate an executive dashboard",
        expected={"chart_count": 3},
        actual={"chart_count": 2},
        scores=[{"dimension": "chart_count", "score": 0.5}],
        model="gpt-test",
    )

    command_class.assert_called_once_with(
        eval_id="00000000-0000-0000-0000-000000000019",
        prompt="Evaluate an executive dashboard",
        expected={"chart_count": 3},
        actual={"chart_count": 2},
        scores=[{"dimension": "chart_count", "score": 0.5}],
        model="gpt-test",
    )
    command_class.return_value.run.assert_called_once_with()


def test_record_evaluation_still_degrades_silently_after_command_failure(
    mocker: MockerFixture,
) -> None:
    """Optional evaluation persistence cannot fail the scored response."""
    command_class = mocker.patch(
        "axbi.mcp_service.ai.tool.evaluate_ai_answer.RecordAIEvaluationRunCommand"
    )
    command_class.return_value.run.side_effect = AIAuditPersistenceError()
    logger = mocker.patch("axbi.mcp_service.ai.tool.evaluate_ai_answer.logger")

    _record_eval_run(
        eval_id="00000000-0000-0000-0000-000000000019",
        prompt="Evaluate an executive dashboard",
        expected={},
        actual={},
        scores=[],
        model="",
    )

    logger.debug.assert_called_once_with(
        "Evaluation run recording unavailable",
        exc_info=True,
    )

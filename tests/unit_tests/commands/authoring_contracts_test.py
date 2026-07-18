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
"""Unit tests for transport-neutral analytics authoring contracts."""

from __future__ import annotations

import pytest

from axbi.commands.ai.authoring.capabilities import (
    GetAuthoringCapabilitiesCommand,
)
from axbi.commands.ai.authoring.confidence import evaluate_compose_gate
from axbi.commands.ai.authoring.context import AuthoringContext
from axbi.commands.ai.authoring.contracts import AuthoringOutcome
from axbi.commands.ai.authoring.errors import AuthoringCommandError


def test_capabilities_are_ordered_and_versioned() -> None:
    result = GetAuthoringCapabilitiesCommand(
        enabled_operations={
            "upload_and_plan",
            "create_chart_from_intent",
            "plan_dashboard",
        },
        max_upload_bytes=1024,
    ).run()

    assert result.contract_version == "1.0"
    assert result.operations == [
        "plan_dashboard",
        "create_chart_from_intent",
        "upload_and_plan",
    ]
    assert result.preview_before_save is True
    assert result.limits.max_charts_per_dashboard == 12
    assert result.limits.max_upload_bytes == 1024
    assert result.deployment_operations == [
        "plan_dashboard",
        "create_chart_from_intent",
        "upload_and_plan",
    ]


def test_capabilities_distinguish_deployment_and_principal_operations() -> None:
    result = GetAuthoringCapabilitiesCommand(
        enabled_operations={
            "plan_dashboard",
            "create_chart_from_intent",
            "prompt_to_dashboard",
        },
        authorized_operations={"plan_dashboard"},
    ).run()

    assert result.deployment_operations == [
        "plan_dashboard",
        "create_chart_from_intent",
        "prompt_to_dashboard",
    ]
    assert result.operations == ["plan_dashboard"]


def test_capabilities_reject_unknown_operations() -> None:
    command = GetAuthoringCapabilitiesCommand(
        enabled_operations={"delete_everything"},  # type: ignore[arg-type]
    )

    with pytest.raises(ValueError, match="Unknown authoring operations"):
        command.run()


def test_authoring_outcome_uses_isolated_mutable_defaults() -> None:
    first = AuthoringOutcome(
        request_id="req-1",
        artifact_type="chart",
        status="completed",
    )
    second = AuthoringOutcome(
        request_id="req-2",
        artifact_type="dashboard",
        status="dry_run",
    )

    first.clarification_questions.append("Which dataset?")

    assert second.clarification_questions == []
    assert second.artifact_refs == []


def test_authoring_context_rejects_untrusted_empty_identity() -> None:
    with pytest.raises(ValueError, match="principal_user_id must be positive"):
        AuthoringContext(
            principal_user_id=0,
            request_id="req-1",
            correlation_id="corr-1",
            transport="mcp",
        )


def test_authoring_error_maps_to_stable_contract() -> None:
    error = AuthoringCommandError(
        "DATASET_NOT_FOUND",
        "No accessible dataset matched the request.",
        details={"candidate_count": 0},
    )

    contract = error.to_contract("req-1")

    assert contract.code == "DATASET_NOT_FOUND"
    assert contract.retryable is False
    assert contract.request_id == "req-1"
    assert contract.details == {"candidate_count": 0}


def test_compose_gate_is_owned_by_authoring_domain() -> None:
    blocked, reason = evaluate_compose_gate(
        0.1,
        2,
        ["Which dataset?"],
        min_confidence=0.25,
    )

    assert blocked is True
    assert "Which dataset?" in reason


def test_capabilities_accept_injected_llm_capability_without_mcp() -> None:
    """Authoring command layer must not require MCP; inject capability metadata."""
    result = GetAuthoringCapabilitiesCommand(
        enabled_operations={"create_chart_from_intent"},
        llm_capability={
            "llm_configured": True,
            "llm_provider_type": "openai_compatible",
            "llm_model": "llama3.1",
            "bounded_samples_allowed": True,
            "genai_features": {
                "semantic_assist": True,
                "plan_dashboard": True,
                "bounded_samples": True,
            },
        },
    ).run()

    assert result.llm_configured is True
    assert result.llm_provider_type == "openai_compatible"
    assert result.llm_model == "llama3.1"
    assert result.bounded_samples_allowed is True
    assert result.genai_features["semantic_assist"] is True


def test_authoring_package_does_not_import_mcp_service_modules() -> None:
    """Layering guard: commands.ai.authoring must not depend on mcp_service."""
    import axbi.commands.ai.authoring.capabilities as caps
    import axbi.commands.ai.authoring.confidence as confidence
    import axbi.commands.ai.authoring.context as context
    import axbi.commands.ai.authoring.contracts as contracts
    import axbi.commands.ai.authoring.errors as errors

    for module in (caps, contracts, context, confidence, errors):
        for name, value in vars(module).items():
            mod = getattr(value, "__module__", "") or ""
            assert not mod.startswith("axbi.mcp_service"), (
                f"{module.__name__}.{name} comes from {mod}"
            )
        # Source-level import check
        source = getattr(module, "__file__", None)
        if source:
            text = open(source, encoding="utf-8").read()
            assert "axbi.mcp_service" not in text, module.__name__

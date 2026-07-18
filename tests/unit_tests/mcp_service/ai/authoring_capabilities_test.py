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
"""Unit tests for the authoring capabilities MCP adapter."""

from __future__ import annotations

from axbi.mcp_service.ai.tool.get_authoring_capabilities import (
    _authorized_operations,
    _build_authoring_capabilities,
    _enabled_operations,
)


def test_capability_operations_follow_tool_feature_flags() -> None:
    enabled = {
        "GENAI_BI",
        "GENAI_BI_MCP_TOOLS",
        "GENAI_PROMPT_TO_DASHBOARD",
        "ENABLE_LOCAL_FILE_UPLOAD",
    }

    operations = _enabled_operations(lambda flag: flag in enabled)

    assert operations == [
        "create_chart_from_intent",
        "plan_dashboard",
        "prompt_to_dashboard",
        "upload_and_plan",
    ]


def test_capability_operations_hide_prompt_pipeline_when_disabled() -> None:
    enabled = {"GENAI_BI", "GENAI_BI_MCP_TOOLS"}

    operations = _enabled_operations(lambda flag: flag in enabled)

    assert operations == ["create_chart_from_intent"]


def test_capability_operations_hide_upload_when_file_upload_is_disabled() -> None:
    enabled = {
        "GENAI_BI",
        "GENAI_BI_MCP_TOOLS",
        "GENAI_PROMPT_TO_DASHBOARD",
    }

    operations = _enabled_operations(lambda flag: flag in enabled)

    assert operations == [
        "create_chart_from_intent",
        "plan_dashboard",
        "prompt_to_dashboard",
    ]


def test_capability_operations_are_empty_when_genai_is_disabled() -> None:
    assert _enabled_operations(lambda _flag: False) == []


def test_capabilities_adapter_returns_canonical_contract() -> None:
    result = _build_authoring_capabilities(lambda _flag: True, 2048)

    assert result["contract_version"] == "1.0"
    assert result["operations"] == [
        "plan_dashboard",
        "create_chart_from_intent",
        "prompt_to_dashboard",
        "upload_and_plan",
    ]
    assert result["limits"] == {
        "max_charts_per_dashboard": 12,
        "max_upload_bytes": 2048,
    }
    assert "llm_configured" in result
    assert result["llm_configured"] in {True, False}


def test_authorized_operations_follow_current_principal_permissions() -> None:
    enabled = [
        "create_chart_from_intent",
        "plan_dashboard",
        "prompt_to_dashboard",
        "upload_and_plan",
    ]
    allowed = {
        ("can_write", "Chart"),
        ("can_read", "Dashboard"),
    }

    operations = _authorized_operations(
        enabled,
        can_access=lambda permission, view: (permission, view) in allowed,
        can_view_metadata=lambda: True,
    )

    assert operations == ["create_chart_from_intent", "plan_dashboard"]


def test_authorized_operations_require_metadata_visibility() -> None:
    operations = _authorized_operations(
        ["create_chart_from_intent", "plan_dashboard"],
        can_access=lambda _permission, _view: True,
        can_view_metadata=lambda: False,
    )

    assert operations == []

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
"""MCP adapter for analytics authoring capability discovery."""

from __future__ import annotations

from collections.abc import Callable

from axbi_core.mcp.decorators import tool, ToolAnnotations

from axbi import is_feature_enabled
from axbi.commands.ai.authoring.capabilities import (
    GetAuthoringCapabilitiesCommand,
)
from axbi.commands.ai.authoring.contracts import AuthoringOperation
from axbi.mcp_service.utils.config_utils import get_upload_max_file_size_bytes
from axbi.mcp_service.utils.logging_utils import mcp_event_log_context


def _enabled_operations(
    feature_enabled: Callable[[str], bool],
) -> list[AuthoringOperation]:
    """Resolve operations from the same feature flags as their MCP tools."""
    if not (feature_enabled("GENAI_BI") and feature_enabled("GENAI_BI_MCP_TOOLS")):
        return []

    operations: list[AuthoringOperation] = ["create_chart_from_intent"]
    if feature_enabled("GENAI_PROMPT_TO_DASHBOARD"):
        operations.extend(["plan_dashboard", "prompt_to_dashboard"])
        if feature_enabled("ENABLE_LOCAL_FILE_UPLOAD"):
            operations.append("upload_and_plan")
    return operations


def _max_upload_bytes() -> int | None:
    """Return a positive configured upload limit or an explicit unknown value."""
    value = get_upload_max_file_size_bytes()
    return value if isinstance(value, int) and value > 0 else None


def _build_authoring_capabilities(
    feature_enabled: Callable[[str], bool],
    max_upload_bytes: int | None,
) -> dict[str, object]:
    """Map MCP deployment state into the transport-neutral command."""
    return (
        GetAuthoringCapabilitiesCommand(
            enabled_operations=_enabled_operations(feature_enabled),
            max_charts_per_dashboard=12,
            max_upload_bytes=max_upload_bytes,
        )
        .run()
        .model_dump()
    )


@tool(
    tags=["discovery", "ai"],
    class_permission_name="Dashboard",
    annotations=ToolAnnotations(
        title="Get analytics authoring capabilities",
        readOnlyHint=True,
        destructiveHint=False,
    ),
)
def get_authoring_capabilities() -> dict[str, object]:
    """Return versioned operations, formats, and limits for authoring clients."""
    with mcp_event_log_context(action="mcp.authoring.capabilities"):
        return _build_authoring_capabilities(
            is_feature_enabled,
            _max_upload_bytes(),
        )

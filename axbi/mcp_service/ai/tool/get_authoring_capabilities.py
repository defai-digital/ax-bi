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

from collections.abc import Callable, Iterable

from axbi_core.mcp.decorators import tool, ToolAnnotations

from axbi import is_feature_enabled
from axbi.commands.ai.authoring.capabilities import (
    GetAuthoringCapabilitiesCommand,
)
from axbi.commands.ai.authoring.contracts import AuthoringOperation
from axbi.mcp_service.privacy import user_can_view_data_model_metadata
from axbi.mcp_service.utils.config_utils import get_upload_max_file_size_bytes
from axbi.mcp_service.utils.logging_utils import mcp_event_log_context
from axbi.mcp_service.utils.permissions_utils import current_user_can_access


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


def _authorized_operations(
    enabled_operations: Iterable[AuthoringOperation],
    *,
    can_access: Callable[[str, str], bool],
    can_view_metadata: Callable[[], bool],
) -> list[AuthoringOperation]:
    """Filter deployment operations by the authenticated principal's RBAC."""
    if not can_view_metadata():
        return []

    authorized: list[AuthoringOperation] = []
    for operation in enabled_operations:
        if operation == "create_chart_from_intent" and can_access("can_write", "Chart"):
            authorized.append(operation)
        elif operation == "plan_dashboard" and can_access("can_read", "Dashboard"):
            authorized.append(operation)
        elif (
            operation == "prompt_to_dashboard"
            and can_access("can_write", "Dashboard")
            and can_access("can_write", "Chart")
        ):
            authorized.append(operation)
        elif operation == "upload_and_plan" and can_access("can_upload", "Database"):
            authorized.append(operation)
    return authorized


def _build_authoring_capabilities(
    feature_enabled: Callable[[str], bool],
    max_upload_bytes: int | None,
    authorized_operations: Iterable[AuthoringOperation] | None = None,
) -> dict[str, object]:
    """Map MCP deployment state into the transport-neutral command."""
    enabled_operations = _enabled_operations(feature_enabled)
    return (
        GetAuthoringCapabilitiesCommand(
            enabled_operations=enabled_operations,
            authorized_operations=authorized_operations,
            max_charts_per_dashboard=12,
            max_upload_bytes=max_upload_bytes,
        )
        .run()
        .model_dump()
    )


@tool(
    tags=["discovery", "ai"],
    annotations=ToolAnnotations(
        title="Get analytics authoring capabilities",
        readOnlyHint=True,
        destructiveHint=False,
    ),
)
def get_authoring_capabilities() -> dict[str, object]:
    """Return versioned operations, formats, and limits for authoring clients."""
    with mcp_event_log_context(action="mcp.authoring.capabilities"):
        enabled_operations = _enabled_operations(is_feature_enabled)
        authorized_operations = _authorized_operations(
            enabled_operations,
            can_access=current_user_can_access,
            can_view_metadata=user_can_view_data_model_metadata,
        )
        return _build_authoring_capabilities(
            is_feature_enabled,
            _max_upload_bytes(),
            authorized_operations,
        )

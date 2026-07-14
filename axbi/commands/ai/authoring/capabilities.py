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
"""Capability discovery command for analytics authoring clients."""

from __future__ import annotations

from collections.abc import Iterable

from axbi.commands.ai.authoring.contracts import (
    AuthoringCapabilities,
    AuthoringLimits,
    AuthoringOperation,
)
from axbi.commands.base import BaseCommand

_OPERATION_ORDER: tuple[AuthoringOperation, ...] = (
    "plan_dashboard",
    "create_chart_from_intent",
    "prompt_to_dashboard",
    "upload_and_plan",
)


class GetAuthoringCapabilitiesCommand(BaseCommand):
    """Return enabled operations and deployment limits without MCP coupling."""

    def __init__(
        self,
        *,
        enabled_operations: Iterable[AuthoringOperation],
        max_charts_per_dashboard: int = 12,
        max_upload_bytes: int | None = None,
    ) -> None:
        self._enabled_operations = set(enabled_operations)
        self._max_charts_per_dashboard = max_charts_per_dashboard
        self._max_upload_bytes = max_upload_bytes

    def run(self) -> AuthoringCapabilities:
        """Build the canonical capabilities response."""
        self.validate()
        operations = [
            operation
            for operation in _OPERATION_ORDER
            if operation in self._enabled_operations
        ]
        return AuthoringCapabilities(
            operations=operations,
            limits=AuthoringLimits(
                max_charts_per_dashboard=self._max_charts_per_dashboard,
                max_upload_bytes=self._max_upload_bytes,
            ),
        )

    def validate(self) -> None:
        """Validate adapter-supplied deployment settings."""
        if unknown := self._enabled_operations.difference(_OPERATION_ORDER):
            raise ValueError(f"Unknown authoring operations: {sorted(unknown)}")
        if not 1 <= self._max_charts_per_dashboard <= 12:
            raise ValueError("max_charts_per_dashboard must be between 1 and 12")
        if self._max_upload_bytes is not None and self._max_upload_bytes < 1:
            raise ValueError("max_upload_bytes must be positive when configured")

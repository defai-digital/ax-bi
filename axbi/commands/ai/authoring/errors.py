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
"""Stable application errors for analytics authoring."""

from __future__ import annotations

from typing import Any

from axbi.commands.ai.authoring.contracts import AuthoringError


class AuthoringCommandError(Exception):
    """Command failure that adapters can map without parsing message text."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        retryable: bool = False,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.retryable = retryable
        self.details = dict(details or {})

    def to_contract(self, request_id: str) -> AuthoringError:
        """Convert this exception to the canonical transport contract."""
        return AuthoringError(
            code=self.code,
            message=str(self),
            retryable=self.retryable,
            request_id=request_id,
            details=self.details,
        )

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
"""Authenticated request context shared by authoring transports."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

AuthoringTransport = Literal["mcp", "rest", "internal"]


@dataclass(frozen=True, slots=True)
class AuthoringContext:
    """Trusted execution context created by an authenticated adapter.

    Transport adapters derive ``principal_user_id`` from their authenticated
    request context. Authoring commands must never accept that identifier from
    an untrusted request payload.
    """

    principal_user_id: int
    request_id: str
    correlation_id: str
    transport: AuthoringTransport
    tenant_id: str | None = None
    idempotency_key: str | None = None
    locale: str | None = None

    def __post_init__(self) -> None:
        """Reject incomplete trusted context before command execution."""
        if self.principal_user_id < 1:
            raise ValueError("principal_user_id must be positive")
        if not self.request_id.strip():
            raise ValueError("request_id must not be empty")
        if not self.correlation_id.strip():
            raise ValueError("correlation_id must not be empty")

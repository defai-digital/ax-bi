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
"""Canonical v1 contracts for analytics authoring adapters."""

from __future__ import annotations

from typing import Any, Final, Literal

from pydantic import BaseModel, Field

AUTHORING_CONTRACT_VERSION: Final[Literal["1.0"]] = "1.0"

AuthoringArtifactType = Literal["chart", "dashboard", "plan", "dataset"]
AuthoringStatus = Literal[
    "completed",
    "partial",
    "blocked",
    "failed",
    "dry_run",
    "unknown_outcome",
]
AuthoringOperation = Literal[
    "plan_dashboard",
    "create_chart_from_intent",
    "prompt_to_dashboard",
    "upload_and_plan",
]


class ArtifactRef(BaseModel):
    """Stable reference to an artifact produced by an authoring command."""

    type: AuthoringArtifactType
    id: int | str
    uuid: str | None = None
    url: str | None = None


class AuthoringWarning(BaseModel):
    """Machine-readable non-fatal authoring warning."""

    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class AuthoringError(BaseModel):
    """Stable error returned by every authoring transport."""

    code: str
    message: str
    retryable: bool = False
    request_id: str
    details: dict[str, Any] = Field(default_factory=dict)


class AuthoringOutcome(BaseModel):
    """Canonical outcome projected by MCP, REST, and internal adapters."""

    contract_version: Literal["1.0"] = AUTHORING_CONTRACT_VERSION
    request_id: str
    artifact_type: AuthoringArtifactType
    status: AuthoringStatus
    artifact_refs: list[ArtifactRef] = Field(default_factory=list)
    plan: dict[str, Any] | None = None
    warnings: list[AuthoringWarning] = Field(default_factory=list)
    clarification_questions: list[str] = Field(default_factory=list)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    error: AuthoringError | None = None


class AuthoringLimits(BaseModel):
    """Deployment limits relevant to authoring clients."""

    max_charts_per_dashboard: int = Field(ge=1, le=12)
    max_upload_bytes: int | None = Field(default=None, ge=1)


class AuthoringCapabilities(BaseModel):
    """Versioned capability discovery response for authoring clients."""

    contract_version: Literal["1.0"] = AUTHORING_CONTRACT_VERSION
    operations: list[AuthoringOperation] = Field(default_factory=list)
    deployment_operations: list[AuthoringOperation] = Field(default_factory=list)
    artifact_types: list[Literal["chart", "dashboard"]] = Field(
        default_factory=lambda: ["chart", "dashboard"]
    )
    preview_before_save: bool = True
    upload_formats: list[Literal["csv", "tsv", "xls", "xlsx", "parquet"]] = Field(
        default_factory=lambda: ["csv", "tsv", "xls", "xlsx", "parquet"]
    )
    limits: AuthoringLimits
    async_jobs: bool = False
    # Server-side LLM (Admin-configured). Never includes secrets or base_url.
    llm_configured: bool = False
    llm_provider_type: str | None = None
    llm_model: str | None = None

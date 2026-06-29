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
"""Runtime ownership inventory for AX-BI modernization planning."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Runtime(str, Enum):
    """Supported runtime ownership categories."""

    PYTHON = "python"
    TYPESCRIPT = "typescript"
    RUST = "rust"
    UNDECIDED = "undecided"


class MigrationDisposition(str, Enum):
    """Migration recommendation for a backend area."""

    KEEP = "keep"
    CANDIDATE = "candidate"
    DEFER = "defer"
    BLOCKED = "blocked"


@dataclass(frozen=True, slots=True)
class RuntimeInventoryItem:
    """Classify one backend area for runtime modernization decisions."""

    area: str
    module_patterns: tuple[str, ...]
    current_runtime: Runtime
    target_runtime: Runtime
    disposition: MigrationDisposition
    rationale: str
    required_evidence: tuple[str, ...] = ()


RUNTIME_INVENTORY: tuple[RuntimeInventoryItem, ...] = (
    RuntimeInventoryItem(
        area="auth_rbac_security",
        module_patterns=("superset/security", "superset/extensions"),
        current_runtime=Runtime.PYTHON,
        target_runtime=Runtime.PYTHON,
        disposition=MigrationDisposition.KEEP,
        rationale=(
            "Authorization behavior is tied to Flask-AppBuilder, the security "
            "manager, and the published Superset security model."
        ),
    ),
    RuntimeInventoryItem(
        area="metadata_models_daos",
        module_patterns=("superset/models", "superset/daos", "superset/migrations"),
        current_runtime=Runtime.PYTHON,
        target_runtime=Runtime.PYTHON,
        disposition=MigrationDisposition.KEEP,
        rationale=(
            "SQLAlchemy models, DAO filters, migrations, and transaction behavior "
            "are core Superset compatibility surfaces."
        ),
    ),
    RuntimeInventoryItem(
        area="core_commands",
        module_patterns=("superset/commands",),
        current_runtime=Runtime.PYTHON,
        target_runtime=Runtime.PYTHON,
        disposition=MigrationDisposition.DEFER,
        rationale=(
            "Core mutations should stay in Python until specific product "
            "orchestration boundaries are proven."
        ),
        required_evidence=(
            "stable request and response contract",
            "authorization compatibility tests",
        ),
    ),
    RuntimeInventoryItem(
        area="mcp_orchestration",
        module_patterns=("superset/mcp_service",),
        current_runtime=Runtime.PYTHON,
        target_runtime=Runtime.TYPESCRIPT,
        disposition=MigrationDisposition.CANDIDATE,
        rationale=(
            "MCP and GenAI orchestration are AX-BI-specific, contract-oriented, "
            "and suitable for shadow execution behind feature flags."
        ),
        required_evidence=(
            "tool contract fixtures",
            "shadow execution mismatch rate",
            "permission parity tests",
        ),
    ),
    RuntimeInventoryItem(
        area="genai_orchestration",
        module_patterns=("superset/mcp_service/ai",),
        current_runtime=Runtime.PYTHON,
        target_runtime=Runtime.TYPESCRIPT,
        disposition=MigrationDisposition.CANDIDATE,
        rationale=(
            "Fast-moving GenAI workflows benefit from TypeScript service "
            "contracts and frontend-aligned types."
        ),
        required_evidence=(
            "versioned schemas",
            "fallback behavior",
            "latency and error baseline",
        ),
    ),
    RuntimeInventoryItem(
        area="asset_search_indexing",
        module_patterns=("superset/mcp_service/ai/asset_search.py",),
        current_runtime=Runtime.PYTHON,
        target_runtime=Runtime.TYPESCRIPT,
        disposition=MigrationDisposition.CANDIDATE,
        rationale=(
            "Derived metadata search can live outside core Superset metadata "
            "writes while delegating authorization back to Superset."
        ),
        required_evidence=(
            "ranking quality baseline",
            "Superset permission delegation",
            "index freshness metrics",
        ),
    ),
    RuntimeInventoryItem(
        area="mcp_user_directory_tools",
        module_patterns=("superset/mcp_service/user",),
        current_runtime=Runtime.PYTHON,
        target_runtime=Runtime.PYTHON,
        disposition=MigrationDisposition.DEFER,
        rationale=(
            "User-directory MCP tools expose sensitive identity metadata and do "
            "not have a general Superset REST list API for ax-services to "
            "delegate to as the authorization and data-shape authority."
        ),
        required_evidence=(
            "general Superset user-list API design",
            "sensitive field redaction parity tests",
            "authorization compatibility review",
        ),
    ),
    RuntimeInventoryItem(
        area="sql_parsing_normalization",
        module_patterns=("superset/sql",),
        current_runtime=Runtime.PYTHON,
        target_runtime=Runtime.RUST,
        disposition=MigrationDisposition.CANDIDATE,
        rationale=(
            "SQL parsing and normalization can be benchmarked as narrow, "
            "deterministic kernels before any production rollout."
        ),
        required_evidence=(
            "CPU profile",
            "fixture compatibility tests",
            "benchmark improvement",
        ),
    ),
    RuntimeInventoryItem(
        area="chart_validation_kernels",
        module_patterns=("superset/mcp_service/chart/validation",),
        current_runtime=Runtime.PYTHON,
        target_runtime=Runtime.RUST,
        disposition=MigrationDisposition.CANDIDATE,
        rationale=(
            "Chart validation subroutines may be good Rust candidates if "
            "profiling shows CPU-bound behavior and narrow payloads."
        ),
        required_evidence=(
            "CPU profile",
            "payload-size analysis",
            "fixture compatibility tests",
        ),
    ),
    RuntimeInventoryItem(
        area="pandas_post_processing",
        module_patterns=("superset/utils/pandas_postprocessing",),
        current_runtime=Runtime.PYTHON,
        target_runtime=Runtime.UNDECIDED,
        disposition=MigrationDisposition.DEFER,
        rationale=(
            "Data transfer costs may outweigh native-code gains, so this needs "
            "profiling and payload analysis before selecting a runtime."
        ),
        required_evidence=(
            "data size distribution",
            "CPU and memory profile",
            "serialization overhead estimate",
        ),
    ),
    RuntimeInventoryItem(
        area="reports_and_celery_tasks",
        module_patterns=("superset/reports", "superset/tasks"),
        current_runtime=Runtime.PYTHON,
        target_runtime=Runtime.PYTHON,
        disposition=MigrationDisposition.DEFER,
        rationale=(
            "Background job reliability needs a separate design before runtime "
            "migration because orchestration, browser automation, and Celery are "
            "coupled."
        ),
        required_evidence=(
            "task failure analysis",
            "operator deployment plan",
            "queue compatibility plan",
        ),
    ),
)


def get_runtime_inventory() -> tuple[RuntimeInventoryItem, ...]:
    """Return the immutable runtime modernization inventory."""

    return RUNTIME_INVENTORY


def get_candidate_inventory() -> tuple[RuntimeInventoryItem, ...]:
    """Return areas that are eligible for measured extraction work."""

    return tuple(
        item
        for item in RUNTIME_INVENTORY
        if item.disposition == MigrationDisposition.CANDIDATE
    )


def get_inventory_item(area: str) -> RuntimeInventoryItem:
    """Return one inventory item by area name."""

    try:
        return next(item for item in RUNTIME_INVENTORY if item.area == area)
    except StopIteration as ex:
        raise KeyError(f"Unknown runtime modernization area: {area}") from ex

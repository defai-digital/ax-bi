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
"""Rollout manifest for runtime modernization candidates."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from superset.runtime_modernization.measurement import runtime_metric_key


@dataclass(frozen=True, slots=True)
class RolloutGate:
    """One rollout gate operators must evaluate before serving traffic."""

    name: str
    metric: str
    target: str
    description: str

    def to_dict(self) -> dict[str, str]:
        """Serialize the rollout gate for CLI output."""

        return {
            "name": self.name,
            "metric": self.metric,
            "target": self.target,
            "description": self.description,
        }


@dataclass(frozen=True, slots=True)
class RolloutWorkflow:
    """Operational rollout metadata for one migrated workflow."""

    name: str
    area: str
    operation: str
    sidecar_route: str
    contract_version: str
    shadow_flags: tuple[str, ...]
    serving_flags: tuple[str, ...]
    python_metrics: tuple[str, ...]
    sidecar_metrics: tuple[str, ...]
    gates: tuple[RolloutGate, ...]

    def to_dict(self) -> dict[str, object]:
        """Serialize the workflow for CLI output."""

        return {
            "name": self.name,
            "area": self.area,
            "operation": self.operation,
            "sidecar_route": self.sidecar_route,
            "contract_version": self.contract_version,
            "shadow_flags": list(self.shadow_flags),
            "serving_flags": list(self.serving_flags),
            "python_metrics": list(self.python_metrics),
            "sidecar_metrics": list(self.sidecar_metrics),
            "gates": [gate.to_dict() for gate in self.gates],
        }


@dataclass(frozen=True, slots=True)
class RolloutEvidenceRequirement:
    """One production evidence artifact required to complete rollout phases."""

    name: str
    phase: str
    source: str
    description: str
    validation: str

    def to_dict(self) -> dict[str, str]:
        """Serialize the production evidence requirement for CLI output."""

        return {
            "name": self.name,
            "phase": self.phase,
            "source": self.source,
            "description": self.description,
            "validation": self.validation,
        }


def _metrics(area: str, operation: str, *metrics: str) -> tuple[str, ...]:
    """Build runtime modernization metric keys for one workflow."""

    return tuple(runtime_metric_key(area, operation, metric) for metric in metrics)


def _mcp_workflow(
    *,
    name: str,
    operation: str,
    sidecar_route: str,
    contract_version: str,
    serving_flag: str,
) -> RolloutWorkflow:
    """Build a standard MCP orchestration rollout workflow."""

    area = "mcp_orchestration"
    shadow_mismatch = runtime_metric_key(area, operation, "shadow_mismatch")
    fallback = runtime_metric_key(area, operation, "fallback")
    error = runtime_metric_key(area, operation, "error")

    return RolloutWorkflow(
        name=name,
        area=area,
        operation=operation,
        sidecar_route=sidecar_route,
        contract_version=contract_version,
        shadow_flags=("RUNTIME_SHADOW_EXECUTION", "TS_MCP_ORCHESTRATION"),
        serving_flags=("TS_MCP_ORCHESTRATION", serving_flag),
        python_metrics=_metrics(
            area,
            operation,
            "duration",
            "success",
            "error",
            "shadow_match",
            "shadow_mismatch",
            "shadow_candidate_error",
            "shadow_compare_error",
            "served_candidate",
            "fallback",
        ),
        sidecar_metrics=(
            "runtime.v1.requests.total",
            f"runtime.v1.requests.routes.{sidecar_route}.count",
            f"runtime.v1.requests.routes.{sidecar_route}.errorCount",
            f"runtime.v1.requests.routes.{sidecar_route}.averageDurationMs",
            f"runtime.v1.requests.routes.{sidecar_route}.maxDurationMs",
        ),
        gates=(
            RolloutGate(
                name="shadow_mismatch_rate",
                metric=shadow_mismatch,
                target="0 mismatches during the evaluation window",
                description=(
                    "Candidate output must match the Python authoritative path "
                    "before enabling serving."
                ),
            ),
            RolloutGate(
                name="fallback_rate",
                metric=fallback,
                target="<= 1% after serving is enabled",
                description=(
                    "Fallbacks indicate invalid sidecar contracts, sidecar errors, "
                    "or timeouts."
                ),
            ),
            RolloutGate(
                name="error_rate",
                metric=error,
                target="no regression versus Python baseline",
                description=(
                    "The migrated workflow must not increase user-visible MCP "
                    "tool failures."
                ),
            ),
        ),
    )


ROLLOUT_WORKFLOWS: tuple[RolloutWorkflow, ...] = (
    _mcp_workflow(
        name="mcp_health_check",
        operation="health_check",
        sidecar_route="GET /health",
        contract_version="runtime.v1",
        serving_flag="TS_HEALTH_CHECK_SERVING",
    ),
    _mcp_workflow(
        name="mcp_asset_search",
        operation="search_assets",
        sidecar_route="POST /mcp/assets/search",
        contract_version="asset-search.v1",
        serving_flag="TS_ASSET_SEARCH_SERVING",
    ),
    _mcp_workflow(
        name="mcp_dashboard_list",
        operation="list_dashboards",
        sidecar_route="POST /mcp/dashboards/list",
        contract_version="dashboard-list.v1",
        serving_flag="TS_DASHBOARD_LIST_SERVING",
    ),
    _mcp_workflow(
        name="mcp_chart_list",
        operation="list_charts",
        sidecar_route="POST /mcp/charts/list",
        contract_version="chart-list.v1",
        serving_flag="TS_CHART_LIST_SERVING",
    ),
    _mcp_workflow(
        name="mcp_database_list",
        operation="list_databases",
        sidecar_route="POST /mcp/databases/list",
        contract_version="database-list.v1",
        serving_flag="TS_DATABASE_LIST_SERVING",
    ),
    _mcp_workflow(
        name="mcp_dataset_list",
        operation="list_datasets",
        sidecar_route="POST /mcp/datasets/list",
        contract_version="dataset-list.v1",
        serving_flag="TS_DATASET_LIST_SERVING",
    ),
)

PRODUCTION_EVIDENCE_REQUIREMENTS: tuple[RolloutEvidenceRequirement, ...] = (
    RolloutEvidenceRequirement(
        name="compatibility_report",
        phase="phase_3_phase_5",
        source="runtime-modernization-compatibility-report CI artifact",
        description=(
            "Machine-readable compatibility report for parser behavior, "
            "inventory, and optional release-candidate gates."
        ),
        validation="status is passed and target_checks are true or explicitly unset",
    ),
    RolloutEvidenceRequirement(
        name="rust_kernel_benchmark",
        phase="phase_4_phase_5",
        source="sql-kernel-benchmark CI artifact",
        description=(
            "Rust PyO3 extension import, output compatibility, and speed "
            "measurement evidence."
        ),
        validation="status is passed and output_matched is true",
    ),
    RolloutEvidenceRequirement(
        name="production_flag_state",
        phase="phase_3_phase_5",
        source="deployment configuration or feature-flag export",
        description=(
            "Snapshot showing which runtime modernization shadow and serving "
            "flags were enabled for each workflow."
        ),
        validation="at least two TypeScript workflow serving flag sets are enabled",
    ),
    RolloutEvidenceRequirement(
        name="operator_dashboard_snapshot",
        phase="phase_5",
        source="production observability dashboard export or screenshot",
        description=(
            "Operator view of latency, error rate, fallback rate, and shadow "
            "mismatch metrics for migrated workflows."
        ),
        validation="fallback rate and error rate meet each workflow gate",
    ),
    RolloutEvidenceRequirement(
        name="operator_approval",
        phase="phase_6",
        source="change ticket, ADR sign-off, or release approval record",
        description=(
            "Operational approval for deployment complexity and remaining "
            "runtime ownership boundaries."
        ),
        validation="approval names the accepted boundary decision and rollout scope",
    ),
)


def get_rollout_workflows() -> tuple[RolloutWorkflow, ...]:
    """Return runtime modernization rollout workflows."""

    return ROLLOUT_WORKFLOWS


def get_rollout_workflow(name: str) -> RolloutWorkflow:
    """Return one rollout workflow by name."""

    try:
        return next(workflow for workflow in ROLLOUT_WORKFLOWS if workflow.name == name)
    except StopIteration as ex:
        raise KeyError(
            f"Unknown runtime modernization rollout workflow: {name}"
        ) from ex


def get_production_evidence_requirements() -> tuple[RolloutEvidenceRequirement, ...]:
    """Return required production evidence artifacts for modernization completion."""

    return PRODUCTION_EVIDENCE_REQUIREMENTS


def build_production_evidence_manifest(
    workflows: tuple[RolloutWorkflow, ...],
) -> dict[str, Any]:
    """Build the production evidence manifest for selected workflows."""

    return {
        "schema_version": 1,
        "status": "requires_external_evidence",
        "minimum_typescript_serving_workflows": 2,
        "workflows": [workflow.to_dict() for workflow in workflows],
        "required_artifacts": [
            requirement.to_dict()
            for requirement in get_production_evidence_requirements()
        ],
    }

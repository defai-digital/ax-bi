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

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from superset.runtime_modernization.inventory import (
    get_runtime_inventory,
    MigrationDisposition,
    Runtime,
)
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


@dataclass(frozen=True, slots=True)
class ProductionEvidenceCheck:
    """Validation result for one production evidence artifact."""

    name: str
    passed: bool
    message: str

    def to_dict(self) -> dict[str, object]:
        """Serialize the validation check for CLI output."""

        return {
            "name": self.name,
            "passed": self.passed,
            "message": self.message,
        }


@dataclass(frozen=True, slots=True)
class PhaseCompletionCheck:
    """Validation result for one runtime modernization phase."""

    name: str
    title: str
    passed: bool
    message: str
    required_checks: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        """Serialize the phase completion check for CLI output."""

        return {
            "name": self.name,
            "title": self.title,
            "passed": self.passed,
            "message": self.message,
            "required_checks": list(self.required_checks),
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
    _mcp_workflow(
        name="mcp_saved_query_list",
        operation="list_saved_queries",
        sidecar_route="POST /mcp/saved-queries/list",
        contract_version="saved-query-list.v1",
        serving_flag="TS_SAVED_QUERY_LIST_SERVING",
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


def build_production_evidence_template(
    workflows: tuple[RolloutWorkflow, ...],
) -> dict[str, Any]:
    """Build a fillable production evidence bundle template."""

    return {
        "schema_version": 1,
        "artifacts": {
            "compatibility_report": {
                "status": "passed",
                "target_checks": {
                    "sql_parsing_operations_per_second_met": None,
                    "rust_kernel_speedup_met": None,
                },
            },
            "rust_kernel_benchmark": {
                "status": "passed",
                "output_matched": True,
                "target_checks": {
                    "speedup_met": None,
                },
            },
            "production_flag_state": {
                "workflows": [
                    {
                        "name": workflow.name,
                        "serving_flags": {
                            flag: False for flag in workflow.serving_flags
                        },
                    }
                    for workflow in workflows
                ],
            },
            "operator_dashboard_snapshot": {
                "snapshot_reference": "",
                "workflows": {
                    workflow.name: {
                        "gates": {
                            gate.name: {
                                "passed": False,
                                "metric": gate.metric,
                                "target": gate.target,
                            }
                            for gate in workflow.gates
                        }
                    }
                    for workflow in workflows
                },
            },
            "operator_approval": {
                "approved": False,
                "boundary_decision": "",
                "rollout_scope": "",
                "approval_reference": "",
            },
        },
    }


def build_production_flag_state(
    workflows: tuple[RolloutWorkflow, ...],
    flag_enabled: Callable[[str], bool],
) -> dict[str, Any]:
    """Build production flag-state evidence for selected workflows."""

    return {
        "workflows": [
            {
                "name": workflow.name,
                "serving_flags": {
                    flag: flag_enabled(flag) for flag in workflow.serving_flags
                },
            }
            for workflow in workflows
        ],
    }


def build_operator_approval_evidence(
    *,
    boundary_decision: str,
    rollout_scope: str,
    approval_reference: str,
    approved: bool = True,
    approver: str | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    """Build operator approval evidence for runtime modernization rollout."""

    evidence: dict[str, Any] = {
        "approved": approved,
        "boundary_decision": boundary_decision,
        "rollout_scope": rollout_scope,
        "approval_reference": approval_reference,
    }
    if approver is not None:
        evidence["approver"] = approver
    if notes is not None:
        evidence["notes"] = notes
    return evidence


def build_operator_dashboard_snapshot(
    workflows: tuple[RolloutWorkflow, ...],
    *,
    snapshot_reference: str,
    gates_passed: bool,
    measurement_window: str | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    """Build operator dashboard evidence for runtime modernization rollout."""

    snapshot: dict[str, Any] = {
        "snapshot_reference": snapshot_reference,
        "workflows": {
            workflow.name: {
                "gates": {
                    gate.name: {
                        "passed": gates_passed,
                        "metric": gate.metric,
                        "target": gate.target,
                    }
                    for gate in workflow.gates
                },
            }
            for workflow in workflows
        },
    }
    if measurement_window is not None:
        snapshot["measurement_window"] = measurement_window
    if notes is not None:
        snapshot["notes"] = notes
    return snapshot


def build_production_evidence_bundle(
    *,
    compatibility_report: Mapping[str, Any],
    rust_kernel_benchmark: Mapping[str, Any],
    production_flag_state: Mapping[str, Any] | None = None,
    operator_dashboard_snapshot: Mapping[str, Any] | None = None,
    operator_approval: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a production evidence bundle from collected artifact payloads."""

    artifacts: dict[str, Mapping[str, Any]] = {
        "compatibility_report": compatibility_report,
        "rust_kernel_benchmark": rust_kernel_benchmark,
    }
    if production_flag_state is not None:
        artifacts["production_flag_state"] = production_flag_state
    if operator_dashboard_snapshot is not None:
        artifacts["operator_dashboard_snapshot"] = operator_dashboard_snapshot
    if operator_approval is not None:
        artifacts["operator_approval"] = operator_approval

    return {
        "schema_version": 1,
        "artifacts": artifacts,
    }


def _artifact_mapping(
    artifacts: Mapping[str, Any],
    name: str,
) -> Mapping[str, Any] | None:
    """Return one object-shaped artifact from an evidence bundle."""

    value = artifacts.get(name)
    return value if isinstance(value, Mapping) else None


def _target_checks_passed(artifact: Mapping[str, Any]) -> bool:
    """Return whether optional target checks are either passing or unset."""

    target_checks = artifact.get("target_checks")
    if target_checks is None:
        return True
    if not isinstance(target_checks, Mapping):
        return False
    return all(value is not False for value in target_checks.values())


def _workflow_records_by_name(
    artifact: Mapping[str, Any],
) -> dict[str, Mapping[str, Any]]:
    """Return workflow evidence records keyed by workflow name."""

    raw_workflows = artifact.get("workflows")
    records: dict[str, Mapping[str, Any]] = {}

    if isinstance(raw_workflows, Mapping):
        for name, raw_record in raw_workflows.items():
            if isinstance(name, str) and isinstance(raw_record, Mapping):
                records[name] = raw_record
        return records

    if isinstance(raw_workflows, list):
        for raw_record in raw_workflows:
            if not isinstance(raw_record, Mapping):
                continue
            name = raw_record.get("name")
            if isinstance(name, str):
                records[name] = raw_record

    return records


def _serving_flags_enabled(
    record: Mapping[str, Any],
    workflow: RolloutWorkflow,
) -> bool:
    """Return whether all serving flags are enabled for one workflow record."""

    raw_flags = record.get("serving_flags", record.get("flags"))
    if isinstance(raw_flags, Mapping):
        return all(raw_flags.get(flag) is True for flag in workflow.serving_flags)
    if isinstance(raw_flags, list):
        return all(flag in raw_flags for flag in workflow.serving_flags)
    return False


def _gate_passed(raw_gates: Any, gate_name: str) -> bool:
    """Return whether one dashboard gate passed."""

    if isinstance(raw_gates, Mapping):
        raw_gate = raw_gates.get(gate_name)
        if raw_gate is True:
            return True
        if isinstance(raw_gate, Mapping):
            return raw_gate.get("passed") is True or raw_gate.get("status") == "passed"
        return False

    if isinstance(raw_gates, list):
        for raw_gate in raw_gates:
            if not isinstance(raw_gate, Mapping) or raw_gate.get("name") != gate_name:
                continue
            return raw_gate.get("passed") is True or raw_gate.get("status") == "passed"

    return False


def _non_empty_string(value: Any) -> bool:
    """Return whether a value is a non-empty string."""

    return isinstance(value, str) and value.strip() != ""


def validate_production_evidence(
    workflows: tuple[RolloutWorkflow, ...],
    evidence: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate production evidence artifacts for selected rollout workflows."""

    raw_artifacts = evidence.get("artifacts")
    artifacts = raw_artifacts if isinstance(raw_artifacts, Mapping) else {}
    checks: list[ProductionEvidenceCheck] = []

    compatibility_report = _artifact_mapping(artifacts, "compatibility_report")
    compatibility_passed = (
        compatibility_report is not None
        and compatibility_report.get("status") == "passed"
        and _target_checks_passed(compatibility_report)
    )
    checks.append(
        ProductionEvidenceCheck(
            name="compatibility_report",
            passed=compatibility_passed,
            message=(
                "compatibility report passed"
                if compatibility_passed
                else "compatibility report is missing or failed"
            ),
        )
    )

    rust_benchmark = _artifact_mapping(artifacts, "rust_kernel_benchmark")
    rust_passed = (
        rust_benchmark is not None
        and rust_benchmark.get("status") == "passed"
        and rust_benchmark.get("output_matched") is True
        and _target_checks_passed(rust_benchmark)
    )
    checks.append(
        ProductionEvidenceCheck(
            name="rust_kernel_benchmark",
            passed=rust_passed,
            message=(
                "Rust kernel benchmark passed"
                if rust_passed
                else "Rust kernel benchmark is missing, failed, or incompatible"
            ),
        )
    )

    flag_state = _artifact_mapping(artifacts, "production_flag_state")
    flag_records = _workflow_records_by_name(flag_state or {})
    enabled_workflows = [
        workflow.name
        for workflow in workflows
        if _serving_flags_enabled(flag_records.get(workflow.name, {}), workflow)
    ]
    minimum_serving_workflows = 2
    flag_state_passed = len(enabled_workflows) >= minimum_serving_workflows
    checks.append(
        ProductionEvidenceCheck(
            name="production_flag_state",
            passed=flag_state_passed,
            message=(
                f"{len(enabled_workflows)} TypeScript serving workflows enabled"
                if flag_state_passed
                else (
                    "production flag state must show at least "
                    f"{minimum_serving_workflows} TypeScript serving workflows"
                )
            ),
        )
    )

    dashboard_snapshot = _artifact_mapping(artifacts, "operator_dashboard_snapshot")
    dashboard_records = _workflow_records_by_name(dashboard_snapshot or {})
    dashboard_passed = bool(workflows) and _non_empty_string(
        (dashboard_snapshot or {}).get("snapshot_reference")
    )
    for workflow in workflows:
        record = dashboard_records.get(workflow.name)
        if record is None:
            dashboard_passed = False
            break
        raw_gates = record.get("gates")
        if not all(_gate_passed(raw_gates, gate.name) for gate in workflow.gates):
            dashboard_passed = False
            break

    checks.append(
        ProductionEvidenceCheck(
            name="operator_dashboard_snapshot",
            passed=dashboard_passed,
            message=(
                "operator dashboard reference and gates passed for selected workflows"
                if dashboard_passed
                else ("operator dashboard reference or gates are missing or failing")
            ),
        )
    )

    operator_approval = _artifact_mapping(artifacts, "operator_approval")
    approval_passed = (
        operator_approval is not None
        and operator_approval.get("approved") is True
        and _non_empty_string(operator_approval.get("boundary_decision"))
        and _non_empty_string(operator_approval.get("approval_reference"))
        and (
            _non_empty_string(operator_approval.get("rollout_scope"))
            or _non_empty_string(operator_approval.get("scope"))
        )
    )
    checks.append(
        ProductionEvidenceCheck(
            name="operator_approval",
            passed=approval_passed,
            message=(
                "operator approval names boundary decision, rollout scope, "
                "and approval reference"
                if approval_passed
                else (
                    "operator approval is missing boundary decision, rollout "
                    "scope, or approval reference"
                )
            ),
        )
    )

    passed = all(check.passed for check in checks)
    return {
        "schema_version": 1,
        "status": "passed" if passed else "failed",
        "workflow_names": [workflow.name for workflow in workflows],
        "checks": [check.to_dict() for check in checks],
    }


def _evidence_check_passed(
    validation: Mapping[str, Any],
    check_name: str,
) -> bool:
    """Return whether one named production evidence check passed."""

    raw_checks = validation.get("checks")
    if not isinstance(raw_checks, list):
        return False
    for raw_check in raw_checks:
        if (
            isinstance(raw_check, Mapping)
            and raw_check.get("name") == check_name
            and raw_check.get("passed") is True
        ):
            return True
    return False


def audit_runtime_modernization_completion(
    workflows: tuple[RolloutWorkflow, ...],
    evidence: Mapping[str, Any],
) -> dict[str, Any]:
    """Audit runtime modernization phase completion from current evidence."""

    inventory = get_runtime_inventory()
    has_typescript_candidate = any(
        item.disposition == MigrationDisposition.CANDIDATE
        and item.target_runtime == Runtime.TYPESCRIPT
        for item in inventory
    )
    has_rust_candidate = any(
        item.disposition == MigrationDisposition.CANDIDATE
        and item.target_runtime == Runtime.RUST
        for item in inventory
    )
    has_service_foundation = any(
        workflow.name == "mcp_health_check"
        and workflow.sidecar_route == "GET /health"
        and workflow.contract_version == "runtime.v1"
        for workflow in get_rollout_workflows()
    )
    validation = validate_production_evidence(workflows, evidence)
    compatibility_passed = _evidence_check_passed(validation, "compatibility_report")
    rust_benchmark_passed = _evidence_check_passed(
        validation,
        "rust_kernel_benchmark",
    )
    flag_state_passed = _evidence_check_passed(validation, "production_flag_state")
    dashboard_passed = _evidence_check_passed(
        validation,
        "operator_dashboard_snapshot",
    )
    approval_passed = _evidence_check_passed(validation, "operator_approval")
    production_typescript_passed = (
        compatibility_passed and flag_state_passed and dashboard_passed
    )

    checks = [
        PhaseCompletionCheck(
            name="phase_0_baseline",
            title="Baseline and decision gates",
            passed=has_typescript_candidate and has_rust_candidate,
            message=(
                "runtime inventory includes TypeScript and Rust candidates"
                if has_typescript_candidate and has_rust_candidate
                else "runtime inventory is missing TypeScript or Rust candidates"
            ),
            required_checks=("runtime_inventory",),
        ),
        PhaseCompletionCheck(
            name="phase_1_python_boundaries",
            title="Stabilize Python boundaries",
            passed=compatibility_passed,
            message=(
                "compatibility evidence passed for selected boundaries"
                if compatibility_passed
                else "compatibility evidence is missing or failed"
            ),
            required_checks=("compatibility_report",),
        ),
        PhaseCompletionCheck(
            name="phase_2_typescript_foundation",
            title="TypeScript service foundation",
            passed=has_service_foundation,
            message=(
                "TypeScript sidecar health workflow is registered"
                if has_service_foundation
                else "TypeScript sidecar health workflow is missing"
            ),
            required_checks=("mcp_health_check_workflow",),
        ),
        PhaseCompletionCheck(
            name="phase_3_first_typescript_extraction",
            title="First TypeScript product extraction",
            passed=production_typescript_passed,
            message=(
                "TypeScript workflow production evidence passed"
                if production_typescript_passed
                else "TypeScript workflow production evidence is incomplete"
            ),
            required_checks=(
                "compatibility_report",
                "production_flag_state",
                "operator_dashboard_snapshot",
            ),
        ),
        PhaseCompletionCheck(
            name="phase_4_rust_kernel_poc",
            title="Rust kernel proof of concept",
            passed=rust_benchmark_passed,
            message=(
                "Rust kernel benchmark evidence passed"
                if rust_benchmark_passed
                else "Rust kernel benchmark evidence is missing or failed"
            ),
            required_checks=("rust_kernel_benchmark",),
        ),
        PhaseCompletionCheck(
            name="phase_5_selective_runtime_split",
            title="Expand runtime split selectively",
            passed=production_typescript_passed and rust_benchmark_passed,
            message=(
                "selective TypeScript and Rust rollout evidence passed"
                if production_typescript_passed and rust_benchmark_passed
                else "selective runtime split production evidence is incomplete"
            ),
            required_checks=(
                "compatibility_report",
                "production_flag_state",
                "operator_dashboard_snapshot",
                "rust_kernel_benchmark",
            ),
        ),
        PhaseCompletionCheck(
            name="phase_6_boundary_reevaluation",
            title="Reevaluate larger boundaries",
            passed=approval_passed,
            message=(
                "operator approval evidence passed"
                if approval_passed
                else "operator approval evidence is missing or failed"
            ),
            required_checks=("operator_approval",),
        ),
    ]

    passed = all(check.passed for check in checks)
    return {
        "schema_version": 1,
        "status": "complete" if passed else "incomplete",
        "workflow_names": [workflow.name for workflow in workflows],
        "phase_checks": [check.to_dict() for check in checks],
        "evidence_validation": validation,
    }

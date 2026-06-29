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
    duration = runtime_metric_key(area, operation, "duration")

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
            RolloutGate(
                name="latency_p95",
                metric=duration,
                target="p95 latency meets the workflow baseline target",
                description=(
                    "The migrated workflow must meet the release-candidate p95 "
                    "latency target measured against the Python baseline."
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
        name="mcp_annotation_layer_list",
        operation="list_annotation_layers",
        sidecar_route="POST /mcp/annotation-layers/list",
        contract_version="annotation-layer-list.v1",
        serving_flag="TS_ANNOTATION_LAYER_LIST_SERVING",
    ),
    _mcp_workflow(
        name="mcp_layer_annotation_list",
        operation="list_layer_annotations",
        sidecar_route="POST /mcp/annotations/list",
        contract_version="annotation-list.v1",
        serving_flag="TS_LAYER_ANNOTATION_LIST_SERVING",
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
        name="mcp_query_list",
        operation="list_queries",
        sidecar_route="POST /mcp/queries/list",
        contract_version="query-list.v1",
        serving_flag="TS_QUERY_LIST_SERVING",
    ),
    _mcp_workflow(
        name="mcp_saved_query_list",
        operation="list_saved_queries",
        sidecar_route="POST /mcp/saved-queries/list",
        contract_version="saved-query-list.v1",
        serving_flag="TS_SAVED_QUERY_LIST_SERVING",
    ),
    _mcp_workflow(
        name="mcp_report_list",
        operation="list_reports",
        sidecar_route="POST /mcp/reports/list",
        contract_version="report-list.v1",
        serving_flag="TS_REPORT_LIST_SERVING",
    ),
    _mcp_workflow(
        name="mcp_role_list",
        operation="list_roles",
        sidecar_route="POST /mcp/roles/list",
        contract_version="role-list.v1",
        serving_flag="TS_ROLE_LIST_SERVING",
    ),
    _mcp_workflow(
        name="mcp_rls_filter_list",
        operation="list_rls_filters",
        sidecar_route="POST /mcp/rls-filters/list",
        contract_version="rls-list.v1",
        serving_flag="TS_RLS_FILTER_LIST_SERVING",
    ),
    _mcp_workflow(
        name="mcp_tag_list",
        operation="list_tags",
        sidecar_route="POST /mcp/tags/list",
        contract_version="tag-list.v1",
        serving_flag="TS_TAG_LIST_SERVING",
    ),
    _mcp_workflow(
        name="mcp_task_list",
        operation="list_tasks",
        sidecar_route="POST /mcp/tasks/list",
        contract_version="task-list.v1",
        serving_flag="TS_TASK_LIST_SERVING",
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
        validation=(
            "schema_version is 1, kernel is named, iterations are positive, "
            "status is passed, and output_matched is true"
        ),
    ),
    RolloutEvidenceRequirement(
        name="rust_kernel_rollout_decision",
        phase="phase_5",
        source="production flag export, change ticket, or release decision record",
        description=(
            "Decision showing the measured Rust kernel either serves production "
            "traffic or was rejected with a documented reason."
        ),
        validation=(
            "decision is served with the kernel flag enabled, or rejected with "
            "rationale and decision reference"
        ),
    ),
    RolloutEvidenceRequirement(
        name="production_flag_state",
        phase="phase_3_phase_5",
        source="deployment configuration or feature-flag export",
        description=(
            "Snapshot showing which runtime modernization shadow and serving "
            "flags were enabled for each workflow, with deployment provenance."
        ),
        validation=(
            "environment and flag-state reference are named, at least one "
            "TypeScript workflow serving flag set is enabled for Phase 3, "
            "and at least two are enabled for Phase 5"
        ),
    ),
    RolloutEvidenceRequirement(
        name="operator_dashboard_snapshot",
        phase="phase_5",
        source="production observability dashboard export or screenshot",
        description=(
            "Operator view of sidecar service health, latency, error rate, "
            "fallback rate, and shadow mismatch metrics for migrated workflows."
        ),
        validation=(
            "measurement window is named, sidecar health and readiness pass, "
            "and fallback rate and error rate meet each workflow gate"
        ),
    ),
    RolloutEvidenceRequirement(
        name="operator_approval",
        phase="phase_6",
        source="change ticket, ADR sign-off, or release approval record",
        description=(
            "Operational approval for deployment complexity and remaining "
            "runtime ownership boundaries."
        ),
        validation=(
            "approval names the accepted boundary decision, rollout scope, "
            "migration decision, compatibility cost estimate, and security "
            "cost estimate"
        ),
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

    if not workflows:
        raise ValueError(
            "production evidence manifest requires at least one workflow",
        )

    return {
        "schema_version": 1,
        "status": "requires_external_evidence",
        "minimum_typescript_serving_workflows": 2,
        "minimum_phase_3_typescript_serving_workflows": 1,
        "minimum_phase_5_typescript_serving_workflows": 2,
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

    if not workflows:
        raise ValueError(
            "production evidence template requires at least one workflow",
        )

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
                "schema_version": 1,
                "status": "passed",
                "kernel": "sql_whitespace_kernel",
                "iterations": 0,
                "output_matched": True,
                "target_checks": {
                    "speedup_met": None,
                },
            },
            "rust_kernel_rollout_decision": {
                **build_rust_kernel_rollout_decision_template(),
            },
            "production_flag_state": {
                "environment": "",
                "flag_state_reference": "",
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
                "measurement_window": "",
                "service_health": {
                    "health_check": {
                        "passed": False,
                        "metric": "runtime.v1.health.ok",
                        "target": "health endpoint returns success",
                    },
                    "readiness_check": {
                        "passed": False,
                        "metric": "runtime.v1.ready.ok",
                        "target": "readiness endpoint returns success",
                    },
                },
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
                "migration_decision": "",
                "compatibility_cost_estimate": "",
                "security_cost_estimate": "",
                "approval_reference": "",
                "workflow_names": [],
            },
        },
    }


def build_production_flag_state(
    workflows: tuple[RolloutWorkflow, ...],
    flag_enabled: Callable[[str], bool],
    *,
    environment: str,
    flag_state_reference: str,
) -> dict[str, Any]:
    """Build production flag-state evidence for selected workflows."""

    if not workflows:
        raise ValueError(
            "production flag-state evidence requires at least one workflow",
        )
    _require_non_empty_evidence_field(environment, "environment")
    _require_non_empty_evidence_field(
        flag_state_reference,
        "flag_state_reference",
    )

    return {
        "environment": environment,
        "flag_state_reference": flag_state_reference,
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
    migration_decision: str,
    compatibility_cost_estimate: str,
    security_cost_estimate: str,
    approval_reference: str,
    workflow_names: tuple[str, ...] = (),
    approved: bool = True,
    approver: str | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    """Build operator approval evidence for runtime modernization rollout."""

    if approved:
        if not workflow_names:
            raise ValueError(
                "approved operator evidence requires at least one workflow name",
            )
        _require_non_empty_evidence_field(boundary_decision, "boundary_decision")
        _require_non_empty_evidence_field(rollout_scope, "rollout_scope")
        if not _migration_decision_passed(migration_decision):
            raise ValueError(
                "migration_decision must be 'expand', 'pause', or 'stop'",
            )
        _require_non_empty_evidence_field(
            compatibility_cost_estimate,
            "compatibility_cost_estimate",
        )
        _require_non_empty_evidence_field(
            security_cost_estimate,
            "security_cost_estimate",
        )
        _require_non_empty_evidence_field(approval_reference, "approval_reference")

    evidence: dict[str, Any] = {
        "approved": approved,
        "boundary_decision": boundary_decision,
        "rollout_scope": rollout_scope,
        "migration_decision": migration_decision,
        "compatibility_cost_estimate": compatibility_cost_estimate,
        "security_cost_estimate": security_cost_estimate,
        "approval_reference": approval_reference,
        "workflow_names": list(workflow_names),
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
    service_health_passed: bool,
    gate_statuses: Mapping[str, bool] | None = None,
    workflow_gate_statuses: Mapping[str, Mapping[str, bool]] | None = None,
    measurement_window: str | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    """Build operator dashboard evidence for runtime modernization rollout."""

    if not workflows:
        raise ValueError(
            "operator dashboard evidence requires at least one workflow",
        )
    _require_non_empty_evidence_field(snapshot_reference, "snapshot_reference")
    _require_non_empty_evidence_field(measurement_window, "measurement_window")

    snapshot: dict[str, Any] = {
        "snapshot_reference": snapshot_reference,
        "service_health": {
            "health_check": {
                "passed": service_health_passed,
                "metric": "runtime.v1.health.ok",
                "target": "health endpoint returns success",
            },
            "readiness_check": {
                "passed": service_health_passed,
                "metric": "runtime.v1.ready.ok",
                "target": "readiness endpoint returns success",
            },
        },
        "workflows": {
            workflow.name: {
                "gates": {
                    gate.name: {
                        "passed": (workflow_gate_statuses or {})
                        .get(workflow.name, {})
                        .get(
                            gate.name,
                            (gate_statuses or {}).get(gate.name, gates_passed),
                        ),
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


def build_rust_kernel_rollout_decision(
    *,
    kernel: str,
    decision: str,
    decision_reference: str,
    rationale: str,
    serving_flag: str = "RUST_SQL_KERNEL",
    serving_flag_enabled: bool | None = None,
) -> dict[str, Any]:
    """Build Rust kernel rollout decision evidence for Phase 5."""

    _require_non_empty_evidence_field(kernel, "kernel")
    _require_non_empty_evidence_field(decision_reference, "decision_reference")
    _require_non_empty_evidence_field(rationale, "rationale")
    _require_non_empty_evidence_field(serving_flag, "serving_flag")
    if decision not in {"served", "rejected"}:
        raise ValueError("Rust rollout decision must be 'served' or 'rejected'")
    if decision == "served" and serving_flag_enabled is not True:
        raise ValueError(
            "served Rust rollout decisions require serving_flag_enabled=True",
        )

    evidence: dict[str, Any] = {
        "kernel": kernel,
        "decision": decision,
        "serving_flag": serving_flag,
        "decision_reference": decision_reference,
        "rationale": rationale,
    }
    if serving_flag_enabled is not None:
        evidence["serving_flag_enabled"] = serving_flag_enabled
    return evidence


def build_rust_kernel_rollout_decision_template(
    *,
    kernel: str = "ax_sql.normalize_sql_whitespace",
    serving_flag: str = "RUST_SQL_KERNEL",
) -> dict[str, Any]:
    """Build a fillable Rust kernel rollout decision evidence template."""

    return {
        "kernel": kernel,
        "decision": "",
        "serving_flag": serving_flag,
        "serving_flag_enabled": False,
        "decision_reference": "",
        "rationale": "",
    }


def build_production_evidence_bundle(
    *,
    compatibility_report: Mapping[str, Any],
    rust_kernel_benchmark: Mapping[str, Any],
    rust_kernel_rollout_decision: Mapping[str, Any] | None = None,
    production_flag_state: Mapping[str, Any] | None = None,
    operator_dashboard_snapshot: Mapping[str, Any] | None = None,
    operator_approval: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a production evidence bundle from collected artifact payloads."""

    _require_artifact_mapping(compatibility_report, "compatibility_report")
    _require_artifact_mapping(rust_kernel_benchmark, "rust_kernel_benchmark")
    if rust_kernel_rollout_decision is not None:
        _require_artifact_mapping(
            rust_kernel_rollout_decision,
            "rust_kernel_rollout_decision",
        )
    if production_flag_state is not None:
        _require_artifact_mapping(production_flag_state, "production_flag_state")
    if operator_dashboard_snapshot is not None:
        _require_artifact_mapping(
            operator_dashboard_snapshot,
            "operator_dashboard_snapshot",
        )
    if operator_approval is not None:
        _require_artifact_mapping(operator_approval, "operator_approval")

    artifacts: dict[str, Mapping[str, Any]] = {
        "compatibility_report": compatibility_report,
        "rust_kernel_benchmark": rust_kernel_benchmark,
    }
    if rust_kernel_rollout_decision is not None:
        artifacts["rust_kernel_rollout_decision"] = rust_kernel_rollout_decision
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


def _require_artifact_mapping(value: Any, artifact_name: str) -> None:
    """Require an object-shaped artifact when assembling evidence bundles."""

    if not isinstance(value, Mapping):
        raise ValueError(f"{artifact_name} artifact must be an object")


def _artifact_mapping(
    artifacts: Mapping[str, Any],
    name: str,
) -> Mapping[str, Any] | None:
    """Return one object-shaped artifact from an evidence bundle."""

    value = artifacts.get(name)
    return value if isinstance(value, Mapping) else None


def _require_non_empty_evidence_field(value: Any, field_name: str) -> None:
    """Require a non-empty string field when building evidence artifacts."""

    if not _non_empty_string(value):
        raise ValueError(f"{field_name} is required")


def _target_checks_passed(artifact: Mapping[str, Any]) -> bool:
    """Return whether optional target checks are either passing or unset."""

    target_checks = artifact.get("target_checks")
    if target_checks is None:
        return True
    if not isinstance(target_checks, Mapping):
        return False
    return all(value is True or value is None for value in target_checks.values())


def _positive_integer(value: Any) -> bool:
    """Return whether a value is a positive integer."""

    return isinstance(value, int) and value > 0


def _rust_benchmark_passed(artifact: Mapping[str, Any] | None) -> bool:
    """Return whether Rust benchmark evidence satisfies Phase 4 and 5."""

    return (
        artifact is not None
        and artifact.get("schema_version") == 1
        and _non_empty_string(artifact.get("kernel"))
        and _positive_integer(artifact.get("iterations"))
        and artifact.get("status") == "passed"
        and artifact.get("output_matched") is True
        and _target_checks_passed(artifact)
    )


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


def _workflow_records_valid(artifact: Mapping[str, Any]) -> bool:
    """Return whether workflow evidence records are well-formed and unique."""

    raw_workflows = artifact.get("workflows")
    if isinstance(raw_workflows, Mapping):
        return all(
            _non_empty_string(name) and isinstance(raw_record, Mapping)
            for name, raw_record in raw_workflows.items()
        )

    if isinstance(raw_workflows, list):
        names: set[str] = set()
        for raw_record in raw_workflows:
            if not isinstance(raw_record, Mapping):
                return False
            name = raw_record.get("name")
            if not isinstance(name, str) or name.strip() == "" or name in names:
                return False
            names.add(name)
        return True

    return False


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


def _service_health_passed(artifact: Mapping[str, Any]) -> bool:
    """Return whether the operator dashboard proves sidecar health."""

    raw_service_health = artifact.get("service_health")
    if not isinstance(raw_service_health, Mapping):
        return False
    return all(
        _gate_passed(raw_service_health, gate_name)
        for gate_name in ("health_check", "readiness_check")
    )


def _non_empty_string(value: Any) -> bool:
    """Return whether a value is a non-empty string."""

    return isinstance(value, str) and value.strip() != ""


def _string_set(value: Any) -> set[str]:
    """Return a string set from a validated string list."""

    if not _string_list(value):
        return set()
    return set(value)


def _string_list(value: Any) -> bool:
    """Return whether a value is a list of non-empty strings."""

    return isinstance(value, list) and all(_non_empty_string(item) for item in value)


def _migration_decision_passed(value: Any) -> bool:
    """Return whether the Phase 6 migration decision is valid."""

    return value in {"expand", "pause", "stop"}


def _rust_rollout_decision_passed(artifact: Mapping[str, Any] | None) -> bool:
    """Return whether Rust rollout decision evidence satisfies Phase 5."""

    if artifact is None:
        return False

    if (
        not _non_empty_string(artifact.get("kernel"))
        or not _non_empty_string(artifact.get("decision_reference"))
        or not _non_empty_string(artifact.get("rationale"))
    ):
        return False

    decision = artifact.get("decision")
    if decision == "served":
        return (
            _non_empty_string(artifact.get("serving_flag"))
            and artifact.get("serving_flag_enabled") is True
        )
    if decision == "rejected":
        return True
    return False


def validate_production_evidence(
    workflows: tuple[RolloutWorkflow, ...],
    evidence: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate production evidence artifacts for selected rollout workflows."""

    raw_artifacts = evidence.get("artifacts")
    artifacts = raw_artifacts if isinstance(raw_artifacts, Mapping) else {}
    checks: list[ProductionEvidenceCheck] = []

    workflow_scope_passed = bool(workflows)
    checks.append(
        ProductionEvidenceCheck(
            name="workflow_scope",
            passed=workflow_scope_passed,
            message=(
                "production evidence is scoped to selected workflows"
                if workflow_scope_passed
                else "production evidence validation requires at least one workflow"
            ),
        )
    )

    evidence_bundle_passed = evidence.get("schema_version") == 1 and isinstance(
        raw_artifacts, Mapping
    )
    checks.append(
        ProductionEvidenceCheck(
            name="evidence_bundle",
            passed=evidence_bundle_passed,
            message=(
                "production evidence bundle schema is supported"
                if evidence_bundle_passed
                else (
                    "production evidence bundle must use schema_version 1 and "
                    "object-shaped artifacts"
                )
            ),
        )
    )

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
    rust_passed = _rust_benchmark_passed(rust_benchmark)
    checks.append(
        ProductionEvidenceCheck(
            name="rust_kernel_benchmark",
            passed=rust_passed,
            message=(
                "Rust kernel benchmark passed"
                if rust_passed
                else (
                    "Rust kernel benchmark is missing, malformed, failed, or "
                    "incompatible"
                )
            ),
        )
    )

    rust_rollout_decision = _artifact_mapping(
        artifacts,
        "rust_kernel_rollout_decision",
    )
    rust_rollout_decision_passed = _rust_rollout_decision_passed(rust_rollout_decision)
    checks.append(
        ProductionEvidenceCheck(
            name="rust_kernel_rollout_decision",
            passed=rust_rollout_decision_passed,
            message=(
                "Rust kernel rollout decision is documented"
                if rust_rollout_decision_passed
                else (
                    "Rust kernel rollout decision must show served production "
                    "traffic or a documented rejection"
                )
            ),
        )
    )

    flag_state = _artifact_mapping(artifacts, "production_flag_state")
    flag_records = _workflow_records_by_name(flag_state or {})
    flag_records_valid = _workflow_records_valid(flag_state or {})
    flag_state_has_provenance = _non_empty_string(
        (flag_state or {}).get("environment")
    ) and _non_empty_string((flag_state or {}).get("flag_state_reference"))
    enabled_workflows = [
        workflow.name
        for workflow in workflows
        if _serving_flags_enabled(flag_records.get(workflow.name, {}), workflow)
    ]
    minimum_first_serving_workflows = 1
    minimum_selective_serving_workflows = 2
    flag_state_passed = (
        flag_state_has_provenance
        and flag_records_valid
        and len(enabled_workflows) >= minimum_first_serving_workflows
    )
    selective_rollout_passed = (
        flag_state_has_provenance
        and flag_records_valid
        and len(enabled_workflows) >= minimum_selective_serving_workflows
    )
    checks.append(
        ProductionEvidenceCheck(
            name="production_flag_state",
            passed=flag_state_passed,
            message=(
                f"{len(enabled_workflows)} TypeScript serving workflows enabled"
                if flag_state_passed
                else (
                    "production flag state must name environment, flag-state "
                    "reference, valid workflow records, and at least "
                    f"{minimum_first_serving_workflows} TypeScript serving workflow"
                )
            ),
        )
    )
    checks.append(
        ProductionEvidenceCheck(
            name="typescript_selective_rollout",
            passed=selective_rollout_passed,
            message=(
                f"{len(enabled_workflows)} TypeScript serving workflows enabled"
                if selective_rollout_passed
                else (
                    "selective rollout requires at least "
                    f"{minimum_selective_serving_workflows} TypeScript serving "
                    "workflows with deployment provenance and valid workflow "
                    "records"
                )
            ),
        )
    )

    dashboard_snapshot = _artifact_mapping(artifacts, "operator_dashboard_snapshot")
    dashboard_records = _workflow_records_by_name(dashboard_snapshot or {})
    dashboard_records_valid = _workflow_records_valid(dashboard_snapshot or {})
    dashboard_required_workflows = [
        workflow for workflow in workflows if workflow.name in enabled_workflows
    ]
    dashboard_passed = (
        bool(dashboard_required_workflows)
        and dashboard_records_valid
        and _non_empty_string((dashboard_snapshot or {}).get("snapshot_reference"))
        and _non_empty_string((dashboard_snapshot or {}).get("measurement_window"))
        and _service_health_passed(dashboard_snapshot or {})
    )
    for workflow in dashboard_required_workflows:
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
                "operator dashboard reference, measurement window, service "
                "health, and gates passed for enabled workflows"
                if dashboard_passed
                else (
                    "operator dashboard reference, measurement window, service "
                    "health, workflow records, or gates are missing or failing"
                )
            ),
        )
    )

    operator_approval = _artifact_mapping(artifacts, "operator_approval")
    raw_approval_workflow_names = (operator_approval or {}).get("workflow_names")
    approval_workflow_names = _string_set(raw_approval_workflow_names)
    approval_workflow_names_valid = _string_list(raw_approval_workflow_names)
    enabled_workflow_names = set(enabled_workflows)
    approval_matches_enabled_workflows = (
        approval_workflow_names == enabled_workflow_names
    )
    approval_passed = (
        operator_approval is not None
        and operator_approval.get("approved") is True
        and _non_empty_string(operator_approval.get("boundary_decision"))
        and _migration_decision_passed(operator_approval.get("migration_decision"))
        and _non_empty_string(operator_approval.get("compatibility_cost_estimate"))
        and _non_empty_string(operator_approval.get("security_cost_estimate"))
        and _non_empty_string(operator_approval.get("approval_reference"))
        and approval_workflow_names_valid
        and bool(approval_workflow_names)
        and approval_matches_enabled_workflows
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
                "migration decision, compatibility and security cost estimates, "
                "approval reference, and enabled workflows"
                if approval_passed
                else (
                    "operator approval is missing boundary decision, rollout "
                    "scope, migration decision, compatibility or security cost "
                    "estimates, approval reference, a valid non-empty workflow "
                    "name list, or exact enabled workflow names"
                )
            ),
        )
    )

    failing_check_names = [check.name for check in checks if not check.passed]
    passed = not failing_check_names
    return {
        "schema_version": 1,
        "status": "passed" if passed else "failed",
        "workflow_names": [workflow.name for workflow in workflows],
        "enabled_workflow_names": enabled_workflows,
        "approved_workflow_names": sorted(approval_workflow_names),
        "dashboard_required_workflow_names": [
            workflow.name for workflow in dashboard_required_workflows
        ],
        "failing_check_names": failing_check_names,
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
    rust_rollout_decision_passed = _evidence_check_passed(
        validation,
        "rust_kernel_rollout_decision",
    )
    flag_state_passed = _evidence_check_passed(validation, "production_flag_state")
    typescript_selective_rollout_passed = _evidence_check_passed(
        validation,
        "typescript_selective_rollout",
    )
    dashboard_passed = _evidence_check_passed(
        validation,
        "operator_dashboard_snapshot",
    )
    approval_passed = _evidence_check_passed(validation, "operator_approval")
    production_typescript_passed = (
        compatibility_passed and flag_state_passed and dashboard_passed
    )
    selective_runtime_split_passed = (
        production_typescript_passed
        and typescript_selective_rollout_passed
        and rust_benchmark_passed
        and rust_rollout_decision_passed
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
            passed=selective_runtime_split_passed,
            message=(
                "selective TypeScript and Rust rollout evidence passed"
                if selective_runtime_split_passed
                else "selective runtime split production evidence is incomplete"
            ),
            required_checks=(
                "compatibility_report",
                "production_flag_state",
                "typescript_selective_rollout",
                "operator_dashboard_snapshot",
                "rust_kernel_benchmark",
                "rust_kernel_rollout_decision",
            ),
        ),
        PhaseCompletionCheck(
            name="phase_6_boundary_reevaluation",
            title="Reevaluate larger boundaries",
            passed=selective_runtime_split_passed and approval_passed,
            message=(
                "operator approval evidence passed after selective rollout"
                if selective_runtime_split_passed and approval_passed
                else (
                    "operator approval evidence is missing, failed, or selective "
                    "runtime split evidence is incomplete"
                )
            ),
            required_checks=("phase_5_selective_runtime_split", "operator_approval"),
        ),
    ]

    incomplete_phase_names = [check.name for check in checks if not check.passed]
    evidence_checks = validation.get("failing_check_names")
    failing_evidence_check_names = (
        evidence_checks if isinstance(evidence_checks, list) else []
    )
    passed = not incomplete_phase_names
    return {
        "schema_version": 1,
        "status": "complete" if passed else "incomplete",
        "workflow_names": [workflow.name for workflow in workflows],
        "incomplete_phase_names": incomplete_phase_names,
        "failing_evidence_check_names": failing_evidence_check_names,
        "phase_checks": [check.to_dict() for check in checks],
        "evidence_validation": validation,
    }

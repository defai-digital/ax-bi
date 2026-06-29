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
import pytest

from superset.runtime_modernization.rollout import (
    audit_runtime_modernization_completion,
    build_operator_approval_evidence,
    build_operator_dashboard_snapshot,
    build_production_evidence_bundle,
    build_production_evidence_manifest,
    build_production_evidence_template,
    build_production_flag_state,
    build_rust_kernel_rollout_decision,
    build_rust_kernel_rollout_decision_template,
    get_production_evidence_requirements,
    get_rollout_workflow,
    get_rollout_workflows,
    RolloutWorkflow,
    validate_production_evidence,
)


def _passing_service_health() -> dict[str, object]:
    """Build passing sidecar service-health dashboard evidence."""

    return {
        "health_check": {"passed": True},
        "readiness_check": {"passed": True},
    }


def _production_flag_state(workflows: tuple[RolloutWorkflow, ...]) -> dict[str, object]:
    """Build passing production flag-state evidence for rollout tests."""

    return {
        "environment": "prod-us",
        "flag_state_reference": "flags/runtime-modernization/prod-us-123",
        "workflows": [
            {
                "name": workflow.name,
                "serving_flags": {flag: True for flag in workflow.serving_flags},
            }
            for workflow in workflows
        ],
    }


def _rust_kernel_benchmark() -> dict[str, object]:
    """Build passing Rust kernel benchmark evidence for rollout tests."""

    return {
        "schema_version": 1,
        "status": "passed",
        "kernel": "sql_whitespace_kernel",
        "iterations": 3,
        "output_matched": True,
        "target_checks": {
            "speedup_met": None,
        },
    }


def _complete_production_evidence() -> dict[str, object]:
    """Build complete production evidence for audit tests."""

    workflows = (
        get_rollout_workflow("mcp_asset_search"),
        get_rollout_workflow("mcp_dashboard_list"),
    )
    return {
        "schema_version": 1,
        "artifacts": {
            "compatibility_report": {
                "status": "passed",
                "target_checks": {
                    "sql_parsing_operations_per_second_met": True,
                    "rust_kernel_speedup_met": None,
                },
            },
            "rust_kernel_benchmark": _rust_kernel_benchmark(),
            "rust_kernel_rollout_decision": {
                "kernel": "ax_sql.normalize_sql_whitespace",
                "decision": "rejected",
                "serving_flag": "RUST_SQL_KERNEL",
                "serving_flag_enabled": False,
                "decision_reference": "PERF-123",
                "rationale": "benchmark gain did not justify rollout",
            },
            "production_flag_state": _production_flag_state(workflows),
            "operator_dashboard_snapshot": {
                "snapshot_reference": "observability/dashboard/snapshot-123",
                "measurement_window": "2026-06-29T00:00Z/2026-06-29T01:00Z",
                "service_health": _passing_service_health(),
                "workflows": {
                    workflow.name: {
                        "gates": {gate.name: True for gate in workflow.gates},
                    }
                    for workflow in workflows
                },
            },
            "operator_approval": {
                "approved": True,
                "boundary_decision": "split MCP by tool class",
                "rollout_scope": "asset search and dashboard listing",
                "migration_decision": "expand",
                "compatibility_cost_estimate": (
                    "versioned contracts and Python fallback keep compatibility "
                    "risk low"
                ),
                "security_cost_estimate": (
                    "Superset remains the authorization authority for extracted "
                    "workflows"
                ),
                "approval_reference": "CHG-123",
                "workflow_names": [workflow.name for workflow in workflows],
            },
        },
    }


def test_rollout_workflows_cover_migrated_mcp_paths() -> None:
    """Rollout manifest includes the TypeScript-routed MCP workflows."""

    workflows = get_rollout_workflows()
    names = {workflow.name for workflow in workflows}

    assert names == {
        "mcp_annotation_layer_list",
        "mcp_asset_search",
        "mcp_chart_list",
        "mcp_dashboard_list",
        "mcp_database_list",
        "mcp_dataset_list",
        "mcp_health_check",
        "mcp_layer_annotation_list",
        "mcp_query_list",
        "mcp_report_list",
        "mcp_role_list",
        "mcp_rls_filter_list",
        "mcp_saved_query_list",
        "mcp_tag_list",
        "mcp_task_list",
    }
    assert all(workflow.area == "mcp_orchestration" for workflow in workflows)


def test_rollout_workflow_serializes_metrics_and_gates() -> None:
    """Rollout workflows expose metrics and gates for operator dashboards."""

    workflow = get_rollout_workflow("mcp_dashboard_list")
    payload = workflow.to_dict()

    assert payload["sidecar_route"] == "POST /mcp/dashboards/list"
    assert payload["contract_version"] == "dashboard-list.v1"
    assert list(workflow.serving_flags) == [
        "TS_MCP_ORCHESTRATION",
        "TS_DASHBOARD_LIST_SERVING",
    ]
    assert (
        "runtime_modernization.mcp_orchestration.list_dashboards.shadow_mismatch"
        in workflow.python_metrics
    )
    assert (
        "runtime.v1.requests.routes.POST /mcp/dashboards/list.errorCount"
        in workflow.sidecar_metrics
    )
    assert {gate.name for gate in workflow.gates} == {
        "error_rate",
        "fallback_rate",
        "latency_p95",
        "shadow_mismatch_rate",
    }


def test_rollout_workflow_includes_annotation_layer_list() -> None:
    """Rollout manifest includes annotation layer listing as a TypeScript workflow."""

    workflow = get_rollout_workflow("mcp_annotation_layer_list")

    assert workflow.sidecar_route == "POST /mcp/annotation-layers/list"
    assert workflow.contract_version == "annotation-layer-list.v1"
    assert list(workflow.serving_flags) == [
        "TS_MCP_ORCHESTRATION",
        "TS_ANNOTATION_LAYER_LIST_SERVING",
    ]
    assert (
        "runtime_modernization.mcp_orchestration.list_annotation_layers.shadow_mismatch"
        in workflow.python_metrics
    )


def test_rollout_workflow_includes_layer_annotation_list() -> None:
    """Rollout manifest includes layer annotation listing as a TypeScript workflow."""

    workflow = get_rollout_workflow("mcp_layer_annotation_list")

    assert workflow.sidecar_route == "POST /mcp/annotations/list"
    assert workflow.contract_version == "annotation-list.v1"
    assert list(workflow.serving_flags) == [
        "TS_MCP_ORCHESTRATION",
        "TS_LAYER_ANNOTATION_LIST_SERVING",
    ]
    assert (
        "runtime_modernization.mcp_orchestration.list_layer_annotations.shadow_mismatch"
        in workflow.python_metrics
    )


def test_rollout_workflow_includes_chart_list() -> None:
    """Rollout manifest includes chart listing as a TypeScript workflow."""

    workflow = get_rollout_workflow("mcp_chart_list")

    assert workflow.sidecar_route == "POST /mcp/charts/list"
    assert workflow.contract_version == "chart-list.v1"
    assert list(workflow.serving_flags) == [
        "TS_MCP_ORCHESTRATION",
        "TS_CHART_LIST_SERVING",
    ]
    assert (
        "runtime_modernization.mcp_orchestration.list_charts.shadow_mismatch"
        in workflow.python_metrics
    )


def test_rollout_workflow_includes_dataset_list() -> None:
    """Rollout manifest includes dataset listing as a TypeScript workflow."""

    workflow = get_rollout_workflow("mcp_dataset_list")

    assert workflow.sidecar_route == "POST /mcp/datasets/list"
    assert workflow.contract_version == "dataset-list.v1"
    assert list(workflow.serving_flags) == [
        "TS_MCP_ORCHESTRATION",
        "TS_DATASET_LIST_SERVING",
    ]
    assert (
        "runtime_modernization.mcp_orchestration.list_datasets.shadow_mismatch"
        in workflow.python_metrics
    )


def test_rollout_workflow_includes_database_list() -> None:
    """Rollout manifest includes database listing as a TypeScript workflow."""

    workflow = get_rollout_workflow("mcp_database_list")

    assert workflow.sidecar_route == "POST /mcp/databases/list"
    assert workflow.contract_version == "database-list.v1"
    assert list(workflow.serving_flags) == [
        "TS_MCP_ORCHESTRATION",
        "TS_DATABASE_LIST_SERVING",
    ]
    assert (
        "runtime_modernization.mcp_orchestration.list_databases.shadow_mismatch"
        in workflow.python_metrics
    )


def test_rollout_workflow_includes_saved_query_list() -> None:
    """Rollout manifest includes saved query listing as a TypeScript workflow."""

    workflow = get_rollout_workflow("mcp_saved_query_list")

    assert workflow.sidecar_route == "POST /mcp/saved-queries/list"
    assert workflow.contract_version == "saved-query-list.v1"
    assert list(workflow.serving_flags) == [
        "TS_MCP_ORCHESTRATION",
        "TS_SAVED_QUERY_LIST_SERVING",
    ]
    assert (
        "runtime_modernization.mcp_orchestration.list_saved_queries.shadow_mismatch"
        in workflow.python_metrics
    )


def test_rollout_workflow_includes_tag_list() -> None:
    """Rollout manifest includes tag listing as a TypeScript workflow."""

    workflow = get_rollout_workflow("mcp_tag_list")

    assert workflow.sidecar_route == "POST /mcp/tags/list"
    assert workflow.contract_version == "tag-list.v1"
    assert list(workflow.serving_flags) == [
        "TS_MCP_ORCHESTRATION",
        "TS_TAG_LIST_SERVING",
    ]
    assert (
        "runtime_modernization.mcp_orchestration.list_tags.shadow_mismatch"
        in workflow.python_metrics
    )


def test_rollout_workflow_includes_report_list() -> None:
    """Rollout manifest includes report listing as a TypeScript workflow."""

    workflow = get_rollout_workflow("mcp_report_list")

    assert workflow.sidecar_route == "POST /mcp/reports/list"
    assert workflow.contract_version == "report-list.v1"
    assert list(workflow.serving_flags) == [
        "TS_MCP_ORCHESTRATION",
        "TS_REPORT_LIST_SERVING",
    ]
    assert (
        "runtime_modernization.mcp_orchestration.list_reports.shadow_mismatch"
        in workflow.python_metrics
    )


def test_rollout_workflow_includes_query_list() -> None:
    """Rollout manifest includes query listing as a TypeScript workflow."""

    workflow = get_rollout_workflow("mcp_query_list")

    assert workflow.sidecar_route == "POST /mcp/queries/list"
    assert workflow.contract_version == "query-list.v1"
    assert list(workflow.serving_flags) == [
        "TS_MCP_ORCHESTRATION",
        "TS_QUERY_LIST_SERVING",
    ]
    assert (
        "runtime_modernization.mcp_orchestration.list_queries.shadow_mismatch"
        in workflow.python_metrics
    )


def test_rollout_workflow_includes_role_list() -> None:
    """Rollout manifest includes role listing as a TypeScript workflow."""

    workflow = get_rollout_workflow("mcp_role_list")

    assert workflow.sidecar_route == "POST /mcp/roles/list"
    assert workflow.contract_version == "role-list.v1"
    assert list(workflow.serving_flags) == [
        "TS_MCP_ORCHESTRATION",
        "TS_ROLE_LIST_SERVING",
    ]
    assert (
        "runtime_modernization.mcp_orchestration.list_roles.shadow_mismatch"
        in workflow.python_metrics
    )


def test_rollout_workflow_includes_rls_filter_list() -> None:
    """Rollout manifest includes RLS filter listing as a TypeScript workflow."""

    workflow = get_rollout_workflow("mcp_rls_filter_list")

    assert workflow.sidecar_route == "POST /mcp/rls-filters/list"
    assert workflow.contract_version == "rls-list.v1"
    assert list(workflow.serving_flags) == [
        "TS_MCP_ORCHESTRATION",
        "TS_RLS_FILTER_LIST_SERVING",
    ]
    assert (
        "runtime_modernization.mcp_orchestration.list_rls_filters.shadow_mismatch"
        in workflow.python_metrics
    )


def test_rollout_workflow_includes_task_list() -> None:
    """Rollout manifest includes task listing as a TypeScript workflow."""

    workflow = get_rollout_workflow("mcp_task_list")

    assert workflow.sidecar_route == "POST /mcp/tasks/list"
    assert workflow.contract_version == "task-list.v1"
    assert list(workflow.serving_flags) == [
        "TS_MCP_ORCHESTRATION",
        "TS_TASK_LIST_SERVING",
    ]
    assert (
        "runtime_modernization.mcp_orchestration.list_tasks.shadow_mismatch"
        in workflow.python_metrics
    )


def test_get_rollout_workflow_rejects_unknown_workflow() -> None:
    """Unknown rollout workflow names fail explicitly."""

    with pytest.raises(KeyError, match="Unknown runtime modernization"):
        get_rollout_workflow("missing")


def test_production_evidence_manifest_lists_required_artifacts() -> None:
    """Production evidence manifest names external completion artifacts."""

    workflows = (get_rollout_workflow("mcp_asset_search"),)
    manifest = build_production_evidence_manifest(workflows)

    artifact_names = {artifact["name"] for artifact in manifest["required_artifacts"]}

    assert manifest["schema_version"] == 1
    assert manifest["status"] == "requires_external_evidence"
    assert manifest["minimum_typescript_serving_workflows"] == 2
    assert [workflow["name"] for workflow in manifest["workflows"]] == [
        "mcp_asset_search"
    ]
    assert artifact_names == {
        "compatibility_report",
        "operator_approval",
        "operator_dashboard_snapshot",
        "production_flag_state",
        "rust_kernel_benchmark",
        "rust_kernel_rollout_decision",
    }
    assert len(get_production_evidence_requirements()) == len(artifact_names)


def test_validate_production_evidence_passes_complete_bundle() -> None:
    """Production evidence validation passes complete release evidence."""

    workflows = (
        get_rollout_workflow("mcp_asset_search"),
        get_rollout_workflow("mcp_dashboard_list"),
    )

    validation = validate_production_evidence(
        workflows,
        {
            "schema_version": 1,
            "artifacts": {
                "compatibility_report": {
                    "status": "passed",
                    "target_checks": {
                        "sql_parsing_operations_per_second_met": True,
                        "rust_kernel_speedup_met": None,
                    },
                },
                "rust_kernel_benchmark": _rust_kernel_benchmark(),
                "rust_kernel_rollout_decision": {
                    "kernel": "ax_sql.normalize_sql_whitespace",
                    "decision": "served",
                    "serving_flag": "RUST_SQL_KERNEL",
                    "serving_flag_enabled": True,
                    "decision_reference": "CHG-RUST-1",
                    "rationale": "canary showed acceptable latency and errors",
                },
                "production_flag_state": _production_flag_state(
                    (
                        get_rollout_workflow("mcp_asset_search"),
                        get_rollout_workflow("mcp_dashboard_list"),
                    )
                ),
                "operator_dashboard_snapshot": {
                    "snapshot_reference": "observability/dashboard/snapshot-123",
                    "measurement_window": "2026-06-29T00:00Z/2026-06-29T01:00Z",
                    "service_health": _passing_service_health(),
                    "workflows": {
                        "mcp_asset_search": {
                            "gates": {
                                "shadow_mismatch_rate": {"passed": True},
                                "fallback_rate": {"passed": True},
                                "error_rate": {"passed": True},
                                "latency_p95": {"passed": True},
                            },
                        },
                        "mcp_dashboard_list": {
                            "gates": {
                                "shadow_mismatch_rate": {"passed": True},
                                "fallback_rate": {"passed": True},
                                "error_rate": {"passed": True},
                                "latency_p95": {"passed": True},
                            },
                        },
                    },
                },
                "operator_approval": {
                    "approved": True,
                    "boundary_decision": "split MCP by tool class",
                    "rollout_scope": "asset search and dashboard listing",
                    "migration_decision": "expand",
                    "compatibility_cost_estimate": (
                        "versioned contracts and Python fallback keep compatibility "
                        "risk low"
                    ),
                    "security_cost_estimate": (
                        "Superset remains the authorization authority for extracted "
                        "workflows"
                    ),
                    "approval_reference": "CHG-123",
                    "workflow_names": [
                        "mcp_asset_search",
                        "mcp_dashboard_list",
                    ],
                },
            },
        },
    )

    assert validation["status"] == "passed"
    assert validation["enabled_workflow_names"] == [
        "mcp_asset_search",
        "mcp_dashboard_list",
    ]
    assert validation["dashboard_required_workflow_names"] == [
        "mcp_asset_search",
        "mcp_dashboard_list",
    ]
    assert validation["approved_workflow_names"] == [
        "mcp_asset_search",
        "mcp_dashboard_list",
    ]
    assert all(check["passed"] for check in validation["checks"])


def test_validate_production_evidence_requires_dashboard_for_enabled_workflows() -> (
    None
):
    """Dashboard evidence is scoped to workflows serving production traffic."""

    validation = validate_production_evidence(
        get_rollout_workflows(),
        {
            "schema_version": 1,
            "artifacts": {
                "compatibility_report": {
                    "status": "passed",
                },
                "rust_kernel_benchmark": _rust_kernel_benchmark(),
                "rust_kernel_rollout_decision": {
                    "kernel": "ax_sql.normalize_sql_whitespace",
                    "decision": "rejected",
                    "decision_reference": "PERF-123",
                    "rationale": "benchmark gain did not justify rollout",
                },
                "production_flag_state": _production_flag_state(
                    (
                        get_rollout_workflow("mcp_asset_search"),
                        get_rollout_workflow("mcp_dashboard_list"),
                    )
                ),
                "operator_dashboard_snapshot": {
                    "snapshot_reference": "observability/dashboard/snapshot-123",
                    "measurement_window": "2026-06-29T00:00Z/2026-06-29T01:00Z",
                    "service_health": _passing_service_health(),
                    "workflows": {
                        "mcp_asset_search": {
                            "gates": {
                                "shadow_mismatch_rate": {"passed": True},
                                "fallback_rate": {"passed": True},
                                "error_rate": {"passed": True},
                                "latency_p95": {"passed": True},
                            },
                        },
                        "mcp_dashboard_list": {
                            "gates": {
                                "shadow_mismatch_rate": {"passed": True},
                                "fallback_rate": {"passed": True},
                                "error_rate": {"passed": True},
                                "latency_p95": {"passed": True},
                            },
                        },
                    },
                },
                "operator_approval": {
                    "approved": True,
                    "boundary_decision": "split MCP by tool class",
                    "rollout_scope": "asset search and dashboard listing",
                    "migration_decision": "expand",
                    "compatibility_cost_estimate": (
                        "versioned contracts and Python fallback keep compatibility "
                        "risk low"
                    ),
                    "security_cost_estimate": (
                        "Superset remains the authorization authority for extracted "
                        "workflows"
                    ),
                    "approval_reference": "CHG-123",
                    "workflow_names": [
                        "mcp_asset_search",
                        "mcp_dashboard_list",
                    ],
                },
            },
        },
    )
    checks = {check["name"]: check for check in validation["checks"]}

    assert validation["status"] == "passed"
    assert validation["enabled_workflow_names"] == [
        "mcp_asset_search",
        "mcp_dashboard_list",
    ]
    assert validation["dashboard_required_workflow_names"] == [
        "mcp_asset_search",
        "mcp_dashboard_list",
    ]
    assert checks["production_flag_state"]["passed"] is True
    assert checks["operator_dashboard_snapshot"]["passed"] is True


def test_validate_production_evidence_requires_flag_state_provenance() -> None:
    """Production flag-state evidence must identify the deployment source."""

    validation = validate_production_evidence(
        (
            get_rollout_workflow("mcp_asset_search"),
            get_rollout_workflow("mcp_dashboard_list"),
        ),
        {
            "schema_version": 1,
            "artifacts": {
                "production_flag_state": {
                    "workflows": [
                        {
                            "name": "mcp_asset_search",
                            "serving_flags": {
                                "TS_MCP_ORCHESTRATION": True,
                                "TS_ASSET_SEARCH_SERVING": True,
                            },
                        },
                        {
                            "name": "mcp_dashboard_list",
                            "serving_flags": {
                                "TS_MCP_ORCHESTRATION": True,
                                "TS_DASHBOARD_LIST_SERVING": True,
                            },
                        },
                    ],
                },
            },
        },
    )
    checks = {check["name"]: check for check in validation["checks"]}

    assert validation["status"] == "failed"
    assert checks["production_flag_state"]["passed"] is False
    assert "flag-state reference" in checks["production_flag_state"]["message"]


def test_validate_production_evidence_scopes_dashboards_to_enabled_flags() -> None:
    """Missing flag-state evidence does not mark every workflow dashboard-required."""

    validation = validate_production_evidence(
        (
            get_rollout_workflow("mcp_asset_search"),
            get_rollout_workflow("mcp_dashboard_list"),
        ),
        {
            "schema_version": 1,
            "artifacts": {
                "operator_dashboard_snapshot": {
                    "snapshot_reference": "observability/dashboard/snapshot-123",
                    "measurement_window": "2026-06-29T00:00Z/2026-06-29T01:00Z",
                    "service_health": _passing_service_health(),
                    "workflows": {},
                },
            },
        },
    )
    checks = {check["name"]: check for check in validation["checks"]}

    assert validation["status"] == "failed"
    assert validation["enabled_workflow_names"] == []
    assert validation["dashboard_required_workflow_names"] == []
    assert checks["production_flag_state"]["passed"] is False
    assert checks["operator_dashboard_snapshot"]["passed"] is False


def test_validate_production_evidence_requires_dashboard_service_health() -> None:
    """Operator dashboard evidence must include sidecar service health."""

    workflows = (
        get_rollout_workflow("mcp_asset_search"),
        get_rollout_workflow("mcp_dashboard_list"),
    )
    evidence = _complete_production_evidence()
    artifacts = evidence["artifacts"]
    assert isinstance(artifacts, dict)
    dashboard_snapshot = artifacts["operator_dashboard_snapshot"]
    assert isinstance(dashboard_snapshot, dict)
    dashboard_snapshot.pop("service_health")

    validation = validate_production_evidence(workflows, evidence)
    checks = {check["name"]: check for check in validation["checks"]}

    assert validation["status"] == "failed"
    assert checks["operator_dashboard_snapshot"]["passed"] is False
    assert "service health" in checks["operator_dashboard_snapshot"]["message"]


def test_validate_production_evidence_requires_dashboard_measurement_window() -> None:
    """Operator dashboard evidence must name the measured production window."""

    workflows = (
        get_rollout_workflow("mcp_asset_search"),
        get_rollout_workflow("mcp_dashboard_list"),
    )
    evidence = _complete_production_evidence()
    artifacts = evidence["artifacts"]
    assert isinstance(artifacts, dict)
    dashboard_snapshot = artifacts["operator_dashboard_snapshot"]
    assert isinstance(dashboard_snapshot, dict)
    dashboard_snapshot.pop("measurement_window")

    validation = validate_production_evidence(workflows, evidence)
    checks = {check["name"]: check for check in validation["checks"]}

    assert validation["status"] == "failed"
    assert checks["operator_dashboard_snapshot"]["passed"] is False
    assert "measurement window" in checks["operator_dashboard_snapshot"]["message"]


def test_validate_production_evidence_requires_approval_for_enabled_workflows() -> None:
    """Operator approval must name workflows serving production traffic."""

    validation = validate_production_evidence(
        (
            get_rollout_workflow("mcp_asset_search"),
            get_rollout_workflow("mcp_dashboard_list"),
        ),
        {
            "schema_version": 1,
            "artifacts": {
                "production_flag_state": {
                    "environment": "prod-us",
                    "flag_state_reference": "flags/runtime-modernization/prod-us-123",
                    "workflows": [
                        {
                            "name": "mcp_asset_search",
                            "serving_flags": {
                                "TS_MCP_ORCHESTRATION": True,
                                "TS_ASSET_SEARCH_SERVING": True,
                            },
                        },
                        {
                            "name": "mcp_dashboard_list",
                            "serving_flags": {
                                "TS_MCP_ORCHESTRATION": True,
                                "TS_DASHBOARD_LIST_SERVING": True,
                            },
                        },
                    ],
                },
                "operator_approval": {
                    "approved": True,
                    "boundary_decision": "split MCP by tool class",
                    "rollout_scope": "asset search only",
                    "migration_decision": "expand",
                    "compatibility_cost_estimate": (
                        "versioned contracts and Python fallback keep compatibility "
                        "risk low"
                    ),
                    "security_cost_estimate": (
                        "Superset remains the authorization authority for extracted "
                        "workflows"
                    ),
                    "approval_reference": "CHG-123",
                    "workflow_names": ["mcp_asset_search"],
                },
            },
        },
    )
    checks = {check["name"]: check for check in validation["checks"]}

    assert validation["status"] == "failed"
    assert checks["operator_approval"]["passed"] is False
    assert "exact enabled workflow names" in checks["operator_approval"]["message"]


def test_validate_production_evidence_rejects_extra_approved_workflows() -> None:
    """Operator approval must not name workflows outside the enabled scope."""

    workflows = (
        get_rollout_workflow("mcp_asset_search"),
        get_rollout_workflow("mcp_dashboard_list"),
        get_rollout_workflow("mcp_chart_list"),
    )
    evidence = _complete_production_evidence()
    artifacts = evidence["artifacts"]
    assert isinstance(artifacts, dict)
    operator_approval = artifacts["operator_approval"]
    assert isinstance(operator_approval, dict)
    operator_approval["workflow_names"] = [
        "mcp_asset_search",
        "mcp_chart_list",
        "mcp_dashboard_list",
    ]

    validation = validate_production_evidence(workflows, evidence)
    checks = {check["name"]: check for check in validation["checks"]}

    assert validation["status"] == "failed"
    assert validation["enabled_workflow_names"] == [
        "mcp_asset_search",
        "mcp_dashboard_list",
    ]
    assert validation["approved_workflow_names"] == [
        "mcp_asset_search",
        "mcp_chart_list",
        "mcp_dashboard_list",
    ]
    assert checks["operator_approval"]["passed"] is False
    assert "exact enabled workflow names" in checks["operator_approval"]["message"]


def test_validate_production_evidence_requires_operator_cost_estimates() -> None:
    """Operator approval must include Phase 6 compatibility and security costs."""

    validation = validate_production_evidence(
        (get_rollout_workflow("mcp_asset_search"),),
        {
            "schema_version": 1,
            "artifacts": {
                "operator_approval": {
                    "approved": True,
                    "boundary_decision": "split MCP by tool class",
                    "rollout_scope": "asset search",
                    "approval_reference": "CHG-123",
                    "workflow_names": ["mcp_asset_search"],
                },
            },
        },
    )
    checks = {check["name"]: check for check in validation["checks"]}

    assert validation["status"] == "failed"
    assert checks["operator_approval"]["passed"] is False
    assert (
        "compatibility or security cost estimates"
        in checks["operator_approval"]["message"]
    )


def test_validate_production_evidence_requires_valid_migration_decision() -> None:
    """Operator approval must choose expand, pause, or stop migration."""

    validation = validate_production_evidence(
        (get_rollout_workflow("mcp_asset_search"),),
        {
            "schema_version": 1,
            "artifacts": {
                "operator_approval": {
                    "approved": True,
                    "boundary_decision": "split MCP by tool class",
                    "rollout_scope": "asset search",
                    "migration_decision": "continue",
                    "compatibility_cost_estimate": (
                        "versioned contracts and Python fallback keep compatibility "
                        "risk low"
                    ),
                    "security_cost_estimate": (
                        "Superset remains the authorization authority for extracted "
                        "workflows"
                    ),
                    "approval_reference": "CHG-123",
                    "workflow_names": ["mcp_asset_search"],
                },
            },
        },
    )
    checks = {check["name"]: check for check in validation["checks"]}

    assert validation["status"] == "failed"
    assert checks["operator_approval"]["passed"] is False
    assert "migration decision" in checks["operator_approval"]["message"]


def test_build_production_evidence_template_includes_workflow_gates() -> None:
    """Production evidence template includes fillable workflow-specific fields."""

    template = build_production_evidence_template(
        (
            get_rollout_workflow("mcp_asset_search"),
            get_rollout_workflow("mcp_dashboard_list"),
        )
    )

    flag_workflows = template["artifacts"]["production_flag_state"]["workflows"]
    dashboard_snapshot = template["artifacts"]["operator_dashboard_snapshot"]
    dashboard_workflows = dashboard_snapshot["workflows"]

    assert template["schema_version"] == 1
    assert template["artifacts"]["production_flag_state"]["environment"] == ""
    assert template["artifacts"]["production_flag_state"]["flag_state_reference"] == ""
    assert flag_workflows == [
        {
            "name": "mcp_asset_search",
            "serving_flags": {
                "TS_MCP_ORCHESTRATION": False,
                "TS_ASSET_SEARCH_SERVING": False,
            },
        },
        {
            "name": "mcp_dashboard_list",
            "serving_flags": {
                "TS_MCP_ORCHESTRATION": False,
                "TS_DASHBOARD_LIST_SERVING": False,
            },
        },
    ]
    assert (
        dashboard_workflows["mcp_asset_search"]["gates"]["shadow_mismatch_rate"][
            "target"
        ]
        == "0 mismatches during the evaluation window"
    )
    assert template["artifacts"]["rust_kernel_benchmark"] == {
        "schema_version": 1,
        "status": "passed",
        "kernel": "sql_whitespace_kernel",
        "iterations": 0,
        "output_matched": True,
        "target_checks": {
            "speedup_met": None,
        },
    }
    assert template["artifacts"]["rust_kernel_rollout_decision"] == {
        "kernel": "ax_sql.normalize_sql_whitespace",
        "decision": "",
        "serving_flag": "RUST_SQL_KERNEL",
        "serving_flag_enabled": False,
        "decision_reference": "",
        "rationale": "",
    }
    assert dashboard_snapshot["snapshot_reference"] == ""
    assert dashboard_snapshot["measurement_window"] == ""
    assert dashboard_snapshot["service_health"] == {
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
    }
    assert template["artifacts"]["operator_approval"] == {
        "approved": False,
        "boundary_decision": "",
        "rollout_scope": "",
        "migration_decision": "",
        "compatibility_cost_estimate": "",
        "security_cost_estimate": "",
        "approval_reference": "",
        "workflow_names": [],
    }


def test_build_production_flag_state_reads_workflow_serving_flags() -> None:
    """Production flag-state evidence includes selected workflow serving flags."""

    enabled_flags = {"TS_MCP_ORCHESTRATION", "TS_ASSET_SEARCH_SERVING"}

    flag_state = build_production_flag_state(
        (
            get_rollout_workflow("mcp_asset_search"),
            get_rollout_workflow("mcp_dashboard_list"),
        ),
        lambda flag: flag in enabled_flags,
        environment="prod-us",
        flag_state_reference="flags/runtime-modernization/prod-us-123",
    )

    assert flag_state == {
        "environment": "prod-us",
        "flag_state_reference": "flags/runtime-modernization/prod-us-123",
        "workflows": [
            {
                "name": "mcp_asset_search",
                "serving_flags": {
                    "TS_MCP_ORCHESTRATION": True,
                    "TS_ASSET_SEARCH_SERVING": True,
                },
            },
            {
                "name": "mcp_dashboard_list",
                "serving_flags": {
                    "TS_MCP_ORCHESTRATION": True,
                    "TS_DASHBOARD_LIST_SERVING": False,
                },
            },
        ],
    }


def test_build_production_flag_state_requires_workflow_scope() -> None:
    """Production flag-state evidence must identify the scoped workflows."""

    with pytest.raises(ValueError, match="at least one workflow"):
        build_production_flag_state(
            (),
            lambda flag: flag == "TS_MCP_ORCHESTRATION",
            environment="prod-us",
            flag_state_reference="flags/runtime-modernization/prod-us-123",
        )


def test_build_production_flag_state_requires_provenance() -> None:
    """Production flag-state evidence must name environment and source."""

    with pytest.raises(ValueError, match="flag_state_reference"):
        build_production_flag_state(
            (get_rollout_workflow("mcp_asset_search"),),
            lambda flag: flag == "TS_MCP_ORCHESTRATION",
            environment="prod-us",
            flag_state_reference="",
        )


def test_build_operator_approval_evidence_includes_required_fields() -> None:
    """Operator approval evidence includes the fields validation requires."""

    approval = build_operator_approval_evidence(
        boundary_decision="split MCP by tool class",
        rollout_scope="asset search and dashboard listing",
        migration_decision="expand",
        compatibility_cost_estimate=(
            "versioned contracts and Python fallback keep compatibility risk low"
        ),
        security_cost_estimate=(
            "Superset remains the authorization authority for extracted workflows"
        ),
        approval_reference="CHG-123",
        workflow_names=("mcp_asset_search", "mcp_dashboard_list"),
        approver="platform-ops",
        notes="approved after canary review",
    )

    assert approval == {
        "approved": True,
        "boundary_decision": "split MCP by tool class",
        "rollout_scope": "asset search and dashboard listing",
        "migration_decision": "expand",
        "compatibility_cost_estimate": (
            "versioned contracts and Python fallback keep compatibility risk low"
        ),
        "security_cost_estimate": (
            "Superset remains the authorization authority for extracted workflows"
        ),
        "approval_reference": "CHG-123",
        "workflow_names": ["mcp_asset_search", "mcp_dashboard_list"],
        "approver": "platform-ops",
        "notes": "approved after canary review",
    }


def test_build_operator_approval_evidence_requires_approved_workflows() -> None:
    """Approved operator evidence must name the production-serving workflows."""

    with pytest.raises(ValueError, match="at least one workflow"):
        build_operator_approval_evidence(
            boundary_decision="split MCP by tool class",
            rollout_scope="asset search and dashboard listing",
            migration_decision="expand",
            compatibility_cost_estimate=(
                "versioned contracts and Python fallback keep compatibility risk low"
            ),
            security_cost_estimate=(
                "Superset remains the authorization authority for extracted workflows"
            ),
            approval_reference="CHG-123",
            workflow_names=(),
        )


def test_build_operator_approval_evidence_allows_empty_rejection_scope() -> None:
    """Rejected operator evidence may omit workflows because none are approved."""

    approval = build_operator_approval_evidence(
        boundary_decision="split MCP by tool class",
        rollout_scope="no production rollout",
        migration_decision="stop",
        compatibility_cost_estimate="compatibility cost exceeds release scope",
        security_cost_estimate="security review requires redesign",
        approval_reference="CHG-123",
        workflow_names=(),
        approved=False,
    )

    assert approval["approved"] is False
    assert approval["workflow_names"] == []


def test_build_operator_approval_evidence_requires_valid_migration_decision() -> None:
    """Approved operator evidence must carry a supported migration decision."""

    with pytest.raises(ValueError, match="migration_decision"):
        build_operator_approval_evidence(
            boundary_decision="split MCP by tool class",
            rollout_scope="asset search and dashboard listing",
            migration_decision="retry",
            compatibility_cost_estimate=(
                "versioned contracts and Python fallback keep compatibility risk low"
            ),
            security_cost_estimate=(
                "Superset remains the authorization authority for extracted workflows"
            ),
            approval_reference="CHG-123",
            workflow_names=("mcp_asset_search",),
        )


def test_build_operator_approval_evidence_requires_cost_estimates() -> None:
    """Approved operator evidence must document compatibility and security cost."""

    with pytest.raises(ValueError, match="compatibility_cost_estimate"):
        build_operator_approval_evidence(
            boundary_decision="split MCP by tool class",
            rollout_scope="asset search and dashboard listing",
            migration_decision="expand",
            compatibility_cost_estimate="",
            security_cost_estimate=(
                "Superset remains the authorization authority for extracted workflows"
            ),
            approval_reference="CHG-123",
            workflow_names=("mcp_asset_search",),
        )


def test_build_rust_kernel_rollout_decision_includes_required_fields() -> None:
    """Rust rollout decision evidence includes Phase 5 validation fields."""

    decision = build_rust_kernel_rollout_decision(
        kernel="ax_sql.normalize_sql_whitespace",
        decision="rejected",
        decision_reference="PERF-123",
        rationale="benchmark gain did not justify rollout",
    )

    assert decision == {
        "kernel": "ax_sql.normalize_sql_whitespace",
        "decision": "rejected",
        "serving_flag": "RUST_SQL_KERNEL",
        "decision_reference": "PERF-123",
        "rationale": "benchmark gain did not justify rollout",
    }


def test_build_rust_kernel_rollout_decision_requires_supported_decision() -> None:
    """Rust rollout evidence only accepts the decisions validation understands."""

    with pytest.raises(ValueError, match="must be 'served' or 'rejected'"):
        build_rust_kernel_rollout_decision(
            kernel="ax_sql.normalize_sql_whitespace",
            decision="paused",
            decision_reference="PERF-123",
            rationale="benchmark gain requires another canary",
        )


def test_build_rust_kernel_rollout_decision_requires_enabled_serving_flag() -> None:
    """Served Rust decisions must prove the feature flag served traffic."""

    with pytest.raises(ValueError, match="serving_flag_enabled=True"):
        build_rust_kernel_rollout_decision(
            kernel="ax_sql.normalize_sql_whitespace",
            decision="served",
            decision_reference="PERF-123",
            rationale="benchmark gain justified rollout",
        )


def test_build_rust_kernel_rollout_decision_records_served_flag() -> None:
    """Valid served Rust decisions include serving flag evidence."""

    decision = build_rust_kernel_rollout_decision(
        kernel="ax_sql.normalize_sql_whitespace",
        decision="served",
        decision_reference="PERF-123",
        rationale="benchmark gain justified rollout",
        serving_flag_enabled=True,
    )

    assert decision["decision"] == "served"
    assert decision["serving_flag_enabled"] is True


def test_build_rust_kernel_rollout_decision_requires_provenance() -> None:
    """Rust rollout evidence must name the kernel, reference, flag, and rationale."""

    with pytest.raises(ValueError, match="decision_reference"):
        build_rust_kernel_rollout_decision(
            kernel="ax_sql.normalize_sql_whitespace",
            decision="rejected",
            decision_reference="",
            rationale="benchmark gain did not justify rollout",
        )


def test_build_rust_kernel_rollout_decision_template_is_incomplete() -> None:
    """Rust rollout decision templates are fillable but do not pass validation."""

    template = build_rust_kernel_rollout_decision_template()

    assert template == {
        "kernel": "ax_sql.normalize_sql_whitespace",
        "decision": "",
        "serving_flag": "RUST_SQL_KERNEL",
        "serving_flag_enabled": False,
        "decision_reference": "",
        "rationale": "",
    }


def test_build_operator_dashboard_snapshot_includes_workflow_gates() -> None:
    """Operator dashboard evidence includes gate status for selected workflows."""

    snapshot = build_operator_dashboard_snapshot(
        (get_rollout_workflow("mcp_asset_search"),),
        snapshot_reference="observability/dashboard/snapshot-123",
        gates_passed=True,
        service_health_passed=True,
        measurement_window="2026-06-29T00:00Z/2026-06-29T01:00Z",
        notes="canary window passed",
    )

    gates = snapshot["workflows"]["mcp_asset_search"]["gates"]
    service_health = snapshot["service_health"]

    assert snapshot["snapshot_reference"] == "observability/dashboard/snapshot-123"
    assert snapshot["measurement_window"] == "2026-06-29T00:00Z/2026-06-29T01:00Z"
    assert snapshot["notes"] == "canary window passed"
    assert service_health["health_check"]["passed"] is True
    assert service_health["readiness_check"]["passed"] is True
    assert set(gates) == {
        "error_rate",
        "fallback_rate",
        "latency_p95",
        "shadow_mismatch_rate",
    }
    assert all(gate["passed"] is True for gate in gates.values())
    assert gates["fallback_rate"]["metric"].endswith(".fallback")


def test_build_operator_dashboard_snapshot_requires_workflow_scope() -> None:
    """Operator dashboard evidence must identify the scoped workflows."""

    with pytest.raises(ValueError, match="at least one workflow"):
        build_operator_dashboard_snapshot(
            (),
            snapshot_reference="observability/dashboard/snapshot-123",
            gates_passed=True,
            service_health_passed=True,
            measurement_window="2026-06-29T00:00Z/2026-06-29T01:00Z",
        )


def test_build_operator_dashboard_snapshot_requires_measurement_window() -> None:
    """Operator dashboard evidence must identify the production window."""

    with pytest.raises(ValueError, match="measurement_window"):
        build_operator_dashboard_snapshot(
            (get_rollout_workflow("mcp_asset_search"),),
            snapshot_reference="observability/dashboard/snapshot-123",
            gates_passed=True,
            service_health_passed=True,
        )


def test_build_operator_dashboard_snapshot_allows_gate_overrides() -> None:
    """Operator dashboard evidence can mark individual gates separately."""

    snapshot = build_operator_dashboard_snapshot(
        (get_rollout_workflow("mcp_asset_search"),),
        snapshot_reference="observability/dashboard/snapshot-123",
        gates_passed=True,
        service_health_passed=True,
        measurement_window="2026-06-29T00:00Z/2026-06-29T01:00Z",
        gate_statuses={"latency_p95": False},
    )

    gates = snapshot["workflows"]["mcp_asset_search"]["gates"]

    assert gates["latency_p95"]["passed"] is False
    assert gates["error_rate"]["passed"] is True


def test_build_operator_dashboard_snapshot_allows_workflow_gate_overrides() -> None:
    """Operator dashboard evidence can mark gates per workflow."""

    snapshot = build_operator_dashboard_snapshot(
        (
            get_rollout_workflow("mcp_asset_search"),
            get_rollout_workflow("mcp_dashboard_list"),
        ),
        snapshot_reference="observability/dashboard/snapshot-123",
        gates_passed=True,
        service_health_passed=True,
        measurement_window="2026-06-29T00:00Z/2026-06-29T01:00Z",
        workflow_gate_statuses={"mcp_dashboard_list": {"latency_p95": False}},
    )

    workflows = snapshot["workflows"]

    assert workflows["mcp_asset_search"]["gates"]["latency_p95"]["passed"] is True
    assert workflows["mcp_dashboard_list"]["gates"]["latency_p95"]["passed"] is False


def test_build_production_evidence_bundle_includes_supplied_artifacts() -> None:
    """Production evidence bundle preserves collected artifact payloads."""

    bundle = build_production_evidence_bundle(
        compatibility_report={
            "status": "passed",
        },
        rust_kernel_benchmark={
            "status": "passed",
            "output_matched": True,
        },
        rust_kernel_rollout_decision={
            "kernel": "ax_sql.normalize_sql_whitespace",
            "decision": "rejected",
            "decision_reference": "PERF-123",
            "rationale": "benchmark gain did not justify rollout",
        },
        production_flag_state={
            "workflows": [],
        },
    )

    assert bundle == {
        "schema_version": 1,
        "artifacts": {
            "compatibility_report": {
                "status": "passed",
            },
            "rust_kernel_benchmark": {
                "status": "passed",
                "output_matched": True,
            },
            "rust_kernel_rollout_decision": {
                "kernel": "ax_sql.normalize_sql_whitespace",
                "decision": "rejected",
                "decision_reference": "PERF-123",
                "rationale": "benchmark gain did not justify rollout",
            },
            "production_flag_state": {
                "workflows": [],
            },
        },
    }


def test_validate_production_evidence_fails_incomplete_bundle() -> None:
    """Production evidence validation identifies missing external artifacts."""

    validation = validate_production_evidence(
        (get_rollout_workflow("mcp_asset_search"),),
        {
            "schema_version": 1,
            "artifacts": {
                "compatibility_report": {
                    "status": "failed",
                    "target_checks": {
                        "sql_parsing_operations_per_second_met": False,
                    },
                },
            },
        },
    )

    checks = {check["name"]: check for check in validation["checks"]}

    assert validation["status"] == "failed"
    assert validation["enabled_workflow_names"] == []
    assert validation["dashboard_required_workflow_names"] == []
    assert checks["compatibility_report"]["passed"] is False
    assert checks["rust_kernel_benchmark"]["passed"] is False
    assert checks["rust_kernel_rollout_decision"]["passed"] is False
    assert checks["production_flag_state"]["passed"] is False


def test_validate_production_evidence_requires_rust_benchmark_identity() -> None:
    """Rust benchmark evidence must name the benchmarked kernel and iterations."""

    validation = validate_production_evidence(
        (get_rollout_workflow("mcp_asset_search"),),
        {
            "schema_version": 1,
            "artifacts": {
                "rust_kernel_benchmark": {
                    "status": "passed",
                    "output_matched": True,
                },
            },
        },
    )
    checks = {check["name"]: check for check in validation["checks"]}

    assert validation["status"] == "failed"
    assert checks["rust_kernel_benchmark"]["passed"] is False
    assert "malformed" in checks["rust_kernel_benchmark"]["message"]


def test_validate_production_evidence_requires_supported_bundle_schema() -> None:
    """Production evidence validation rejects unsupported bundle schema versions."""

    validation = validate_production_evidence(
        (get_rollout_workflow("mcp_asset_search"),),
        {
            "schema_version": 2,
            "artifacts": {},
        },
    )
    checks = {check["name"]: check for check in validation["checks"]}

    assert validation["status"] == "failed"
    assert checks["evidence_bundle"]["passed"] is False
    assert "schema_version 1" in checks["evidence_bundle"]["message"]


def test_validate_production_evidence_requires_object_artifacts() -> None:
    """Production evidence validation rejects malformed artifact containers."""

    validation = validate_production_evidence(
        (get_rollout_workflow("mcp_asset_search"),),
        {
            "schema_version": 1,
            "artifacts": [],
        },
    )
    checks = {check["name"]: check for check in validation["checks"]}

    assert validation["status"] == "failed"
    assert checks["evidence_bundle"]["passed"] is False
    assert "object-shaped artifacts" in checks["evidence_bundle"]["message"]


def test_validate_production_evidence_rejects_unserved_rust_decision() -> None:
    """A served Rust decision must prove the production serving flag is enabled."""

    validation = validate_production_evidence(
        (get_rollout_workflow("mcp_asset_search"),),
        {
            "schema_version": 1,
            "artifacts": {
                "rust_kernel_rollout_decision": {
                    "kernel": "ax_sql.normalize_sql_whitespace",
                    "decision": "served",
                    "serving_flag": "RUST_SQL_KERNEL",
                    "serving_flag_enabled": False,
                    "decision_reference": "CHG-RUST-1",
                    "rationale": "planned rollout",
                },
            },
        },
    )
    checks = {check["name"]: check for check in validation["checks"]}

    assert validation["status"] == "failed"
    assert checks["rust_kernel_rollout_decision"]["passed"] is False


def test_audit_runtime_modernization_completion_reports_missing_evidence() -> None:
    """Phase completion audit identifies production evidence gaps."""

    audit = audit_runtime_modernization_completion(
        (get_rollout_workflow("mcp_asset_search"),),
        {"schema_version": 1, "artifacts": {}},
    )
    phase_checks = {check["name"]: check for check in audit["phase_checks"]}

    assert audit["status"] == "incomplete"
    assert phase_checks["phase_0_baseline"]["passed"] is True
    assert phase_checks["phase_2_typescript_foundation"]["passed"] is True
    assert phase_checks["phase_5_selective_runtime_split"]["passed"] is False
    assert audit["evidence_validation"]["status"] == "failed"


def test_audit_runtime_modernization_completion_passes_complete_evidence() -> None:
    """Phase completion audit passes when all required evidence is present."""

    workflows = (
        get_rollout_workflow("mcp_asset_search"),
        get_rollout_workflow("mcp_dashboard_list"),
    )

    audit = audit_runtime_modernization_completion(
        workflows,
        _complete_production_evidence(),
    )

    assert audit["status"] == "complete"
    assert audit["workflow_names"] == ["mcp_asset_search", "mcp_dashboard_list"]
    assert all(check["passed"] for check in audit["phase_checks"])
    assert audit["evidence_validation"]["status"] == "passed"

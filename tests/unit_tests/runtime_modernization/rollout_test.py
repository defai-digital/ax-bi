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
    get_production_evidence_requirements,
    get_rollout_workflow,
    get_rollout_workflows,
    validate_production_evidence,
)


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
                            flag: True for flag in workflow.serving_flags
                        },
                    }
                    for workflow in workflows
                ],
            },
            "operator_dashboard_snapshot": {
                "snapshot_reference": "observability/dashboard/snapshot-123",
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
                "approval_reference": "CHG-123",
            },
        },
    }


def test_rollout_workflows_cover_migrated_mcp_paths() -> None:
    """Rollout manifest includes the TypeScript-routed MCP workflows."""

    workflows = get_rollout_workflows()
    names = {workflow.name for workflow in workflows}

    assert names == {
        "mcp_asset_search",
        "mcp_chart_list",
        "mcp_dashboard_list",
        "mcp_database_list",
        "mcp_dataset_list",
        "mcp_health_check",
        "mcp_saved_query_list",
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
        "shadow_mismatch_rate",
    }


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
                "operator_dashboard_snapshot": {
                    "snapshot_reference": "observability/dashboard/snapshot-123",
                    "workflows": {
                        "mcp_asset_search": {
                            "gates": {
                                "shadow_mismatch_rate": {"passed": True},
                                "fallback_rate": {"passed": True},
                                "error_rate": {"passed": True},
                            },
                        },
                        "mcp_dashboard_list": {
                            "gates": {
                                "shadow_mismatch_rate": {"passed": True},
                                "fallback_rate": {"passed": True},
                                "error_rate": {"passed": True},
                            },
                        },
                    },
                },
                "operator_approval": {
                    "approved": True,
                    "boundary_decision": "split MCP by tool class",
                    "rollout_scope": "asset search and dashboard listing",
                    "approval_reference": "CHG-123",
                },
            },
        },
    )

    assert validation["status"] == "passed"
    assert all(check["passed"] for check in validation["checks"])


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
    assert dashboard_snapshot["snapshot_reference"] == ""
    assert template["artifacts"]["operator_approval"] == {
        "approved": False,
        "boundary_decision": "",
        "rollout_scope": "",
        "approval_reference": "",
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
    )

    assert flag_state == {
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


def test_build_operator_approval_evidence_includes_required_fields() -> None:
    """Operator approval evidence includes the fields validation requires."""

    approval = build_operator_approval_evidence(
        boundary_decision="split MCP by tool class",
        rollout_scope="asset search and dashboard listing",
        approval_reference="CHG-123",
        approver="platform-ops",
        notes="approved after canary review",
    )

    assert approval == {
        "approved": True,
        "boundary_decision": "split MCP by tool class",
        "rollout_scope": "asset search and dashboard listing",
        "approval_reference": "CHG-123",
        "approver": "platform-ops",
        "notes": "approved after canary review",
    }


def test_build_operator_dashboard_snapshot_includes_workflow_gates() -> None:
    """Operator dashboard evidence includes gate status for selected workflows."""

    snapshot = build_operator_dashboard_snapshot(
        (get_rollout_workflow("mcp_asset_search"),),
        snapshot_reference="observability/dashboard/snapshot-123",
        gates_passed=True,
        measurement_window="2026-06-29T00:00Z/2026-06-29T01:00Z",
        notes="canary window passed",
    )

    gates = snapshot["workflows"]["mcp_asset_search"]["gates"]

    assert snapshot["snapshot_reference"] == "observability/dashboard/snapshot-123"
    assert snapshot["measurement_window"] == "2026-06-29T00:00Z/2026-06-29T01:00Z"
    assert snapshot["notes"] == "canary window passed"
    assert set(gates) == {
        "error_rate",
        "fallback_rate",
        "shadow_mismatch_rate",
    }
    assert all(gate["passed"] is True for gate in gates.values())
    assert gates["fallback_rate"]["metric"].endswith(".fallback")


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
    assert checks["compatibility_report"]["passed"] is False
    assert checks["rust_kernel_benchmark"]["passed"] is False
    assert checks["production_flag_state"]["passed"] is False


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

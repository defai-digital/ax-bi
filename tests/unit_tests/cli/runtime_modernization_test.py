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
from pathlib import Path

from click.testing import CliRunner
from flask import current_app
from pytest_mock import MockerFixture

from superset.cli.runtime_modernization import runtime_modernization
from superset.runtime_modernization.ax_services import AxServicesResponse
from superset.runtime_modernization.benchmarks import (
    RuntimeBenchmarkResult,
    RuntimeKernelBenchmarkResult,
)
from superset.utils import json


def _write_complete_runtime_evidence(tmp_path: Path) -> Path:
    """Write a complete production evidence bundle for CLI tests."""

    evidence_file = tmp_path / "runtime-evidence.json"
    evidence_file.write_text(
        json.dumps(
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
                    "rust_kernel_rollout_decision": {
                        "kernel": "ax_sql.normalize_sql_whitespace",
                        "decision": "rejected",
                        "serving_flag": "RUST_SQL_KERNEL",
                        "serving_flag_enabled": False,
                        "decision_reference": "PERF-123",
                        "rationale": "benchmark gain did not justify rollout",
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
                                    "shadow_mismatch_rate": True,
                                    "fallback_rate": True,
                                    "error_rate": True,
                                    "latency_p95": True,
                                },
                            },
                            "mcp_dashboard_list": {
                                "gates": {
                                    "shadow_mismatch_rate": True,
                                    "fallback_rate": True,
                                    "error_rate": True,
                                    "latency_p95": True,
                                },
                            },
                        },
                    },
                    "operator_approval": {
                        "approved": True,
                        "boundary_decision": "split MCP by tool class",
                        "rollout_scope": "asset search and dashboard listing",
                        "approval_reference": "CHG-123",
                        "workflow_names": [
                            "mcp_asset_search",
                            "mcp_dashboard_list",
                        ],
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    return evidence_file


def test_runtime_modernization_inventory_outputs_table() -> None:
    """Inventory command prints a human-readable candidate matrix."""

    result = CliRunner().invoke(runtime_modernization, ["inventory"])

    assert result.exit_code == 0
    assert "area" in result.output
    assert "mcp_orchestration" in result.output
    assert "typescript" in result.output
    assert "sql_parsing_normalization" in result.output
    assert "rust" in result.output


def test_runtime_modernization_inventory_outputs_json() -> None:
    """Inventory command prints stable JSON for automation."""

    result = CliRunner().invoke(
        runtime_modernization,
        ["inventory", "--format", "json", "--disposition", "candidate"],
    )

    assert result.exit_code == 0

    payload = json.loads(result.output)
    areas = {item["area"] for item in payload}

    assert "mcp_orchestration" in areas
    assert "auth_rbac_security" not in areas
    assert all(item["disposition"] == "candidate" for item in payload)


def test_runtime_modernization_rollout_manifest_outputs_json() -> None:
    """Rollout manifest emits stable JSON for operator dashboard wiring."""

    result = CliRunner().invoke(
        runtime_modernization,
        ["rollout-manifest", "--workflow", "mcp_dashboard_list"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["schema_version"] == 1
    assert len(payload["workflows"]) == 1
    workflow = payload["workflows"][0]
    assert workflow["name"] == "mcp_dashboard_list"
    assert workflow["sidecar_route"] == "POST /mcp/dashboards/list"
    assert workflow["contract_version"] == "dashboard-list.v1"
    assert workflow["serving_flags"] == [
        "TS_MCP_ORCHESTRATION",
        "TS_DASHBOARD_LIST_SERVING",
    ]
    assert (
        "runtime_modernization.mcp_orchestration.list_dashboards.fallback"
        in workflow["python_metrics"]
    )


def test_runtime_modernization_rollout_manifest_outputs_text() -> None:
    """Rollout manifest has a compact human-readable mode."""

    result = CliRunner().invoke(
        runtime_modernization,
        ["rollout-manifest", "--workflow", "mcp_dataset_list", "--format", "text"],
    )

    assert result.exit_code == 0
    assert "mcp_dataset_list: POST /mcp/datasets/list" in result.output
    assert "TS_DATASET_LIST_SERVING" in result.output
    assert "mcp_database_list: POST /mcp/databases/list" not in result.output
    assert "shadow_mismatch_rate" in result.output


def test_runtime_modernization_rollout_manifest_outputs_database_list_text() -> None:
    """Rollout manifest text mode includes database listing when selected."""

    result = CliRunner().invoke(
        runtime_modernization,
        ["rollout-manifest", "--workflow", "mcp_database_list", "--format", "text"],
    )

    assert result.exit_code == 0
    assert "mcp_database_list: POST /mcp/databases/list" in result.output
    assert "TS_DATABASE_LIST_SERVING" in result.output


def test_runtime_modernization_rollout_manifest_rejects_unknown_workflow() -> None:
    """Rollout manifest fails on unknown workflow names."""

    result = CliRunner().invoke(
        runtime_modernization,
        ["rollout-manifest", "--workflow", "missing"],
    )

    assert result.exit_code != 0
    assert "Unknown runtime modernization rollout workflow" in result.output


def test_runtime_modernization_production_evidence_outputs_json() -> None:
    """Production evidence command emits stable JSON for external rollout proof."""

    result = CliRunner().invoke(
        runtime_modernization,
        ["production-evidence", "--workflow", "mcp_asset_search"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["schema_version"] == 1
    assert payload["status"] == "requires_external_evidence"
    assert payload["minimum_typescript_serving_workflows"] == 2
    assert [workflow["name"] for workflow in payload["workflows"]] == [
        "mcp_asset_search"
    ]
    assert {artifact["name"] for artifact in payload["required_artifacts"]} == {
        "compatibility_report",
        "operator_approval",
        "operator_dashboard_snapshot",
        "production_flag_state",
        "rust_kernel_benchmark",
        "rust_kernel_rollout_decision",
    }


def test_runtime_modernization_production_evidence_outputs_text() -> None:
    """Production evidence command has a compact operator-facing mode."""

    result = CliRunner().invoke(
        runtime_modernization,
        ["production-evidence", "--workflow", "mcp_dashboard_list", "--format", "text"],
    )

    assert result.exit_code == 0
    assert "runtime modernization production evidence" in result.output
    assert "mcp_dashboard_list: POST /mcp/dashboards/list" in result.output
    assert "operator_dashboard_snapshot" in result.output


def test_runtime_modernization_production_evidence_rejects_unknown_workflow() -> None:
    """Production evidence command fails on unknown workflow names."""

    result = CliRunner().invoke(
        runtime_modernization,
        ["production-evidence", "--workflow", "missing"],
    )

    assert result.exit_code != 0
    assert "Unknown runtime modernization rollout workflow" in result.output


def test_runtime_modernization_production_evidence_template_outputs_json() -> None:
    """Production evidence template command emits a fillable JSON bundle."""

    result = CliRunner().invoke(
        runtime_modernization,
        [
            "production-evidence-template",
            "--workflow",
            "mcp_asset_search",
            "--workflow",
            "mcp_dashboard_list",
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["schema_version"] == 1
    assert payload["artifacts"]["production_flag_state"]["workflows"] == [
        {
            "name": "mcp_asset_search",
            "serving_flags": {
                "TS_ASSET_SEARCH_SERVING": False,
                "TS_MCP_ORCHESTRATION": False,
            },
        },
        {
            "name": "mcp_dashboard_list",
            "serving_flags": {
                "TS_DASHBOARD_LIST_SERVING": False,
                "TS_MCP_ORCHESTRATION": False,
            },
        },
    ]
    assert "operator_dashboard_snapshot" in payload["artifacts"]
    assert "rust_kernel_rollout_decision" in payload["artifacts"]
    assert payload["artifacts"]["operator_approval"]["approved"] is False
    assert payload["artifacts"]["operator_approval"]["workflow_names"] == []


def test_runtime_modernization_production_evidence_template_outputs_text() -> None:
    """Production evidence template command has a compact text mode."""

    result = CliRunner().invoke(
        runtime_modernization,
        [
            "production-evidence-template",
            "--workflow",
            "mcp_asset_search",
            "--format",
            "text",
        ],
    )

    assert result.exit_code == 0
    assert "runtime modernization production evidence template" in result.output
    assert "workflows: mcp_asset_search" in result.output
    assert "operator_approval" in result.output


def test_runtime_modernization_production_flag_state_outputs_json(
    mocker: MockerFixture,
    app_context: None,
) -> None:
    """Production flag-state command emits selected workflow serving flags."""

    mocker.patch(
        "superset.cli.runtime_modernization.is_feature_enabled",
        side_effect=lambda flag: flag
        in {"TS_MCP_ORCHESTRATION", "TS_ASSET_SEARCH_SERVING"},
    )

    result = CliRunner().invoke(
        runtime_modernization,
        [
            "production-flag-state",
            "--workflow",
            "mcp_asset_search",
            "--workflow",
            "mcp_dashboard_list",
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 0
    assert json.loads(result.output) == {
        "workflows": [
            {
                "name": "mcp_asset_search",
                "serving_flags": {
                    "TS_ASSET_SEARCH_SERVING": True,
                    "TS_MCP_ORCHESTRATION": True,
                },
            },
            {
                "name": "mcp_dashboard_list",
                "serving_flags": {
                    "TS_DASHBOARD_LIST_SERVING": False,
                    "TS_MCP_ORCHESTRATION": True,
                },
            },
        ],
    }


def test_runtime_modernization_production_flag_state_outputs_text(
    mocker: MockerFixture,
    app_context: None,
) -> None:
    """Production flag-state command has a compact text mode."""

    mocker.patch(
        "superset.cli.runtime_modernization.is_feature_enabled",
        return_value=False,
    )

    result = CliRunner().invoke(
        runtime_modernization,
        [
            "production-flag-state",
            "--workflow",
            "mcp_database_list",
            "--format",
            "text",
        ],
    )

    assert result.exit_code == 0
    assert "runtime modernization production flag state" in result.output
    assert "mcp_database_list" in result.output
    assert "enabled: none" in result.output
    assert "TS_DATABASE_LIST_SERVING" in result.output


def test_runtime_modernization_operator_approval_outputs_json() -> None:
    """Operator approval command emits validation-ready approval evidence."""

    result = CliRunner().invoke(
        runtime_modernization,
        [
            "operator-approval",
            "--workflow",
            "mcp_asset_search",
            "--workflow",
            "mcp_dashboard_list",
            "--boundary-decision",
            "split MCP by tool class",
            "--rollout-scope",
            "asset search and dashboard listing",
            "--approval-reference",
            "CHG-123",
            "--approver",
            "platform-ops",
            "--notes",
            "approved after canary review",
        ],
    )

    assert result.exit_code == 0
    assert json.loads(result.output) == {
        "approved": True,
        "boundary_decision": "split MCP by tool class",
        "rollout_scope": "asset search and dashboard listing",
        "approval_reference": "CHG-123",
        "workflow_names": ["mcp_asset_search", "mcp_dashboard_list"],
        "approver": "platform-ops",
        "notes": "approved after canary review",
    }


def test_runtime_modernization_operator_approval_outputs_text() -> None:
    """Operator approval command has a compact text mode."""

    result = CliRunner().invoke(
        runtime_modernization,
        [
            "operator-approval",
            "--workflow",
            "mcp_asset_search",
            "--boundary-decision",
            "split MCP by tool class",
            "--rollout-scope",
            "asset search",
            "--approval-reference",
            "ADR-42",
            "--not-approved",
            "--format",
            "text",
        ],
    )

    assert result.exit_code == 0
    assert "runtime modernization operator approval" in result.output
    assert "approved: False" in result.output
    assert "split MCP by tool class" in result.output
    assert "approval reference: ADR-42" in result.output
    assert "workflows: mcp_asset_search" in result.output


def test_runtime_modernization_operator_approval_rejects_unknown_workflow() -> None:
    """Operator approval command rejects unknown workflow names."""

    result = CliRunner().invoke(
        runtime_modernization,
        [
            "operator-approval",
            "--workflow",
            "missing",
            "--boundary-decision",
            "split MCP by tool class",
            "--rollout-scope",
            "asset search",
            "--approval-reference",
            "ADR-42",
        ],
    )

    assert result.exit_code != 0
    assert "Unknown runtime modernization rollout workflow" in result.output


def test_runtime_modernization_operator_dashboard_snapshot_outputs_json() -> None:
    """Operator dashboard snapshot command emits validation-ready gate evidence."""

    result = CliRunner().invoke(
        runtime_modernization,
        [
            "operator-dashboard-snapshot",
            "--workflow",
            "mcp_asset_search",
            "--snapshot-reference",
            "observability/dashboard/snapshot-123",
            "--gates-passed",
            "--measurement-window",
            "2026-06-29T00:00Z/2026-06-29T01:00Z",
            "--notes",
            "canary window passed",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    gates = payload["workflows"]["mcp_asset_search"]["gates"]
    assert payload["snapshot_reference"] == "observability/dashboard/snapshot-123"
    assert payload["measurement_window"] == "2026-06-29T00:00Z/2026-06-29T01:00Z"
    assert payload["notes"] == "canary window passed"
    assert set(gates) == {
        "error_rate",
        "fallback_rate",
        "latency_p95",
        "shadow_mismatch_rate",
    }
    assert all(gate["passed"] is True for gate in gates.values())


def test_runtime_modernization_operator_dashboard_snapshot_outputs_text() -> None:
    """Operator dashboard snapshot command has a compact text mode."""

    result = CliRunner().invoke(
        runtime_modernization,
        [
            "operator-dashboard-snapshot",
            "--workflow",
            "mcp_dashboard_list",
            "--snapshot-reference",
            "dashboards/runtime-modernization.png",
            "--format",
            "text",
        ],
    )

    assert result.exit_code == 0
    assert "runtime modernization operator dashboard snapshot" in result.output
    assert "snapshot reference: dashboards/runtime-modernization.png" in result.output
    assert "mcp_dashboard_list" in result.output
    assert (
        "failed: shadow_mismatch_rate, fallback_rate, error_rate, latency_p95"
        in result.output
    )


def test_runtime_modernization_operator_dashboard_snapshot_accepts_gate_overrides() -> (
    None
):
    """Operator dashboard snapshot can record mixed per-gate status."""

    result = CliRunner().invoke(
        runtime_modernization,
        [
            "operator-dashboard-snapshot",
            "--workflow",
            "mcp_asset_search",
            "--snapshot-reference",
            "observability/dashboard/snapshot-123",
            "--gates-passed",
            "--failed-gate",
            "latency_p95",
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 0
    gates = json.loads(result.output)["workflows"]["mcp_asset_search"]["gates"]
    assert gates["latency_p95"]["passed"] is False
    assert gates["error_rate"]["passed"] is True


def test_operator_dashboard_snapshot_accepts_workflow_gate_overrides() -> None:
    """Operator dashboard snapshot can record per-workflow gate status."""

    result = CliRunner().invoke(
        runtime_modernization,
        [
            "operator-dashboard-snapshot",
            "--workflow",
            "mcp_asset_search",
            "--workflow",
            "mcp_dashboard_list",
            "--snapshot-reference",
            "observability/dashboard/snapshot-123",
            "--gates-passed",
            "--failed-workflow-gate",
            "mcp_dashboard_list:latency_p95",
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 0
    workflows = json.loads(result.output)["workflows"]
    assert workflows["mcp_asset_search"]["gates"]["latency_p95"]["passed"] is True
    assert workflows["mcp_dashboard_list"]["gates"]["latency_p95"]["passed"] is False


def test_runtime_modernization_operator_dashboard_snapshot_rejects_unknown_gate() -> (
    None
):
    """Operator dashboard snapshot rejects unknown gate overrides."""

    result = CliRunner().invoke(
        runtime_modernization,
        [
            "operator-dashboard-snapshot",
            "--workflow",
            "mcp_asset_search",
            "--snapshot-reference",
            "observability/dashboard/snapshot-123",
            "--passed-gate",
            "missing_gate",
        ],
    )

    assert result.exit_code != 0
    assert "Unknown dashboard gate: missing_gate" in result.output


def test_operator_dashboard_snapshot_rejects_unknown_workflow_gate() -> None:
    """Operator dashboard snapshot rejects unknown workflow gate overrides."""

    result = CliRunner().invoke(
        runtime_modernization,
        [
            "operator-dashboard-snapshot",
            "--workflow",
            "mcp_asset_search",
            "--snapshot-reference",
            "observability/dashboard/snapshot-123",
            "--failed-workflow-gate",
            "mcp_asset_search:missing_gate",
        ],
    )

    assert result.exit_code != 0
    assert "Unknown dashboard gate for mcp_asset_search: missing_gate" in (
        result.output
    )


def test_operator_dashboard_snapshot_rejects_unselected_workflow_gate() -> None:
    """Operator dashboard snapshot rejects overrides for unselected workflows."""

    result = CliRunner().invoke(
        runtime_modernization,
        [
            "operator-dashboard-snapshot",
            "--workflow",
            "mcp_asset_search",
            "--snapshot-reference",
            "observability/dashboard/snapshot-123",
            "--failed-workflow-gate",
            "mcp_dashboard_list:latency_p95",
        ],
    )

    assert result.exit_code != 0
    assert "Unknown dashboard workflow: mcp_dashboard_list" in result.output


def test_operator_dashboard_snapshot_rejects_conflicting_gate() -> None:
    """Operator dashboard snapshot rejects contradictory gate overrides."""

    result = CliRunner().invoke(
        runtime_modernization,
        [
            "operator-dashboard-snapshot",
            "--workflow",
            "mcp_asset_search",
            "--snapshot-reference",
            "observability/dashboard/snapshot-123",
            "--passed-gate",
            "latency_p95",
            "--failed-gate",
            "latency_p95",
        ],
    )

    assert result.exit_code != 0
    assert "Dashboard gate cannot be both passed and failed: latency_p95" in (
        result.output
    )


def test_operator_dashboard_snapshot_rejects_conflicting_workflow_gate() -> None:
    """Operator dashboard snapshot rejects contradictory workflow gate overrides."""

    result = CliRunner().invoke(
        runtime_modernization,
        [
            "operator-dashboard-snapshot",
            "--workflow",
            "mcp_asset_search",
            "--snapshot-reference",
            "observability/dashboard/snapshot-123",
            "--passed-workflow-gate",
            "mcp_asset_search:latency_p95",
            "--failed-workflow-gate",
            "mcp_asset_search:latency_p95",
        ],
    )

    assert result.exit_code != 0
    assert (
        "Dashboard gate cannot be both passed and failed: mcp_asset_search:latency_p95"
    ) in result.output


def test_operator_dashboard_snapshot_rejects_unknown_workflow() -> None:
    """Operator dashboard snapshot command fails on unknown workflow names."""

    result = CliRunner().invoke(
        runtime_modernization,
        [
            "operator-dashboard-snapshot",
            "--workflow",
            "missing",
            "--snapshot-reference",
            "dashboards/runtime-modernization.png",
        ],
    )

    assert result.exit_code != 0
    assert "Unknown runtime modernization rollout workflow" in result.output


def test_runtime_modernization_rust_kernel_rollout_decision_outputs_json() -> None:
    """Rust rollout decision command emits validation-ready evidence."""

    result = CliRunner().invoke(
        runtime_modernization,
        [
            "rust-kernel-rollout-decision",
            "--decision",
            "served",
            "--decision-reference",
            "CHG-RUST-1",
            "--rationale",
            "canary showed acceptable latency and errors",
            "--serving-flag-enabled",
        ],
    )

    assert result.exit_code == 0
    assert json.loads(result.output) == {
        "kernel": "ax_sql.normalize_sql_whitespace",
        "decision": "served",
        "serving_flag": "RUST_SQL_KERNEL",
        "serving_flag_enabled": True,
        "decision_reference": "CHG-RUST-1",
        "rationale": "canary showed acceptable latency and errors",
    }


def test_runtime_modernization_rust_kernel_rollout_decision_outputs_text() -> None:
    """Rust rollout decision command has a compact text mode."""

    result = CliRunner().invoke(
        runtime_modernization,
        [
            "rust-kernel-rollout-decision",
            "--decision",
            "rejected",
            "--decision-reference",
            "PERF-123",
            "--rationale",
            "benchmark gain did not justify rollout",
            "--format",
            "text",
        ],
    )

    assert result.exit_code == 0
    assert "runtime modernization Rust kernel rollout decision" in result.output
    assert "decision: rejected" in result.output
    assert "decision reference: PERF-123" in result.output


def test_runtime_modernization_rust_kernel_rollout_decision_template_outputs_json() -> (
    None
):
    """Rust rollout decision template command emits fillable evidence JSON."""

    result = CliRunner().invoke(
        runtime_modernization,
        ["rust-kernel-rollout-decision-template"],
    )

    assert result.exit_code == 0
    assert json.loads(result.output) == {
        "kernel": "ax_sql.normalize_sql_whitespace",
        "decision": "",
        "serving_flag": "RUST_SQL_KERNEL",
        "serving_flag_enabled": False,
        "decision_reference": "",
        "rationale": "",
    }


def test_runtime_modernization_rust_kernel_rollout_decision_template_outputs_text() -> (
    None
):
    """Rust rollout decision template command has a compact text mode."""

    result = CliRunner().invoke(
        runtime_modernization,
        [
            "rust-kernel-rollout-decision-template",
            "--kernel",
            "custom.kernel",
            "--serving-flag",
            "CUSTOM_RUST_KERNEL",
            "--format",
            "text",
        ],
    )

    assert result.exit_code == 0
    assert "runtime modernization Rust kernel rollout decision" in result.output
    assert "kernel: custom.kernel" in result.output
    assert "serving flag: CUSTOM_RUST_KERNEL" in result.output


def test_runtime_modernization_assemble_production_evidence_outputs_bundle(
    tmp_path,
) -> None:
    """Production evidence assembly combines collected artifact JSON files."""

    compatibility_report = tmp_path / "compatibility-report.json"
    rust_benchmark = tmp_path / "sql-kernel-benchmark.json"
    rust_decision = tmp_path / "rust-kernel-rollout-decision.json"
    flag_state = tmp_path / "flag-state.json"
    dashboard_snapshot = tmp_path / "dashboard-snapshot.json"
    operator_approval = tmp_path / "operator-approval.json"

    compatibility_report.write_text(
        json.dumps(
            {
                "status": "passed",
                "target_checks": {
                    "sql_parsing_operations_per_second_met": True,
                    "rust_kernel_speedup_met": None,
                },
            }
        ),
        encoding="utf-8",
    )
    rust_benchmark.write_text(
        json.dumps(
            {
                "status": "passed",
                "output_matched": True,
                "target_checks": {
                    "speedup_met": None,
                },
            }
        ),
        encoding="utf-8",
    )
    rust_decision.write_text(
        json.dumps(
            {
                "kernel": "ax_sql.normalize_sql_whitespace",
                "decision": "rejected",
                "serving_flag": "RUST_SQL_KERNEL",
                "serving_flag_enabled": False,
                "decision_reference": "PERF-123",
                "rationale": "benchmark gain did not justify rollout",
            }
        ),
        encoding="utf-8",
    )
    flag_state.write_text(
        json.dumps(
            {
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
            }
        ),
        encoding="utf-8",
    )
    dashboard_snapshot.write_text(
        json.dumps(
            {
                "snapshot_reference": "observability/dashboard/snapshot-123",
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
            }
        ),
        encoding="utf-8",
    )
    operator_approval.write_text(
        json.dumps(
            {
                "approved": True,
                "boundary_decision": "split MCP by tool class",
                "rollout_scope": "asset search and dashboard listing",
                "approval_reference": "CHG-123",
                "workflow_names": [
                    "mcp_asset_search",
                    "mcp_dashboard_list",
                ],
            }
        ),
        encoding="utf-8",
    )

    result = CliRunner().invoke(
        runtime_modernization,
        [
            "assemble-production-evidence",
            "--compatibility-report",
            str(compatibility_report),
            "--rust-kernel-benchmark",
            str(rust_benchmark),
            "--rust-kernel-rollout-decision",
            str(rust_decision),
            "--production-flag-state",
            str(flag_state),
            "--operator-dashboard-snapshot",
            str(dashboard_snapshot),
            "--operator-approval",
            str(operator_approval),
            "--workflow",
            "mcp_asset_search",
            "--workflow",
            "mcp_dashboard_list",
            "--validate",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["schema_version"] == 1
    assert payload["artifacts"]["compatibility_report"]["status"] == "passed"
    assert payload["artifacts"]["rust_kernel_benchmark"]["output_matched"] is True
    assert (
        payload["artifacts"]["rust_kernel_rollout_decision"]["decision"] == "rejected"
    )
    assert payload["artifacts"]["operator_approval"]["approved"] is True


def test_runtime_modernization_assemble_production_evidence_strict_failure(
    tmp_path,
) -> None:
    """Strict evidence assembly fails when required production artifacts are absent."""

    compatibility_report = tmp_path / "compatibility-report.json"
    rust_benchmark = tmp_path / "sql-kernel-benchmark.json"
    compatibility_report.write_text(
        json.dumps({"status": "passed"}),
        encoding="utf-8",
    )
    rust_benchmark.write_text(
        json.dumps({"status": "passed", "output_matched": True}),
        encoding="utf-8",
    )

    result = CliRunner().invoke(
        runtime_modernization,
        [
            "assemble-production-evidence",
            "--compatibility-report",
            str(compatibility_report),
            "--rust-kernel-benchmark",
            str(rust_benchmark),
            "--workflow",
            "mcp_asset_search",
            "--strict",
        ],
    )

    assert result.exit_code != 0
    assert '"compatibility_report"' in result.output
    assert "runtime modernization production evidence validation: failed" in (
        result.output
    )
    assert "runtime modernization production evidence failed" in result.output


def test_runtime_modernization_validate_production_evidence_outputs_json(
    tmp_path,
) -> None:
    """Production evidence validation emits stable JSON for release gates."""

    evidence_file = tmp_path / "runtime-evidence.json"
    evidence_file.write_text(
        json.dumps(
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
                    "rust_kernel_rollout_decision": {
                        "kernel": "ax_sql.normalize_sql_whitespace",
                        "decision": "served",
                        "serving_flag": "RUST_SQL_KERNEL",
                        "serving_flag_enabled": True,
                        "decision_reference": "CHG-RUST-1",
                        "rationale": "canary showed acceptable latency and errors",
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
                        "approval_reference": "CHG-123",
                        "workflow_names": [
                            "mcp_asset_search",
                            "mcp_dashboard_list",
                        ],
                    },
                },
            }
        ),
        encoding="utf-8",
    )

    result = CliRunner().invoke(
        runtime_modernization,
        [
            "validate-production-evidence",
            str(evidence_file),
            "--workflow",
            "mcp_asset_search",
            "--workflow",
            "mcp_dashboard_list",
            "--format",
            "json",
            "--strict",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["schema_version"] == 1
    assert payload["status"] == "passed"
    assert payload["workflow_names"] == ["mcp_asset_search", "mcp_dashboard_list"]
    assert payload["enabled_workflow_names"] == [
        "mcp_asset_search",
        "mcp_dashboard_list",
    ]
    assert payload["dashboard_required_workflow_names"] == [
        "mcp_asset_search",
        "mcp_dashboard_list",
    ]
    assert all(check["passed"] for check in payload["checks"])


def test_runtime_modernization_validate_production_evidence_strict_failure(
    tmp_path,
) -> None:
    """Strict production evidence validation exits nonzero for missing artifacts."""

    evidence_file = tmp_path / "runtime-evidence.json"
    evidence_file.write_text(
        json.dumps({"schema_version": 1, "artifacts": {}}),
        encoding="utf-8",
    )

    result = CliRunner().invoke(
        runtime_modernization,
        [
            "validate-production-evidence",
            str(evidence_file),
            "--workflow",
            "mcp_asset_search",
            "--format",
            "text",
            "--strict",
        ],
    )

    assert result.exit_code != 0
    assert "runtime modernization production evidence validation: failed" in (
        result.output
    )
    assert "FAIL compatibility_report" in result.output
    assert "runtime modernization production evidence failed" in result.output


def test_runtime_modernization_completion_audit_outputs_json(tmp_path: Path) -> None:
    """Completion audit emits stable phase status JSON."""

    evidence_file = _write_complete_runtime_evidence(tmp_path)

    result = CliRunner().invoke(
        runtime_modernization,
        [
            "completion-audit",
            str(evidence_file),
            "--workflow",
            "mcp_asset_search",
            "--workflow",
            "mcp_dashboard_list",
            "--format",
            "json",
            "--strict",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["schema_version"] == 1
    assert payload["status"] == "complete"
    assert payload["workflow_names"] == ["mcp_asset_search", "mcp_dashboard_list"]
    assert all(check["passed"] for check in payload["phase_checks"])
    assert payload["evidence_validation"]["status"] == "passed"
    assert payload["evidence_validation"]["enabled_workflow_names"] == [
        "mcp_asset_search",
        "mcp_dashboard_list",
    ]
    assert payload["evidence_validation"]["dashboard_required_workflow_names"] == [
        "mcp_asset_search",
        "mcp_dashboard_list",
    ]


def test_runtime_modernization_completion_audit_strict_failure() -> None:
    """Strict completion audit exits nonzero when phase evidence is incomplete."""

    result = CliRunner().invoke(
        runtime_modernization,
        [
            "completion-audit",
            "--workflow",
            "mcp_asset_search",
            "--format",
            "text",
            "--strict",
        ],
    )

    assert result.exit_code != 0
    assert "runtime modernization completion audit: incomplete" in result.output
    assert "FAIL phase_5_selective_runtime_split" in result.output
    assert "runtime modernization phases incomplete" in result.output


def test_runtime_modernization_benchmark_outputs_json(
    mocker: MockerFixture,
) -> None:
    """Benchmark command emits stable JSON for automation."""

    benchmark = mocker.patch(
        "superset.cli.runtime_modernization.benchmark_sql_parsing_normalization"
    )
    benchmark.return_value = RuntimeBenchmarkResult(
        area="sql_parsing_normalization",
        operation="parse_format_table_check",
        engine="postgresql",
        iterations=3,
        duration_ms=12.5,
        operations_per_second=240.0,
        statement_count=1,
        formatted_bytes=128,
        table_check_matched=True,
        has_mutation=False,
    )

    result = CliRunner().invoke(
        runtime_modernization,
        ["benchmark", "--iterations", "3", "--format", "json"],
    )

    assert result.exit_code == 0
    assert json.loads(result.output) == {
        "area": "sql_parsing_normalization",
        "duration_ms": 12.5,
        "engine": "postgresql",
        "formatted_bytes": 128,
        "has_mutation": False,
        "iterations": 3,
        "operation": "parse_format_table_check",
        "operations_per_second": 240.0,
        "statement_count": 1,
        "table_check_matched": True,
    }
    benchmark.assert_called_once_with(iterations=3)


def test_runtime_modernization_kernel_benchmark_outputs_json(
    mocker: MockerFixture,
) -> None:
    """Kernel benchmark command emits stable JSON for automation."""

    benchmark = mocker.patch(
        "superset.cli.runtime_modernization.benchmark_sql_whitespace_kernel"
    )
    benchmark.return_value = RuntimeKernelBenchmarkResult(
        area="sql_whitespace_kernel",
        operation="normalize_whitespace",
        iterations=5,
        python_duration_ms=10.0,
        python_operations_per_second=500.0,
        rust_available=True,
        rust_duration_ms=2.5,
        rust_operations_per_second=2000.0,
        speedup=4.0,
        output_matched=True,
        output_bytes=64,
    )

    result = CliRunner().invoke(
        runtime_modernization,
        [
            "benchmark",
            "--candidate",
            "sql_whitespace_kernel",
            "--iterations",
            "5",
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 0
    assert json.loads(result.output) == {
        "area": "sql_whitespace_kernel",
        "iterations": 5,
        "operation": "normalize_whitespace",
        "output_bytes": 64,
        "output_matched": True,
        "python_duration_ms": 10.0,
        "python_operations_per_second": 500.0,
        "rust_available": True,
        "rust_duration_ms": 2.5,
        "rust_operations_per_second": 2000.0,
        "speedup": 4.0,
    }
    benchmark.assert_called_once_with(iterations=5)


def test_runtime_modernization_compatibility_report_outputs_json(
    mocker: MockerFixture,
) -> None:
    """Compatibility report command emits stable JSON for CI artifacts."""

    parsing_benchmark = mocker.patch(
        "superset.cli.runtime_modernization.benchmark_sql_parsing_normalization"
    )
    parsing_benchmark.return_value = RuntimeBenchmarkResult(
        area="sql_parsing_normalization",
        operation="parse_format_table_check",
        engine="postgresql",
        iterations=7,
        duration_ms=14.0,
        operations_per_second=500.0,
        statement_count=1,
        formatted_bytes=128,
        table_check_matched=True,
        has_mutation=False,
    )
    kernel_benchmark = mocker.patch(
        "superset.cli.runtime_modernization.benchmark_sql_whitespace_kernel"
    )
    kernel_benchmark.return_value = RuntimeKernelBenchmarkResult(
        area="sql_whitespace_kernel",
        operation="normalize_whitespace",
        iterations=7,
        python_duration_ms=21.0,
        python_operations_per_second=333.3,
        rust_available=True,
        rust_duration_ms=7.0,
        rust_operations_per_second=1000.0,
        speedup=3.0,
        output_matched=True,
        output_bytes=64,
    )

    result = CliRunner().invoke(
        runtime_modernization,
        ["compatibility-report", "--iterations", "7", "--format", "json"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["schema_version"] == 1
    assert payload["status"] == "passed"
    assert payload["checks"] == {
        "rust_kernel_available": True,
        "rust_kernel_output_compatible": True,
        "sql_parsing_has_mutation": False,
        "sql_parsing_table_check_matched": True,
    }
    assert payload["targets"] == {
        "rust_kernel_min_speedup": None,
        "sql_parsing_min_operations_per_second": None,
    }
    assert payload["target_checks"] == {
        "rust_kernel_speedup_met": None,
        "sql_parsing_operations_per_second_met": None,
    }
    assert payload["inventory"]["by_disposition"]["candidate"] >= 1
    assert "mcp_orchestration" in payload["inventory"]["candidate_areas"]
    assert payload["benchmarks"]["sql_parsing_normalization"]["iterations"] == 7
    assert payload["benchmarks"]["sql_whitespace_kernel"]["speedup"] == 3.0
    parsing_benchmark.assert_called_once_with(iterations=7)
    kernel_benchmark.assert_called_once_with(iterations=7)


def test_runtime_modernization_compatibility_report_strict_failure(
    mocker: MockerFixture,
) -> None:
    """Strict compatibility report exits nonzero when checks fail."""

    parsing_benchmark = mocker.patch(
        "superset.cli.runtime_modernization.benchmark_sql_parsing_normalization"
    )
    parsing_benchmark.return_value = RuntimeBenchmarkResult(
        area="sql_parsing_normalization",
        operation="parse_format_table_check",
        engine="postgresql",
        iterations=1,
        duration_ms=1.0,
        operations_per_second=1000.0,
        statement_count=1,
        formatted_bytes=128,
        table_check_matched=False,
        has_mutation=False,
    )
    kernel_benchmark = mocker.patch(
        "superset.cli.runtime_modernization.benchmark_sql_whitespace_kernel"
    )
    kernel_benchmark.return_value = RuntimeKernelBenchmarkResult(
        area="sql_whitespace_kernel",
        operation="normalize_whitespace",
        iterations=1,
        python_duration_ms=1.0,
        python_operations_per_second=1000.0,
        rust_available=False,
        rust_duration_ms=None,
        rust_operations_per_second=None,
        speedup=None,
        output_matched=None,
        output_bytes=64,
    )

    result = CliRunner().invoke(
        runtime_modernization,
        ["compatibility-report", "--iterations", "1", "--strict"],
    )

    assert result.exit_code != 0
    assert "runtime modernization compatibility failed" in result.output


def test_runtime_modernization_compatibility_report_strict_target_failure(
    mocker: MockerFixture,
) -> None:
    """Strict compatibility report exits nonzero when target gates fail."""

    parsing_benchmark = mocker.patch(
        "superset.cli.runtime_modernization.benchmark_sql_parsing_normalization"
    )
    parsing_benchmark.return_value = RuntimeBenchmarkResult(
        area="sql_parsing_normalization",
        operation="parse_format_table_check",
        engine="postgresql",
        iterations=3,
        duration_ms=30.0,
        operations_per_second=100.0,
        statement_count=1,
        formatted_bytes=128,
        table_check_matched=True,
        has_mutation=False,
    )
    kernel_benchmark = mocker.patch(
        "superset.cli.runtime_modernization.benchmark_sql_whitespace_kernel"
    )
    kernel_benchmark.return_value = RuntimeKernelBenchmarkResult(
        area="sql_whitespace_kernel",
        operation="normalize_whitespace",
        iterations=3,
        python_duration_ms=30.0,
        python_operations_per_second=100.0,
        rust_available=True,
        rust_duration_ms=20.0,
        rust_operations_per_second=150.0,
        speedup=1.5,
        output_matched=True,
        output_bytes=64,
    )

    result = CliRunner().invoke(
        runtime_modernization,
        [
            "compatibility-report",
            "--iterations",
            "3",
            "--min-sql-parsing-ops-per-second",
            "200",
            "--min-rust-kernel-speedup",
            "2",
            "--strict",
        ],
    )

    assert result.exit_code != 0
    payload = json.loads(result.output.split("\nError:")[0])
    assert payload["status"] == "failed"
    assert payload["targets"] == {
        "rust_kernel_min_speedup": 2.0,
        "sql_parsing_min_operations_per_second": 200.0,
    }
    assert payload["target_checks"] == {
        "rust_kernel_speedup_met": False,
        "sql_parsing_operations_per_second_met": False,
    }
    assert "runtime modernization compatibility failed" in result.output


def test_runtime_modernization_ax_services_ready_outputs_text(
    mocker: MockerFixture,
    app_context: None,
) -> None:
    """AX services CLI uses Superset config and prints readiness status."""

    current_app.config["AX_SERVICES_BASE_URL"] = "http://ax-services.local"
    client = mocker.patch(
        "superset.cli.runtime_modernization.AxServicesClient"
    ).return_value
    client.ready.return_value = AxServicesResponse(
        ok=True,
        status_code=200,
        payload={"status": "ready"},
    )

    result = CliRunner().invoke(
        runtime_modernization,
        ["ax-services", "--request-id", "request-abc"],
    )

    assert result.exit_code == 0
    assert "ax-services ready: ok" in result.output
    client.ready.assert_called_once_with(request_id="request-abc")


def test_runtime_modernization_ax_services_health_outputs_json(
    mocker: MockerFixture,
    app_context: None,
) -> None:
    """AX services CLI can emit machine-readable health output."""

    client = mocker.patch(
        "superset.cli.runtime_modernization.AxServicesClient"
    ).return_value
    client.health.return_value = AxServicesResponse(
        ok=True,
        status_code=200,
        payload={"status": "ok"},
    )

    result = CliRunner().invoke(
        runtime_modernization,
        ["ax-services", "--check", "health", "--format", "json"],
    )

    assert result.exit_code == 0
    assert json.loads(result.output) == {
        "error": None,
        "ok": True,
        "payload": {"status": "ok"},
        "status_code": 200,
    }
    client.health.assert_called_once_with(request_id=None)


def test_runtime_modernization_ax_services_metadata_outputs_json(
    mocker: MockerFixture,
    app_context: None,
) -> None:
    """AX services CLI can emit machine-readable metadata probe output."""

    client = mocker.patch(
        "superset.cli.runtime_modernization.AxServicesClient"
    ).return_value
    client.metadata.return_value = AxServicesResponse(
        ok=True,
        status_code=200,
        payload={"dependencies": {"supersetMetadata": {"ok": True}}},
    )

    result = CliRunner().invoke(
        runtime_modernization,
        ["ax-services", "--check", "metadata", "--format", "json"],
    )

    assert result.exit_code == 0
    assert json.loads(result.output) == {
        "error": None,
        "ok": True,
        "payload": {"dependencies": {"supersetMetadata": {"ok": True}}},
        "status_code": 200,
    }
    client.metadata.assert_called_once_with(request_id=None)


def test_runtime_modernization_ax_services_metrics_outputs_json(
    mocker: MockerFixture,
    app_context: None,
) -> None:
    """AX services CLI can emit machine-readable metrics output."""

    client = mocker.patch(
        "superset.cli.runtime_modernization.AxServicesClient"
    ).return_value
    client.metrics.return_value = AxServicesResponse(
        ok=True,
        status_code=200,
        payload={"requests": {"total": 2, "errorCount": 0}},
    )

    result = CliRunner().invoke(
        runtime_modernization,
        ["ax-services", "--check", "metrics", "--format", "json"],
    )

    assert result.exit_code == 0
    assert json.loads(result.output) == {
        "error": None,
        "ok": True,
        "payload": {"requests": {"total": 2, "errorCount": 0}},
        "status_code": 200,
    }
    client.metrics.assert_called_once_with(request_id=None)


def test_runtime_modernization_ax_services_failure_exits_nonzero(
    mocker: MockerFixture,
    app_context: None,
) -> None:
    """AX services CLI fails when the sidecar is unavailable."""

    client = mocker.patch(
        "superset.cli.runtime_modernization.AxServicesClient"
    ).return_value
    client.ready.return_value = AxServicesResponse(
        ok=False,
        status_code=None,
        error="connection failed",
    )

    result = CliRunner().invoke(runtime_modernization, ["ax-services"])

    assert result.exit_code != 0
    assert "ax-services ready check failed" in result.output

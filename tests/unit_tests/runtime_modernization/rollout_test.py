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
    build_production_evidence_manifest,
    get_production_evidence_requirements,
    get_rollout_workflow,
    get_rollout_workflows,
)


def test_rollout_workflows_cover_migrated_mcp_paths() -> None:
    """Rollout manifest includes the TypeScript-routed MCP workflows."""

    workflows = get_rollout_workflows()
    names = {workflow.name for workflow in workflows}

    assert names == {
        "mcp_asset_search",
        "mcp_chart_list",
        "mcp_dashboard_list",
        "mcp_health_check",
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

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
        ["rollout-manifest", "--workflow", "mcp_asset_search", "--format", "text"],
    )

    assert result.exit_code == 0
    assert "mcp_asset_search: POST /mcp/assets/search" in result.output
    assert "TS_ASSET_SEARCH_SERVING" in result.output
    assert "shadow_mismatch_rate" in result.output


def test_runtime_modernization_rollout_manifest_rejects_unknown_workflow() -> None:
    """Rollout manifest fails on unknown workflow names."""

    result = CliRunner().invoke(
        runtime_modernization,
        ["rollout-manifest", "--workflow", "missing"],
    )

    assert result.exit_code != 0
    assert "Unknown runtime modernization rollout workflow" in result.output


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

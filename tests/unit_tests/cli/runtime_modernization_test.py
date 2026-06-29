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

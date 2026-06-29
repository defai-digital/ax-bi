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
"""CLI commands for AX-BI runtime modernization planning."""

from __future__ import annotations

from typing import Any

import click
from flask import current_app
from flask.cli import with_appcontext

from superset.runtime_modernization.ax_services import (
    AxServicesClient,
    AxServicesConfig,
    AxServicesResponse,
)
from superset.runtime_modernization.benchmarks import (
    benchmark_sql_parsing_normalization,
    benchmark_sql_whitespace_kernel,
    RuntimeBenchmarkResult,
    RuntimeKernelBenchmarkResult,
)
from superset.runtime_modernization.inventory import (
    get_runtime_inventory,
    MigrationDisposition,
    RuntimeInventoryItem,
)
from superset.runtime_modernization.rollout import (
    build_production_evidence_manifest,
    get_rollout_workflow,
    get_rollout_workflows,
    RolloutWorkflow,
    validate_production_evidence,
)
from superset.utils import json


@click.group()
def runtime_modernization() -> None:
    """Runtime modernization planning commands."""


def _inventory_item_to_dict(item: RuntimeInventoryItem) -> dict[str, Any]:
    """Serialize a runtime inventory item for CLI output."""

    return {
        "area": item.area,
        "module_patterns": list(item.module_patterns),
        "current_runtime": item.current_runtime.value,
        "target_runtime": item.target_runtime.value,
        "disposition": item.disposition.value,
        "rationale": item.rationale,
        "required_evidence": list(item.required_evidence),
    }


def _format_table(items: tuple[RuntimeInventoryItem, ...]) -> str:
    """Render runtime inventory items as a compact table."""

    rows = [
        (
            item.area,
            item.current_runtime.value,
            item.target_runtime.value,
            item.disposition.value,
        )
        for item in items
    ]
    header = ("area", "current", "target", "disposition")
    widths = [
        max(len(str(row[index])) for row in (header, *rows))
        for index in range(len(header))
    ]
    lines = [
        "  ".join(value.ljust(widths[index]) for index, value in enumerate(header)),
        "  ".join("-" * width for width in widths),
    ]
    lines.extend(
        "  ".join(value.ljust(widths[index]) for index, value in enumerate(row))
        for row in rows
    )
    return "\n".join(lines)


def _response_to_dict(response: AxServicesResponse) -> dict[str, Any]:
    """Serialize an ax-services response for CLI output."""

    return {
        "ok": response.ok,
        "status_code": response.status_code,
        "payload": response.payload,
        "error": response.error,
    }


def _benchmark_result_to_dict(result: RuntimeBenchmarkResult) -> dict[str, Any]:
    """Serialize a runtime benchmark result for CLI output."""

    return {
        "area": result.area,
        "operation": result.operation,
        "engine": result.engine,
        "iterations": result.iterations,
        "duration_ms": result.duration_ms,
        "operations_per_second": result.operations_per_second,
        "statement_count": result.statement_count,
        "formatted_bytes": result.formatted_bytes,
        "table_check_matched": result.table_check_matched,
        "has_mutation": result.has_mutation,
    }


def _kernel_benchmark_result_to_dict(
    result: RuntimeKernelBenchmarkResult,
) -> dict[str, Any]:
    """Serialize a runtime kernel benchmark result for CLI output."""

    return {
        "area": result.area,
        "operation": result.operation,
        "iterations": result.iterations,
        "python_duration_ms": result.python_duration_ms,
        "python_operations_per_second": result.python_operations_per_second,
        "rust_available": result.rust_available,
        "rust_duration_ms": result.rust_duration_ms,
        "rust_operations_per_second": result.rust_operations_per_second,
        "speedup": result.speedup,
        "output_matched": result.output_matched,
        "output_bytes": result.output_bytes,
    }


def _inventory_summary_to_dict(
    items: tuple[RuntimeInventoryItem, ...],
) -> dict[str, Any]:
    """Summarize runtime inventory items for compatibility reports."""

    by_disposition = {disposition.value: 0 for disposition in MigrationDisposition}
    for item in items:
        by_disposition[item.disposition.value] += 1

    return {
        "total": len(items),
        "by_disposition": by_disposition,
        "candidate_areas": [
            item.area
            for item in items
            if item.disposition == MigrationDisposition.CANDIDATE
        ],
    }


def _rollout_workflow_to_dict(workflow: RolloutWorkflow) -> dict[str, object]:
    """Serialize a rollout workflow for CLI output."""

    return workflow.to_dict()


def _format_rollout_workflows(workflows: tuple[RolloutWorkflow, ...]) -> str:
    """Render rollout workflows as compact text."""

    lines = []
    for workflow in workflows:
        lines.append(
            f"{workflow.name}: {workflow.sidecar_route} ({workflow.contract_version})"
        )
        lines.append(f"  shadow: {', '.join(workflow.shadow_flags)}")
        lines.append(f"  serving: {', '.join(workflow.serving_flags)}")
        lines.append(
            "  gates: "
            + ", ".join(f"{gate.name} {gate.target}" for gate in workflow.gates)
        )
    return "\n".join(lines)


def _format_production_evidence_manifest(manifest: dict[str, Any]) -> str:
    """Render a compact production evidence manifest."""

    lines = [
        f"runtime modernization production evidence: {manifest['status']}",
        (
            "minimum TypeScript serving workflows: "
            f"{manifest['minimum_typescript_serving_workflows']}"
        ),
    ]
    lines.append("workflows:")
    for workflow in manifest["workflows"]:
        lines.append(f"  {workflow['name']}: {workflow['sidecar_route']}")
    lines.append("required artifacts:")
    for artifact in manifest["required_artifacts"]:
        lines.append(
            f"  {artifact['name']} ({artifact['phase']}): {artifact['source']}"
        )
    return "\n".join(lines)


def _format_production_evidence_validation(validation: dict[str, Any]) -> str:
    """Render a compact production evidence validation report."""

    lines = [
        f"runtime modernization production evidence validation: {validation['status']}"
    ]
    for check in validation["checks"]:
        marker = "PASS" if check["passed"] else "FAIL"
        lines.append(f"  {marker} {check['name']}: {check['message']}")
    return "\n".join(lines)


def _build_compatibility_report(
    iterations: int,
    *,
    min_sql_parsing_ops_per_second: float | None = None,
    min_rust_kernel_speedup: float | None = None,
) -> dict[str, Any]:
    """Build a runtime modernization compatibility report."""

    inventory_items = get_runtime_inventory()
    parsing_result = benchmark_sql_parsing_normalization(iterations=iterations)
    kernel_result = benchmark_sql_whitespace_kernel(iterations=iterations)
    rust_output_compatible = kernel_result.output_matched is not False
    sql_parsing_target_met = (
        None
        if min_sql_parsing_ops_per_second is None
        else parsing_result.operations_per_second >= min_sql_parsing_ops_per_second
    )
    rust_speedup_target_met = (
        None
        if min_rust_kernel_speedup is None
        else kernel_result.speedup is not None
        and kernel_result.speedup >= min_rust_kernel_speedup
    )
    passed = (
        parsing_result.table_check_matched
        and not parsing_result.has_mutation
        and rust_output_compatible
        and sql_parsing_target_met is not False
        and rust_speedup_target_met is not False
    )

    return {
        "schema_version": 1,
        "status": "passed" if passed else "failed",
        "checks": {
            "sql_parsing_table_check_matched": parsing_result.table_check_matched,
            "sql_parsing_has_mutation": parsing_result.has_mutation,
            "rust_kernel_available": kernel_result.rust_available,
            "rust_kernel_output_compatible": rust_output_compatible,
        },
        "targets": {
            "sql_parsing_min_operations_per_second": min_sql_parsing_ops_per_second,
            "rust_kernel_min_speedup": min_rust_kernel_speedup,
        },
        "target_checks": {
            "sql_parsing_operations_per_second_met": sql_parsing_target_met,
            "rust_kernel_speedup_met": rust_speedup_target_met,
        },
        "inventory": _inventory_summary_to_dict(inventory_items),
        "benchmarks": {
            "sql_parsing_normalization": _benchmark_result_to_dict(parsing_result),
            "sql_whitespace_kernel": _kernel_benchmark_result_to_dict(kernel_result),
        },
    }


@runtime_modernization.command()
@click.option(
    "--format",
    "output_format",
    type=click.Choice(("table", "json")),
    default="table",
    show_default=True,
    help="Output format.",
)
@click.option(
    "--disposition",
    type=click.Choice(tuple(disposition.value for disposition in MigrationDisposition)),
    help="Filter by migration disposition.",
)
def inventory(output_format: str, disposition: str | None) -> None:
    """Print the runtime modernization inventory."""

    items = get_runtime_inventory()
    if disposition:
        items = tuple(item for item in items if item.disposition.value == disposition)

    if output_format == "json":
        click.echo(
            json.dumps(
                [_inventory_item_to_dict(item) for item in items],
                sort_keys=True,
                indent=2,
            )
        )
        return

    click.echo(_format_table(items))


@runtime_modernization.command("rollout-manifest")
@click.option(
    "--workflow",
    help="Optional rollout workflow name to print.",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(("text", "json")),
    default="json",
    show_default=True,
    help="Output format.",
)
def rollout_manifest(workflow: str | None, output_format: str) -> None:
    """Print rollout gates and dashboard metrics for migrated workflows."""

    try:
        workflows = (
            (get_rollout_workflow(workflow),)
            if workflow is not None
            else get_rollout_workflows()
        )
    except KeyError as ex:
        raise click.ClickException(str(ex)) from ex

    if output_format == "json":
        click.echo(
            json.dumps(
                {
                    "schema_version": 1,
                    "workflows": [
                        _rollout_workflow_to_dict(item) for item in workflows
                    ],
                },
                sort_keys=True,
                indent=2,
            )
        )
        return

    click.echo(_format_rollout_workflows(workflows))


@runtime_modernization.command("production-evidence")
@click.option(
    "--workflow",
    help="Optional rollout workflow name to include.",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(("text", "json")),
    default="json",
    show_default=True,
    help="Output format.",
)
def production_evidence(workflow: str | None, output_format: str) -> None:
    """Print required production evidence for runtime modernization completion."""

    try:
        workflows = (
            (get_rollout_workflow(workflow),)
            if workflow is not None
            else get_rollout_workflows()
        )
    except KeyError as ex:
        raise click.ClickException(str(ex)) from ex

    manifest = build_production_evidence_manifest(workflows)

    if output_format == "json":
        click.echo(json.dumps(manifest, sort_keys=True, indent=2))
        return

    click.echo(_format_production_evidence_manifest(manifest))


@runtime_modernization.command("validate-production-evidence")
@click.argument("evidence_file", type=click.File("r"))
@click.option(
    "--workflow",
    multiple=True,
    help="Optional rollout workflow name to validate. Can be supplied more than once.",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(("text", "json")),
    default="json",
    show_default=True,
    help="Output format.",
)
@click.option(
    "--strict",
    is_flag=True,
    help="Exit with an error when evidence validation fails.",
)
def validate_production_evidence_command(
    evidence_file: Any,
    workflow: tuple[str, ...],
    output_format: str,
    strict: bool,
) -> None:
    """Validate runtime modernization production evidence from a JSON file."""

    try:
        workflows = (
            tuple(get_rollout_workflow(name) for name in workflow)
            if workflow
            else get_rollout_workflows()
        )
    except KeyError as ex:
        raise click.ClickException(str(ex)) from ex

    try:
        evidence = json.loads(evidence_file.read())
    except ValueError as ex:
        raise click.ClickException(f"Invalid evidence JSON: {ex}") from ex
    if not isinstance(evidence, dict):
        raise click.ClickException("Evidence JSON must be an object")

    validation = validate_production_evidence(workflows, evidence)

    if output_format == "json":
        click.echo(json.dumps(validation, sort_keys=True, indent=2))
    else:
        click.echo(_format_production_evidence_validation(validation))

    if strict and validation["status"] != "passed":
        raise click.ClickException("runtime modernization production evidence failed")


@runtime_modernization.command("compatibility-report")
@click.option(
    "--iterations",
    type=click.IntRange(min=1),
    default=10,
    show_default=True,
    help="Number of benchmark iterations.",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(("text", "json")),
    default="json",
    show_default=True,
    help="Output format.",
)
@click.option(
    "--strict",
    is_flag=True,
    help="Exit with an error when compatibility checks fail.",
)
@click.option(
    "--min-sql-parsing-ops-per-second",
    type=click.FloatRange(min=0.0),
    help="Optional minimum SQL parsing throughput target.",
)
@click.option(
    "--min-rust-kernel-speedup",
    type=click.FloatRange(min=0.0),
    help="Optional minimum Rust kernel speedup target.",
)
def compatibility_report(
    iterations: int,
    output_format: str,
    strict: bool,
    min_sql_parsing_ops_per_second: float | None,
    min_rust_kernel_speedup: float | None,
) -> None:
    """Generate a runtime modernization compatibility report."""

    report = _build_compatibility_report(
        iterations,
        min_sql_parsing_ops_per_second=min_sql_parsing_ops_per_second,
        min_rust_kernel_speedup=min_rust_kernel_speedup,
    )

    if output_format == "json":
        click.echo(json.dumps(report, sort_keys=True, indent=2))
    else:
        click.echo(
            f"runtime modernization compatibility: {report['status']} "
            f"({iterations} benchmark iterations)"
        )

    if strict and report["status"] != "passed":
        raise click.ClickException("runtime modernization compatibility failed")


@runtime_modernization.command("benchmark")
@click.option(
    "--candidate",
    type=click.Choice(("sql_parsing_normalization", "sql_whitespace_kernel")),
    default="sql_parsing_normalization",
    show_default=True,
    help="Runtime modernization candidate to benchmark.",
)
@click.option(
    "--iterations",
    type=click.IntRange(min=1),
    default=50,
    show_default=True,
    help="Number of benchmark iterations.",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(("text", "json")),
    default="text",
    show_default=True,
    help="Output format.",
)
def benchmark(candidate: str, iterations: int, output_format: str) -> None:
    """Run a local runtime modernization benchmark."""

    if candidate == "sql_parsing_normalization":
        result = benchmark_sql_parsing_normalization(iterations=iterations)

        if output_format == "json":
            click.echo(
                json.dumps(_benchmark_result_to_dict(result), sort_keys=True, indent=2)
            )
            return

        click.echo(
            f"{result.area} {result.operation}: "
            f"{result.iterations} iterations in {result.duration_ms:.2f} ms "
            f"({result.operations_per_second:.2f} ops/s)"
        )
        return

    if candidate != "sql_whitespace_kernel":
        raise click.ClickException(f"Unsupported benchmark candidate: {candidate}")

    kernel_result = benchmark_sql_whitespace_kernel(iterations=iterations)

    if output_format == "json":
        click.echo(
            json.dumps(
                _kernel_benchmark_result_to_dict(kernel_result),
                sort_keys=True,
                indent=2,
            )
        )
        return

    rust_summary = "rust unavailable"
    if kernel_result.rust_available:
        rust_duration_ms = kernel_result.rust_duration_ms or 0
        rust_operations_per_second = kernel_result.rust_operations_per_second or 0
        speedup = (
            f"{kernel_result.speedup:.2f}x"
            if kernel_result.speedup is not None
            else "n/a"
        )
        rust_summary = (
            f"rust {rust_duration_ms:.2f} ms "
            f"({rust_operations_per_second:.2f} ops/s), "
            f"speedup {speedup}, "
            f"matched={kernel_result.output_matched}"
        )

    click.echo(
        f"{kernel_result.area} {kernel_result.operation}: "
        f"{kernel_result.iterations} iterations, "
        f"python {kernel_result.python_duration_ms:.2f} ms "
        f"({kernel_result.python_operations_per_second:.2f} ops/s), "
        f"{rust_summary}"
    )


@runtime_modernization.command("ax-services")
@click.option(
    "--check",
    type=click.Choice(("health", "metadata", "metrics", "ready")),
    default="ready",
    show_default=True,
    help="Sidecar endpoint to check.",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(("text", "json")),
    default="text",
    show_default=True,
    help="Output format.",
)
@click.option("--request-id", help="Optional request ID to forward.")
@with_appcontext
def ax_services(check: str, output_format: str, request_id: str | None) -> None:
    """Check AX services sidecar runtime endpoints."""

    client = AxServicesClient(AxServicesConfig.from_mapping(current_app.config))
    if check == "health":
        response = client.health(request_id=request_id)
    elif check == "metadata":
        response = client.metadata(request_id=request_id)
    elif check == "metrics":
        response = client.metrics(request_id=request_id)
    else:
        response = client.ready(request_id=request_id)

    if output_format == "json":
        click.echo(json.dumps(_response_to_dict(response), sort_keys=True, indent=2))
    elif response.ok:
        click.echo(f"ax-services {check}: ok")
    else:
        message = response.error or response.payload or "not ready"
        click.echo(f"ax-services {check}: failed ({message})", err=True)

    if not response.ok:
        raise click.ClickException(f"ax-services {check} check failed")

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

from superset import is_feature_enabled
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
    audit_runtime_modernization_completion,
    build_operator_approval_evidence,
    build_operator_dashboard_snapshot,
    build_production_evidence_bundle,
    build_production_evidence_manifest,
    build_production_evidence_template,
    build_production_flag_state,
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


def _format_production_evidence_template(template: dict[str, Any]) -> str:
    """Render a compact production evidence template summary."""

    artifacts = template["artifacts"]
    workflow_names = [
        workflow["name"] for workflow in artifacts["production_flag_state"]["workflows"]
    ]
    return "\n".join(
        [
            "runtime modernization production evidence template",
            "workflows: " + ", ".join(workflow_names),
            "artifacts: " + ", ".join(sorted(artifacts)),
        ]
    )


def _format_production_flag_state(flag_state: dict[str, Any]) -> str:
    """Render a compact production flag-state report."""

    lines = ["runtime modernization production flag state"]
    for workflow in flag_state["workflows"]:
        flags = workflow["serving_flags"]
        enabled = [name for name, value in flags.items() if value]
        disabled = [name for name, value in flags.items() if not value]
        lines.append(f"  {workflow['name']}")
        lines.append(f"    enabled: {', '.join(enabled) if enabled else 'none'}")
        lines.append(f"    disabled: {', '.join(disabled) if disabled else 'none'}")
    return "\n".join(lines)


def _format_operator_approval_evidence(approval: dict[str, Any]) -> str:
    """Render compact operator approval evidence."""

    lines = [
        "runtime modernization operator approval",
        f"  approved: {approval['approved']}",
        f"  boundary decision: {approval['boundary_decision']}",
        f"  rollout scope: {approval['rollout_scope']}",
        f"  approval reference: {approval['approval_reference']}",
    ]
    if "approver" in approval:
        lines.append(f"  approver: {approval['approver']}")
    if "notes" in approval:
        lines.append(f"  notes: {approval['notes']}")
    return "\n".join(lines)


def _format_operator_dashboard_snapshot(snapshot: dict[str, Any]) -> str:
    """Render compact operator dashboard snapshot evidence."""

    lines = [
        "runtime modernization operator dashboard snapshot",
        f"  snapshot reference: {snapshot['snapshot_reference']}",
    ]
    if "measurement_window" in snapshot:
        lines.append(f"  measurement window: {snapshot['measurement_window']}")
    if "notes" in snapshot:
        lines.append(f"  notes: {snapshot['notes']}")
    lines.append("  workflows:")
    for workflow_name, workflow in snapshot["workflows"].items():
        gates = workflow["gates"]
        passed = [
            name
            for name, gate in gates.items()
            if isinstance(gate, dict) and gate.get("passed") is True
        ]
        failed = [
            name
            for name, gate in gates.items()
            if isinstance(gate, dict) and gate.get("passed") is not True
        ]
        lines.append(f"    {workflow_name}")
        lines.append(f"      passed: {', '.join(passed) if passed else 'none'}")
        lines.append(f"      failed: {', '.join(failed) if failed else 'none'}")
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


def _format_completion_audit(audit: dict[str, Any]) -> str:
    """Render a compact runtime modernization completion audit."""

    lines = [f"runtime modernization completion audit: {audit['status']}"]
    for check in audit["phase_checks"]:
        marker = "PASS" if check["passed"] else "FAIL"
        lines.append(f"  {marker} {check['name']}: {check['message']}")
    return "\n".join(lines)


def _read_json_object(file: Any, label: str) -> dict[str, Any]:
    """Read one JSON object from a Click file handle."""

    try:
        payload = json.loads(file.read())
    except ValueError as ex:
        raise click.ClickException(f"Invalid {label} JSON: {ex}") from ex
    if not isinstance(payload, dict):
        raise click.ClickException(f"{label} JSON must be an object")
    return payload


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


@runtime_modernization.command("production-evidence-template")
@click.option(
    "--workflow",
    multiple=True,
    help="Optional rollout workflow name to include. Can be supplied more than once.",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(("text", "json")),
    default="json",
    show_default=True,
    help="Output format.",
)
def production_evidence_template(
    workflow: tuple[str, ...],
    output_format: str,
) -> None:
    """Print a fillable production evidence JSON bundle template."""

    try:
        workflows = (
            tuple(get_rollout_workflow(name) for name in workflow)
            if workflow
            else get_rollout_workflows()
        )
    except KeyError as ex:
        raise click.ClickException(str(ex)) from ex

    template = build_production_evidence_template(workflows)

    if output_format == "json":
        click.echo(json.dumps(template, sort_keys=True, indent=2))
        return

    click.echo(_format_production_evidence_template(template))


@runtime_modernization.command("production-flag-state")
@click.option(
    "--workflow",
    multiple=True,
    help="Optional rollout workflow name to include. Can be supplied more than once.",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(("text", "json")),
    default="json",
    show_default=True,
    help="Output format.",
)
@with_appcontext
def production_flag_state(
    workflow: tuple[str, ...],
    output_format: str,
) -> None:
    """Print runtime modernization serving flag state for this deployment."""

    try:
        workflows = (
            tuple(get_rollout_workflow(name) for name in workflow)
            if workflow
            else get_rollout_workflows()
        )
    except KeyError as ex:
        raise click.ClickException(str(ex)) from ex

    flag_state = build_production_flag_state(workflows, is_feature_enabled)

    if output_format == "json":
        click.echo(json.dumps(flag_state, sort_keys=True, indent=2))
        return

    click.echo(_format_production_flag_state(flag_state))


@runtime_modernization.command("operator-approval")
@click.option(
    "--boundary-decision",
    required=True,
    help="Accepted runtime ownership boundary decision.",
)
@click.option(
    "--rollout-scope",
    required=True,
    help="Approved rollout scope.",
)
@click.option(
    "--approval-reference",
    required=True,
    help="Change ticket, ADR sign-off, or release approval reference.",
)
@click.option(
    "--approved/--not-approved",
    default=True,
    show_default=True,
    help="Whether the operator approved this rollout scope.",
)
@click.option(
    "--approver",
    help="Optional operator or approval group name.",
)
@click.option(
    "--notes",
    help="Optional approval notes.",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(("text", "json")),
    default="json",
    show_default=True,
    help="Output format.",
)
def operator_approval(
    boundary_decision: str,
    rollout_scope: str,
    approval_reference: str,
    approved: bool,
    approver: str | None,
    notes: str | None,
    output_format: str,
) -> None:
    """Print operator approval evidence for runtime modernization rollout."""

    approval = build_operator_approval_evidence(
        boundary_decision=boundary_decision,
        rollout_scope=rollout_scope,
        approval_reference=approval_reference,
        approved=approved,
        approver=approver,
        notes=notes,
    )

    if output_format == "json":
        click.echo(json.dumps(approval, sort_keys=True, indent=2))
        return

    click.echo(_format_operator_approval_evidence(approval))


@runtime_modernization.command("operator-dashboard-snapshot")
@click.option(
    "--workflow",
    multiple=True,
    help="Optional rollout workflow name to include. Can be supplied more than once.",
)
@click.option(
    "--snapshot-reference",
    required=True,
    help="Dashboard export, screenshot, or observability record reference.",
)
@click.option(
    "--gates-passed/--gates-failed",
    default=False,
    show_default=True,
    help="Whether all selected workflow dashboard gates passed.",
)
@click.option(
    "--measurement-window",
    help="Optional production measurement window covered by the snapshot.",
)
@click.option(
    "--notes",
    help="Optional dashboard evidence notes.",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(("text", "json")),
    default="json",
    show_default=True,
    help="Output format.",
)
def operator_dashboard_snapshot(
    workflow: tuple[str, ...],
    snapshot_reference: str,
    gates_passed: bool,
    measurement_window: str | None,
    notes: str | None,
    output_format: str,
) -> None:
    """Print operator dashboard evidence for runtime modernization rollout."""

    try:
        workflows = (
            tuple(get_rollout_workflow(name) for name in workflow)
            if workflow
            else get_rollout_workflows()
        )
    except KeyError as ex:
        raise click.ClickException(str(ex)) from ex

    snapshot = build_operator_dashboard_snapshot(
        workflows,
        snapshot_reference=snapshot_reference,
        gates_passed=gates_passed,
        measurement_window=measurement_window,
        notes=notes,
    )

    if output_format == "json":
        click.echo(json.dumps(snapshot, sort_keys=True, indent=2))
        return

    click.echo(_format_operator_dashboard_snapshot(snapshot))


@runtime_modernization.command("assemble-production-evidence")
@click.option(
    "--compatibility-report",
    "compatibility_report_file",
    required=True,
    type=click.File("r"),
    help="Compatibility report JSON artifact.",
)
@click.option(
    "--rust-kernel-benchmark",
    "rust_kernel_benchmark_file",
    required=True,
    type=click.File("r"),
    help="Rust kernel benchmark JSON artifact.",
)
@click.option(
    "--production-flag-state",
    "production_flag_state_file",
    type=click.File("r"),
    help="Production feature flag state JSON artifact.",
)
@click.option(
    "--operator-dashboard-snapshot",
    "operator_dashboard_snapshot_file",
    type=click.File("r"),
    help="Operator dashboard gate JSON artifact.",
)
@click.option(
    "--operator-approval",
    "operator_approval_file",
    type=click.File("r"),
    help="Operator approval JSON artifact.",
)
@click.option(
    "--workflow",
    multiple=True,
    help="Optional rollout workflow name to validate. Can be supplied more than once.",
)
@click.option(
    "--validate",
    "validate_bundle",
    is_flag=True,
    help="Validate the assembled evidence bundle after printing it.",
)
@click.option(
    "--strict",
    is_flag=True,
    help="Exit with an error when assembled evidence validation fails.",
)
def assemble_production_evidence(
    compatibility_report_file: Any,
    rust_kernel_benchmark_file: Any,
    production_flag_state_file: Any | None,
    operator_dashboard_snapshot_file: Any | None,
    operator_approval_file: Any | None,
    workflow: tuple[str, ...],
    validate_bundle: bool,
    strict: bool,
) -> None:
    """Assemble collected production artifacts into one evidence bundle."""

    try:
        workflows = (
            tuple(get_rollout_workflow(name) for name in workflow)
            if workflow
            else get_rollout_workflows()
        )
    except KeyError as ex:
        raise click.ClickException(str(ex)) from ex

    bundle = build_production_evidence_bundle(
        compatibility_report=_read_json_object(
            compatibility_report_file,
            "compatibility report",
        ),
        rust_kernel_benchmark=_read_json_object(
            rust_kernel_benchmark_file,
            "Rust kernel benchmark",
        ),
        production_flag_state=_read_json_object(
            production_flag_state_file,
            "production flag state",
        )
        if production_flag_state_file is not None
        else None,
        operator_dashboard_snapshot=_read_json_object(
            operator_dashboard_snapshot_file,
            "operator dashboard snapshot",
        )
        if operator_dashboard_snapshot_file is not None
        else None,
        operator_approval=_read_json_object(
            operator_approval_file,
            "operator approval",
        )
        if operator_approval_file is not None
        else None,
    )

    click.echo(json.dumps(bundle, sort_keys=True, indent=2))

    if validate_bundle or strict:
        validation = validate_production_evidence(workflows, bundle)
        if validation["status"] != "passed":
            click.echo(_format_production_evidence_validation(validation), err=True)
        if strict and validation["status"] != "passed":
            raise click.ClickException(
                "runtime modernization production evidence failed"
            )


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

    evidence = _read_json_object(evidence_file, "evidence")

    validation = validate_production_evidence(workflows, evidence)

    if output_format == "json":
        click.echo(json.dumps(validation, sort_keys=True, indent=2))
    else:
        click.echo(_format_production_evidence_validation(validation))

    if strict and validation["status"] != "passed":
        raise click.ClickException("runtime modernization production evidence failed")


@runtime_modernization.command("completion-audit")
@click.argument("evidence_file", required=False, type=click.File("r"))
@click.option(
    "--workflow",
    multiple=True,
    help="Optional rollout workflow name to audit. Can be supplied more than once.",
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
    help="Exit with an error when phase completion audit is incomplete.",
)
def completion_audit(
    evidence_file: Any | None,
    workflow: tuple[str, ...],
    output_format: str,
    strict: bool,
) -> None:
    """Audit runtime modernization phase completion from production evidence."""

    try:
        workflows = (
            tuple(get_rollout_workflow(name) for name in workflow)
            if workflow
            else get_rollout_workflows()
        )
    except KeyError as ex:
        raise click.ClickException(str(ex)) from ex

    evidence = (
        _read_json_object(evidence_file, "evidence")
        if evidence_file is not None
        else {"schema_version": 1, "artifacts": {}}
    )
    audit = audit_runtime_modernization_completion(workflows, evidence)

    if output_format == "json":
        click.echo(json.dumps(audit, sort_keys=True, indent=2))
    else:
        click.echo(_format_completion_audit(audit))

    if strict and audit["status"] != "complete":
        raise click.ClickException("runtime modernization phases incomplete")


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

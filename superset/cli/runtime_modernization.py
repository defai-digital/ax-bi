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

from superset.runtime_modernization.inventory import (
    get_runtime_inventory,
    MigrationDisposition,
    RuntimeInventoryItem,
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

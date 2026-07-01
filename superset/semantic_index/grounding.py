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
"""Governed grounding contract for prompt-to-dashboard.

Semantic retrieval finds the *right dataset*; this module produces the governed
*business contract* for that dataset — certified measures with their real SQL
expressions, dimensions, time columns, a synonym glossary, and disambiguation
instructions. Injecting this contract into a prompt-to-dashboard call is what
lets an LLM select certified metric definitions instead of re-deriving
aggregations (which is where hallucinated SQL and wrong numbers come from).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from superset.semantic_index.governance import aliases_for, AliasMap


@dataclass(frozen=True)
class GroundingMeasure:
    """A certified measure (metric) the model should reuse verbatim."""

    name: str
    expression: str
    verbose_name: str = ""
    d3format: str = ""
    description: str = ""
    aliases: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class GroundingDimension:
    """A dimension (column) available for grouping/filtering."""

    name: str
    type: str = ""
    description: str = ""
    groupable: bool = False
    filterable: bool = False
    is_temporal: bool = False
    aliases: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class GroundingContract:
    """The governed context for one dataset, ready to inject into a prompt."""

    dataset_id: int | None
    dataset_name: str
    description: str
    database: str
    schema: str
    time_columns: list[str]
    dimensions: list[GroundingDimension]
    measures: list[GroundingMeasure]
    glossary: dict[str, list[str]]
    instructions: list[str]
    policies: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable form for tool responses."""

        return {
            "dataset_id": self.dataset_id,
            "dataset_name": self.dataset_name,
            "description": self.description,
            "database": self.database,
            "schema": self.schema,
            "time_columns": list(self.time_columns),
            "dimensions": [dimension.__dict__ for dimension in self.dimensions],
            "measures": [measure.__dict__ for measure in self.measures],
            "glossary": {key: list(value) for key, value in self.glossary.items()},
            "instructions": list(self.instructions),
            "policies": [dict(policy) for policy in self.policies],
        }

    def to_markdown(self) -> str:  # noqa: C901
        """Render the compact governed contract to inject into an LLM prompt."""

        lines: list[str] = [f"# Dataset: {self.dataset_name}"]
        if self.description:
            lines.append(self.description)
        source = ".".join(part for part in (self.database, self.schema) if part)
        if source:
            lines.append(f"Source: {source}")

        if self.instructions:
            lines.append("")
            lines.append("## Instructions (MUST follow)")
            for instruction in self.instructions:
                lines.append(f"- {instruction}")

        if self.policies:
            lines.append("")
            lines.append("## Policies (enforced)")
            for policy in self.policies:
                if policy.get("type") == "non_additive":
                    target = policy.get("target", "")
                    dims = ", ".join(policy.get("dimensions", []))
                    reason = policy.get("reason", "")
                    line = (
                        f"- Do NOT aggregate '{target}' across {dims} "
                        f"without grouping by or filtering to a single value"
                    )
                    if reason:
                        line += f" ({reason})"
                    lines.append(line)

        if self.measures:
            lines.append("")
            lines.append(
                "## Measures (use these certified definitions; do not re-derive)"
            )
            for measure in self.measures:
                parts = [f"- {measure.name}"]
                if measure.expression:
                    parts.append(f"= {measure.expression}")
                if measure.d3format:
                    parts.append(f"[format {measure.d3format}]")
                extra = " ".join(parts)
                notes = []
                if measure.description:
                    notes.append(measure.description)
                if measure.aliases:
                    notes.append(f"aka {', '.join(measure.aliases)}")
                if notes:
                    extra += " — " + "; ".join(notes)
                lines.append(extra)

        if self.dimensions:
            lines.append("")
            lines.append("## Dimensions")
            for dimension in self.dimensions:
                flags = []
                if dimension.is_temporal:
                    flags.append("time")
                if dimension.groupable:
                    flags.append("groupable")
                if dimension.filterable:
                    flags.append("filterable")
                extra = f"- {dimension.name}"
                if dimension.type:
                    extra += f" ({dimension.type})"
                if flags:
                    extra += " — " + ", ".join(flags)
                if dimension.aliases:
                    extra += f" [aka {', '.join(dimension.aliases)}]"
                lines.append(extra)

        if self.glossary:
            lines.append("")
            lines.append("## Glossary")
            for canonical, synonyms in self.glossary.items():
                lines.append(f"- {canonical}: {', '.join(synonyms)}")

        return "\n".join(lines)


def build_grounding_contract(  # noqa: C901
    dataset: Any,
    *,
    aliases: AliasMap | None = None,
    instructions: list[str] | None = None,
    policies: list[dict[str, Any]] | None = None,
) -> GroundingContract:
    """Build the governed grounding contract for a Superset SQL dataset."""

    def clean(value: Any) -> str:
        return "" if value is None else str(value).strip()

    dataset_id = getattr(dataset, "id", None)
    dataset_name = clean(getattr(dataset, "table_name", "")) or str(dataset_id)
    schema = clean(getattr(dataset, "schema", ""))
    database = clean(getattr(getattr(dataset, "database", None), "database_name", ""))
    description = clean(getattr(dataset, "description", ""))
    main_dttm = clean(getattr(dataset, "main_dttm_col", ""))

    dimensions: list[GroundingDimension] = []
    time_columns: list[str] = []
    for column in list(getattr(dataset, "columns", []) or []):
        name = clean(getattr(column, "column_name", ""))
        if not name:
            continue
        is_temporal = bool(getattr(column, "is_dttm", False)) or name == main_dttm
        if is_temporal and name not in time_columns:
            time_columns.append(name)
        dimensions.append(
            GroundingDimension(
                name=name,
                type=clean(getattr(column, "type", "")),
                description=clean(getattr(column, "description", "")),
                groupable=bool(getattr(column, "groupby", False)),
                filterable=bool(getattr(column, "filterable", False)),
                is_temporal=is_temporal,
                aliases=aliases_for(aliases, "column", name),
            )
        )

    measures: list[GroundingMeasure] = []
    for metric in list(getattr(dataset, "metrics", []) or []):
        name = clean(getattr(metric, "metric_name", ""))
        if not name:
            continue
        measures.append(
            GroundingMeasure(
                name=name,
                expression=clean(getattr(metric, "expression", "")),
                verbose_name=clean(getattr(metric, "verbose_name", "")),
                d3format=clean(getattr(metric, "d3format", "")),
                description=clean(getattr(metric, "description", "")),
                aliases=aliases_for(aliases, "metric", name),
            )
        )

    glossary: dict[str, list[str]] = {}
    for dimension in dimensions:
        if dimension.aliases:
            glossary[dimension.name] = dimension.aliases
    for measure in measures:
        if measure.aliases:
            glossary[measure.name] = measure.aliases
    dataset_aka = aliases_for(aliases, "dataset", dataset_name)
    if dataset_aka:
        glossary[dataset_name] = dataset_aka

    return GroundingContract(
        dataset_id=dataset_id,
        dataset_name=dataset_name,
        description=description,
        database=database,
        schema=schema,
        time_columns=time_columns,
        dimensions=dimensions,
        measures=measures,
        glossary=glossary,
        instructions=[clean(item) for item in (instructions or []) if clean(item)],
        policies=[policy for policy in (policies or []) if isinstance(policy, dict)],
    )

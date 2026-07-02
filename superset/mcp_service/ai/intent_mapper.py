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
"""Intent-to-chart mapping using LLM provider.

Translates natural language intent into a structured chart configuration
by combining dataset metadata with LLM reasoning.
"""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, Field

from superset.mcp_service.ai.llm_provider import LLMProvider

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You are a data visualization expert. Given a user's request and a dataset's
metadata (columns and metrics), produce a chart configuration.

RULES:
- Use ONLY column names and metric names that exist in the dataset metadata.
- ALWAYS obey any "Governed instructions (MUST follow)" in the metadata — these
  are authoritative business rules (for example, do not sum a value across a
  dimension, or a required filter). Never produce a config that violates them.
- Prefer the dataset's certified saved metrics over re-deriving an aggregate
  from a raw column. Use a raw-column aggregate only when no saved metric fits.
- Use the "Business glossary" to map the user's wording (synonyms) to the real
  column/metric names.
- For saved metrics (from the metrics list), use
  {"name": "<metric_name>", "saved_metric": true}.
  Do NOT add an aggregate when using saved_metric.
- For raw columns, use
  {"name": "<column_name>", "aggregate": "<SUM|COUNT|AVG|MIN|MAX>"}.
- chart_type must be one of: "xy", "big_number", "table", "pie", "pivot_table".
- For chart_type "xy", kind must be one of: "line", "bar", "area", "scatter".
- Set time_grain when a temporal column is used on the x-axis
  (PT1H, P1D, P1W, P1M, P1Y).
- Include filters only when the user's request implies filtering.
- confidence should be 0.0-1.0 based on how well the request maps to available data.
- explanation should briefly describe why you chose this chart type and these fields.
- If the request cannot be fulfilled with the available columns/metrics, set
  confidence below 0.3 and explain what is missing.
"""


class MetricSpec(BaseModel):
    """A single metric specification."""

    name: str = Field(description="Column name or metric name")
    aggregate: str | None = Field(
        default=None, description="Aggregate function for raw columns"
    )
    saved_metric: bool = Field(
        default=False, description="True if this is a saved metric"
    )
    sql_expression: str | None = Field(
        default=None, description="Custom SQL expression"
    )
    label: str | None = Field(default=None, description="Display label")


class DimensionSpec(BaseModel):
    """A single dimension specification."""

    name: str = Field(description="Column name")


class FilterSpec(BaseModel):
    """A single filter specification."""

    column: str = Field(description="Column to filter on")
    operator: str = Field(
        description="Filter operator (eq, ne, gt, lt, gte, lte, in, like)"
    )
    value: Any = Field(description="Filter value")


class IntentMapperResponse(BaseModel):
    """Structured response from the intent mapper."""

    config: dict[str, Any] | None = Field(
        default=None,
        description=(
            "Chart configuration dict compatible with GenerateChartRequest.config"
        ),
    )
    chart_type: str = Field(
        default="table",
        description="The viz_type that will be created",
    )
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Confidence score for the mapping",
    )
    explanation: str = Field(
        default="",
        description="Why this chart type and these fields were selected",
    )


def _governed_context(dataset: Any) -> str:
    """Return governed instructions + glossary from the semantic layer.

    This is the grounding that raw column/metric metadata lacks: authoritative
    business rules (for example, "do not sum across regions") and the synonym
    glossary. Degrades to an empty string if the semantic layer is unavailable
    so intent mapping never depends on it being configured.
    """

    try:
        from superset.semantic_index.governance import (
            load_dataset_aliases,
            load_dataset_instructions,
            load_dataset_policies,
        )
        from superset.semantic_index.grounding import build_grounding_contract

        dataset_id = getattr(dataset, "id", None)
        aliases = load_dataset_aliases(dataset_id) if dataset_id is not None else {}
        contract = build_grounding_contract(
            dataset,
            aliases=aliases,
            instructions=load_dataset_instructions(dataset),
            policies=load_dataset_policies(dataset),
        )
    except Exception:  # pylint: disable=broad-except
        return ""

    lines: list[str] = []
    if contract.instructions:
        lines.append("Governed instructions (MUST follow):")
        lines.extend(f"  - {instruction}" for instruction in contract.instructions)
    for policy in contract.policies:
        if policy.get("type") == "non_additive":
            target = policy.get("target", "")
            dims = ", ".join(policy.get("dimensions", []))
            lines.append(
                f"  - Do NOT aggregate '{target}' across {dims} without grouping "
                "by or filtering it to a single value."
            )
    if contract.glossary:
        lines.append("Business glossary (map synonyms to these names):")
        for canonical, synonyms in contract.glossary.items():
            lines.append(f"  - {canonical}: {', '.join(synonyms)}")
    return "\n".join(lines)


def _build_dataset_context(dataset: Any) -> str:  # noqa: C901
    """Build a compact text representation of the dataset for the LLM."""
    lines: list[str] = []
    name = getattr(dataset, "table_name", "unknown")
    lines.append(f"Dataset: {name}")
    if desc := getattr(dataset, "description", None) or "":
        lines.append(f"Description: {desc}")

    # Time columns
    time_cols = []
    for col in getattr(dataset, "columns", []) or []:
        if getattr(col, "is_dttm", False):
            time_cols.append(getattr(col, "column_name", ""))
    if time_cols:
        lines.append(f"Time columns: {', '.join(time_cols[:5])}")

    # All columns with types
    col_lines = []
    for col in getattr(dataset, "columns", []) or []:
        col_name = getattr(col, "column_name", "")
        col_type = str(getattr(col, "type", "UNKNOWN"))
        col_desc = getattr(col, "description", None) or ""
        entry = f"  - {col_name} ({col_type})"
        if col_desc:
            entry += f": {col_desc[:80]}"
        col_lines.append(entry)
    if col_lines:
        lines.append("Columns:")
        lines.extend(col_lines[:30])  # Cap at 30 to stay in context window

    # Saved metrics
    metric_lines = []
    for metric in getattr(dataset, "metrics", []) or []:
        m_name = getattr(metric, "metric_name", "")
        m_expr = getattr(metric, "expression", "")
        m_desc = getattr(metric, "description", None) or ""
        entry = f"  - {m_name}: {m_expr}"
        if m_desc:
            entry += f" ({m_desc[:60]})"
        metric_lines.append(entry)
    if metric_lines:
        lines.append("Saved metrics (use saved_metric=true):")
        lines.extend(metric_lines[:20])

    # Governed grounding (instructions + glossary) — the highest-signal context.
    if governed := _governed_context(dataset):
        lines.append(governed)

    return "\n".join(lines)


def map_intent_to_chart(
    prompt: str,
    dataset: Any,
    provider: LLMProvider,
) -> IntentMapperResponse:
    """Map natural language intent to a chart configuration using the LLM.

    Args:
        prompt: User's natural language request.
        dataset: Dataset ORM object with columns and metrics loaded.
        provider: Configured LLM provider instance.

    Returns:
        IntentMapperResponse with config, chart_type, confidence, and explanation.
    """
    dataset_context = _build_dataset_context(dataset)
    user_prompt = (
        f"User request: {prompt}\n\n"
        f"Dataset metadata:\n{dataset_context}\n\n"
        "Produce a chart configuration."
    )

    result = provider.complete_json(
        system_prompt=_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        response_schema=IntentMapperResponse,
        metadata={"action": "map_intent_to_chart", "prompt": prompt[:200]},
    )

    if not isinstance(result, IntentMapperResponse):
        result = IntentMapperResponse.model_validate(result)

    return result

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
"""Build generate_chart configs from structured chart intents.

Plan/orchestrator tools already know metrics, dimensions, and chart type.
Using those fields directly avoids re-interpreting natural language for each
chart (a major failure mode for external agents chaining MCP tools).
"""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

_XY_KINDS = frozenset({"line", "bar", "area", "scatter"})
_CHART_TYPES = frozenset(
    {"xy", "big_number", "table", "pie", "pivot_table", "mixed_timeseries"}
)


def has_structured_chart_fields(
    metrics: list[str] | None,
    dimensions: list[str] | None,
    chart_type: str | None,
) -> bool:
    """Return True when enough structured fields exist to skip NL mapping."""
    if chart_type and chart_type.strip().lower() in _CHART_TYPES:
        return True
    return bool(metrics) or bool(dimensions)


def _saved_metric_names(dataset: Any) -> set[str]:
    names: set[str] = set()
    for metric in getattr(dataset, "metrics", []) or []:
        name = getattr(metric, "metric_name", None)
        if name:
            names.add(str(name))
    return names


def _column_names(dataset: Any) -> set[str]:
    names: set[str] = set()
    for col in getattr(dataset, "columns", []) or []:
        name = getattr(col, "column_name", None)
        if name:
            names.add(str(name))
    return names


def _time_columns(dataset: Any) -> list[str]:
    cols: list[str] = []
    if main := getattr(dataset, "main_dttm_col", None):
        cols.append(str(main))
    for col in getattr(dataset, "columns", []) or []:
        name = getattr(col, "column_name", None)
        if not name:
            continue
        if getattr(col, "is_dttm", False) and str(name) not in cols:
            cols.append(str(name))
    return cols


def resolve_metric_ref(name: str, dataset: Any) -> dict[str, Any]:  # noqa: C901
    """Map a metric/column name to a ColumnRef-compatible dict."""
    cleaned = (name or "").strip()
    if not cleaned:
        return {"name": "count", "aggregate": "COUNT"}

    # Grounding / glossary first (business synonyms → certified measures)
    try:
        from axbi.mcp_service.ai.grounding_utils import (
            load_grounding_contract,
            resolve_name_via_grounding,
        )

        contract = load_grounding_contract(dataset)
        grounded = resolve_name_via_grounding(cleaned, contract, prefer="measure")
        if grounded:
            cleaned = grounded
    except Exception:  # pylint: disable=broad-except
        logger.debug("Grounding metric resolve skipped", exc_info=True)

    saved = _saved_metric_names(dataset)
    if cleaned in saved:
        return {"name": cleaned, "saved_metric": True}

    # Case-insensitive match for saved metrics
    for saved_name in saved:
        if saved_name.lower() == cleaned.lower():
            return {"name": saved_name, "saved_metric": True}

    columns = _column_names(dataset)
    if cleaned in columns:
        return {"name": cleaned, "aggregate": "SUM"}

    for col_name in columns:
        if col_name.lower() == cleaned.lower():
            return {"name": col_name, "aggregate": "SUM"}

    # Prefer saved metric over inventing aggregates when name is unknown
    if saved:
        # If user said something like "revenue" and we have no match, keep raw
        # aggregate attempt so validation can surface a clear error.
        return {"name": cleaned, "aggregate": "SUM"}

    return {"name": cleaned, "aggregate": "SUM"}


def resolve_dimension_name(name: str, dataset: Any) -> str:
    """Return the best-matching column name for a dimension string."""
    cleaned = (name or "").strip()
    if not cleaned:
        return cleaned

    try:
        from axbi.mcp_service.ai.grounding_utils import (
            load_grounding_contract,
            resolve_name_via_grounding,
        )

        contract = load_grounding_contract(dataset)
        grounded = resolve_name_via_grounding(cleaned, contract, prefer="dimension")
        if grounded:
            cleaned = grounded
    except Exception:  # pylint: disable=broad-except
        logger.debug("Grounding dimension resolve skipped", exc_info=True)

    columns = _column_names(dataset)
    if cleaned in columns:
        return cleaned
    for col_name in columns:
        if col_name.lower() == cleaned.lower():
            return col_name
    return cleaned


def _normalize_chart_type(chart_type: str | None) -> tuple[str, str]:  # noqa: C901
    """Return (chart_type, xy_kind)."""
    raw = (chart_type or "table").strip().lower()
    if raw in _XY_KINDS:
        return "xy", raw
    if raw.startswith("echarts_timeseries_"):
        kind = raw.removeprefix("echarts_timeseries_")
        return "xy", kind if kind in _XY_KINDS else "line"
    if raw in {"bar", "column"}:
        return "xy", "bar"
    if raw in {"line", "area", "scatter"}:
        return "xy", raw
    if raw in {"big_number", "big_number_total", "kpi"}:
        return "big_number", "big_number"
    if raw in {"pie", "donut", "doughnut"}:
        return "pie", "pie"
    if raw in {"pivot", "pivot_table", "pivot_table_v2"}:
        return "pivot_table", "pivot_table"
    if raw == "xy":
        return "xy", "bar"
    if raw == "table":
        return "table", "table"
    if raw in _CHART_TYPES:
        return raw, raw
    return "table", "table"


def _normalize_filters(filters: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for item in filters or []:
        if not isinstance(item, dict):
            continue
        column = item.get("column") or item.get("col")
        if not column:
            continue
        op = item.get("op") or item.get("operator") or item.get("opr") or "="
        # Map common text ops to chart schema ops
        op_map = {
            "eq": "=",
            "ne": "!=",
            "gt": ">",
            "lt": "<",
            "gte": ">=",
            "lte": "<=",
            "equals": "=",
            "not_equals": "!=",
        }
        op_str = str(op)
        op_str = op_map.get(op_str.lower(), op_str)
        if "value" not in item and "val" not in item:
            continue
        value = item.get("value", item.get("val"))
        normalized.append({"column": str(column), "op": op_str, "value": value})
    return normalized


def chart_config_from_structured_intent(  # noqa: C901
    *,
    chart_type: str | None,
    metrics: list[str] | None,
    dimensions: list[str] | None,
    filters: list[dict[str, Any]] | None = None,
    time_range: str | None = None,
    dataset: Any = None,
    kind: str | None = None,
) -> tuple[dict[str, Any] | None, str, float, str, list[str]]:
    """Build a generate_chart config from structured plan fields.

    Returns:
        (config, chart_type_label, confidence, explanation, warnings)
    """
    warnings: list[str] = []
    metric_names = [m for m in (metrics or []) if m]
    dimension_names = [d for d in (dimensions or []) if d]
    resolved_type, default_kind = _normalize_chart_type(chart_type)
    xy_kind = (kind or default_kind).lower() if (kind or default_kind) else "bar"
    if xy_kind not in _XY_KINDS:
        xy_kind = "bar"

    filter_configs = _normalize_filters(filters)
    time_cols = _time_columns(dataset) if dataset is not None else []

    if not metric_names and resolved_type != "table":
        # Tables can work with dimensions only; other charts need a metric.
        if dataset is not None:
            saved = list(_saved_metric_names(dataset))
            if saved:
                metric_names = [saved[0]]
                warnings.append(
                    f"No metrics in intent; defaulted to saved metric '{saved[0]}'."
                )
            else:
                cols = list(_column_names(dataset))
                # Prefer a numeric-looking name is hard without types; leave empty
                # and fail below if still empty for non-table charts.
                del cols

    metric_refs = [resolve_metric_ref(m, dataset) for m in metric_names]
    dim_names = [resolve_dimension_name(d, dataset) for d in dimension_names]

    explanation_parts = [
        f"Built chart config from structured intent (type={resolved_type})."
    ]
    if metric_names:
        explanation_parts.append(f"Metrics: {', '.join(metric_names)}.")
    if dim_names:
        explanation_parts.append(f"Dimensions: {', '.join(dim_names)}.")

    confidence = 0.75 if metric_names or dim_names else 0.45
    if chart_type:
        confidence = min(1.0, confidence + 0.1)

    config: dict[str, Any]

    if resolved_type == "big_number":
        if not metric_refs:
            return (
                None,
                "big_number",
                0.1,
                "Structured intent missing metrics for big_number.",
                warnings,
            )
        config = {"chart_type": "big_number", "metric": metric_refs[0]}
        if time_cols:
            config["show_trendline"] = True
            config["temporal_column"] = time_cols[0]
        if filter_configs:
            config["filters"] = filter_configs
        _note_time_range(time_range, warnings)
        return config, "big_number", confidence, " ".join(explanation_parts), warnings

    if resolved_type == "pie":
        if not metric_refs or not dim_names:
            return (
                None,
                "pie",
                0.15,
                "Pie chart requires at least one metric and one dimension.",
                warnings,
            )
        config = {
            "chart_type": "pie",
            "metric": metric_refs[0],
            "group_by": dim_names[0],
        }
        if filter_configs:
            config["filters"] = filter_configs
        _note_time_range(time_range, warnings)
        return config, "pie", confidence, " ".join(explanation_parts), warnings

    if resolved_type == "xy":
        if not metric_refs:
            return (
                None,
                f"echarts_timeseries_{xy_kind}",
                0.1,
                "Structured intent missing metrics for xy chart.",
                warnings,
            )
        # Prefer temporal x when available and no dimension, or when dimension
        # is itself a time column.
        x_name: str | None = None
        if dim_names:
            x_name = dim_names[0]
            if x_name in time_cols:
                xy_kind = xy_kind if xy_kind != "bar" else "line"
        elif time_cols:
            x_name = time_cols[0]
            xy_kind = "line" if xy_kind == "bar" else xy_kind
        else:
            # Group-by style bar without explicit x still needs an x axis;
            # fall back to first non-metric column if present.
            cols = list(_column_names(dataset)) if dataset is not None else []
            metric_set = {m.get("name") for m in metric_refs}
            for col in cols:
                if col not in metric_set:
                    x_name = col
                    break
        if not x_name:
            return (
                None,
                f"echarts_timeseries_{xy_kind}",
                0.15,
                "Structured intent missing a dimension/time column for xy chart.",
                warnings,
            )
        config = {
            "chart_type": "xy",
            "kind": xy_kind,
            "x": {"name": x_name},
            "y": metric_refs,
        }
        if x_name in time_cols:
            config["time_grain"] = _guess_time_grain(time_range)
        # Additional dimensions become series breakdown
        if len(dim_names) > 1:
            config["group_by"] = [{"name": d} for d in dim_names[1:]]
        if filter_configs:
            config["filters"] = filter_configs
        _note_time_range(time_range, warnings)
        return (
            config,
            f"echarts_timeseries_{xy_kind}",
            confidence,
            " ".join(explanation_parts),
            warnings,
        )

    if resolved_type == "pivot_table":
        if not metric_refs:
            return (
                None,
                "pivot_table",
                0.1,
                "Structured intent missing metrics for pivot_table.",
                warnings,
            )
        if not dim_names:
            return (
                None,
                "pivot_table",
                0.15,
                "Structured intent missing dimensions for pivot_table rows.",
                warnings,
            )
        config = {
            "chart_type": "pivot_table",
            "rows": [{"name": dim_names[0]}],
            "metrics": metric_refs,
        }
        if len(dim_names) > 1:
            config["columns"] = [{"name": d} for d in dim_names[1:3]]
        if filter_configs:
            config["filters"] = filter_configs
        _note_time_range(time_range, warnings)
        return (
            config,
            "pivot_table",
            confidence,
            " ".join(explanation_parts),
            warnings,
        )

    # table (default)
    columns: list[dict[str, Any]] = []
    for dim in dim_names:
        columns.append({"name": dim})
    for metric in metric_refs:
        columns.append(metric)
    if not columns and dataset is not None:
        for col in list(_column_names(dataset))[:8]:
            columns.append({"name": col})
    if not columns:
        return None, "table", 0.1, "Structured intent has no columns/metrics.", warnings
    config = {"chart_type": "table", "columns": columns}
    if filter_configs:
        config["filters"] = filter_configs
    _note_time_range(time_range, warnings)
    return config, "table", confidence, " ".join(explanation_parts), warnings


def _note_time_range(time_range: str | None, warnings: list[str]) -> None:
    """Record time_range as a non-blocking note.

    Typed chart configs do not accept a top-level time_range field; dashboard
    native filters and Explore defaults handle period selection. Surface the
    intent so callers can wire filters separately.
    """
    if time_range:
        warnings.append(
            f"Time range '{time_range}' noted on intent; apply via dashboard "
            "filters or Explore if needed."
        )


def _guess_time_grain(time_range: str | None) -> str:
    text = (time_range or "").lower()
    if re.search(r"\b(hour|hourly)\b", text):
        return "PT1H"
    if re.search(r"\b(day|daily)\b", text):
        return "P1D"
    if re.search(r"\b(week|weekly)\b", text):
        return "P1W"
    if re.search(r"\b(year|yearly|annual)\b", text):
        return "P1Y"
    if re.search(r"\b(quarter|quarterly)\b", text):
        return "P3M"
    return "P1M"

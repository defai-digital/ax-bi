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
"""Heuristic intent-to-chart mapping fallback.

When no LLM provider is configured, this module uses keyword matching and
dataset metadata inspection to produce a best-effort chart configuration.
This provides a functional (if less sophisticated) experience out of the box.
"""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# Keywords that hint at specific chart types
_TREND_KEYWORDS = re.compile(
    r"\b(trend|over time|timeline|history|monthly|weekly|daily|yearly|quarterly)\b",
    re.IGNORECASE,
)
_COMPARISON_KEYWORDS = re.compile(
    r"\b(compare|comparison|ranking|top|bottom|versus|vs\.?|by)\b",
    re.IGNORECASE,
)
_PROPORTION_KEYWORDS = re.compile(
    r"\b(share|proportion|percentage|breakdown|distribution|split|composition)\b",
    re.IGNORECASE,
)
_SINGLE_VALUE_KEYWORDS = re.compile(
    r"\b(total|count|sum|average|single|kpi|headline|big number|overview)\b",
    re.IGNORECASE,
)
_TABLE_KEYWORDS = re.compile(
    r"\b(list|table|detail|all rows|raw data|export|grid)\b",
    re.IGNORECASE,
)
_EXPLICIT_CHART_TYPE_PATTERNS: tuple[tuple[re.Pattern[str], str, str, str], ...] = (
    (
        re.compile(r"\b(bar|column)\s+(chart|graph|plot)\b", re.IGNORECASE),
        "xy",
        "bar",
        "Detected explicit bar chart request.",
    ),
    (
        re.compile(r"\bscatter\s+(chart|graph|plot)\b", re.IGNORECASE),
        "xy",
        "scatter",
        "Detected explicit scatter chart request.",
    ),
    (
        re.compile(r"\bline\s+(chart|graph|plot)\b", re.IGNORECASE),
        "xy",
        "line",
        "Detected explicit line chart request.",
    ),
    (
        re.compile(r"\barea\s+(chart|graph|plot)\b", re.IGNORECASE),
        "xy",
        "area",
        "Detected explicit area chart request.",
    ),
    (
        re.compile(r"\b(pie|donut|doughnut)\s+(chart|graph|plot)\b", re.IGNORECASE),
        "pie",
        "pie",
        "Detected explicit pie chart request.",
    ),
    (
        re.compile(r"\b(table|grid)\s+(chart|view|visualization)\b", re.IGNORECASE),
        "table",
        "table",
        "Detected explicit table request.",
    ),
)
_DIMENSION_PHRASE = re.compile(
    r"\b(?:by|per|group(?:ed)?\s+by|split\s+by|broken\s+down\s+by)\s+"
    r"([a-zA-Z_][\w\s-]*?)(?=\s+(?:showing|using|with|where|for|named|name|"
    r"sorted|colored|coloured|and|as)\b|[.,;!?]|$)",
    re.IGNORECASE,
)


def _normalize_column_token(value: str) -> str:
    """Normalize a prompt phrase or column name for matching."""
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def _find_time_column(dataset: Any) -> str | None:
    """Find the primary time column in a dataset."""
    # Check main_dttm_col first
    if main_col := getattr(dataset, "main_dttm_col", None):
        return main_col
    # Fall back to first datetime column
    for col in getattr(dataset, "columns", []) or []:
        if getattr(col, "is_dttm", False):
            return getattr(col, "column_name", None)
    return None


def _find_first_metric(
    dataset: Any, prefer_saved: bool = True
) -> dict[str, Any] | None:
    """Find the first usable metric."""
    if prefer_saved:
        metrics = getattr(dataset, "metrics", []) or []
        if metrics:
            m = metrics[0]
            return {
                "name": getattr(m, "metric_name", "count"),
                "saved_metric": True,
            }

    # Fall back to first numeric column with COUNT
    for col in getattr(dataset, "columns", []) or []:
        col_name = getattr(col, "column_name", "")
        col_type = str(getattr(col, "type", "")).upper()
        if any(t in col_type for t in ("INT", "FLOAT", "NUMERIC", "DECIMAL", "DOUBLE")):
            return {"name": col_name, "aggregate": "SUM"}

    # Last resort: count all rows
    return (
        {"name": "count", "saved_metric": True}
        if (
            getattr(dataset, "metrics", None)
            and any(getattr(m, "metric_name", "") == "count" for m in dataset.metrics)
        )
        else None
    )


def _find_first_dimension(dataset: Any) -> str | None:
    """Find a reasonable dimension column."""
    for col in getattr(dataset, "columns", []) or []:
        if getattr(col, "is_dttm", False):
            continue
        col_name = getattr(col, "column_name", "")
        col_type = str(getattr(col, "type", "")).upper()
        # Prefer string/categorical columns
        if any(t in col_type for t in ("VARCHAR", "TEXT", "STRING", "CHAR")):
            return col_name
    # Fall back to any non-time column
    for col in getattr(dataset, "columns", []) or []:
        if not getattr(col, "is_dttm", False):
            return getattr(col, "column_name", None)
    return None


def _find_dimension_from_prompt(prompt: str, dataset: Any) -> str | None:
    """Find a requested dimension column from prompt phrases like 'by region'."""
    columns = [
        getattr(col, "column_name", "")
        for col in getattr(dataset, "columns", []) or []
        if getattr(col, "column_name", "")
    ]
    if not columns:
        return None

    normalized_columns = {_normalize_column_token(col): col for col in columns}
    for match in _DIMENSION_PHRASE.finditer(prompt):
        requested = _normalize_column_token(match.group(1))
        if not requested:
            continue
        if requested in normalized_columns:
            return normalized_columns[requested]
        for normalized, column in normalized_columns.items():
            if requested in normalized or normalized in requested:
                return column

    return None


def _detect_chart_type(prompt: str, dataset: Any) -> tuple[str, str, str]:
    """Detect the best chart type from keywords.

    Returns:
        Tuple of (chart_type, kind_or_subtype, explanation).
    """
    for pattern, chart_type, kind, explanation in _EXPLICIT_CHART_TYPE_PATTERNS:
        if pattern.search(prompt):
            return chart_type, kind, explanation

    if _SINGLE_VALUE_KEYWORDS.search(prompt):
        return "big_number", "big_number", "Detected request for a single KPI metric."

    if _TREND_KEYWORDS.search(prompt):
        time_col = _find_time_column(dataset)
        if time_col:
            return (
                "xy",
                "line",
                f"Detected time-series request (time column: {time_col}).",
            )
        return (
            "xy",
            "bar",
            "Trend keywords found but no time column detected; using bar chart.",
        )

    if _PROPORTION_KEYWORDS.search(prompt):
        return "pie", "pie", "Detected request for proportional/breakdown data."

    if _TABLE_KEYWORDS.search(prompt):
        return "table", "table", "Detected request for tabular data."

    if _COMPARISON_KEYWORDS.search(prompt):
        return "xy", "bar", "Detected comparison request; using bar chart."

    # Default: table is the safest fallback
    return (
        "table",
        "table",
        "No specific chart type detected; defaulting to table view.",
    )


def heuristic_chart_config(  # noqa: C901
    prompt: str,
    dataset: Any,
    warnings: list[str],
) -> tuple[dict[str, Any] | None, str, float, str, list[str]]:
    """Build a chart configuration using heuristic keyword matching.

    Args:
        prompt: User's natural language request.
        dataset: Dataset ORM object with columns and metrics.
        warnings: Accumulated warnings list to append to.

    Returns:
        Tuple of (config_dict, chart_type, confidence, explanation, warnings).
    """
    chart_type, kind, type_explanation = _detect_chart_type(prompt, dataset)
    confidence = 0.4  # Low confidence for heuristic

    # Build config based on detected type
    if chart_type == "big_number":
        metric = _find_first_metric(dataset)
        if not metric:
            warnings.append("No suitable metric found for big number chart.")
            return (
                None,
                chart_type,
                0.1,
                "Could not find a metric to display.",
                warnings,
            )

        config: dict[str, Any] = {
            "chart_type": "big_number",
            "metric": metric,
        }

        # Add trendline if time column exists
        time_col = _find_time_column(dataset)
        if time_col:
            config["show_trendline"] = True
            config["temporal_column"] = time_col
            type_explanation += f" Added trendline using {time_col}."

        return config, "big_number", confidence, type_explanation, warnings

    if chart_type == "xy":
        metric = _find_first_metric(dataset)
        time_col = _find_time_column(dataset)
        dimension = _find_dimension_from_prompt(prompt, dataset) or (
            _find_first_dimension(dataset)
        )

        if not metric:
            warnings.append("No suitable metric found.")
            return None, chart_type, 0.1, "Could not find a metric.", warnings

        # Use time column for x-axis if available, otherwise use a dimension
        x_col = time_col or dimension
        if not x_col:
            warnings.append("No suitable x-axis column found.")
            return None, chart_type, 0.1, "Could not find an x-axis column.", warnings

        config = {
            "chart_type": "xy",
            "kind": kind,
            "x": {"name": x_col},
            "y": [metric],
        }

        # Add time_grain for temporal x-axis
        if time_col and x_col == time_col:
            # Guess grain from prompt
            grain = "P1M"  # Default monthly
            if re.search(r"\b(daily|day)\b", prompt, re.IGNORECASE):
                grain = "P1D"
            elif re.search(r"\b(weekly|week)\b", prompt, re.IGNORECASE):
                grain = "P1W"
            elif re.search(r"\b(yearly|year|annual)\b", prompt, re.IGNORECASE):
                grain = "P1Y"
            elif re.search(r"\b(hourly|hour)\b", prompt, re.IGNORECASE):
                grain = "PT1H"
            config["time_grain"] = grain

        return (
            config,
            f"echarts_timeseries_{kind}",
            confidence,
            type_explanation,
            warnings,
        )

    if chart_type == "pie":
        metric = _find_first_metric(dataset)
        dimension = _find_first_dimension(dataset)

        if not metric or not dimension:
            warnings.append("Pie chart requires at least one metric and one dimension.")
            return None, chart_type, 0.1, "Missing data for pie chart.", warnings

        config = {
            "chart_type": "pie",
            "metric": metric,
            "group_by": dimension,
        }
        return config, "pie", confidence, type_explanation, warnings

    # Default: table
    columns: list[dict[str, Any]] = []
    for col in (getattr(dataset, "columns", []) or [])[:10]:
        col_name = getattr(col, "column_name", "")
        col_type = str(getattr(col, "type", "")).upper()
        col_spec: dict[str, Any] = {"name": col_name}
        if any(t in col_type for t in ("INT", "FLOAT", "NUMERIC", "DECIMAL")):
            col_spec["aggregate"] = "SUM"
        columns.append(col_spec)

    if not columns:
        warnings.append("No columns found in dataset.")
        return None, "table", 0.1, "Dataset has no columns.", warnings

    config = {
        "chart_type": "table",
        "columns": columns,
    }
    return config, "table", confidence, type_explanation, warnings

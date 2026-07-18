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
"""Data-minimization policy for GenAI prompt payloads.

Bounded samples (row/column excerpts) are denied by default. Operators enable
them via ``GENAI_LLM_ALLOW_BOUNDED_SAMPLES`` when metadata alone is insufficient.
"""

from __future__ import annotations

import logging
from typing import Any

from flask import current_app, has_app_context

logger = logging.getLogger(__name__)

# Hard ceilings even when Admin enables samples.
DEFAULT_MAX_SAMPLE_ROWS = 5
DEFAULT_MAX_SAMPLE_COLUMNS = 10
ABSOLUTE_MAX_SAMPLE_ROWS = 20
ABSOLUTE_MAX_SAMPLE_COLUMNS = 40
MAX_SAMPLE_VALUE_CHARS = 100


def _config_get(key: str, default: Any = None) -> Any:
    if not has_app_context():
        return default
    try:
        return current_app.config.get(key, default)
    except RuntimeError:
        return default


def _as_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "on"}:
        return True
    if text in {"0", "false", "no", "off", ""}:
        return False
    return default


def _as_int(value: Any, default: int, *, minimum: int, maximum: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = default
    return max(minimum, min(maximum, number))


def bounded_samples_allowed() -> bool:
    """Return True when Admin/operator policy permits bounded sample values."""
    return _as_bool(
        _config_get("GENAI_LLM_ALLOW_BOUNDED_SAMPLES", False),
        default=False,
    )


def sample_limits() -> tuple[int, int]:
    """Return (max_rows, max_columns) caps for bounded samples."""
    max_rows = _as_int(
        _config_get("GENAI_LLM_BOUNDED_SAMPLE_MAX_ROWS", DEFAULT_MAX_SAMPLE_ROWS),
        DEFAULT_MAX_SAMPLE_ROWS,
        minimum=1,
        maximum=ABSOLUTE_MAX_SAMPLE_ROWS,
    )
    max_columns = _as_int(
        _config_get(
            "GENAI_LLM_BOUNDED_SAMPLE_MAX_COLUMNS",
            DEFAULT_MAX_SAMPLE_COLUMNS,
        ),
        DEFAULT_MAX_SAMPLE_COLUMNS,
        minimum=1,
        maximum=ABSOLUTE_MAX_SAMPLE_COLUMNS,
    )
    return max_rows, max_columns


def should_include_samples(requested: bool) -> bool:
    """Gate client requests for sample values behind operator policy."""
    return bool(requested) and bounded_samples_allowed()


def sanitize_sample_value(value: Any) -> str | None:
    """Coerce a cell value into a short string safe for LLM context."""
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if len(text) > MAX_SAMPLE_VALUE_CHARS:
        return text[: MAX_SAMPLE_VALUE_CHARS - 1] + "…"
    return text


def _samples_for_column(
    dataset: Any, col_name: str, *, limit_rows: int
) -> list[str]:
    """Best-effort sample list for one column; empty on failure."""
    try:
        raw_values = dataset.values_for_column(col_name, limit=limit_rows)
    except Exception:  # pylint: disable=broad-except
        logger.debug(
            "values_for_column failed for %s", col_name, exc_info=True
        )
        return []
    cleaned: list[str] = []
    for raw in raw_values or []:
        item = sanitize_sample_value(raw)
        if item is not None and item not in cleaned:
            cleaned.append(item)
        if len(cleaned) >= limit_rows:
            break
    return cleaned


def fetch_bounded_column_samples(
    dataset: Any,
    *,
    max_rows: int | None = None,
    max_columns: int | None = None,
) -> dict[str, list[str]]:
    """Fetch distinct-ish sample values per column with hard caps.

    Returns an empty dict when policy denies samples or fetch fails.
    Never raises — sample enrichment is best-effort only.
    """
    if not bounded_samples_allowed() or dataset is None:
        return {}

    limit_rows, limit_cols = sample_limits()
    if max_rows is not None:
        limit_rows = min(limit_rows, max_rows)
    if max_columns is not None:
        limit_cols = min(limit_cols, max_columns)

    columns = list(getattr(dataset, "columns", None) or [])[:limit_cols]
    samples: dict[str, list[str]] = {}
    for col in columns:
        col_name = getattr(col, "column_name", None) or getattr(col, "name", None)
        if not col_name:
            continue
        cleaned = _samples_for_column(dataset, str(col_name), limit_rows=limit_rows)
        if cleaned:
            samples[str(col_name)] = cleaned
    return samples

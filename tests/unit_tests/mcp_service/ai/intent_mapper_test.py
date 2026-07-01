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
"""Tests for grounding-contract injection into intent mapping."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from superset.mcp_service.ai.intent_mapper import (
    _build_dataset_context,
    _governed_context,
)

_GOVERNANCE = "superset.semantic_index.governance"


def _dataset() -> SimpleNamespace:
    return SimpleNamespace(
        id=11,
        table_name="service_revenue_2025",
        description="Service revenue by client (LCY).",
        main_dttm_col="month_date",
        schema="public",
        database=SimpleNamespace(database_name="analytics"),
        columns=[
            SimpleNamespace(
                column_name="client",
                type="VARCHAR",
                is_dttm=False,
                groupby=True,
                filterable=True,
                description=None,
            ),
            SimpleNamespace(
                column_name="month_date",
                type="TIMESTAMP",
                is_dttm=True,
                groupby=True,
                filterable=True,
                description=None,
            ),
        ],
        metrics=[
            SimpleNamespace(
                metric_name="total_revenue",
                expression="SUM(revenue)",
                verbose_name="",
                d3format=",.0f",
                description=None,
            )
        ],
    )


def test_governed_context_includes_instructions_and_glossary() -> None:
    with (
        patch(
            f"{_GOVERNANCE}.load_dataset_aliases",
            return_value={("metric", "total_revenue"): ["turnover", "sales"]},
        ),
        patch(
            f"{_GOVERNANCE}.load_dataset_instructions",
            return_value=["Amounts are LCY; do not sum across regions."],
        ),
    ):
        context = _governed_context(_dataset())

    assert "Governed instructions (MUST follow):" in context
    assert "do not sum across regions" in context
    assert "total_revenue: turnover, sales" in context


def test_build_dataset_context_appends_governed_block() -> None:
    with (
        patch(f"{_GOVERNANCE}.load_dataset_aliases", return_value={}),
        patch(
            f"{_GOVERNANCE}.load_dataset_instructions",
            return_value=["Required filter: fiscal_year = 2025."],
        ),
    ):
        context = _build_dataset_context(_dataset())

    # Existing metadata still present...
    assert "Saved metrics (use saved_metric=true):" in context
    assert "total_revenue: SUM(revenue)" in context
    # ...and the governed grounding is appended.
    assert "Required filter: fiscal_year = 2025." in context


def test_governed_context_degrades_gracefully() -> None:
    with patch(
        f"{_GOVERNANCE}.load_dataset_instructions",
        side_effect=RuntimeError("no table"),
    ):
        assert _governed_context(_dataset()) == ""

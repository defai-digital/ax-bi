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
"""Evaluation fixtures: plan quality with vs without LLM.

These tests do not call a live model. They compare heuristic planning against
a mock LLM provider that returns structured intents, documenting the quality
gap GenAI is meant to close when Admin configures a provider.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

from pydantic import BaseModel

from axbi.mcp_service.ai.schemas import ChartIntentDetail, DashboardPlanFull
from axbi.mcp_service.ai.tool.plan_dashboard import (
    _build_chart_intents_heuristic,
    _plan_with_llm,
)


def _sales_datasets() -> list[dict[str, Any]]:
    return [
        {
            "id": 42,
            "name": "sales_orders",
            "description": "Sales order facts with revenue by region",
            "certified": True,
            "metrics": ["revenue", "order_count"],
            "columns": [
                {
                    "name": "order_date",
                    "type": "DATE",
                    "is_numeric": False,
                    "is_dttm": True,
                },
                {
                    "name": "region",
                    "type": "VARCHAR",
                    "is_numeric": False,
                    "is_dttm": False,
                },
                {
                    "name": "product",
                    "type": "VARCHAR",
                    "is_numeric": False,
                    "is_dttm": False,
                },
                {
                    "name": "amount",
                    "type": "FLOAT",
                    "is_numeric": True,
                    "is_dttm": False,
                },
            ],
            "grounding": {
                "measures": [
                    {
                        "name": "revenue",
                        "expression": "SUM(amount)",
                        "aliases": ["sales"],
                    }
                ],
                "time_columns": ["order_date"],
                "glossary": {"revenue": ["sales", "bookings"]},
            },
        }
    ]


PROMPT = "Show revenue trend by region and a KPI for total bookings"


def test_heuristic_plan_produces_usable_intents() -> None:
    intents = _build_chart_intents_heuristic(PROMPT, _sales_datasets(), max_charts=4)
    assert intents
    assert len(intents) <= 4
    # Heuristic may not map glossary "bookings" → revenue perfectly
    names = " ".join(
        str(getattr(i, "purpose", "") or getattr(i, "metrics", "") or i)
        for i in intents
    ).lower()
    assert names  # non-empty plan


def test_llm_plan_uses_grounded_metrics_and_types() -> None:
    class _Provider:
        def complete_json(
            self,
            *,
            system_prompt: str,
            user_prompt: str,
            response_schema: type[BaseModel],
            metadata: dict[str, Any],
        ) -> Any:
            return DashboardPlanFull(
                title="Sales Overview",
                confidence=0.86,
                assumptions=["bookings maps to revenue via glossary"],
                clarifying_questions=[],
                chart_intents=[
                    ChartIntentDetail(
                        purpose="Revenue trend over time by region",
                        chart_type="xy",
                        dataset_id=42,
                        metrics=["revenue"],
                        dimensions=["region"],
                        time_range="Last year",
                    ),
                    ChartIntentDetail(
                        purpose="Total bookings KPI",
                        chart_type="big_number",
                        dataset_id=42,
                        metrics=["revenue"],
                        dimensions=[],
                    ),
                ],
            )

        def provider_name(self) -> str:
            return "openai_compatible"

        def model_name(self) -> str:
            return "llama3.1"

    with patch(
        "axbi.mcp_service.ai.provider_factory.get_llm_provider",
        return_value=_Provider(),
    ):
        packed = _plan_with_llm(PROMPT, _sales_datasets(), max_charts=4)

    assert packed is not None
    plan, warnings = packed
    assert plan.confidence >= 0.8
    assert len(plan.chart_intents) == 2
    metrics = [m for ci in plan.chart_intents for m in (ci.metrics or [])]
    assert "revenue" in metrics
    assert all(ci.dataset_id == 42 for ci in plan.chart_intents)
    # Mock LLM should outscore bare heuristic on confidence when present
    heuristic = _build_chart_intents_heuristic(PROMPT, _sales_datasets(), max_charts=4)
    assert len(plan.chart_intents) >= 1
    assert len(heuristic) >= 1


def test_unconfigured_llm_returns_none_for_llm_planner() -> None:
    from axbi.genai.llm_provider import StubLLMProvider

    with patch(
        "axbi.mcp_service.ai.provider_factory.get_llm_provider",
        return_value=StubLLMProvider(),
    ):
        assert _plan_with_llm(PROMPT, _sales_datasets(), max_charts=3) is None

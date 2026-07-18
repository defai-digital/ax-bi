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
"""Tests for semantic assist (heuristic + LLM factory path)."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch

from pydantic import BaseModel

from axbi.genai.llm_provider import LLMProvider, StubLLMProvider
from axbi.genai.semantic_assist import (
    heuristic_semantic_suggestions,
    SemanticSuggestion,
    suggest_semantic_enrichment,
)


def _dataset() -> SimpleNamespace:
    return SimpleNamespace(
        table_name="sales_orders",
        description="Order facts",
        columns=[
            SimpleNamespace(
                column_name="customer_id",
                type="INTEGER",
                description="",
                is_dttm=False,
                expression=None,
            ),
            SimpleNamespace(
                column_name="region",
                type="VARCHAR",
                description="Sales region",
                is_dttm=False,
                expression=None,
            ),
            SimpleNamespace(
                column_name="order_date",
                type="DATE",
                description="",
                is_dttm=True,
                expression=None,
            ),
        ],
        metrics=[
            SimpleNamespace(
                metric_name="revenue",
                expression="SUM(amount)",
                description="",
            )
        ],
    )


class _FakeProvider(LLMProvider):
    def complete_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_schema: type[BaseModel],
        metadata: dict[str, Any],
    ) -> Any:
        return response_schema(
            suggestions=[
                SemanticSuggestion(
                    object_type="column",
                    object_name="region",
                    suggestion_type="synonym",
                    value="Territory",
                    confidence=0.9,
                    rationale="Business synonym",
                ),
                SemanticSuggestion(
                    object_type="column",
                    object_name="customer_id",
                    suggestion_type="relationship",
                    value="References customer dimension",
                    related_object="customer",
                    confidence=0.8,
                    rationale="FK pattern",
                ),
            ]
        )

    def provider_name(self) -> str:
        return "openai_compatible"

    def model_name(self) -> str:
        return "llama3.1"


def test_heuristic_suggests_synonyms_and_fk_relationships() -> None:
    result = heuristic_semantic_suggestions(_dataset())
    assert result.used_llm is False
    types = {s.suggestion_type for s in result.suggestions}
    assert "synonym" in types
    assert "relationship" in types
    assert any(s.object_name == "customer_id" for s in result.suggestions)
    assert any("LLM" in w or "heuristic" in w.lower() for w in result.warnings)


def test_heuristic_fk_related_object_is_not_self() -> None:
    """FK heuristics must not set related_object to the same column name."""
    result = heuristic_semantic_suggestions(_dataset())
    fk_hits = [
        s
        for s in result.suggestions
        if s.suggestion_type == "relationship" and s.object_name == "customer_id"
    ]
    assert fk_hits
    for hit in fk_hits:
        assert hit.related_object != "customer_id"
        assert hit.related_object == "customer"


def test_heuristic_does_not_treat_bare_id_as_fk() -> None:
    dataset = SimpleNamespace(
        table_name="items",
        description="",
        columns=[
            SimpleNamespace(column_name="id", type="INTEGER", description=""),
            SimpleNamespace(column_name="name", type="VARCHAR", description=""),
        ],
        metrics=[],
    )
    result = heuristic_semantic_suggestions(dataset)
    assert not any(
        s.object_name == "id" and s.suggestion_type == "relationship"
        for s in result.suggestions
    )


def test_llm_path_uses_factory_provider() -> None:
    with patch(
        "axbi.genai.semantic_assist.get_llm_provider",
        return_value=_FakeProvider(),
    ), patch("axbi.genai.audit.event_logger"), patch(
        "axbi.genai.audit.stats_logger_manager"
    ) as sl:
        sl.instance.incr = MagicMock()
        result = suggest_semantic_enrichment(_dataset())
    assert result.used_llm is True
    assert result.provider_type == "openai_compatible"
    assert any(s.value == "Territory" for s in result.suggestions)


def test_stub_provider_falls_back_to_heuristic() -> None:
    with patch(
        "axbi.genai.semantic_assist.get_llm_provider",
        return_value=StubLLMProvider(),
    ):
        result = suggest_semantic_enrichment(_dataset())
    assert result.used_llm is False
    assert result.suggestions


class _InventingProvider(LLMProvider):
    def complete_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_schema: type[BaseModel],
        metadata: dict[str, Any],
    ) -> Any:
        return response_schema(
            suggestions=[
                SemanticSuggestion(
                    object_type="column",
                    object_name="region",
                    suggestion_type="synonym",
                    value="Territory",
                    confidence=0.9,
                ),
                SemanticSuggestion(
                    object_type="column",
                    object_name="not_a_real_column",
                    suggestion_type="description",
                    value="Invented",
                    confidence=0.9,
                ),
                SemanticSuggestion(
                    object_type="column",
                    object_name="customer_id",
                    suggestion_type="relationship",
                    value="Self loop",
                    related_object="customer_id",
                    confidence=0.9,
                ),
            ]
        )

    def provider_name(self) -> str:
        return "openai_compatible"

    def model_name(self) -> str:
        return "test-model"


def test_llm_path_drops_unknown_object_names_and_self_related() -> None:
    with patch(
        "axbi.genai.semantic_assist.get_llm_provider",
        return_value=_InventingProvider(),
    ), patch("axbi.genai.audit.event_logger"), patch(
        "axbi.genai.audit.stats_logger_manager"
    ) as sl:
        sl.instance.incr = MagicMock()
        result = suggest_semantic_enrichment(_dataset())
    assert result.used_llm is True
    names = {s.object_name for s in result.suggestions}
    assert "not_a_real_column" not in names
    assert "region" in names
    for s in result.suggestions:
        if s.object_name == "customer_id" and s.suggestion_type == "relationship":
            assert s.related_object != "customer_id"
    assert any("Dropped" in w for w in result.warnings)

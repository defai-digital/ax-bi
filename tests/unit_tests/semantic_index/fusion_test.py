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
"""Tests for hybrid-retrieval helpers (tokenizer + rank fusion)."""

from __future__ import annotations

from axbi.semantic_index.repository import (
    _query_tokens,
    _reciprocal_rank_fusion,
)
from axbi.semantic_index.types import SemanticSearchResult


def _result(object_id: str, distance: float | None = None) -> SemanticSearchResult:
    return SemanticSearchResult(
        uuid=object_id,
        object_type="column",
        object_id=object_id,
        object_name=object_id,
        document_kind="column_profile",
        content=object_id,
        distance=distance,
    )


def test_query_tokens_drops_stopwords_and_dedups() -> None:
    tokens = _query_tokens("Which clients generate the most REVENUE revenue?")
    assert "the" not in tokens  # stopword
    assert "which" not in tokens  # stopword
    assert tokens.count("revenue") == 1  # de-duplicated + lowercased
    assert "clients" in tokens
    assert "generate" in tokens


def test_rrf_rewards_agreement_across_retrievers() -> None:
    dense = [_result("a", 0.1), _result("b", 0.2), _result("c", 0.3)]
    lexical = [_result("c"), _result("a"), _result("d")]

    fused = _reciprocal_rank_fusion([dense, lexical], limit=4)
    ids = [r.object_id for r in fused]

    # 'a' (rank0 dense, rank1 lexical) and 'c' (rank2 dense, rank0 lexical)
    # both appear in both lists, so they outrank the single-list items.
    assert set(ids[:2]) == {"a", "c"}
    assert set(ids) == {"a", "b", "c", "d"}  # union, de-duplicated


def test_rrf_keeps_dense_distance_for_display() -> None:
    dense = [_result("a", 0.42)]
    lexical = [_result("a", None)]
    fused = _reciprocal_rank_fusion([dense, lexical], limit=1)
    assert fused[0].distance == 0.42  # representative carries the dense distance


def test_rrf_respects_limit() -> None:
    dense = [_result(x) for x in "abcdef"]
    assert len(_reciprocal_rank_fusion([dense], limit=3)) == 3

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
"""Tests for semantic embedding providers."""

from __future__ import annotations

import math
from typing import Any, cast

import pytest

from axbi.semantic_index.embedding import (
    _validate_embeddings,
    build_query_text,
    EmbeddingProviderError,
    HashDevEmbeddingProvider,
)
from axbi.semantic_index.repository import vector_literal


def test_build_query_text_adds_instruction() -> None:
    text = build_query_text("sales by region", "Find BI assets")

    assert text == "Instruct: Find BI assets\nQuery: sales by region"


def test_hash_dev_embedding_provider_shape_and_normalization() -> None:
    provider = HashDevEmbeddingProvider(model_name="hash", dimensions=8)
    vectors = provider.embed_texts(["alpha", "beta"])

    assert len(vectors) == 2
    assert all(len(vector) == 8 for vector in vectors)
    assert vectors[0] != vectors[1]
    norm = sum(value * value for value in vectors[0]) ** 0.5
    assert round(norm, 6) == 1.0


def test_vector_literal() -> None:
    assert vector_literal([1, 2.5, -3]) == "[1.0,2.5,-3.0]"


@pytest.mark.parametrize(
    "vector",
    [
        [],
        [math.nan],
        [math.inf],
        [True],
        ["1.0"],
    ],
)
def test_vector_literal_rejects_invalid_values(vector: list[object]) -> None:
    with pytest.raises(ValueError, match="Embedding"):
        vector_literal(cast(Any, vector))


@pytest.mark.parametrize(
    "embeddings",
    [
        [[1.0, math.nan]],
        [[1.0, math.inf]],
        [[1.0, True]],
        [[1.0, "2.0"]],
        ["not-a-vector"],
        [1.0],
    ],
)
def test_validate_embeddings_rejects_invalid_values(
    embeddings: list[object],
) -> None:
    with pytest.raises(EmbeddingProviderError):
        _validate_embeddings(
            cast(Any, embeddings),
            expected_count=1,
            expected_dimensions=2,
        )


def test_hash_dev_embedding_provider_rejects_empty_dimension() -> None:
    with pytest.raises(EmbeddingProviderError):
        HashDevEmbeddingProvider(model_name="hash", dimensions=0)

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
"""Embedding providers for the GenAI BI semantic index."""

from __future__ import annotations

import math
from hashlib import sha256
from threading import Lock
from typing import Any, Protocol

import requests
from flask import current_app

DEFAULT_QUERY_INSTRUCTION = (
    "Given a BI analytics question, retrieve relevant datasets, columns, "
    "metrics, and dashboard examples."
)


class EmbeddingProviderError(RuntimeError):
    """Raised when semantic embedding generation fails."""


class EmbeddingProvider(Protocol):
    """Protocol for semantic embedding providers."""

    provider_name: str
    model_name: str
    dimensions: int

    def embed_texts(
        self,
        texts: list[str],
        *,
        is_query: bool = False,
    ) -> list[list[float]]:
        """Embed a batch of texts."""


def build_query_text(query: str, instruction: str = DEFAULT_QUERY_INSTRUCTION) -> str:
    """Return Qwen3-Embedding instruction-aware query text."""

    return f"Instruct: {instruction}\nQuery: {query}"


def _validate_embeddings(
    embeddings: list[list[float]],
    *,
    expected_count: int,
    expected_dimensions: int,
) -> None:
    """Validate provider output shape."""

    if len(embeddings) != expected_count:
        raise EmbeddingProviderError(
            f"Embedding provider returned {len(embeddings)} vectors for "
            f"{expected_count} inputs"
        )
    for index, vector in enumerate(embeddings):
        if isinstance(vector, (bytes, str)):
            raise EmbeddingProviderError(f"Embedding {index} is not a vector")
        try:
            vector_length = len(vector)
        except TypeError as ex:
            raise EmbeddingProviderError(f"Embedding {index} is not a vector") from ex
        if vector_length != expected_dimensions:
            raise EmbeddingProviderError(
                f"Embedding {index} has dimension {vector_length}, expected "
                f"{expected_dimensions}"
            )
        for dimension, value in enumerate(vector):
            if isinstance(value, (bool, bytes, str)):
                raise EmbeddingProviderError(
                    f"Embedding {index} dimension {dimension} is not numeric"
                )
            try:
                numeric_value = float(value)
            except (TypeError, ValueError) as ex:
                raise EmbeddingProviderError(
                    f"Embedding {index} dimension {dimension} is not numeric"
                ) from ex
            if not math.isfinite(numeric_value):
                raise EmbeddingProviderError(
                    f"Embedding {index} dimension {dimension} is not finite"
                )


class AxEngineHttpEmbeddingProvider:
    """Embedding provider backed by the repo host-side ax-engine proxy."""

    provider_name = "ax_engine_http"

    def __init__(
        self,
        *,
        endpoint: str,
        model_name: str,
        dimensions: int,
        timeout: float,
        query_instruction: str = DEFAULT_QUERY_INSTRUCTION,
    ) -> None:
        self.endpoint = endpoint
        self.model_name = model_name
        self.dimensions = dimensions
        self.timeout = timeout
        self.query_instruction = query_instruction

    def embed_texts(
        self,
        texts: list[str],
        *,
        is_query: bool = False,
    ) -> list[list[float]]:
        """Embed texts by calling the configured ax-engine HTTP proxy."""

        if not texts:
            return []

        try:
            response = requests.post(
                self.endpoint,
                json={
                    "texts": texts,
                    "is_query": is_query,
                    "instruction": self.query_instruction,
                },
                timeout=self.timeout,
            )
            response.raise_for_status()
            payload = response.json()
        except requests.RequestException as ex:
            raise EmbeddingProviderError(
                f"Embedding endpoint request failed: {ex}"
            ) from ex
        except ValueError as ex:
            raise EmbeddingProviderError(
                "Embedding endpoint returned invalid JSON"
            ) from ex

        embeddings = payload.get("embeddings")
        if not isinstance(embeddings, list):
            raise EmbeddingProviderError("Embedding response missing embeddings list")

        _validate_embeddings(
            embeddings,
            expected_count=len(texts),
            expected_dimensions=self.dimensions,
        )
        return embeddings


class AxEngineLocalEmbeddingProvider:
    """In-process ax-engine provider for non-containerized workers."""

    provider_name = "ax_engine_local"

    def __init__(
        self,
        *,
        model_dir: str,
        model_name: str,
        dimensions: int,
        max_length: int,
        query_instruction: str = DEFAULT_QUERY_INSTRUCTION,
    ) -> None:
        self.model_dir = model_dir
        self.model_name = model_name
        self.dimensions = dimensions
        self.max_length = max_length
        self.query_instruction = query_instruction
        self._lock = Lock()
        self._session: Any | None = None
        self._tokenizer: Any | None = None

    def _ensure_runtime(self) -> tuple[Any, Any]:
        """Load ax-engine and tokenizer lazily."""

        with self._lock:
            if self._session is None or self._tokenizer is None:
                try:
                    from ax_engine import Session
                    from transformers import AutoTokenizer
                except ImportError as ex:
                    raise EmbeddingProviderError(
                        "ax_engine and transformers are required for "
                        "AI_SEMANTIC_EMBEDDING_PROVIDER='ax_engine_local'"
                    ) from ex

                self._tokenizer = AutoTokenizer.from_pretrained(
                    self.model_dir,
                    padding_side="left",
                )
                self._session = Session(
                    mlx=True,
                    mlx_model_artifacts_dir=self.model_dir,
                )
        return self._session, self._tokenizer

    def _tokenize(self, text: str, tokenizer: Any) -> list[int]:
        """Tokenize one text for ax-engine embedding."""

        encoded = tokenizer(
            text,
            truncation=True,
            max_length=self.max_length,
            add_special_tokens=True,
        )
        token_ids = list(encoded.input_ids)
        eos_token_id = getattr(tokenizer, "eos_token_id", None)
        if eos_token_id is not None and token_ids and token_ids[-1] != eos_token_id:
            token_ids.append(eos_token_id)
        return token_ids

    def embed_texts(
        self,
        texts: list[str],
        *,
        is_query: bool = False,
    ) -> list[list[float]]:
        """Embed texts with the ax-engine Python SDK."""

        if not texts:
            return []

        session, tokenizer = self._ensure_runtime()
        input_texts = [
            build_query_text(text, self.query_instruction) if is_query else text
            for text in texts
        ]
        batch_token_ids = [self._tokenize(text, tokenizer) for text in input_texts]
        embeddings = session.embed_batch(
            batch_token_ids,
            pooling="last",
            normalize=True,
        )
        _validate_embeddings(
            embeddings,
            expected_count=len(texts),
            expected_dimensions=self.dimensions,
        )
        return embeddings


class HashDevEmbeddingProvider:
    """Deterministic local provider for tests and wiring checks only."""

    provider_name = "hash_dev"

    def __init__(self, *, model_name: str, dimensions: int) -> None:
        if dimensions <= 0:
            raise EmbeddingProviderError("Embedding dimensions must be positive")
        self.model_name = model_name
        self.dimensions = dimensions

    def embed_texts(
        self,
        texts: list[str],
        *,
        is_query: bool = False,
    ) -> list[list[float]]:
        """Return deterministic pseudo-embeddings for development tests."""

        embeddings = []
        for text in texts:
            seed = sha256(f"{is_query}:{text}".encode()).digest()
            values: list[float] = []
            while len(values) < self.dimensions:
                seed = sha256(seed).digest()
                values.extend((byte / 255.0) * 2.0 - 1.0 for byte in seed)
            vector = values[: self.dimensions]
            norm = sum(value * value for value in vector) ** 0.5
            embeddings.append([value / norm for value in vector])
        return embeddings


def get_embedding_provider(config: dict[str, Any] | None = None) -> EmbeddingProvider:
    """Build the configured semantic embedding provider."""

    app_config = config or current_app.config
    provider = app_config.get("AI_SEMANTIC_EMBEDDING_PROVIDER", "disabled")
    model_name = app_config.get(
        "AI_SEMANTIC_EMBEDDING_MODEL",
        "Qwen/Qwen3-Embedding-0.6B",
    )
    dimensions = int(app_config.get("AI_SEMANTIC_EMBEDDING_DIMENSIONS", 1024))
    if dimensions <= 0:
        raise EmbeddingProviderError(
            "AI_SEMANTIC_EMBEDDING_DIMENSIONS must be positive"
        )
    query_instruction = app_config.get(
        "AI_SEMANTIC_QUERY_INSTRUCTION",
        DEFAULT_QUERY_INSTRUCTION,
    )

    if provider == "ax_engine_http":
        endpoint = app_config.get("AI_SEMANTIC_EMBEDDING_ENDPOINT")
        if not endpoint:
            raise EmbeddingProviderError(
                "AI_SEMANTIC_EMBEDDING_ENDPOINT is required for ax_engine_http"
            )
        return AxEngineHttpEmbeddingProvider(
            endpoint=endpoint,
            model_name=model_name,
            dimensions=dimensions,
            timeout=float(app_config.get("AI_SEMANTIC_EMBEDDING_TIMEOUT", 120)),
            query_instruction=query_instruction,
        )

    if provider == "ax_engine_local":
        model_dir = app_config.get("AI_SEMANTIC_EMBEDDING_MODEL_DIR")
        if not model_dir:
            raise EmbeddingProviderError(
                "AI_SEMANTIC_EMBEDDING_MODEL_DIR is required for ax_engine_local"
            )
        return AxEngineLocalEmbeddingProvider(
            model_dir=model_dir,
            model_name=model_name,
            dimensions=dimensions,
            max_length=int(app_config.get("AI_SEMANTIC_EMBEDDING_MAX_LENGTH", 8192)),
            query_instruction=query_instruction,
        )

    if provider == "hash_dev":
        return HashDevEmbeddingProvider(model_name=model_name, dimensions=dimensions)

    raise EmbeddingProviderError(
        "AI_SEMANTIC_EMBEDDING_PROVIDER must be one of "
        "ax_engine_http, ax_engine_local, or hash_dev"
    )

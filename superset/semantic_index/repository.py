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
"""Persistence and pgvector retrieval for semantic documents."""

from __future__ import annotations

import math
import re
from collections.abc import Sequence
from datetime import datetime
from typing import Any

import sqlalchemy as sa

from superset.extensions import db
from superset.models.ai import AISemanticDocument
from superset.semantic_index.embedding import EmbeddingProvider
from superset.semantic_index.types import (
    SemanticDocument,
    SemanticIndexSummary,
    SemanticSearchResult,
)
from superset.utils import json


def vector_literal(vector: Sequence[float]) -> str:
    """Return a pgvector-compatible vector literal."""

    values: list[str] = []
    for index, value in enumerate(vector):
        if isinstance(value, (bool, bytes, str)):
            raise ValueError(f"Embedding value {index} is not numeric")
        try:
            numeric_value = float(value)
        except (TypeError, ValueError) as ex:
            raise ValueError(f"Embedding value {index} is not numeric") from ex
        if not math.isfinite(numeric_value):
            raise ValueError(f"Embedding value {index} is not finite")
        values.append(repr(numeric_value))

    if not values:
        raise ValueError("Embedding vector cannot be empty")

    return "[" + ",".join(values) + "]"


def _embedding_literals(
    embeddings: Sequence[Sequence[float]],
    *,
    expected_count: int,
    expected_dimensions: int,
) -> list[str]:
    """Validate embedding batch shape and return pgvector literals."""

    if len(embeddings) != expected_count:
        raise ValueError(
            f"Embedding provider returned {len(embeddings)} vectors for "
            f"{expected_count} documents"
        )

    literals = []
    for index, embedding in enumerate(embeddings):
        try:
            embedding_length = len(embedding)
        except TypeError as ex:
            raise ValueError(f"Embedding {index} is not a vector") from ex
        if embedding_length != expected_dimensions:
            raise ValueError(
                f"Embedding {index} has dimension {embedding_length}, expected "
                f"{expected_dimensions}"
            )
        literals.append(vector_literal(embedding))
    return literals


def _escape_like_pattern(value: str) -> str:
    """Escape LIKE wildcard characters in a search value."""

    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


# Generic words that carry no retrieval signal for a BI corpus.
_STOPWORDS = frozenset(
    {
        "the",
        "and",
        "for",
        "with",
        "that",
        "this",
        "from",
        "are",
        "was",
        "have",
        "has",
        "will",
        "per",
        "all",
        "any",
        "how",
        "what",
        "which",
        "who",
        "show",
        "give",
        "list",
        "into",
        "out",
        "get",
        "using",
        "over",
    }
)


def _query_tokens(query: str) -> list[str]:
    """Split a query into de-duplicated, meaningful keyword tokens."""

    tokens: list[str] = []
    for token in re.findall(r"[a-z0-9_]{3,}", query.lower()):
        if token in _STOPWORDS or token in tokens:
            continue
        tokens.append(token)
    return tokens


def _reciprocal_rank_fusion(
    ranked_lists: Sequence[Sequence[SemanticSearchResult]],
    *,
    limit: int,
    k: int = 60,
) -> list[SemanticSearchResult]:
    """Fuse ranked result lists with Reciprocal Rank Fusion.

    Dense (vector) and lexical (keyword) retrieval have complementary blind
    spots, so a document ranked well by *either* retriever should surface. RRF
    combines them on rank — ``score = sum 1/(k + rank)`` — which avoids
    reconciling incompatible score scales. A representative result carrying the
    dense distance (when available) is kept for display.
    """

    scores: dict[tuple[str, str, str], float] = {}
    representative: dict[tuple[str, str, str], SemanticSearchResult] = {}
    for ranked in ranked_lists:
        for rank, result in enumerate(ranked):
            key = (result.object_type, result.object_id, result.document_kind)
            scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank + 1)
            current = representative.get(key)
            if current is None or (
                current.distance is None and result.distance is not None
            ):
                representative[key] = result
    ordered = sorted(
        representative.values(),
        key=lambda result: scores[
            (result.object_type, result.object_id, result.document_kind)
        ],
        reverse=True,
    )
    return ordered[:limit]


def _parse_extra_json(value: str | None) -> dict[str, Any]:
    """Parse stored JSON metadata."""

    if not value:
        return {}
    parsed = json.loads(value)
    return parsed if isinstance(parsed, dict) else {}


def _embedding_column_uses_pgvector() -> bool:
    """Return whether the migrated embedding column is a pgvector column."""

    # ``db.session.bind`` is ``None`` when the session routes across multiple
    # binds (the default under SQLAlchemy 2.x), so resolve the engine for the
    # model instead — otherwise pgvector search silently degrades to lexical.
    bind = db.session.get_bind(AISemanticDocument)
    if bind is None or bind.dialect.name != "postgresql":
        return False

    column_type = db.session.execute(
        sa.text(
            """
            SELECT format_type(attribute.atttypid, attribute.atttypmod)
            FROM pg_attribute attribute
            JOIN pg_class relation ON relation.oid = attribute.attrelid
            JOIN pg_namespace namespace ON namespace.oid = relation.relnamespace
            WHERE relation.relname = 'ai_semantic_documents'
              AND attribute.attname = 'embedding'
              AND NOT attribute.attisdropped
              AND namespace.nspname = ANY(current_schemas(false))
            LIMIT 1
            """
        )
    ).scalar()
    return isinstance(column_type, str) and column_type.startswith("vector")


class SemanticIndexRepository:
    """Repository for semantic documents and pgvector search."""

    def upsert_documents(
        self,
        documents: Sequence[SemanticDocument],
        *,
        provider: EmbeddingProvider,
    ) -> SemanticIndexSummary:
        """Generate embeddings and upsert semantic documents."""

        if not documents:
            return SemanticIndexSummary(
                documents_seen=0,
                documents_written=0,
                embedding_model=provider.model_name,
                embedding_dimension=provider.dimensions,
            )

        embeddings = provider.embed_texts([document.content for document in documents])
        embedding_literals = _embedding_literals(
            embeddings,
            expected_count=len(documents),
            expected_dimensions=provider.dimensions,
        )
        written = 0
        embedded_at = datetime.utcnow()

        for document, embedding_literal in zip(
            documents,
            embedding_literals,
            strict=True,
        ):
            row = (
                db.session.query(AISemanticDocument)
                .filter(
                    AISemanticDocument.object_type == document.object_type,
                    AISemanticDocument.object_id == document.object_id,
                    AISemanticDocument.document_kind == document.document_kind,
                    AISemanticDocument.embedding_model == provider.model_name,
                )
                .one_or_none()
            )
            if row is None:
                row = AISemanticDocument(
                    object_type=document.object_type,
                    object_id=document.object_id,
                    document_kind=document.document_kind,
                    embedding_model=provider.model_name,
                )
                db.session.add(row)

            row.dataset_id = document.dataset_id
            row.object_name = document.object_name
            row.source = document.source
            row.source_hash = document.source_hash
            row.content = document.content
            row.extra_json = json.dumps(document.extra, sort_keys=True)
            row.embedding_provider = provider.provider_name
            row.embedding_dimension = provider.dimensions
            row.embedding = embedding_literal
            row.review_status = "generated"
            row.last_embedded_at = embedded_at
            row.embedding_error = None
            written += 1

        db.session.flush()
        return SemanticIndexSummary(
            documents_seen=len(documents),
            documents_written=written,
            embedding_model=provider.model_name,
            embedding_dimension=provider.dimensions,
        )

    def prune_dataset_documents(
        self,
        dataset_id: int,
        *,
        keep_keys: set[tuple[str, str, str]],
        embedding_model: str,
        source: str = "dataset_profile",
    ) -> int:
        """Delete auto-generated docs for a dataset that no longer exist.

        Only ``source`` documents for ``embedding_model`` are considered, so
        curated (user/admin) documents and other-model rows are preserved.
        ``keep_keys`` is the set of ``(object_type, object_id, document_kind)``
        tuples produced by the current build; anything outside it (for example a
        dropped column or a renamed metric) is removed so the index does not
        accumulate orphaned documents.
        """

        rows = (
            db.session.query(AISemanticDocument)
            .filter(
                AISemanticDocument.dataset_id == dataset_id,
                AISemanticDocument.source == source,
                AISemanticDocument.embedding_model == embedding_model,
            )
            .all()
        )
        removed = 0
        for row in rows:
            key = (row.object_type, row.object_id, row.document_kind)
            if key not in keep_keys:
                db.session.delete(row)
                removed += 1
        if removed:
            db.session.flush()
        return removed

    def delete_dataset_documents(self, dataset_id: int) -> int:
        """Delete every semantic document for a dataset."""

        removed = (
            db.session.query(AISemanticDocument)
            .filter(AISemanticDocument.dataset_id == dataset_id)
            .delete(synchronize_session=False)
        )
        db.session.flush()
        return removed

    def search(
        self,
        query: str,
        *,
        provider: EmbeddingProvider,
        limit: int,
        object_types: Sequence[str] | None = None,
        ef_search: int | None = None,
    ) -> list[SemanticSearchResult]:
        """Search semantic documents, fusing vector and keyword retrieval.

        When pgvector is available, dense (cosine) and lexical (keyword) results
        are fused with Reciprocal Rank Fusion so exact-name matches are not
        buried by topically-similar neighbours and vice versa. Without pgvector
        (for example a SQLite test database) the lexical retriever is used
        directly.
        """

        if not query.strip() or limit <= 0:
            return []

        if _embedding_column_uses_pgvector():
            candidate_pool = max(limit * 4, limit)
            dense = self._search_pgvector(
                query,
                provider=provider,
                limit=candidate_pool,
                object_types=object_types,
                ef_search=ef_search,
            )
            lexical = self._search_lexical(
                query, limit=candidate_pool, object_types=object_types
            )
            return _reciprocal_rank_fusion([dense, lexical], limit=limit)
        return self._search_lexical(query, limit=limit, object_types=object_types)

    def _search_pgvector(
        self,
        query: str,
        *,
        provider: EmbeddingProvider,
        limit: int,
        object_types: Sequence[str] | None,
        ef_search: int | None,
    ) -> list[SemanticSearchResult]:
        """Search semantic documents using pgvector cosine distance."""

        query_embedding = provider.embed_texts([query], is_query=True)[0]
        params: dict[str, Any] = {
            "embedding": vector_literal(query_embedding),
            "embedding_model": provider.model_name,
            "embedding_dimension": provider.dimensions,
            "limit": limit,
        }

        filters = [
            "embedding_model = :embedding_model",
            "embedding_dimension = :embedding_dimension",
            "embedding IS NOT NULL",
            "review_status IN ('generated', 'approved')",
        ]
        statement = sa.text(
            """
            SELECT
              uuid,
              object_type,
              object_id,
              object_name,
              document_kind,
              content,
              dataset_id,
              extra_json,
              embedding <=> CAST(:embedding AS vector) AS distance
            FROM ai_semantic_documents
            WHERE {filters}
            ORDER BY embedding <=> CAST(:embedding AS vector)
            LIMIT :limit
            """.format(filters=" AND ".join(filters))
        )
        if object_types:
            filters.append("object_type IN :object_types")
            params["object_types"] = tuple(object_types)
            statement = sa.text(
                """
                SELECT
                  uuid,
                  object_type,
                  object_id,
                  object_name,
                  document_kind,
                  content,
                  dataset_id,
                  extra_json,
                  embedding <=> CAST(:embedding AS vector) AS distance
                FROM ai_semantic_documents
                WHERE {filters}
                ORDER BY embedding <=> CAST(:embedding AS vector)
                LIMIT :limit
                """.format(filters=" AND ".join(filters))
            ).bindparams(sa.bindparam("object_types", expanding=True))

        if ef_search:
            db.session.execute(
                sa.text("SELECT set_config('hnsw.ef_search', :ef_search, true)"),
                {"ef_search": str(ef_search)},
            )

        rows = db.session.execute(statement, params).mappings().all()
        return [
            SemanticSearchResult(
                uuid=str(row["uuid"]),
                object_type=row["object_type"],
                object_id=row["object_id"],
                object_name=row["object_name"],
                document_kind=row["document_kind"],
                content=row["content"],
                dataset_id=row["dataset_id"],
                extra=_parse_extra_json(row["extra_json"]),
                distance=(
                    float(row["distance"]) if row["distance"] is not None else None
                ),
            )
            for row in rows
        ]

    def _search_lexical(
        self,
        query: str,
        *,
        limit: int,
        object_types: Sequence[str] | None,
    ) -> list[SemanticSearchResult]:
        """Keyword retriever: match any query token, rank by token overlap.

        Used both as the sparse arm of hybrid search and as the standalone
        fallback when pgvector is unavailable. Matching on individual tokens
        (rather than the whole query string) is what makes it a useful recall
        complement to dense search.
        """

        tokens = _query_tokens(query)
        model_query = db.session.query(AISemanticDocument).filter(
            AISemanticDocument.review_status.in_(("generated", "approved")),
        )
        if object_types:
            model_query = model_query.filter(
                AISemanticDocument.object_type.in_(object_types)
            )
        if tokens:
            clauses = [
                AISemanticDocument.content.ilike(
                    f"%{_escape_like_pattern(token)}%", escape="\\"
                )
                for token in tokens
            ]
            model_query = model_query.filter(sa.or_(*clauses))
        else:
            escaped_query = _escape_like_pattern(query)
            model_query = model_query.filter(
                AISemanticDocument.content.ilike(f"%{escaped_query}%", escape="\\")
            )

        # Overfetch, then rank by how many distinct query tokens each document
        # contains so the fused ranking sees a meaningful lexical order.
        rows = model_query.limit(max(limit * 5, limit)).all()

        def _overlap(row: AISemanticDocument) -> int:
            content = (row.content or "").lower()
            return sum(1 for token in tokens if token in content)

        if tokens:
            rows.sort(key=_overlap, reverse=True)
        rows = rows[:limit]
        return [
            SemanticSearchResult(
                uuid=str(row.uuid),
                object_type=row.object_type,
                object_id=row.object_id,
                object_name=row.object_name,
                document_kind=row.document_kind,
                content=row.content,
                dataset_id=row.dataset_id,
                extra=_parse_extra_json(row.extra_json),
                distance=None,
            )
            for row in rows
        ]

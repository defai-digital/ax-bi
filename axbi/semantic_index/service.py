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
"""Service API for the GenAI BI semantic index."""

from __future__ import annotations

from collections.abc import Sequence

from flask import current_app

from axbi.extensions import db
from axbi.semantic_index.documents import build_dataset_semantic_documents
from axbi.semantic_index.embedding import EmbeddingProvider, get_embedding_provider
from axbi.semantic_index.governance import (
    load_dataset_aliases,
    load_dataset_instructions,
    load_dataset_policies,
)
from axbi.semantic_index.grounding import (
    build_grounding_contract,
    GroundingContract,
)
from axbi.semantic_index.repository import SemanticIndexRepository
from axbi.semantic_index.types import SemanticIndexSummary, SemanticSearchResult


class SemanticIndexService:
    """Application service for semantic document indexing and retrieval."""

    def __init__(
        self,
        *,
        provider: EmbeddingProvider | None = None,
        repository: SemanticIndexRepository | None = None,
    ) -> None:
        self.provider = provider or get_embedding_provider()
        self.repository = repository or SemanticIndexRepository()

    def index_dataset(self, dataset_id: int) -> SemanticIndexSummary:
        """Build, store, and reconcile semantic documents for one dataset.

        Newly built documents are embedded and upserted; auto-generated
        documents for columns or metrics that no longer exist are pruned so a
        reindex reflects the current dataset shape.
        """

        from axbi.connectors.sqla.models import SqlaTable

        dataset = db.session.query(SqlaTable).filter(SqlaTable.id == dataset_id).one()
        documents = build_dataset_semantic_documents(
            dataset,
            aliases=load_dataset_aliases(dataset_id),
            instructions=load_dataset_instructions(dataset),
        )
        summary = self.repository.upsert_documents(documents, provider=self.provider)
        keep_keys = {
            (document.object_type, document.object_id, document.document_kind)
            for document in documents
        }
        self.repository.prune_dataset_documents(
            dataset_id,
            keep_keys=keep_keys,
            embedding_model=self.provider.model_name,
        )
        return summary

    def remove_dataset(self, dataset_id: int) -> int:
        """Delete all semantic documents for a dataset (no embedding needed)."""

        return self.repository.delete_dataset_documents(dataset_id)

    def get_grounding_contract(self, dataset_id: int) -> GroundingContract:
        """Return the governed grounding contract for a dataset.

        This is the artifact prompt-to-dashboard should inject once a dataset is
        resolved: certified measures with their real expressions, dimensions,
        time columns, a synonym glossary, and disambiguation instructions.
        """

        from axbi.connectors.sqla.models import SqlaTable

        dataset = db.session.query(SqlaTable).filter(SqlaTable.id == dataset_id).one()
        return build_grounding_contract(
            dataset,
            aliases=load_dataset_aliases(dataset_id),
            instructions=load_dataset_instructions(dataset),
            policies=load_dataset_policies(dataset),
        )

    def search(
        self,
        query: str,
        *,
        limit: int | None = None,
        object_types: Sequence[str] | None = None,
    ) -> list[SemanticSearchResult]:
        """Search semantic documents for a natural-language BI query."""

        if not query.strip():
            return []

        resolved_limit = (
            limit
            if limit is not None
            else int(current_app.config["AI_SEMANTIC_INDEX_TOP_K"])
        )
        if resolved_limit <= 0:
            return []

        ef_search = current_app.config.get("AI_SEMANTIC_INDEX_HNSW_EF_SEARCH")
        return self.repository.search(
            query,
            provider=self.provider,
            limit=resolved_limit,
            object_types=object_types,
            ef_search=int(ef_search) if ef_search else None,
        )

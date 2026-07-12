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
"""Tests for the semantic index service reconcile behaviour."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from axbi.semantic_index.service import SemanticIndexService
from axbi.semantic_index.types import SemanticDocument, SemanticIndexSummary


def _provider() -> SimpleNamespace:
    return SimpleNamespace(
        provider_name="hash_dev",
        model_name="test-model",
        dimensions=8,
    )


def _document(object_type: str, object_id: str, document_kind: str) -> SemanticDocument:
    return SemanticDocument(
        object_type=object_type,
        object_id=object_id,
        object_name=object_id,
        document_kind=document_kind,
        source="dataset_profile",
        content="content",
        dataset_id=5,
    )


def test_index_dataset_upserts_then_prunes() -> None:
    repository = MagicMock()
    repository.upsert_documents.return_value = SemanticIndexSummary(
        documents_seen=2,
        documents_written=2,
        embedding_model="test-model",
        embedding_dimension=8,
    )
    service = SemanticIndexService(provider=_provider(), repository=repository)

    documents = [
        _document("dataset", "abc", "summary"),
        _document("column", "abc:region", "column_profile"),
    ]

    with (
        patch("axbi.semantic_index.service.db") as mock_db,
        patch(
            "axbi.semantic_index.service.build_dataset_semantic_documents",
            return_value=documents,
        ),
    ):
        mock_db.session.query.return_value.filter.return_value.one.return_value = (
            SimpleNamespace(id=5)
        )
        service.index_dataset(5)

    repository.upsert_documents.assert_called_once()
    repository.prune_dataset_documents.assert_called_once()
    _, kwargs = repository.prune_dataset_documents.call_args
    assert kwargs["keep_keys"] == {
        ("dataset", "abc", "summary"),
        ("column", "abc:region", "column_profile"),
    }
    assert kwargs["embedding_model"] == "test-model"


def test_remove_dataset_delegates_to_repository() -> None:
    repository = MagicMock()
    repository.delete_dataset_documents.return_value = 3
    service = SemanticIndexService(provider=_provider(), repository=repository)

    assert service.remove_dataset(5) == 3
    repository.delete_dataset_documents.assert_called_once_with(5)

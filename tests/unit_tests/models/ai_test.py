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
"""Unit tests for GenAI BI SQLAlchemy models."""

from __future__ import annotations

import uuid

from superset.models.ai import (
    AIEvaluationRun,
    AIGeneratedArtifact,
    AISemanticAlias,
    AISemanticDocument,
    PGVector,
)


def test_ai_generated_artifact_table_name() -> None:
    assert AIGeneratedArtifact.__tablename__ == "ai_generated_artifacts"


def test_ai_generated_artifact_uuid_default() -> None:
    artifact = AIGeneratedArtifact()
    assert artifact.uuid is None  # default is a callable, not a value


def test_ai_generated_artifact_columns() -> None:
    columns = {c.name for c in AIGeneratedArtifact.__table__.columns}
    expected = {
        "uuid",
        "artifact_type",
        "artifact_id",
        "principal_user_id",
        "source_prompt",
        "normalized_intent",
        "llm_provider",
        "llm_model",
        "tool_chain",
        "source_asset_refs",
        "validation_summary",
        "confidence_score",
        "created_on",
        "changed_on",
    }
    assert expected.issubset(columns)


def test_ai_generated_artifact_pk_is_uuid() -> None:
    pk_cols = list(AIGeneratedArtifact.__table__.primary_key.columns)
    assert len(pk_cols) == 1
    assert pk_cols[0].name == "uuid"


def test_ai_semantic_alias_table_name() -> None:
    assert AISemanticAlias.__tablename__ == "ai_semantic_aliases"


def test_ai_semantic_alias_columns() -> None:
    columns = {c.name for c in AISemanticAlias.__table__.columns}
    expected = {
        "uuid",
        "dataset_id",
        "object_type",
        "object_name",
        "alias",
        "source",
        "approved_by",
        "created_on",
        "changed_on",
    }
    assert expected.issubset(columns)


def test_ai_semantic_alias_indexes() -> None:
    index_names = {idx.name for idx in AISemanticAlias.__table__.indexes}
    assert "ix_ai_alias_alias" in index_names
    assert "ix_ai_alias_type_alias" in index_names
    assert "ix_ai_alias_dataset_obj" in index_names


def test_ai_evaluation_run_table_name() -> None:
    assert AIEvaluationRun.__tablename__ == "ai_evaluation_runs"


def test_ai_evaluation_run_columns() -> None:
    columns = {c.name for c in AIEvaluationRun.__table__.columns}
    expected = {
        "uuid",
        "prompt",
        "expected_result",
        "actual_result",
        "scores",
        "model",
        "tool_versions",
        "created_on",
        "changed_on",
    }
    assert expected.issubset(columns)


def test_ai_evaluation_run_pk_is_uuid() -> None:
    pk_cols = list(AIEvaluationRun.__table__.primary_key.columns)
    assert len(pk_cols) == 1
    assert pk_cols[0].name == "uuid"


def test_ai_semantic_document_table_name() -> None:
    assert AISemanticDocument.__tablename__ == "ai_semantic_documents"


def test_ai_semantic_document_columns() -> None:
    columns = {c.name for c in AISemanticDocument.__table__.columns}
    expected = {
        "uuid",
        "dataset_id",
        "object_type",
        "object_id",
        "object_name",
        "document_kind",
        "source",
        "source_hash",
        "content",
        "extra_json",
        "embedding_provider",
        "embedding_model",
        "embedding_dimension",
        "embedding",
        "review_status",
        "last_embedded_at",
        "embedding_error",
        "created_on",
        "changed_on",
    }
    assert expected.issubset(columns)


def test_ai_semantic_document_indexes() -> None:
    index_names = {idx.name for idx in AISemanticDocument.__table__.indexes}
    assert "ix_ai_sem_doc_object" in index_names
    assert "ix_ai_sem_doc_dataset" in index_names
    assert "ix_ai_sem_doc_kind" in index_names
    assert "ix_ai_sem_doc_review_status" in index_names
    assert "ix_ai_sem_doc_embedding_model" in index_names
    assert "ix_ai_sem_doc_source" in index_names


def test_pgvector_column_spec() -> None:
    assert PGVector(1024).get_col_spec() == "vector(1024)"


def test_uuid_generation_on_instances() -> None:
    """Verify that the UUID default callable produces unique UUIDs."""
    default_fn = AIGeneratedArtifact.__table__.c.uuid.default.arg
    u1 = default_fn(None)
    u2 = default_fn(None)
    assert isinstance(u1, uuid.UUID)
    assert isinstance(u2, uuid.UUID)
    assert u1 != u2

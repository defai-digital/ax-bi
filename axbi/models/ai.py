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
"""SQLAlchemy models for GenAI BI metadata tables."""

from __future__ import annotations

import uuid
from typing import Any

from flask_appbuilder import Model
from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.types import UserDefinedType
from sqlalchemy_utils import UUIDType

from axbi.models.helpers import AuditMixinNullable


class PGVector(UserDefinedType):
    """SQLAlchemy type for pgvector columns.

    The Python ``pgvector`` package is intentionally not required for model
    import. Runtime search writes vectors through SQL parameters and the
    migration creates the PostgreSQL extension-backed column.
    """

    cache_ok = True

    def __init__(self, dimensions: int) -> None:
        self.dimensions = dimensions

    def get_col_spec(self, **kw: Any) -> str:
        """Return the PostgreSQL column specification."""

        return f"vector({self.dimensions})"


class AIGeneratedArtifact(Model, AuditMixinNullable):
    """Lineage and audit record for AI-generated BI artifacts.

    Tracks every chart, dashboard, dataset, or report produced through
    the GenAI BI pipeline so that operators can trace which prompt,
    model, and source assets led to each artifact.
    """

    __tablename__ = "ai_generated_artifacts"
    __table_args__ = (
        Index("ix_ai_gen_artifact_type_id", "artifact_type", "artifact_id"),
        Index("ix_ai_gen_artifact_user", "principal_user_id"),
    )

    uuid = Column(UUIDType(binary=True), default=uuid.uuid4, primary_key=True)
    artifact_type = Column(
        String(50),
        nullable=False,
        comment="chart, dashboard, dataset, or report",
    )
    artifact_id = Column(Integer, nullable=True)
    principal_user_id = Column(
        Integer,
        ForeignKey("ab_user.id", ondelete="SET NULL"),
        nullable=True,
    )
    source_prompt = Column(Text, nullable=True)
    normalized_intent = Column(Text, nullable=True, comment="JSON")
    llm_provider = Column(String(100), nullable=True)
    llm_model = Column(String(100), nullable=True)
    tool_chain = Column(Text, nullable=True, comment="JSON")
    source_asset_refs = Column(Text, nullable=True, comment="JSON")
    validation_summary = Column(Text, nullable=True, comment="JSON")
    confidence_score = Column(Numeric(precision=5, scale=4), nullable=True)


class AISemanticAlias(Model, AuditMixinNullable):
    """Business synonyms for AI semantic resolution.

    Maps alternative names (aliases) to datasets, columns, metrics,
    dashboards, or charts so that the AI layer can resolve user
    terminology to the correct AxBI objects.
    """

    __tablename__ = "ai_semantic_aliases"
    __table_args__ = (
        Index(
            "ix_ai_alias_dataset_obj",
            "dataset_id",
            "object_type",
            "object_name",
        ),
        Index("ix_ai_alias_alias", "alias"),
        Index("ix_ai_alias_type_alias", "object_type", "alias"),
    )

    uuid = Column(UUIDType(binary=True), default=uuid.uuid4, primary_key=True)
    dataset_id = Column(
        Integer,
        ForeignKey("tables.id", ondelete="SET NULL"),
        nullable=True,
    )
    object_type = Column(
        String(50),
        nullable=False,
        comment="dataset, column, metric, dashboard, or chart",
    )
    object_name = Column(String(250), nullable=False)
    alias = Column(String(250), nullable=False)
    source = Column(
        String(50),
        nullable=False,
        comment="user, admin, usage, or generated",
    )
    approved_by = Column(
        Integer,
        ForeignKey("ab_user.id", ondelete="SET NULL"),
        nullable=True,
    )


class AIEvaluationRun(Model, AuditMixinNullable):
    """Repeatable prompt-to-dashboard evaluation record.

    Stores the prompt, expected vs. actual results, and scoring
    for a single evaluation run so that the GenAI BI pipeline can
    be regression-tested across model or prompt changes.
    """

    __tablename__ = "ai_evaluation_runs"

    uuid = Column(UUIDType(binary=True), default=uuid.uuid4, primary_key=True)
    prompt = Column(Text, nullable=False)
    expected_result = Column(Text, nullable=True, comment="JSON")
    actual_result = Column(Text, nullable=True, comment="JSON")
    scores = Column(Text, nullable=True, comment="JSON")
    model = Column(String(100), nullable=True)
    tool_versions = Column(Text, nullable=True, comment="JSON")


class AISemanticDocument(Model, AuditMixinNullable):
    """Distilled semantic document used for pgvector-backed BI retrieval.

    Stores the AI-ready text generated from uploaded files, datasets, columns,
    metrics, and example questions. The relational columns remain the source
    of governance metadata; the vector column is used only for retrieval.
    """

    __tablename__ = "ai_semantic_documents"
    __table_args__ = (
        Index("ix_ai_sem_doc_object", "object_type", "object_id"),
        Index("ix_ai_sem_doc_dataset", "dataset_id"),
        Index("ix_ai_sem_doc_kind", "document_kind"),
        Index("ix_ai_sem_doc_review_status", "review_status"),
        Index(
            "ix_ai_sem_doc_embedding_model",
            "embedding_model",
            "embedding_dimension",
        ),
        Index(
            "ix_ai_sem_doc_source",
            "object_type",
            "object_id",
            "document_kind",
            "source_hash",
        ),
    )

    uuid = Column(UUIDType(binary=True), default=uuid.uuid4, primary_key=True)
    dataset_id = Column(
        Integer,
        ForeignKey("tables.id", ondelete="CASCADE"),
        nullable=True,
    )
    object_type = Column(
        String(50),
        nullable=False,
        comment="dataset, column, metric, dashboard, chart, or upload",
    )
    object_id = Column(
        String(500),
        nullable=False,
        comment="Stable identifier for the source object.",
    )
    object_name = Column(String(500), nullable=False)
    document_kind = Column(
        String(50),
        nullable=False,
        comment="summary, column_profile, metric_candidate, sample_question, or note",
    )
    source = Column(
        String(50),
        nullable=False,
        comment="upload, dataset_profile, user, admin, usage, or generated",
    )
    source_hash = Column(
        String(64),
        nullable=False,
        comment="SHA-256 hash of the source text and metadata.",
    )
    content = Column(Text, nullable=False)
    extra_json = Column(Text, nullable=True, comment="JSON")
    embedding_provider = Column(String(100), nullable=False)
    embedding_model = Column(String(200), nullable=False)
    embedding_dimension = Column(Integer, nullable=False)
    embedding = Column(PGVector(1024), nullable=True)
    review_status = Column(
        String(50),
        nullable=False,
        default="generated",
        comment="generated, approved, rejected, or stale",
    )
    last_embedded_at = Column(DateTime(), nullable=True)
    embedding_error = Column(Text, nullable=True)

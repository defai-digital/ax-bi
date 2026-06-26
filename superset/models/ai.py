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

from flask_appbuilder import Model
from sqlalchemy import (
    Column,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy_utils import UUIDType

from superset.models.helpers import AuditMixinNullable


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
    terminology to the correct Superset objects.
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

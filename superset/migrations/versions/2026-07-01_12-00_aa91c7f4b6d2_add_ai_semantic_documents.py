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
"""add ai semantic documents

Creates the semantic document table used by the GenAI BI pgvector index.

Revision ID: aa91c7f4b6d2
Revises: 17a4dfa2f9ab
Create Date: 2026-07-01 12:00:00.000000

"""

from __future__ import annotations

from typing import Any

import sqlalchemy as sa
from alembic import op
from sqlalchemy.types import UserDefinedType
from sqlalchemy_utils import UUIDType

# revision identifiers, used by Alembic.
revision = "aa91c7f4b6d2"
down_revision = "17a4dfa2f9ab"


class PGVector(UserDefinedType):
    """Alembic-local pgvector type."""

    cache_ok = True

    def __init__(self, dimensions: int) -> None:
        self.dimensions = dimensions

    def get_col_spec(self, **kw: Any) -> str:
        """Return the PostgreSQL column specification."""

        return f"vector({self.dimensions})"


def _pgvector_available() -> bool:
    """Return whether the connected PostgreSQL database can create pgvector."""

    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return False

    result = bind.execute(
        sa.text("SELECT 1 FROM pg_available_extensions WHERE name = 'vector'")
    ).scalar()
    return bool(result)


def upgrade() -> None:
    """Create the AI semantic document table."""

    use_pgvector = _pgvector_available()
    if use_pgvector:
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    embedding_type = PGVector(1024) if use_pgvector else sa.Text()

    op.create_table(
        "ai_semantic_documents",
        sa.Column("uuid", UUIDType(binary=True), nullable=False),
        sa.Column("dataset_id", sa.Integer(), nullable=True),
        sa.Column("object_type", sa.String(50), nullable=False),
        sa.Column("object_id", sa.String(500), nullable=False),
        sa.Column("object_name", sa.String(500), nullable=False),
        sa.Column("document_kind", sa.String(50), nullable=False),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("source_hash", sa.String(64), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("extra_json", sa.Text(), nullable=True),
        sa.Column("embedding_provider", sa.String(100), nullable=False),
        sa.Column("embedding_model", sa.String(200), nullable=False),
        sa.Column("embedding_dimension", sa.Integer(), nullable=False),
        sa.Column("embedding", embedding_type, nullable=True),
        sa.Column(
            "review_status",
            sa.String(50),
            nullable=False,
            server_default="generated",
        ),
        sa.Column("last_embedded_at", sa.DateTime(), nullable=True),
        sa.Column("embedding_error", sa.Text(), nullable=True),
        sa.Column("created_on", sa.DateTime(), nullable=True),
        sa.Column("changed_on", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["dataset_id"],
            ["tables.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("uuid"),
    )
    op.create_index(
        "ix_ai_sem_doc_object",
        "ai_semantic_documents",
        ["object_type", "object_id"],
    )
    op.create_index(
        "ix_ai_sem_doc_dataset",
        "ai_semantic_documents",
        ["dataset_id"],
    )
    op.create_index(
        "ix_ai_sem_doc_kind",
        "ai_semantic_documents",
        ["document_kind"],
    )
    op.create_index(
        "ix_ai_sem_doc_review_status",
        "ai_semantic_documents",
        ["review_status"],
    )
    op.create_index(
        "ix_ai_sem_doc_embedding_model",
        "ai_semantic_documents",
        ["embedding_model", "embedding_dimension"],
    )
    op.create_index(
        "ix_ai_sem_doc_source",
        "ai_semantic_documents",
        ["object_type", "object_id", "document_kind", "source_hash"],
    )

    if use_pgvector:
        op.execute(
            "CREATE INDEX ix_ai_sem_doc_embedding_hnsw "
            "ON ai_semantic_documents "
            "USING hnsw (embedding vector_cosine_ops)"
        )


def downgrade() -> None:
    """Drop the AI semantic document table."""

    op.drop_table("ai_semantic_documents")

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
"""add ai bi tables

Creates three tables for the GenAI BI foundation:
- ``ai_generated_artifacts``: lineage/audit for AI-generated BI artifacts.
- ``ai_semantic_aliases``: business synonyms for AI semantic resolution.
- ``ai_evaluation_runs``: repeatable prompt-to-dashboard evaluation records.

Revision ID: 17a4dfa2f9ab
Revises: 78a40c08b4be
Create Date: 2026-06-26 10:00:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy_utils import UUIDType

# revision identifiers, used by Alembic.
revision = "17a4dfa2f9ab"
down_revision = "78a40c08b4be"


def upgrade() -> None:
    """Create the three GenAI BI metadata tables."""
    op.create_table(
        "ai_generated_artifacts",
        sa.Column("uuid", UUIDType(binary=True), nullable=False),
        sa.Column("artifact_type", sa.String(50), nullable=False),
        sa.Column("artifact_id", sa.Integer(), nullable=True),
        sa.Column("principal_user_id", sa.Integer(), nullable=True),
        sa.Column("source_prompt", sa.Text(), nullable=True),
        sa.Column("normalized_intent", sa.Text(), nullable=True),
        sa.Column("llm_provider", sa.String(100), nullable=True),
        sa.Column("llm_model", sa.String(100), nullable=True),
        sa.Column("tool_chain", sa.Text(), nullable=True),
        sa.Column("source_asset_refs", sa.Text(), nullable=True),
        sa.Column("validation_summary", sa.Text(), nullable=True),
        sa.Column("confidence_score", sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column("created_on", sa.DateTime(), nullable=True),
        sa.Column("changed_on", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["principal_user_id"],
            ["ab_user.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("uuid"),
    )
    op.create_index(
        "ix_ai_gen_artifact_type_id",
        "ai_generated_artifacts",
        ["artifact_type", "artifact_id"],
    )
    op.create_index(
        "ix_ai_gen_artifact_user",
        "ai_generated_artifacts",
        ["principal_user_id"],
    )

    op.create_table(
        "ai_semantic_aliases",
        sa.Column("uuid", UUIDType(binary=True), nullable=False),
        sa.Column("dataset_id", sa.Integer(), nullable=True),
        sa.Column("object_type", sa.String(50), nullable=False),
        sa.Column("object_name", sa.String(250), nullable=False),
        sa.Column("alias", sa.String(250), nullable=False),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("approved_by", sa.Integer(), nullable=True),
        sa.Column("created_on", sa.DateTime(), nullable=True),
        sa.Column("changed_on", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["dataset_id"],
            ["tables.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["approved_by"],
            ["ab_user.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("uuid"),
    )
    op.create_index(
        "ix_ai_alias_dataset_obj",
        "ai_semantic_aliases",
        ["dataset_id", "object_type", "object_name"],
    )
    op.create_index("ix_ai_alias_alias", "ai_semantic_aliases", ["alias"])
    op.create_index(
        "ix_ai_alias_type_alias",
        "ai_semantic_aliases",
        ["object_type", "alias"],
    )

    op.create_table(
        "ai_evaluation_runs",
        sa.Column("uuid", UUIDType(binary=True), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("expected_result", sa.Text(), nullable=True),
        sa.Column("actual_result", sa.Text(), nullable=True),
        sa.Column("scores", sa.Text(), nullable=True),
        sa.Column("model", sa.String(100), nullable=True),
        sa.Column("tool_versions", sa.Text(), nullable=True),
        sa.Column("created_on", sa.DateTime(), nullable=True),
        sa.Column("changed_on", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("uuid"),
    )


def downgrade() -> None:
    """Drop the three GenAI BI metadata tables."""
    op.drop_table("ai_evaluation_runs")
    op.drop_table("ai_semantic_aliases")
    op.drop_table("ai_generated_artifacts")

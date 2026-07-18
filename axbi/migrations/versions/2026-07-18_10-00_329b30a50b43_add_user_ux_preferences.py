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
"""add user_ux_preferences

Creates the per-user UX preference table backing
``GET/PUT /api/v1/me/preferences``: one JSON document of namespaced
``ux.*`` UI preferences per user.

Revision ID: 329b30a50b43
Revises: aa91c7f4b6d2
Create Date: 2026-07-18 10:00:00.000000

"""

import sqlalchemy as sa
from sqlalchemy_utils import UUIDType

from axbi.migrations.shared.utils import create_table, drop_table

# revision identifiers, used by Alembic.
revision = "329b30a50b43"
down_revision = "aa91c7f4b6d2"


def upgrade() -> None:
    create_table(
        "user_ux_preferences",
        sa.Column("uuid", UUIDType(binary=True), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("preferences", sa.Text(), nullable=False),
        sa.Column("created_on", sa.DateTime(), nullable=True),
        sa.Column("changed_on", sa.DateTime(), nullable=True),
        sa.Column("created_by_fk", sa.Integer(), nullable=True),
        sa.Column("changed_by_fk", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["ab_user.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["created_by_fk"], ["ab_user.id"]),
        sa.ForeignKeyConstraint(["changed_by_fk"], ["ab_user.id"]),
        sa.PrimaryKeyConstraint("uuid"),
        sa.UniqueConstraint("user_id", name="uq_user_ux_preferences_user_id"),
    )


def downgrade() -> None:
    drop_table("user_ux_preferences")

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
"""Per-user UX preference storage.

Holds the server-side copy of a user's namespaced ``ux.*`` UI preferences
(view modes, onboarding dismissal, ...). One row per user, mirroring the
``user_attribute`` extension pattern; preferences are stored as a JSON
object serialized into a text column for cross-database compatibility.
"""

from __future__ import annotations

import uuid

from flask_appbuilder import Model
from sqlalchemy import Column, ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy_utils import UUIDType

from axbi.models.helpers import AuditMixinNullable


class UserUxPreference(Model, AuditMixinNullable):
    """JSON document of a single user's ``ux.*`` preferences."""

    __tablename__ = "user_ux_preferences"
    # One preference document per user; the DAO/command upsert relies on this
    # for race safety.
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_user_ux_preferences_user_id"),
    )

    uuid = Column(UUIDType(binary=True), default=uuid.uuid4, primary_key=True)
    user_id = Column(
        Integer,
        ForeignKey("ab_user.id", ondelete="CASCADE"),
        nullable=False,
    )
    # Serialized JSON object mapping ``ux.*`` keys to JSON scalars
    # (string/number/boolean/null). Kept as text so the column works on every
    # supported database, matching the convention in ``axbi.models.ai``.
    preferences = Column(Text, nullable=False, default="{}")

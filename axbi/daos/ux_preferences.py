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
from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.exc import IntegrityError

from axbi.daos.base import BaseDAO
from axbi.extensions import db
from axbi.models.user_ux_preferences import UserUxPreference
from axbi.utils import json

logger = logging.getLogger(__name__)


class UserUxPreferencesDAO(BaseDAO[UserUxPreference]):
    """Data access for per-user UX preference documents."""

    @staticmethod
    def find_by_user_id(user_id: int) -> UserUxPreference | None:
        """Return the preference row for the given user, if any."""
        return (
            db.session.query(UserUxPreference).filter_by(user_id=user_id).one_or_none()
        )

    @staticmethod
    def _decode(row: UserUxPreference) -> dict[str, Any]:
        """Decode a row's preference document (empty dict when undecodable)."""
        try:
            decoded = json.loads(row.preferences)
        except json.JSONDecodeError:
            logger.warning(
                "Ignoring undecodable UX preferences for user %s", row.user_id
            )
            return {}
        return decoded if isinstance(decoded, dict) else {}

    @classmethod
    def get_preferences(cls, user_id: int) -> dict[str, Any]:
        """Return the user's decoded preference map (empty dict when unset)."""
        row = cls.find_by_user_id(user_id)
        if row is None or not row.preferences:
            return {}
        return cls._decode(row)

    @classmethod
    def upsert_preferences(
        cls,
        user_id: int,
        preferences: dict[str, Any],
    ) -> UserUxPreference:
        """Merge ``preferences`` into the user's stored preference document.

        Creates the row when missing. When a concurrent request wins the
        first-insert race, merge into the row it created instead of
        surfacing an integrity error.
        """
        row = cls.find_by_user_id(user_id)
        if row is None:
            row = UserUxPreference(user_id=user_id)
            row.preferences = json.dumps(preferences)
            db.session.add(row)
            try:
                db.session.flush()
                return row
            except IntegrityError:
                # Lost the first-insert race; merge into the winner's row.
                db.session.rollback()
                row = cls.find_by_user_id(user_id)
                if row is None:
                    raise
        row.preferences = json.dumps({**cls._decode(row), **preferences})
        db.session.flush()
        return row

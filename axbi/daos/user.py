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

from flask_appbuilder.security.sqla.models import User
from sqlalchemy import or_

from axbi.daos.base import _escape_like, BaseDAO
from axbi.extensions import db, security_manager
from axbi.models.user_attributes import UserAttribute

logger = logging.getLogger(__name__)


class UserDAO(BaseDAO[User]):
    @staticmethod
    def find_for_filter_resolution(search_term: str, limit: int) -> list[User]:
        """Find a bounded user set for resolving MCP ownership filters.

        The defensive validation prevents this privacy-scoped lookup from
        becoming an unbounded user-directory enumeration path when called
        outside the MCP request schema.
        """
        normalized_term = search_term.strip()
        if not normalized_term:
            raise ValueError("search_term must contain a non-whitespace character")
        if limit < 1:
            raise ValueError("limit must be positive")

        user_model = security_manager.user_model
        needle = f"%{_escape_like(normalized_term)}%"
        return (
            db.session.query(user_model)
            .filter(
                or_(
                    user_model.username.ilike(needle, escape="\\"),
                    user_model.first_name.ilike(needle, escape="\\"),
                    user_model.last_name.ilike(needle, escape="\\"),
                    user_model.email.ilike(needle, escape="\\"),
                )
            )
            .order_by(user_model.username.asc())
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_by_id(user_id: int) -> User:
        return db.session.query(security_manager.user_model).filter_by(id=user_id).one()

    @staticmethod
    def set_avatar_url(user: User, url: str) -> None:
        if user.extra_attributes:
            user.extra_attributes[0].avatar_url = url
        else:
            attrs = UserAttribute(avatar_url=url, user_id=user.id)
            user.extra_attributes = [attrs]
            db.session.add(attrs)

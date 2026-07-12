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

from functools import partial
from typing import Any

from axbi.commands.base import BaseCommand
from axbi.commands.query.exceptions import (
    SavedQueryCreateFailedError,
    SavedQueryDatabaseAccessDeniedError,
    SavedQueryDatabaseNotFoundError,
    SavedQueryUserNotFoundError,
)
from axbi.daos.database import DatabaseDAO
from axbi.daos.query import SavedQueryDAO
from axbi.extensions import security_manager
from axbi.models.sql_lab import SavedQuery
from axbi.utils.core import get_user_id
from axbi.utils.decorators import on_error, transaction


class CreateSavedQueryCommand(BaseCommand):
    """Validate and persist a saved SQL query for the current user."""

    def __init__(self, data: dict[str, Any]) -> None:
        self._properties = data.copy()

    @transaction(on_error=partial(on_error, reraise=SavedQueryCreateFailedError))
    def run(self) -> SavedQuery:
        """Create the saved query within a command-owned transaction."""
        self.validate()
        return SavedQueryDAO.create(attributes=self._properties)

    def validate(self) -> None:
        """Validate database visibility and populate server-owned identity."""
        database_id = self._properties["db_id"]
        database = DatabaseDAO.find_by_id(
            database_id,
            skip_base_filter=True,
            skip_visibility_filter=True,
        )
        if database is None:
            raise SavedQueryDatabaseNotFoundError(database_id)
        if not security_manager.can_access_database(database):
            raise SavedQueryDatabaseAccessDeniedError(database.database_name)

        user_id = get_user_id()
        if user_id is None:
            raise SavedQueryUserNotFoundError()
        self._properties["user_id"] = user_id

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

from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture
from sqlalchemy.exc import SQLAlchemyError

from axbi.commands.query.create import CreateSavedQueryCommand
from axbi.commands.query.exceptions import (
    SavedQueryCreateFailedError,
    SavedQueryDatabaseAccessDeniedError,
    SavedQueryDatabaseNotFoundError,
    SavedQueryUserNotFoundError,
)


def _saved_query_properties() -> dict[str, object]:
    """Return valid command properties for a saved query."""
    return {
        "db_id": 7,
        "label": "Revenue query",
        "sql": "SELECT SUM(revenue) FROM sales",
        "schema": "analytics",
        "catalog": "warehouse",
        "description": "Revenue by period",
    }


def _mock_valid_context(mocker: MockerFixture) -> tuple[MagicMock, MagicMock]:
    """Configure a visible database and authenticated user for a command test."""
    database = MagicMock()
    database.database_name = "analytics"
    mocker.patch(
        "axbi.commands.query.create.DatabaseDAO.find_by_id",
        return_value=database,
    )
    access = mocker.patch(
        "axbi.commands.query.create.security_manager.can_access_database",
        return_value=True,
    )
    mocker.patch("axbi.commands.query.create.get_user_id", return_value=17)
    return database, access


def test_create_saved_query_uses_command_owned_identity_and_dao(
    mocker: MockerFixture,
) -> None:
    """The command validates access and owns user attribution before creation."""
    original = _saved_query_properties()
    database, access = _mock_valid_context(mocker)
    saved_query = MagicMock()
    create = mocker.patch(
        "axbi.commands.query.create.SavedQueryDAO.create",
        return_value=saved_query,
    )

    result = CreateSavedQueryCommand(original).run()

    assert result is saved_query
    assert original == _saved_query_properties()
    access.assert_called_once_with(database)
    create.assert_called_once_with(attributes={**original, "user_id": 17})


def test_create_saved_query_looks_up_database_outside_visibility_filters(
    mocker: MockerFixture,
) -> None:
    """Explicit access validation follows an unfiltered existence lookup."""
    database, _ = _mock_valid_context(mocker)
    find_database = mocker.patch(
        "axbi.commands.query.create.DatabaseDAO.find_by_id",
        return_value=database,
    )
    mocker.patch("axbi.commands.query.create.SavedQueryDAO.create")

    CreateSavedQueryCommand(_saved_query_properties()).run()

    find_database.assert_called_once_with(
        7,
        skip_base_filter=True,
        skip_visibility_filter=True,
    )


def test_create_saved_query_rejects_missing_database(
    mocker: MockerFixture,
) -> None:
    """A missing database is distinguishable from an access denial."""
    mocker.patch(
        "axbi.commands.query.create.DatabaseDAO.find_by_id",
        return_value=None,
    )
    create = mocker.patch("axbi.commands.query.create.SavedQueryDAO.create")

    with pytest.raises(SavedQueryDatabaseNotFoundError, match="ID 7"):
        CreateSavedQueryCommand(_saved_query_properties()).run()

    create.assert_not_called()


def test_create_saved_query_rejects_inaccessible_database(
    mocker: MockerFixture,
) -> None:
    """Database access remains mandatory before saved-query persistence."""
    database = MagicMock()
    database.database_name = "restricted"
    mocker.patch(
        "axbi.commands.query.create.DatabaseDAO.find_by_id",
        return_value=database,
    )
    mocker.patch(
        "axbi.commands.query.create.security_manager.can_access_database",
        return_value=False,
    )
    create = mocker.patch("axbi.commands.query.create.SavedQueryDAO.create")

    with pytest.raises(SavedQueryDatabaseAccessDeniedError, match="restricted"):
        CreateSavedQueryCommand(_saved_query_properties()).run()

    create.assert_not_called()


def test_create_saved_query_requires_session_user(mocker: MockerFixture) -> None:
    """A query cannot be persisted without server-owned user attribution."""
    _mock_valid_context(mocker)
    mocker.patch("axbi.commands.query.create.get_user_id", return_value=None)
    create = mocker.patch("axbi.commands.query.create.SavedQueryDAO.create")

    with pytest.raises(SavedQueryUserNotFoundError):
        CreateSavedQueryCommand(_saved_query_properties()).run()

    create.assert_not_called()


def test_create_saved_query_maps_persistence_error_and_rolls_back(
    mocker: MockerFixture,
) -> None:
    """SQLAlchemy failures leave the command through its stable domain error."""
    _mock_valid_context(mocker)
    mocker.patch(
        "axbi.commands.query.create.SavedQueryDAO.create",
        side_effect=SQLAlchemyError("write failed"),
    )

    with pytest.raises(SavedQueryCreateFailedError) as exc_info:
        CreateSavedQueryCommand(_saved_query_properties()).run()

    assert isinstance(exc_info.value.__cause__, SQLAlchemyError)

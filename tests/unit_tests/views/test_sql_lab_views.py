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

"""Unit tests for legacy SQL Lab views."""

import inspect
from unittest.mock import MagicMock, patch

import pytest


def _expanded_view_func():
    """Return the unwrapped body of TableSchemaView.expanded."""
    from axbi.views.sql_lab.views import TableSchemaView

    return inspect.unwrap(TableSchemaView.expanded)


@pytest.mark.parametrize("expanded", ["[]", "{}", '"true"', "1", "null"])
@patch("axbi.views.sql_lab.views.json_error_response", return_value="error")
@patch("axbi.views.sql_lab.views.get_user_id", return_value=1)
@patch("axbi.views.sql_lab.views._get_owner_id", return_value=1)
@patch("axbi.views.sql_lab.views.db")
def test_table_schema_expanded_rejects_non_boolean_payload(
    mock_db: MagicMock,
    mock_get_owner_id: MagicMock,
    mock_get_user_id: MagicMock,
    mock_json_error_response: MagicMock,
    app,
    expanded: str,
) -> None:
    mock_query = MagicMock()
    mock_query.filter_by.return_value.scalar.return_value = 5
    mock_db.session.query.return_value = mock_query

    with app.test_request_context(
        "/tableschemaview/10/expanded",
        method="POST",
        data={"expanded": expanded},
    ):
        result = _expanded_view_func()(MagicMock(), 10)

    assert result == "error"
    mock_json_error_response.assert_called_once_with(
        "expanded must be a JSON boolean",
        400,
    )
    mock_query.filter_by.return_value.update.assert_not_called()
    mock_db.session.commit.assert_not_called()
    mock_db.session.rollback.assert_called_once()
    mock_get_owner_id.assert_called_once_with(5)
    mock_get_user_id.assert_called_once_with()


@patch("axbi.views.sql_lab.views.json_success", return_value="ok")
@patch("axbi.views.sql_lab.views.get_user_id", return_value=1)
@patch("axbi.views.sql_lab.views._get_owner_id", return_value=1)
@patch("axbi.views.sql_lab.views.db")
def test_table_schema_expanded_accepts_boolean_payload(
    mock_db: MagicMock,
    mock_get_owner_id: MagicMock,
    mock_get_user_id: MagicMock,
    mock_json_success: MagicMock,
    app,
) -> None:
    mock_query = MagicMock()
    mock_query.filter_by.return_value.scalar.return_value = 5
    mock_db.session.query.return_value = mock_query

    with app.test_request_context(
        "/tableschemaview/10/expanded",
        method="POST",
        data={"expanded": "false"},
    ):
        result = _expanded_view_func()(MagicMock(), 10)

    assert result == "ok"
    mock_query.filter_by.return_value.update.assert_called_once_with(
        {"expanded": False}
    )
    mock_db.session.commit.assert_called_once()
    mock_db.session.rollback.assert_not_called()
    mock_get_owner_id.assert_called_once_with(5)
    mock_get_user_id.assert_called_once_with()
    response_payload = mock_json_success.call_args.args[0]
    assert '"expanded": false' in response_payload

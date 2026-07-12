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
import inspect
from unittest.mock import MagicMock, patch

import pytest
from flask import Flask

from axbi.queries.api import QueryRestApi


@pytest.mark.parametrize("payload", [{}, {"client_id": ["foo"]}])
def test_stop_query_rejects_invalid_payload(payload: dict[str, object]) -> None:
    """Query cancellation should reject malformed JSON before DAO dispatch."""
    app = Flask(__name__)
    api = QueryRestApi.__new__(QueryRestApi)
    api.response_400 = MagicMock(return_value=("bad request", {}))
    stop_query = inspect.unwrap(QueryRestApi.stop_query)

    with app.test_request_context(json=payload):
        with patch("axbi.queries.api.QueryDAO.stop_query") as stop_query_dao:
            result = stop_query(api)

    assert result == ("bad request", {})
    api.response_400.assert_called_once()
    stop_query_dao.assert_not_called()


def test_stop_query_rejects_malformed_json_body() -> None:
    """Query cancellation should reject parser failures before DAO dispatch."""
    app = Flask(__name__)
    api = QueryRestApi.__new__(QueryRestApi)
    api.response_400 = MagicMock(return_value=("bad request", {}))
    stop_query = inspect.unwrap(QueryRestApi.stop_query)

    with app.test_request_context(
        method="POST",
        data="{malformed",
        content_type="application/json",
    ):
        with patch("axbi.queries.api.QueryDAO.stop_query") as stop_query_dao:
            result = stop_query(api)

    assert result == ("bad request", {})
    api.response_400.assert_called_once_with(
        message={"_schema": ["Invalid input type."]}
    )
    stop_query_dao.assert_not_called()

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

from typing import Any
from unittest.mock import Mock, patch

import pytest

from superset.exceptions import SerializationError, SupersetErrorException


def _query() -> Mock:
    query = Mock()
    query.results_key = "results-key"
    query.raise_for_access.return_value = None
    return query


def _run_export_with_payload(payload: dict[str, Any] | Exception) -> None:
    from superset.commands.sql_lab.export import SqlResultExportCommand

    query = _query()
    with (
        patch("superset.commands.sql_lab.export.db") as mock_db,
        patch("superset.commands.sql_lab.export.results_backend") as mock_backend,
        patch(
            "superset.commands.sql_lab.export.utils.zlib_decompress",
            return_value=b"payload",
        ),
        patch(
            "superset.commands.sql_lab.export._deserialize_results_payload"
        ) as mock_deserialize,
    ):
        query_filter = mock_db.session.query.return_value.filter_by.return_value
        query_filter.one_or_none.return_value = query
        mock_backend.get.return_value = b"blob"
        if isinstance(payload, Exception):
            mock_deserialize.side_effect = payload
        else:
            mock_deserialize.return_value = payload

        SqlResultExportCommand("client-id").run()


def test_export_wraps_results_payload_deserialization_error() -> None:
    """Stale result-backend payloads should raise a Superset error."""
    with pytest.raises(SupersetErrorException) as exc_info:
        _run_export_with_payload(SerializationError("Unable to deserialize table"))

    assert exc_info.value.status == 404
    assert "results backend" in exc_info.value.message


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"data": [], "columns": "not-columns"},
        {"data": [], "columns": [{}]},
        {"data": [], "columns": [{"name": None}]},
    ],
)
def test_export_wraps_malformed_results_payload(payload: dict[str, Any]) -> None:
    """Malformed cached export payloads should not leak raw key/type errors."""
    with pytest.raises(SupersetErrorException) as exc_info:
        _run_export_with_payload(payload)

    assert exc_info.value.status == 404
    assert "results backend" in exc_info.value.message

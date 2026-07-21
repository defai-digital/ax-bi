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
"""handle_query_error must preserve TIMED_OUT status."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from axbi.common.db_query_status import QueryStatus
from axbi.sql_lab import handle_query_error


def test_handle_query_error_preserves_timed_out(app_context: None) -> None:
    query = MagicMock()
    query.status = QueryStatus.TIMED_OUT
    query.end_time = None
    query.database.db_engine_spec.extract_errors.return_value = []
    query.database.unique_name = "db"

    with patch("axbi.sql_lab.commit_session", return_value=True):
        payload = handle_query_error(TimeoutError("soft limit"), query)

    assert query.status == QueryStatus.TIMED_OUT
    assert payload["status"] == QueryStatus.TIMED_OUT.value


def test_handle_query_error_sets_failed_for_other_errors(app_context: None) -> None:
    query = MagicMock()
    query.status = QueryStatus.RUNNING
    query.end_time = None
    query.database.db_engine_spec.extract_errors.return_value = []
    query.database.unique_name = "db"

    with patch("axbi.sql_lab.commit_session", return_value=True):
        payload = handle_query_error(RuntimeError("boom"), query)

    assert query.status == QueryStatus.FAILED
    assert payload["status"] == QueryStatus.FAILED.value

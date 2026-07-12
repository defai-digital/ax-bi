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

import pytest

from axbi.common.db_query_status import QueryStatus
from axbi.sqllab.utils import apply_display_max_row_configuration_if_require


def test_apply_display_max_row_configuration_truncates_success_payload() -> None:
    sql_results = {
        "status": QueryStatus.SUCCESS,
        "query": {"rows": 3},
        "data": [{"id": 1}, {"id": 2}, {"id": 3}],
    }

    result = apply_display_max_row_configuration_if_require(sql_results, 2)

    assert result["data"] == [{"id": 1}, {"id": 2}]
    assert result["displayLimitReached"] is True


@pytest.mark.parametrize(
    "sql_results",
    [
        {},
        {"status": QueryStatus.SUCCESS},
        {"status": QueryStatus.SUCCESS, "query": None, "data": []},
        {"status": QueryStatus.SUCCESS, "query": {"rows": "3"}, "data": []},
        {"status": QueryStatus.SUCCESS, "query": {"rows": 3}, "data": None},
    ],
)
def test_apply_display_max_row_configuration_ignores_malformed_payloads(
    sql_results: dict[str, object],
) -> None:
    original = dict(sql_results)

    result = apply_display_max_row_configuration_if_require(sql_results, 2)

    assert result == original

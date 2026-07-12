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

import pytest

from axbi.views.sqllab import _load_requested_query


def test_load_requested_query_accepts_object() -> None:
    assert _load_requested_query('{"database_id": 1, "sql": "select 1"}') == {
        "database_id": 1,
        "sql": "select 1",
    }


@pytest.mark.parametrize(
    "form_data",
    [
        None,
        "",
        "[]",
        '"select 1"',
        "1",
        "true",
        "null",
        "{",
    ],
)
def test_load_requested_query_ignores_non_object_json(form_data: Any) -> None:
    assert _load_requested_query(form_data) is None

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

from types import SimpleNamespace

import pytest
from pytest_mock import MockerFixture

from axbi.commands.sql_lab.permalink.get import GetSqlLabPermalinkCommand
from axbi.sqllab.permalink.exceptions import SqlLabPermalinkGetFailedError


def _mock_legacy_kv(mocker: MockerFixture, value: str) -> None:
    db = mocker.patch("axbi.commands.sql_lab.permalink.get.db")
    db.session.query.return_value.filter_by.return_value.scalar.return_value = (
        SimpleNamespace(value=value)
    )


def test_get_sql_lab_permalink_decodes_legacy_kv_value(
    mocker: MockerFixture,
) -> None:
    _mock_legacy_kv(
        mocker,
        (
            '{"dbId": 1, "name": "SQL Lab", "schema": null, "catalog": null, '
            '"sql": "SELECT 1", "templateParams": null, "autorun": false}'
        ),
    )

    result = GetSqlLabPermalinkCommand("kv:1").run()

    assert result == {
        "autorun": False,
        "catalog": None,
        "dbId": 1,
        "name": "SQL Lab",
        "schema": None,
        "sql": "SELECT 1",
        "templateParams": None,
    }


def test_get_sql_lab_permalink_rejects_malformed_legacy_kv_value(
    mocker: MockerFixture,
) -> None:
    _mock_legacy_kv(mocker, '["bad-state"]')

    with pytest.raises(SqlLabPermalinkGetFailedError):
        GetSqlLabPermalinkCommand("kv:1").run()

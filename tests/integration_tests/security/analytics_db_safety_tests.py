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

import pytest
from flask import current_app
from sqlalchemy.engine.url import make_url

from axbi.exceptions import AxBISecurityException
from axbi.security.analytics_db_safety import check_sqlalchemy_uri


@pytest.mark.parametrize(
    "sqlalchemy_uri, error, error_message",
    [
        ("postgres://user:password@test.com", False, None),
        (
            "sqlite:///home/ax-bi/bad.db",
            True,
            "SQLiteDialect_pysqlite cannot be used as a data source for security reasons.",  # noqa: E501
        ),
        (
            "sqlite+pysqlite:///home/ax-bi/bad.db",
            True,
            "SQLiteDialect_pysqlite cannot be used as a data source for security reasons.",  # noqa: E501
        ),
        (
            "sqlite+aiosqlite:///home/ax-bi/bad.db",
            True,
            "SQLiteDialect_pysqlite cannot be used as a data source for security reasons.",  # noqa: E501
        ),
        (
            "sqlite+pysqlcipher:///home/ax-bi/bad.db",
            True,
            "SQLiteDialect_pysqlite cannot be used as a data source for security reasons.",  # noqa: E501
        ),
        (
            "sqlite+:///home/ax-bi/bad.db",
            True,
            "SQLiteDialect_pysqlite cannot be used as a data source for security reasons.",  # noqa: E501
        ),
        (
            "sqlite+new+driver:///home/ax-bi/bad.db",
            True,
            "SQLiteDialect_pysqlite cannot be used as a data source for security reasons.",  # noqa: E501
        ),
        (
            "sqlite+new+:///home/ax-bi/bad.db",
            True,
            "SQLiteDialect_pysqlite cannot be used as a data source for security reasons.",  # noqa: E501
        ),
        (
            "shillelagh:///home/ax-bi/bad.db",
            True,
            "shillelagh cannot be used as a data source for security reasons.",
        ),
        (
            "shillelagh+apsw:///home/ax-bi/bad.db",
            True,
            "shillelagh cannot be used as a data source for security reasons.",
        ),
        (
            "shillelagh+:///home/ax-bi/bad.db",
            True,
            "shillelagh cannot be used as a data source for security reasons.",
        ),
        (
            "shillelagh+something:///home/ax-bi/bad.db",
            True,
            "shillelagh cannot be used as a data source for security reasons.",
        ),
        (
            "shillelagh+csv:///etc/passwd",
            True,
            "shillelagh cannot be used as a data source for security reasons.",
        ),
        (
            "shillelagh+json:///etc/passwd",
            True,
            "shillelagh cannot be used as a data source for security reasons.",
        ),
        (
            "shillelagh+gsheets:///",
            True,
            "shillelagh cannot be used as a data source for security reasons.",
        ),
        (
            "duckdb:///:memory:",
            True,
            "duckdb cannot be used as a data source for security reasons.",
        ),
        (
            "duckdb:////tmp/local.db",
            True,
            "duckdb cannot be used as a data source for security reasons.",
        ),
        (
            "duckdb+duckdb_engine:////tmp/local.db",
            True,
            "duckdb cannot be used as a data source for security reasons.",
        ),
        (
            "duckdb:///md:my_db?motherduck_token=tok",
            True,
            "duckdb cannot be used as a data source for security reasons.",
        ),
    ],
)
def test_check_sqlalchemy_uri(
    app_context,
    monkeypatch,
    sqlalchemy_uri: str,
    error: bool,
    error_message: str | None,
):
    monkeypatch.setitem(current_app.config, "ALLOW_DUCKDB_CONNECTIONS", False)
    if error:
        with pytest.raises(AxBISecurityException) as excinfo:  # noqa: PT012
            check_sqlalchemy_uri(make_url(sqlalchemy_uri))
            assert str(excinfo.value) == error_message
    else:
        check_sqlalchemy_uri(make_url(sqlalchemy_uri))

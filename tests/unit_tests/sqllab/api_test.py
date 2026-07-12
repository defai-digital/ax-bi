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

import inspect
import re
from unittest.mock import MagicMock, patch

import pytest
from flask import Flask


def _disposition_filename(form_filename: str | None) -> str:
    """Return the filename rendered into a streaming CSV Content-Disposition."""
    from axbi.sqllab.api import SqlLabRestApi

    app = Flask(__name__)
    app.config["CSV_EXPORT"] = {"encoding": "utf-8"}
    with (
        app.app_context(),
        patch("axbi.sqllab.api.StreamingSqlResultExportCommand") as command_cls,
    ):
        command = command_cls.return_value
        command.run.return_value = lambda: iter([b""])
        response = SqlLabRestApi._create_streaming_csv_response(
            MagicMock(), client_id="abc123", filename=form_filename
        )
    disposition = response.headers["Content-Disposition"]
    match = re.search(r'filename="([^"]*)"', disposition)
    assert match is not None, disposition
    return match.group(1)


def test_streaming_csv_sanitizes_user_filename() -> None:
    """A path-y / header-injecting filename is sanitized before the header."""
    filename = _disposition_filename('../../etc/pa"ss\r\nSet-Cookie: x.csv')

    for bad in ("/", "\\", '"', "\r", "\n", ".."):
        assert bad not in filename


def test_streaming_csv_preserves_normal_filename() -> None:
    """A normal filename passes through unchanged."""
    assert _disposition_filename("my_results.csv") == "my_results.csv"


def test_streaming_csv_falls_back_when_filename_empty() -> None:
    """An all-unsafe filename collapses to the generated default, not empty."""
    filename = _disposition_filename("///")

    assert filename.startswith("sqllab_abc123_")
    assert filename.endswith(".csv")


@pytest.mark.parametrize(
    "template_params, expected",
    [
        ('{"region": "APAC"}', {"region": "APAC"}),
        ({"region": "APAC"}, {"region": "APAC"}),
        ("[]", {}),
        (["bad"], {}),
        ("{malformed", {}),
    ],
)
def test_load_template_params_accepts_only_objects(
    template_params: object,
    expected: dict[str, object],
) -> None:
    """SQL formatting template params should only expand mapping values."""
    from axbi.sqllab.api import _load_template_params

    assert _load_template_params(template_params) == expected


@pytest.mark.parametrize(
    "method_name",
    [
        "estimate_query_cost",
        "format_sql",
        "execute_sql_query",
    ],
)
def test_json_post_handlers_reject_malformed_json_body(method_name: str) -> None:
    """SQL Lab JSON handlers should reject parser failures as validation errors."""
    from axbi.sqllab.api import SqlLabRestApi

    app = Flask(__name__)
    api = SqlLabRestApi.__new__(SqlLabRestApi)
    api.response_400 = MagicMock(return_value=("bad request", {}))
    method = inspect.unwrap(getattr(SqlLabRestApi, method_name))

    with app.test_request_context(
        method="POST",
        data="{malformed",
        content_type="application/json",
    ):
        result = method(api)

    assert result == ("bad request", {})
    api.response_400.assert_called_once_with(
        message={"_schema": ["Invalid input type."]}
    )

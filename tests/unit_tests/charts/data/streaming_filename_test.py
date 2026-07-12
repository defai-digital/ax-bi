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
from unittest.mock import MagicMock, patch

import pytest

from tests.conftest import with_config


def _build_response(filename: str | None):
    from axbi.charts.data.api import ChartDataRestApi

    api = ChartDataRestApi.__new__(ChartDataRestApi)
    result = {"query_context": MagicMock()}

    with patch("axbi.charts.data.api.StreamingCSVExportCommand") as mock_command_cls:
        mock_command = mock_command_cls.return_value
        mock_command.run.return_value = lambda: iter([b"a,b\n"])
        return api._create_streaming_csv_response(result, filename=filename)


@pytest.mark.parametrize(
    "provided,expected_substring",
    [
        ('"; evil="x', "evil"),  # quotes/special chars stripped
        ("../../etc/passwd", "etc_passwd"),
        ("report 2020.csv", "report_2020.csv"),
    ],
)
def test_client_filename_is_sanitized(provided: str, expected_substring: str) -> None:
    response = _build_response(provided)
    disposition = response.headers["Content-Disposition"]

    # No raw quotes/newlines/path separators leak into the header.
    assert "/" not in disposition.split("filename=")[1]
    assert "\n" not in disposition
    # Header is well-formed: exactly the opening/closing quotes around the name.
    assert disposition.count('"') == 2
    assert expected_substring in disposition


def test_blank_filename_falls_back_to_default() -> None:
    response = _build_response("...")
    disposition = response.headers["Content-Disposition"]
    assert 'filename="export.csv"' in disposition


def _should_use_streaming(result: dict[str, Any], form_data: dict[str, Any]) -> bool:
    from axbi.charts.data.api import ChartDataRestApi

    api = ChartDataRestApi.__new__(ChartDataRestApi)
    return api._should_use_streaming(result, form_data=form_data)


@with_config({"CSV_STREAMING_ROW_THRESHOLD": 50})
def test_should_use_streaming_ignores_malformed_rowcount_query() -> None:
    result = {
        "query_context": MagicMock(result_format="csv", form_data={"row_limit": "bad"}),
        "queries": [{"data": []}, "not a query result"],
    }

    assert _should_use_streaming(result, {"viz_type": "table"}) is False


@with_config({"CSV_STREAMING_ROW_THRESHOLD": 50})
def test_should_use_streaming_ignores_invalid_rowcount_values() -> None:
    result = {
        "query_context": MagicMock(result_format="csv", form_data={}),
        "queries": [{"data": []}, {"data": [{"rowcount": "not-a-number"}]}],
    }

    assert (
        _should_use_streaming(result, {"viz_type": "table", "row_limit": "bad"})
        is False
    )


@with_config({"CSV_STREAMING_ROW_THRESHOLD": 50})
def test_should_use_streaming_uses_valid_rowcount() -> None:
    result = {
        "query_context": MagicMock(result_format="csv", form_data={}),
        "queries": [{"data": []}, {"data": [{"rowcount": "100"}]}],
    }

    assert _should_use_streaming(result, {"viz_type": "table"}) is True

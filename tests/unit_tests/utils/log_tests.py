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

from datetime import timedelta
from typing import Any
from unittest.mock import patch

from flask import Flask

from superset.utils import json
from superset.utils.log import (
    AbstractEventLogger,
    collect_request_payload,
    DBEventLogger,
    get_logger_from_status,
)


class RecordingEventLogger(AbstractEventLogger):
    def __init__(self) -> None:
        self.kwargs: dict[str, Any] = {}

    def log(  # pylint: disable=too-many-arguments
        self,
        user_id: int | None,
        action: str,
        dashboard_id: int | None,
        duration_ms: int | None,
        slice_id: int | None,
        referrer: str | None,
        curated_payload: dict[str, Any] | None = None,
        curated_form_data: dict[str, Any] | None = None,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        self.kwargs = kwargs


def test_log_from_status_exception() -> None:
    (func, log_level) = get_logger_from_status(500)
    assert func.__name__ == "exception"
    assert log_level == "exception"


def test_log_from_status_warning() -> None:
    (func, log_level) = get_logger_from_status(422)
    assert func.__name__ == "warning"
    assert log_level == "warning"


def test_log_from_status_info() -> None:
    (func, log_level) = get_logger_from_status(300)
    assert func.__name__ == "info"
    assert log_level == "info"


def test_log_with_context_normalizes_exploded_dict_records() -> None:
    logger = RecordingEventLogger()
    app = Flask(__name__)

    with app.test_request_context(
        "/log", method="POST", data={"explode": "records", "records": '{"a": 1}'}
    ):
        logger.log_with_context(
            "test_action", timedelta(seconds=1), log_to_statsd=False
        )

    assert logger.kwargs["records"] == [{"a": 1}]


def test_log_with_context_filters_exploded_list_records() -> None:
    logger = RecordingEventLogger()
    app = Flask(__name__)

    with app.test_request_context(
        "/log",
        method="POST",
        data={"explode": "records", "records": '[{"a": 1}, "bad", {"b": 2}]'},
    ):
        logger.log_with_context("test_action", log_to_statsd=False)

    assert logger.kwargs["records"] == [{"a": 1}, {"b": 2}]


def test_log_with_context_falls_back_for_exploded_scalar_records() -> None:
    logger = RecordingEventLogger()
    app = Flask(__name__)

    with app.test_request_context(
        "/log", method="POST", data={"explode": "records", "records": '"bad"'}
    ):
        logger.log_with_context("test_action", log_to_statsd=False)

    assert logger.kwargs["records"] == [
        {
            "explode": "records",
            "records": '"bad"',
            "path": "/log",
            "url_rule": "None",
        }
    ]


def test_collect_request_payload_ignores_non_object_json() -> None:
    app = Flask(__name__)

    with app.test_request_context("/log?query=1", method="POST", json=["bad"]):
        payload = collect_request_payload()

    assert payload == {"path": "/log", "query": "1", "url_rule": "None"}


@patch("superset.db")
def test_db_event_logger_normalizes_direct_dict_records(mock_db: Any) -> None:
    logger = DBEventLogger()

    logger.log(
        user_id=1,
        action="test_action",
        dashboard_id=None,
        duration_ms=50,
        slice_id=None,
        referrer=None,
        records={"from_dict": True},
    )

    mock_db.session.bulk_save_objects.assert_called_once()
    logs = mock_db.session.bulk_save_objects.call_args[0][0]
    assert len(logs) == 1
    assert json.loads(logs[0].json) == {"from_dict": True}

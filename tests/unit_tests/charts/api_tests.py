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
from unittest.mock import MagicMock

import pytest
from flask import Flask

from superset.charts.api import ChartRestApi


@pytest.mark.parametrize(
    ("method_name", "args"),
    [
        ("post", ()),
        ("put", (1,)),
        ("warm_up_cache", ()),
    ],
)
def test_json_body_handlers_reject_malformed_json_body(
    method_name: str,
    args: tuple[object, ...],
) -> None:
    """Chart JSON handlers should reject parser failures as validation errors."""
    app = Flask(__name__)
    api = ChartRestApi.__new__(ChartRestApi)
    api.response_400 = MagicMock(return_value="bad request")
    method = inspect.unwrap(getattr(ChartRestApi, method_name))

    with app.test_request_context(
        method="POST",
        data="{malformed",
        content_type="application/json",
    ):
        response = method(api, *args)

    assert response == "bad request"
    api.response_400.assert_called_once_with(
        message={"_schema": ["Invalid input type."]}
    )

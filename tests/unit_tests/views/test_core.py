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
"""Tests for superset.views.core module."""

from unittest.mock import Mock, patch
from urllib.parse import quote

import pytest
from flask import current_app

from superset.utils import json
from superset.utils.core import DatasourceType
from superset.views.core import _parse_datasource_key, Superset


@pytest.mark.parametrize(
    "datasource_key, expected",
    [
        ("1__table", (1, DatasourceType.TABLE)),
        ("2__dataset", (2, DatasourceType.DATASET)),
    ],
)
def test_parse_datasource_key_accepts_valid_keys(
    datasource_key: str,
    expected: tuple[int, DatasourceType],
) -> None:
    """Legacy datasource keys should parse to typed datasource details."""
    assert _parse_datasource_key(datasource_key) == expected


@pytest.mark.parametrize(
    "datasource_key",
    [
        (None,),
        ("",),
        ("bad",),
        ("1__table__extra",),
        ("bad__table",),
        ("1__bad_type",),
        ([],),
    ],
)
def test_parse_datasource_key_rejects_malformed_keys(datasource_key: object) -> None:
    """Malformed datasource keys should not raise raw parsing errors."""
    assert _parse_datasource_key(datasource_key) is None


@patch("superset.views.core.CreateFormDataCommand.run")
def test_get_redirect_url_ignores_malformed_form_data_datasource(
    create_form_data: Mock,
) -> None:
    """Malformed datasource keys should not break the explore redirect."""
    form_data = {"slice_id": 1, "viz_type": "line", "datasource": "bad"}
    with current_app.test_request_context(
        f"/superset/explore/?form_data={quote(json.dumps(form_data))}"
    ):
        assert Superset.get_redirect_url().startswith("/explore/?form_data=")

    create_form_data.assert_not_called()

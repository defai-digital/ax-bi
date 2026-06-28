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
import inspect
from unittest.mock import MagicMock, patch

import pytest
from flask import Flask

from superset.datasource.api import DatasourceRestApi


def test_parse_validation_request_rejects_non_object_body() -> None:
    """Expression validation should reject non-object JSON bodies cleanly."""
    api = DatasourceRestApi()
    app = Flask(__name__)

    with app.test_request_context(json=["not", "an", "object"]):
        with pytest.raises(ValueError, match="Expression is required"):
            api._parse_validation_request()


@patch("superset.datasource.api.cache_manager")
@patch("superset.datasource.api.DatasourceDAO")
def test_compatible_ignores_malformed_selection_body(
    mock_dao: MagicMock,
    mock_cache_manager: MagicMock,
) -> None:
    """Compatible selections should be normalized before sorting."""
    app = Flask(__name__)
    api = DatasourceRestApi()
    api.response = MagicMock(side_effect=lambda status, **kwargs: (status, kwargs))

    datasource = MagicMock()
    datasource.uid = "1__table"
    datasource.cache_timeout = 60
    datasource.get_compatible_metrics.return_value = ["metric"]
    datasource.get_compatible_dimensions.return_value = ["dimension"]
    mock_dao.get_datasource.return_value = datasource
    mock_cache_manager.data_cache.get.return_value = None

    with app.test_request_context(
        json={
            "selected_metrics": "not-list",
            "selected_dimensions": ["dim", 1, None],
        }
    ):
        result = inspect.unwrap(DatasourceRestApi.compatible)(api, "table", 1)

    assert result[0] == 200
    datasource.get_compatible_metrics.assert_called_once_with([], ["dim"])
    datasource.get_compatible_dimensions.assert_called_once_with([], ["dim"])

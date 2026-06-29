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

from unittest.mock import MagicMock

import yaml

from superset.commands.chart.export import ExportChartsCommand
from superset.utils import json


def _chart_with_params(params: str | None) -> MagicMock:
    chart = MagicMock()
    chart.export_to_dict.return_value = {
        "slice_name": "my chart",
        "viz_type": "table",
        "params": params,
    }
    chart.table = None
    return chart


def test_file_content_exports_object_params() -> None:
    content = ExportChartsCommand._file_content(  # pylint: disable=protected-access
        _chart_with_params(json.dumps({"viz_type": "table"}))
    )

    assert yaml.safe_load(content)["params"] == {"viz_type": "table"}


def test_file_content_replaces_non_object_params_with_empty_dict() -> None:
    content = ExportChartsCommand._file_content(  # pylint: disable=protected-access
        _chart_with_params("[]")
    )

    assert yaml.safe_load(content)["params"] == {}


def test_file_content_replaces_malformed_params_with_empty_dict() -> None:
    content = ExportChartsCommand._file_content(  # pylint: disable=protected-access
        _chart_with_params("{")
    )

    assert yaml.safe_load(content)["params"] == {}

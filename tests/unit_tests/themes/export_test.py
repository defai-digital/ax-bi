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

from axbi.commands.theme.export import ExportThemesCommand
from axbi.utils import json


def _theme(json_data: str) -> MagicMock:
    theme = MagicMock()
    theme.theme_name = "Test Theme"
    theme.id = 1
    theme.export_to_dict.return_value = {
        "theme_name": "Test Theme",
        "json_data": json_data,
    }
    return theme


def test_theme_export_formats_json_data_object() -> None:
    content = ExportThemesCommand._file_content(
        _theme(json.dumps({"token": {"colorPrimary": "#1890ff"}}))
    )

    payload = yaml.safe_load(content)

    assert payload["json_data"] == {"token": {"colorPrimary": "#1890ff"}}


def test_theme_export_defaults_non_object_json_data() -> None:
    content = ExportThemesCommand._file_content(_theme("[]"))

    payload = yaml.safe_load(content)

    assert payload["json_data"] == {}

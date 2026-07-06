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
import uuid

from superset.themes.schemas import (
    ImportV1ThemeSchema,
    ThemePostSchema,
    ThemePutSchema,
)
from superset.utils import json


def test_theme_post_schema_returns_sanitized_json_data() -> None:
    """Theme create payloads store sanitized JSON data."""
    payload = {
        "theme_name": "Unsafe theme",
        "json_data": json.dumps({"token": {"brandSpinnerUrl": "javascript:alert(1)"}}),
    }

    result = ThemePostSchema().load(payload)

    assert json.loads(result["json_data"]) == {"token": {"brandSpinnerUrl": ""}}


def test_theme_put_schema_returns_sanitized_json_data() -> None:
    """Theme update payloads store sanitized JSON data."""
    payload = {
        "theme_name": "Unsafe theme",
        "json_data": json.dumps(
            {"token": {"brandSpinnerSvg": '<svg onload="alert(1)"></svg>'}}
        ),
    }

    result = ThemePutSchema().load(payload)

    assert json.loads(result["json_data"]) == {
        "token": {"brandSpinnerSvg": "<svg></svg>"}
    }


def test_import_theme_schema_sanitizes_string_json_data_in_place() -> None:
    """Theme import validation sanitizes string JSON data before persistence."""
    payload = {
        "theme_name": "Unsafe theme",
        "uuid": str(uuid.uuid4()),
        "version": "1.0.0",
        "json_data": json.dumps({"token": {"brandSpinnerUrl": "javascript:alert(1)"}}),
    }

    result = ImportV1ThemeSchema().load(payload)

    assert json.loads(payload["json_data"]) == {"token": {"brandSpinnerUrl": ""}}
    assert json.loads(result["json_data"]) == {"token": {"brandSpinnerUrl": ""}}

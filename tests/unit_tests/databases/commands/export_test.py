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

from axbi.commands.database.export import parse_extra
from axbi.utils import json


def test_parse_extra_returns_empty_dict_for_non_object_json() -> None:
    assert parse_extra("[]") == {}


def test_parse_extra_returns_empty_dict_for_malformed_json() -> None:
    assert parse_extra("{") == {}


def test_parse_extra_decodes_schemas_allowed_for_csv_upload() -> None:
    assert parse_extra(
        json.dumps({"schemas_allowed_for_csv_upload": '["public", "examples"]'})
    ) == {"schemas_allowed_for_csv_upload": ["public", "examples"]}


def test_parse_extra_drops_invalid_schemas_allowed_for_csv_upload() -> None:
    assert parse_extra(json.dumps({"schemas_allowed_for_csv_upload": "not json"})) == {
        "schemas_allowed_for_csv_upload": []
    }


def test_parse_extra_drops_non_list_schemas_allowed_for_csv_upload() -> None:
    assert parse_extra(json.dumps({"schemas_allowed_for_csv_upload": "{}"})) == {
        "schemas_allowed_for_csv_upload": []
    }

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
"""Chart bulk_delete schema enforces maxItems cap."""

from __future__ import annotations

from axbi.charts.schemas import MAX_BULK_DELETE_IDS, get_delete_ids_schema


def test_bulk_delete_schema_has_max_items() -> None:
    assert get_delete_ids_schema["maxItems"] == MAX_BULK_DELETE_IDS
    assert MAX_BULK_DELETE_IDS == 1000


def test_bulk_delete_schema_rejects_oversized_list() -> None:
    # jsonschema-style validation as used by parse_rison
    from jsonschema import Draft7Validator

    validator = Draft7Validator(get_delete_ids_schema)
    ok = list(range(10))
    assert validator.is_valid(ok)
    too_many = list(range(MAX_BULK_DELETE_IDS + 1))
    assert not validator.is_valid(too_many)

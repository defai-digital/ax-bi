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

from superset.utils import json
from superset.utils.dashboard_filter_scopes_converter import (
    convert_filter_scopes,
    copy_filter_scopes,
)


def test_convert_filter_scopes_ignores_malformed_metadata_containers() -> None:
    """Malformed immune metadata should not prevent valid filters from loading."""
    filter_box = MagicMock(
        id=10,
        params=json.dumps({"filter_configs": [{"column": "country"}]}),
    )

    result = convert_filter_scopes(
        {
            "filter_immune_slices": "not-a-list",
            "filter_immune_slice_fields": "not-an-object",
        },
        [filter_box],
    )

    assert result == {
        10: {"country": {"scope": ["ROOT_ID"], "immune": []}},
    }


def test_convert_filter_scopes_skips_malformed_filter_params() -> None:
    """Malformed filter-box params and config entries should be ignored."""
    malformed_params_filter = MagicMock(id=10, params="[]")
    mixed_config_filter = MagicMock(
        id=11,
        params=json.dumps(
            {
                "filter_configs": ["bad-config", {"column": "country"}],
                "date_filter": True,
            }
        ),
    )

    result = convert_filter_scopes({}, [malformed_params_filter, mixed_config_filter])

    assert result == {
        11: {
            "__time_range": {"scope": ["ROOT_ID"], "immune": []},
            "country": {"scope": ["ROOT_ID"], "immune": []},
        },
    }


def test_convert_filter_scopes_skips_malformed_immune_ids() -> None:
    """Malformed immune ids should not crash scope generation."""
    filter_box = MagicMock(
        id=10,
        params=json.dumps({"filter_configs": [{"column": "country"}]}),
    )

    result = convert_filter_scopes(
        {
            "filter_immune_slices": [1, "bad"],
            "filter_immune_slice_fields": {
                "2": ["country"],
                "bad": ["country"],
            },
        },
        [filter_box],
    )

    assert result[10]["country"]["scope"] == ["ROOT_ID"]
    assert sorted(result[10]["country"]["immune"]) == [1, 2]


def test_copy_filter_scopes_skips_malformed_entries() -> None:
    """Malformed copied scope entries should not block valid immune remapping."""
    result = copy_filter_scopes(
        {10: 100, 20: 200},
        {
            "bad": {"country": {"immune": [10]}},  # type: ignore[dict-item]
            10: {
                "country": {"immune": [20, "bad"]},
                "broken": "not-an-object",  # type: ignore[dict-item]
            },
        },
    )

    assert result == {
        "100": {
            "country": {"immune": [200]},
            "broken": "not-an-object",
        }
    }

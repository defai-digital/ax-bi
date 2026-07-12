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

from typing import Any

import pytest

from axbi.views.custom_tags_api_mixin import CustomTagsOptimizationMixin


class BaseApiStub:
    """Base class that records pre_get_list calls from the mixin."""

    super_called = False

    def pre_get_list(self, _data: dict[str, Any]) -> None:
        """Record that the parent hook was invoked."""
        self.super_called = True


class CustomTagsApiStub(CustomTagsOptimizationMixin, BaseApiStub):
    """Concrete class for testing CustomTagsOptimizationMixin."""


@pytest.mark.parametrize(
    "data",
    [
        {"result": {"custom_tags": [{"name": "tag"}]}},
        {"result": [None, {"id": 1}, {"custom_tags": [{"name": "tag"}]}]},
        {"message": "no result"},
    ],
)
def test_pre_get_list_tolerates_malformed_result_entries(
    data: dict[str, Any],
) -> None:
    """Malformed list response entries should not break the response hook."""
    api = CustomTagsApiStub()
    api._custom_tags_only = True

    api.pre_get_list(data)

    assert api.super_called is True
    result = data.get("result")
    if isinstance(result, list):
        assert result[2]["tags"] == [{"name": "tag"}]
        assert "custom_tags" not in result[2]


def test_pre_get_list_renames_custom_tags_when_enabled() -> None:
    """custom_tags is exposed as tags when optimization is enabled."""
    api = CustomTagsApiStub()
    api._custom_tags_only = True
    data = {"result": [{"custom_tags": [{"name": "tag"}]}]}

    api.pre_get_list(data)

    assert data == {"result": [{"tags": [{"name": "tag"}]}]}


def test_pre_get_list_keeps_custom_tags_when_disabled() -> None:
    """custom_tags is not rewritten when optimization is disabled."""
    api = CustomTagsApiStub()
    api._custom_tags_only = False
    data = {"result": [{"custom_tags": [{"name": "tag"}]}]}

    api.pre_get_list(data)

    assert data == {"result": [{"custom_tags": [{"name": "tag"}]}]}

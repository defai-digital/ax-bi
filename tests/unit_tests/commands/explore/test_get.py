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
from unittest.mock import patch

import pytest

from superset.commands.explore.get import _get_slice_metadata, GetExploreCommand
from superset.commands.explore.parameters import CommandParameters
from superset.explore.permalink.exceptions import ExplorePermalinkGetFailedError
from superset.explore.permalink.schemas import ExplorePermalinkSchema
from superset.key_value.exceptions import KeyValueCodecDecodeException
from superset.key_value.types import MarshmallowKeyValueCodec
from superset.models.slice import Slice


def test_slice_metadata_handles_missing_timestamps(app: Any) -> None:
    """Explore metadata serialization should tolerate incomplete chart rows."""
    slc = Slice(created_on=None, changed_on=None)
    slc.owners = []
    slc.dashboards = []

    metadata = _get_slice_metadata(slc)

    assert metadata["created_on_humanized"] is None
    assert metadata["changed_on_humanized"] is None


@pytest.mark.parametrize(
    "permalink_value",
    [
        {
            "chartId": 1,
            "datasourceId": 1,
            "datasourceType": "table",
            "datasource": "1__table",
        },
        {
            "chartId": 1,
            "datasourceId": 1,
            "datasourceType": "table",
            "datasource": "1__table",
            "state": {"formData": "not-an-object"},
        },
        {
            "chartId": 1,
            "datasourceId": 1,
            "datasourceType": "table",
            "datasource": "1__table",
            "state": {"formData": {}, "urlParams": ["bad-url-param"]},
        },
    ],
)
def test_get_explore_rejects_malformed_permalink_state(
    permalink_value: dict[str, Any],
) -> None:
    """Malformed Explore permalinks should fail as missing values, not KeyErrors."""
    params = CommandParameters(
        permalink_key="key",
        form_data_key=None,
        datasource_id=None,
        datasource_type=None,
        slice_id=None,
    )

    with patch(
        "superset.commands.explore.get.GetExplorePermalinkCommand.run",
        return_value=permalink_value,
    ):
        with pytest.raises(ExplorePermalinkGetFailedError):
            GetExploreCommand(params).run()


def test_explore_permalink_codec_rejects_missing_state() -> None:
    """Stored Explore permalink values must include usable state."""
    codec = MarshmallowKeyValueCodec(ExplorePermalinkSchema())
    encoded = b'{"datasourceType": "table", "datasourceId": 1}'

    with pytest.raises(KeyValueCodecDecodeException):
        codec.decode(encoded)

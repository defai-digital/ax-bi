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

import pytest

from axbi.commands.explore.permalink.create import CreateExplorePermalinkCommand
from axbi.explore.permalink.exceptions import ExplorePermalinkInvalidStateError


def test_create_explore_permalink_validates_datasource_key() -> None:
    command = CreateExplorePermalinkCommand(
        {"formData": {"datasource": "12__table", "slice_id": 3}}
    )

    command.validate()


@pytest.mark.parametrize(
    "state",
    [
        {"formData": []},
        {"formData": {}},
        {"formData": {"datasource": None}},
        {"formData": {"datasource": []}},
        {"formData": {"datasource": "bad__table"}},
        {"formData": {"datasource": "1__table__extra"}},
        {"formData": {"datasource": "1__bad_type"}},
    ],
)
def test_create_explore_permalink_rejects_malformed_datasource_key(
    state: dict[str, object],
) -> None:
    command = CreateExplorePermalinkCommand(state)

    with pytest.raises(ExplorePermalinkInvalidStateError):
        command.validate()

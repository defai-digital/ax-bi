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
from pytest_mock import MockerFixture

from superset.tags.models import ObjectType


@pytest.mark.parametrize(
    "payload",
    [
        None,
        [],
        {"properties": None},
        {"properties": []},
        {"properties": {}},
        {"properties": {"tags": "not-a-list"}},
        {"properties": {"tags": [1]}},
    ],
)
def test_add_objects_rejects_malformed_tag_payloads(
    client: Any,
    full_api_access: None,
    mocker: MockerFixture,
    payload: Any,
) -> None:
    """Malformed legacy tag payloads fail before the command layer."""
    command = mocker.patch("superset.tags.api.CreateCustomTagCommand")

    response = client.post(
        f"/api/v1/tag/{ObjectType.dashboard.value}/1/",
        json=payload,
    )

    assert response.status_code == 400
    assert response.json["message"] == "Missing required field 'tags' in 'properties'"
    command.assert_not_called()


def test_add_objects_accepts_valid_tag_payload(
    client: Any,
    full_api_access: None,
    mocker: MockerFixture,
) -> None:
    """Valid legacy tag payloads still dispatch to the create command."""
    command_class = mocker.patch("superset.tags.api.CreateCustomTagCommand")
    command = command_class.return_value

    response = client.post(
        f"/api/v1/tag/{ObjectType.dashboard.value}/1/",
        json={"properties": {"tags": ["alpha", "beta"]}},
    )

    assert response.status_code == 201
    command_class.assert_called_once_with(
        ObjectType.dashboard.value, 1, ["alpha", "beta"]
    )
    command.run.assert_called_once_with()

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

from axbi.tags.models import ObjectType


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
    command = mocker.patch("axbi.tags.api.CreateCustomTagCommand")

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
    command_class = mocker.patch("axbi.tags.api.CreateCustomTagCommand")
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


def test_create_tag_rejects_malformed_json_body(
    client: Any,
    full_api_access: None,
    mocker: MockerFixture,
) -> None:
    """Malformed JSON request bodies should fail before tag creation."""
    command = mocker.patch("axbi.tags.api.CreateCustomTagWithRelationshipsCommand")

    response = client.post(
        "/api/v1/tag/",
        data="{malformed",
        content_type="application/json",
    )

    assert response.status_code == 400
    assert response.json["message"] == {"_schema": ["Invalid input type."]}
    command.assert_not_called()


def test_bulk_create_tag_rejects_malformed_json_body(
    client: Any,
    full_api_access: None,
    mocker: MockerFixture,
) -> None:
    """Malformed JSON request bodies should fail before bulk tag creation."""
    command = mocker.patch("axbi.tags.api.CreateCustomTagWithRelationshipsCommand")

    response = client.post(
        "/api/v1/tag/bulk_create",
        data="{malformed",
        content_type="application/json",
    )

    assert response.status_code == 400
    assert response.json["message"] == {"_schema": ["Invalid input type."]}
    command.assert_not_called()


def test_update_uses_schema_normalized_payload(
    client: Any,
    full_api_access: None,
    mocker: MockerFixture,
) -> None:
    """Tag updates should pass schema-coerced values to the command layer."""
    command_class = mocker.patch("axbi.tags.api.UpdateTagCommand")
    command = command_class.return_value
    command.run.return_value.id = 10

    response = client.put(
        "/api/v1/tag/10",
        json={"name": "owner", "objects_to_tag": [["dashboard", "7"]]},
    )

    assert response.status_code == 200
    command_class.assert_called_once_with(
        "10",
        {
            "name": "owner",
            "objects_to_tag": [("dashboard", 7)],
        },
    )
    command.run.assert_called_once_with()


def test_update_tag_rejects_malformed_json_body(
    client: Any,
    full_api_access: None,
    mocker: MockerFixture,
) -> None:
    """Malformed JSON request bodies should fail before tag updates."""
    command = mocker.patch("axbi.tags.api.UpdateTagCommand")

    response = client.put(
        "/api/v1/tag/10",
        data="{malformed",
        content_type="application/json",
    )

    assert response.status_code == 400
    assert response.json["message"] == {"_schema": ["Invalid input type."]}
    command.assert_not_called()

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
from __future__ import annotations

from typing import Any

import pytest
from pytest_mock import MockerFixture
from sqlalchemy.orm.session import Session

from axbi.daos.ux_preferences import UserUxPreferencesDAO
from axbi.models.user_ux_preferences import UserUxPreference
from axbi.utils import json
from axbi.views.users.schemas import UX_PREFERENCES_MAX_PAYLOAD_BYTES
from tests.unit_tests.utils.db import get_test_user

PREFERENCES_URI = "/api/v1/me/preferences/"


@pytest.fixture
def ux_tables(session: Session) -> None:
    """Create the user_ux_preferences table in the in-memory database."""
    UserUxPreference.metadata.create_all(  # pylint: disable=no-member
        session.get_bind()
    )


def login_as(mocker: MockerFixture, user_id: int, username: str) -> Any:
    """Point the API module's ``g.user`` at a test user."""
    mock_g = mocker.patch("axbi.views.users.preferences_api.g")
    mock_g.user = get_test_user(user_id, username)
    return mock_g


def test_get_preferences_empty(
    mocker: MockerFixture,
    client: Any,
    full_api_access: None,
    ux_tables: None,
) -> None:
    """A user with no stored preferences gets an empty object."""
    login_as(mocker, 1, "alpha")

    response = client.get(PREFERENCES_URI)

    assert response.status_code == 200
    assert response.json == {"result": {}}


def test_put_and_get_roundtrip(
    mocker: MockerFixture,
    client: Any,
    full_api_access: None,
    ux_tables: None,
) -> None:
    """Preferences written via PUT are returned by GET."""
    login_as(mocker, 1, "alpha")
    preferences = {
        "ux.home.onboarding_dismissed": True,
        "ux.home.thumbnails": False,
        "ux.lists.page_size": 25,
        "ux.theme": None,
    }

    put_response = client.put(PREFERENCES_URI, json=preferences)
    assert put_response.status_code == 200
    assert put_response.json == {"result": preferences}

    get_response = client.get(PREFERENCES_URI)
    assert get_response.status_code == 200
    assert get_response.json == {"result": preferences}


def test_put_merges_instead_of_replacing(
    mocker: MockerFixture,
    client: Any,
    full_api_access: None,
    ux_tables: None,
) -> None:
    """A PUT carries a partial document and merges with the stored one."""
    login_as(mocker, 1, "alpha")
    client.put(PREFERENCES_URI, json={"ux.home.thumbnails": False})

    response = client.put(PREFERENCES_URI, json={"ux.home.onboarding_dismissed": True})

    assert response.status_code == 200
    assert response.json == {
        "result": {
            "ux.home.thumbnails": False,
            "ux.home.onboarding_dismissed": True,
        }
    }


def test_put_overwrites_single_key(
    mocker: MockerFixture,
    client: Any,
    full_api_access: None,
    ux_tables: None,
) -> None:
    """Re-writing an existing key updates only that key."""
    login_as(mocker, 1, "alpha")
    client.put(
        PREFERENCES_URI,
        json={"ux.home.thumbnails": False, "ux.home.onboarding_dismissed": True},
    )

    response = client.put(PREFERENCES_URI, json={"ux.home.thumbnails": True})

    assert response.status_code == 200
    assert response.json == {
        "result": {
            "ux.home.thumbnails": True,
            "ux.home.onboarding_dismissed": True,
        }
    }


def test_put_rejects_keys_outside_ux_namespace(
    mocker: MockerFixture,
    client: Any,
    full_api_access: None,
    ux_tables: None,
) -> None:
    """Keys outside the ``ux.*`` allowlist are rejected with a 400."""
    login_as(mocker, 1, "alpha")

    for payload in (
        {"home.thumbnails": False},
        {"UX.home.thumbnails": False},
        {"ux": False},
        {"ux.Home.thumbnails": False},
        {"database.connections": {"evil": True}},
    ):
        response = client.put(PREFERENCES_URI, json=payload)
        assert response.status_code == 400, payload


def test_put_rejects_non_scalar_values(
    mocker: MockerFixture,
    client: Any,
    full_api_access: None,
    ux_tables: None,
) -> None:
    """Objects and arrays are rejected as preference values."""
    login_as(mocker, 1, "alpha")

    for payload in (
        {"ux.home": {"thumbnails": False}},
        {"ux.home.filters": ["a", "b"]},
    ):
        response = client.put(PREFERENCES_URI, json=payload)
        assert response.status_code == 400, payload


def test_put_rejects_non_object_body(
    mocker: MockerFixture,
    client: Any,
    full_api_access: None,
    ux_tables: None,
) -> None:
    """A JSON body that is not an object is rejected."""
    login_as(mocker, 1, "alpha")

    response = client.put(PREFERENCES_URI, json=["ux.home.thumbnails"])

    assert response.status_code == 400


def test_put_rejects_oversized_payload(
    mocker: MockerFixture,
    client: Any,
    full_api_access: None,
    ux_tables: None,
) -> None:
    """Payloads beyond the 8KB cap are rejected."""
    login_as(mocker, 1, "alpha")
    payload = {"ux.home.notes": "x" * UX_PREFERENCES_MAX_PAYLOAD_BYTES}

    response = client.put(PREFERENCES_URI, json=payload)

    assert response.status_code == 400


def test_preferences_are_isolated_per_user(
    mocker: MockerFixture,
    client: Any,
    full_api_access: None,
    ux_tables: None,
) -> None:
    """One user cannot read or overwrite another user's preferences."""
    login_as(mocker, 1, "alpha")
    client.put(PREFERENCES_URI, json={"ux.home.thumbnails": False})

    login_as(mocker, 2, "beta")
    get_response = client.get(PREFERENCES_URI)
    assert get_response.status_code == 200
    assert get_response.json == {"result": {}}

    put_response = client.put(PREFERENCES_URI, json={"ux.home.thumbnails": True})
    assert put_response.status_code == 200
    assert put_response.json == {"result": {"ux.home.thumbnails": True}}

    login_as(mocker, 1, "alpha")
    get_response = client.get(PREFERENCES_URI)
    assert get_response.json == {"result": {"ux.home.thumbnails": False}}


def test_get_preferences_anonymous_unauthorized(
    mocker: MockerFixture,
    client: Any,
    full_api_access: None,
    ux_tables: None,
) -> None:
    """Anonymous callers get a 401 even when route access is granted."""
    mock_g = mocker.patch("axbi.views.users.preferences_api.g")
    mock_g.user = None

    assert client.get(PREFERENCES_URI).status_code == 401


def test_put_preferences_anonymous_unauthorized(
    mocker: MockerFixture,
    client: Any,
    full_api_access: None,
    ux_tables: None,
) -> None:
    """Anonymous callers cannot write preferences."""
    mock_g = mocker.patch("axbi.views.users.preferences_api.g")
    mock_g.user.is_anonymous = True

    response = client.put(PREFERENCES_URI, json={"ux.home.thumbnails": False})

    assert response.status_code == 401


def test_put_rejects_malformed_ux_keys(
    mocker: MockerFixture,
    client: Any,
    full_api_access: None,
    ux_tables: None,
) -> None:
    """Keys with empty segments or trailing newlines are rejected."""
    login_as(mocker, 1, "alpha")

    for payload in (
        {"ux.home.thumbnails\n": False},
        {"ux..thumbnails": False},
        {"ux.home.": False},
        {"ux.": False},
    ):
        response = client.put(PREFERENCES_URI, json=payload)
        assert response.status_code == 400, payload


def test_put_rejects_non_finite_numbers(
    mocker: MockerFixture,
    client: Any,
    full_api_access: None,
    ux_tables: None,
) -> None:
    """NaN and infinities are rejected as preference values."""
    login_as(mocker, 1, "alpha")

    for value in (float("nan"), float("inf"), float("-inf")):
        response = client.put(PREFERENCES_URI, json={"ux.home.threshold": value})
        assert response.status_code == 400, value


def test_put_rejects_when_merged_document_exceeds_cap(
    mocker: MockerFixture,
    client: Any,
    full_api_access: None,
    ux_tables: None,
) -> None:
    """The size cap applies to the merged document, not just one request."""
    login_as(mocker, 1, "alpha")
    chunk = "x" * (UX_PREFERENCES_MAX_PAYLOAD_BYTES // 2 + 100)

    first = client.put(PREFERENCES_URI, json={"ux.home.notes_a": chunk})
    assert first.status_code == 200

    second = client.put(PREFERENCES_URI, json={"ux.home.notes_b": chunk})
    assert second.status_code == 400
    assert client.get(PREFERENCES_URI).json == {"result": {"ux.home.notes_a": chunk}}


def test_upsert_preferences_merges_after_concurrent_insert(
    mocker: MockerFixture,
    session: Session,
    ux_tables: None,
) -> None:
    """A lost first-insert race merges into the winner's row instead of failing."""
    winner = UserUxPreference(user_id=1, preferences='{"ux.won": true}')
    session.add(winner)
    session.commit()

    real_find = UserUxPreferencesDAO.find_by_user_id
    lookups = 0

    def racy_find(user_id: int) -> UserUxPreference | None:
        nonlocal lookups
        lookups += 1
        # The first lookup happens before the winner's row becomes visible.
        return None if lookups == 1 else real_find(user_id)

    mocker.patch.object(UserUxPreferencesDAO, "find_by_user_id", side_effect=racy_find)

    row = UserUxPreferencesDAO.upsert_preferences(1, {"ux.lost": False})

    assert row.uuid == winner.uuid
    assert json.loads(row.preferences) == {"ux.won": True, "ux.lost": False}
    assert session.query(UserUxPreference).count() == 1

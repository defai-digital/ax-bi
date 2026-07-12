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

import pytest
from flask_appbuilder.security.sqla.models import User
from sqlalchemy.exc import NoResultFound

from axbi import db
from axbi.daos.user import UserDAO
from axbi.extensions import security_manager
from axbi.models.user_attributes import UserAttribute
from tests.unit_tests.fixtures.common import admin_user, after_each  # noqa: F401


def _add_user(
    username: str,
    *,
    first_name: str = "Boundary",
    last_name: str = "User",
    email: str | None = None,
) -> User:
    """Persist a user for DAO search tests."""
    user = User(
        username=username,
        first_name=first_name,
        last_name=last_name,
        email=email or f"{username}@example.org",
        roles=[],
    )
    db.session.add(user)
    db.session.flush()
    return user


def test_get_by_id_found(admin_user: User, after_each: None) -> None:  # noqa: F811
    user = UserDAO.get_by_id(admin_user.id)
    assert user.id == admin_user.id


def test_get_by_id_not_found():
    with pytest.raises(NoResultFound):
        UserDAO.get_by_id(123456)


def test_set_avatar_url_with_existing_attributes(
    admin_user: User,  # noqa: F811
    after_each: None,  # noqa: F811
) -> None:
    admin_user.extra_attributes = [
        UserAttribute(user_id=admin_user.id, avatar_url="old_url"),
    ]
    db.session.flush()

    new_url = "http://newurl.com"
    UserDAO.set_avatar_url(admin_user, new_url)
    user = UserDAO.get_by_id(admin_user.id)
    assert user.extra_attributes[0].avatar_url == new_url


def test_set_avatar_url_without_existing_attributes(
    admin_user: User,  # noqa: F811
    after_each: None,  # noqa: F811
) -> None:
    new_url = "http://newurl.com"
    UserDAO.set_avatar_url(admin_user, new_url)

    user = UserDAO.get_by_id(admin_user.id)
    assert len(admin_user.extra_attributes) == 1
    assert user.extra_attributes[0].avatar_url == new_url


def test_get_by_id_custom_user_class(
    monkeypatch: pytest.MonkeyPatch,
    admin_user: User,  # noqa: F811
    after_each: None,  # noqa: F811
) -> None:
    class CustomUserModel(User):
        __tablename__ = "ab_user"

    monkeypatch.setattr(security_manager, "user_model", CustomUserModel)

    user = UserDAO.get_by_id(admin_user.id)
    assert isinstance(user, CustomUserModel)


@pytest.mark.parametrize(
    "search_term",
    ["mcpresolverusername", "mcpresolverfirst", "mcpresolverlast", "resolver-mail"],
)
def test_find_for_filter_resolution_matches_supported_identity_fields(
    search_term: str,
    admin_user: User,  # noqa: F811
    after_each: None,  # noqa: F811
) -> None:
    """The resolver searches username, first name, last name, and email."""
    user = _add_user(
        "mcpresolverusername",
        first_name="McpResolverFirst",
        last_name="McpResolverLast",
        email="resolver-mail@example.org",
    )

    result = UserDAO.find_for_filter_resolution(search_term, limit=10)

    assert result == [user]


def test_find_for_filter_resolution_treats_like_wildcards_literally(
    admin_user: User,  # noqa: F811
    after_each: None,  # noqa: F811
) -> None:
    """Percent and underscore characters cannot broaden directory searches."""
    percent_user = _add_user(
        "mcp_percent_literal",
        first_name="Mcp%Resolver",
        email="mcp-percent-literal@example.org",
    )
    _add_user(
        "mcp_percent_decoy",
        first_name="McpXResolver",
        email="mcp-percent-decoy@example.org",
    )
    underscore_user = _add_user(
        "mcp_underscore_literal",
        first_name="Mcp_Resolver",
        email="mcp-underscore-literal@example.org",
    )
    _add_user(
        "mcp_underscore_decoy",
        first_name="McpYResolver",
        email="mcp-underscore-decoy@example.org",
    )

    percent_results = UserDAO.find_for_filter_resolution("Mcp%Resolver", limit=10)
    underscore_results = UserDAO.find_for_filter_resolution(
        "Mcp_Resolver",
        limit=10,
    )

    assert percent_results == [percent_user]
    assert underscore_results == [underscore_user]


def test_find_for_filter_resolution_orders_before_applying_limit(
    admin_user: User,  # noqa: F811
    after_each: None,  # noqa: F811
) -> None:
    """Bounded resolver results remain deterministic by username."""
    first = _add_user("aa_mcpbound")
    second = _add_user("mm_mcpbound")
    _add_user("zz_mcpbound")

    result = UserDAO.find_for_filter_resolution("mcpbound", limit=2)

    assert result == [first, second]


@pytest.mark.parametrize("search_term", ["", " ", "\t", "\n"])
def test_find_for_filter_resolution_rejects_blank_search(
    search_term: str,
) -> None:
    """DAO callers cannot bypass the MCP schema's non-enumeration safeguard."""
    with pytest.raises(ValueError, match="non-whitespace"):
        UserDAO.find_for_filter_resolution(search_term, limit=10)


def test_find_for_filter_resolution_rejects_nonpositive_limit() -> None:
    """DAO callers must always supply a positive result bound."""
    with pytest.raises(ValueError, match="positive"):
        UserDAO.find_for_filter_resolution("mcpbound", limit=0)

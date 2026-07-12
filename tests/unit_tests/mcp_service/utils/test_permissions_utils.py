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

"""Tests for active MCP permission adapters."""

from unittest.mock import Mock, patch

from axbi.mcp_service.utils import permissions_utils
from axbi.mcp_service.utils.permissions_utils import (
    current_user_can_access,
    current_user_can_access_database,
    get_current_user,
    user_can_access_dataset_permission,
)


def test_get_current_user_returns_none_without_app_context() -> None:
    with patch.object(permissions_utils, "has_app_context", return_value=False):
        assert get_current_user() is None


def test_get_current_user_reads_flask_context_user() -> None:
    user = Mock()
    with (
        patch.object(permissions_utils, "has_app_context", return_value=True),
        patch.object(permissions_utils, "g") as flask_global,
    ):
        flask_global.user = user

        assert get_current_user() is user


def test_user_can_access_dataset_permission_uses_dataset_resource() -> None:
    with patch("axbi.security_manager.can_access", return_value=True) as can_access:
        assert user_can_access_dataset_permission("can_write") is True

    can_access.assert_called_once_with("can_write", "Dataset")


def test_current_user_can_access_delegates_to_security_manager() -> None:
    with patch("axbi.security_manager.can_access", return_value=False) as can_access:
        assert current_user_can_access("can_read", "Dashboard") is False

    can_access.assert_called_once_with("can_read", "Dashboard")


def test_current_user_can_access_database_delegates_to_security_manager() -> None:
    database = Mock()
    with patch(
        "axbi.security_manager.can_access_database", return_value=True
    ) as can_access_database:
        assert current_user_can_access_database(database) is True

    can_access_database.assert_called_once_with(database)

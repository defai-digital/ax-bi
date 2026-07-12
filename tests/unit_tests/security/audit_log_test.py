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

from unittest.mock import MagicMock, patch

from flask_appbuilder.security.sqla.models import Group, Role, User

from axbi.security.manager import (
    _log_audit_event,
    AxBIGroupApi,
    AxBIRoleApi,
    AxBISecurityManager,
    AxBIUserApi,
)


@patch("axbi.extensions.event_logger")
@patch("axbi.security.manager.get_user_id", return_value=1)
def test_log_audit_event_calls_event_logger(
    mock_get_user_id: MagicMock,
    mock_event_logger: MagicMock,
) -> None:
    """_log_audit_event delegates to the configured event_logger."""
    _log_audit_event("TestAction", {"key": "value"})

    mock_event_logger.log.assert_called_once_with(
        user_id=1,
        action="TestAction",
        dashboard_id=None,
        duration_ms=None,
        slice_id=None,
        referrer=None,
        curated_payload=None,
        curated_form_data=None,
        records=[{"key": "value"}],
    )


@patch("axbi.extensions.event_logger")
@patch("axbi.security.manager.get_user_id", return_value=1)
def test_log_audit_event_handles_logger_error(
    mock_get_user_id: MagicMock,
    mock_event_logger: MagicMock,
) -> None:
    """_log_audit_event does not raise on event_logger errors."""
    mock_event_logger.log.side_effect = Exception("Logger error")
    # Should not raise
    _log_audit_event("TestAction", {"key": "value"})


# --- Role CRUD ---


@patch("axbi.security.manager._log_audit_event")
def test_role_api_post_add_logs_event(mock_log: MagicMock) -> None:
    """AxBIRoleApi.post_add logs a RoleCreated event."""
    api = AxBIRoleApi.__new__(AxBIRoleApi)
    role = MagicMock(spec=Role)
    role.name = "TestRole"
    role.id = 42
    api.post_add(role)
    mock_log.assert_called_once_with(
        "RoleCreated", {"role_name": "TestRole", "role_id": 42}
    )


@patch("axbi.security.manager._log_audit_event")
def test_role_api_post_update_logs_event(mock_log: MagicMock) -> None:
    """AxBIRoleApi.post_update logs a RoleUpdated event."""
    api = AxBIRoleApi.__new__(AxBIRoleApi)
    role = MagicMock(spec=Role)
    role.name = "TestRole"
    role.id = 42
    api.post_update(role)
    mock_log.assert_called_once_with(
        "RoleUpdated", {"role_name": "TestRole", "role_id": 42}
    )


@patch("axbi.security.manager._log_audit_event")
def test_role_api_post_delete_logs_event(mock_log: MagicMock) -> None:
    """AxBIRoleApi.post_delete logs a RoleDeleted event."""
    api = AxBIRoleApi.__new__(AxBIRoleApi)
    role = MagicMock(spec=Role)
    role.name = "TestRole"
    role.id = 42
    api.post_delete(role)
    mock_log.assert_called_once_with(
        "RoleDeleted", {"role_name": "TestRole", "role_id": 42}
    )


# --- User CRUD ---


@patch("axbi.security.manager._log_audit_event")
def test_user_api_post_add_logs_event(mock_log: MagicMock) -> None:
    """AxBIUserApi.post_add logs a UserCreated event."""
    api = AxBIUserApi.__new__(AxBIUserApi)
    user = MagicMock(spec=User)
    user.username = "testuser"
    user.id = 7
    user.email = "test@example.com"
    api.post_add(user)
    mock_log.assert_called_once_with(
        "UserCreated",
        {
            "target_username": "testuser",
            "target_user_id": 7,
            "email": "test@example.com",
        },
    )


@patch("axbi.security.manager._log_audit_event")
def test_user_api_post_update_logs_event(mock_log: MagicMock) -> None:
    """AxBIUserApi.post_update logs a UserUpdated event."""
    api = AxBIUserApi.__new__(AxBIUserApi)
    user = MagicMock(spec=User)
    user.username = "testuser"
    user.id = 7
    user.email = "test@example.com"
    user.active = True
    api.post_update(user)
    mock_log.assert_called_once_with(
        "UserUpdated",
        {
            "target_username": "testuser",
            "target_user_id": 7,
            "email": "test@example.com",
            "active": True,
        },
    )


@patch("axbi.security.manager._log_audit_event")
def test_user_api_post_delete_logs_event(mock_log: MagicMock) -> None:
    """AxBIUserApi.post_delete logs a UserDeleted event."""
    api = AxBIUserApi.__new__(AxBIUserApi)
    user = MagicMock(spec=User)
    user.username = "testuser"
    user.id = 7
    api.post_delete(user)
    mock_log.assert_called_once_with(
        "UserDeleted",
        {"target_username": "testuser", "target_user_id": 7},
    )


# --- Group CRUD ---


@patch("axbi.security.manager._log_audit_event")
def test_group_api_post_add_logs_event(mock_log: MagicMock) -> None:
    """AxBIGroupApi.post_add logs a GroupCreated event."""
    api = AxBIGroupApi.__new__(AxBIGroupApi)
    group = MagicMock(spec=Group)
    group.name = "TestGroup"
    group.id = 10
    api.post_add(group)
    mock_log.assert_called_once_with(
        "GroupCreated", {"group_name": "TestGroup", "group_id": 10}
    )


@patch("axbi.security.manager._log_audit_event")
def test_group_api_post_update_logs_event(mock_log: MagicMock) -> None:
    """AxBIGroupApi.post_update logs a GroupUpdated event."""
    api = AxBIGroupApi.__new__(AxBIGroupApi)
    group = MagicMock(spec=Group)
    group.name = "TestGroup"
    group.id = 10
    api.post_update(group)
    mock_log.assert_called_once_with(
        "GroupUpdated", {"group_name": "TestGroup", "group_id": 10}
    )


@patch("axbi.security.manager._log_audit_event")
def test_group_api_post_delete_logs_event(mock_log: MagicMock) -> None:
    """AxBIGroupApi.post_delete logs a GroupDeleted event."""
    api = AxBIGroupApi.__new__(AxBIGroupApi)
    group = MagicMock(spec=Group)
    group.name = "TestGroup"
    group.id = 10
    api.post_delete(group)
    mock_log.assert_called_once_with(
        "GroupDeleted", {"group_name": "TestGroup", "group_id": 10}
    )


# --- Login / Logout ---


@patch("axbi.security.session_invalidation.stamp_login_time")
@patch("axbi.security.manager._log_audit_event")
def test_on_user_login_logs_event(
    mock_log: MagicMock, mock_stamp_login_time: MagicMock
) -> None:
    """on_user_login logs a UserLoggedIn event and stamps the session."""
    sm = AxBISecurityManager.__new__(AxBISecurityManager)
    user = MagicMock(spec=User)
    user.username = "testuser"
    user.id = 7

    sm.on_user_login(user)

    mock_stamp_login_time.assert_called_once()
    mock_log.assert_called_once_with(
        "UserLoggedIn", {"username": "testuser", "user_id": 7}
    )


@patch("axbi.security.manager._log_audit_event")
def test_on_user_login_failed_logs_event(mock_log: MagicMock) -> None:
    """on_user_login_failed logs a UserLoginFailed event."""
    sm = AxBISecurityManager.__new__(AxBISecurityManager)
    user = MagicMock(spec=User)
    user.username = "testuser"
    user.id = 7

    sm.on_user_login_failed(user)

    mock_log.assert_called_once_with(
        "UserLoginFailed", {"username": "testuser", "user_id": 7}
    )


@patch("axbi.security.manager._log_audit_event")
def test_on_user_logout_logs_event(mock_log: MagicMock) -> None:
    """on_user_logout logs a UserLoggedOut event."""
    sm = AxBISecurityManager.__new__(AxBISecurityManager)
    user = MagicMock(spec=User)
    user.username = "testuser"
    user.id = 7

    sm.on_user_logout(user)

    mock_log.assert_called_once_with(
        "UserLoggedOut", {"username": "testuser", "user_id": 7}
    )

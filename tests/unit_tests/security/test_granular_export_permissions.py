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

from flask_appbuilder.security.sqla.manager import SecurityManager

from axbi.security.manager import AxBISecurityManager


def test_granular_export_permissions_registered_in_create_custom_permissions(
    app_context: None,
) -> None:
    """Verify that create_custom_permissions registers all granular export perms."""
    from axbi.extensions import appbuilder

    sm = AxBISecurityManager(appbuilder)
    sm.add_permission_view_menu = MagicMock()

    sm.create_custom_permissions()

    calls = [
        (call.args[0], call.args[1])
        for call in sm.add_permission_view_menu.call_args_list
    ]
    assert ("can_export_data", "AxBI") in calls
    assert ("can_export_image", "AxBI") in calls
    assert ("can_copy_clipboard", "AxBI") in calls


def test_sqllab_extra_permission_views_include_export_perms() -> None:
    """Verify SQLLAB_EXTRA_PERMISSION_VIEWS includes granular export perms."""
    assert ("can_export_data", "AxBI") in (
        AxBISecurityManager.SQLLAB_EXTRA_PERMISSION_VIEWS
    )
    assert ("can_copy_clipboard", "AxBI") in (
        AxBISecurityManager.SQLLAB_EXTRA_PERMISSION_VIEWS
    )


def test_gamma_excluded_pvms_excludes_export_data_and_image() -> None:
    """Verify GAMMA_EXCLUDED_PVMS excludes can_export_data and can_export_image."""
    assert ("can_export_data", "AxBI") in (AxBISecurityManager.GAMMA_EXCLUDED_PVMS)
    assert ("can_export_image", "AxBI") in (AxBISecurityManager.GAMMA_EXCLUDED_PVMS)


def test_gamma_excluded_pvms_allows_copy_clipboard() -> None:
    """Verify GAMMA_EXCLUDED_PVMS does NOT exclude can_copy_clipboard."""
    assert ("can_copy_clipboard", "AxBI") not in (
        AxBISecurityManager.GAMMA_EXCLUDED_PVMS
    )


def test_is_gamma_pvm_excludes_export_data(app_context: None) -> None:
    """Verify _is_gamma_pvm returns False for can_export_data."""
    from axbi.extensions import appbuilder

    sm = AxBISecurityManager(appbuilder)
    pvm = MagicMock()
    pvm.permission.name = "can_export_data"
    pvm.view_menu.name = "AxBI"

    assert sm._is_gamma_pvm(pvm) is False


def test_is_gamma_pvm_excludes_export_image(app_context: None) -> None:
    """Verify _is_gamma_pvm returns False for can_export_image."""
    from axbi.extensions import appbuilder

    sm = AxBISecurityManager(appbuilder)
    pvm = MagicMock()
    pvm.permission.name = "can_export_image"
    pvm.view_menu.name = "AxBI"

    assert sm._is_gamma_pvm(pvm) is False


def test_api_key_view_menu_is_self_service_for_authenticated_roles(
    app_context: None,
) -> None:
    """Alpha and Gamma may manage only their own keys; Public may not."""
    from axbi.extensions import appbuilder

    sm = AxBISecurityManager(appbuilder)
    pvm = MagicMock()
    pvm.permission.name = "can_create"
    pvm.view_menu.name = "ApiKey"

    assert "ApiKey" not in AxBISecurityManager.ADMIN_ONLY_VIEW_MENUS
    assert sm._is_alpha_pvm(pvm) is True
    assert sm._is_gamma_pvm(pvm) is True
    assert sm._is_public_pvm(pvm) is False


def test_create_api_key_persists_masked_display_hint(app_context: None) -> None:
    """The stored hint identifies a key without retaining its plaintext."""
    from axbi.extensions import appbuilder

    sm = AxBISecurityManager(appbuilder)
    api_key = MagicMock()
    parent_result = {
        "uuid": "key-uuid",
        "name": "AX BI MCP",
        "key": "sst_M8hayd7-example-secret-iay8hfdsG",
        "key_prefix": "sst_",
    }

    with (
        patch.object(SecurityManager, "create_api_key", return_value=parent_result),
        patch.object(sm, "get_api_key_by_uuid", return_value=api_key),
        patch.object(sm.session, "commit") as commit,
    ):
        result = sm.create_api_key(MagicMock(), "AX BI MCP")

    assert result is not None
    assert result["key_prefix"] == "M8hayhfdsG"
    assert api_key.key_prefix == "M8hayhfdsG"
    commit.assert_called_once_with()


def test_is_gamma_pvm_allows_copy_clipboard(app_context: None) -> None:
    """Verify _is_gamma_pvm returns True for can_copy_clipboard."""
    from axbi.extensions import appbuilder

    sm = AxBISecurityManager(appbuilder)
    pvm = MagicMock()
    pvm.permission.name = "can_copy_clipboard"
    pvm.view_menu.name = "AxBI"
    # Ensure the pvm doesn't trigger other exclusion checks
    with (
        patch.object(sm, "_is_user_defined_permission", return_value=False),
        patch.object(sm, "_is_admin_only", return_value=False),
        patch.object(sm, "_is_alpha_only", return_value=False),
        patch.object(sm, "_is_sql_lab_only", return_value=False),
        patch.object(sm, "_is_accessible_to_all", return_value=False),
    ):
        assert sm._is_gamma_pvm(pvm) is True

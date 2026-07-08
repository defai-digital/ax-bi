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

from superset.mcp_service.utils.config_utils import (
    get_fab_api_key_enabled,
    get_fab_api_key_prefixes,
    get_mcp_api_key_create_url,
    get_mcp_api_key_enabled_flag,
    get_mcp_auth_enabled,
    get_mcp_auth_factory,
    get_mcp_bug_report_contact,
    get_mcp_cache_config,
    get_mcp_debug_enabled,
    get_mcp_dev_username,
    get_mcp_disabled_tools,
    get_mcp_hello_page_config,
    get_mcp_jwks_uri,
    get_mcp_jwt_algorithm,
    get_mcp_jwt_algorithm_with_default,
    get_mcp_jwt_audience,
    get_mcp_jwt_debug_errors,
    get_mcp_jwt_issuer,
    get_mcp_jwt_public_key,
    get_mcp_jwt_secret,
    get_mcp_rate_limit_config,
    get_mcp_rbac_enabled,
    get_mcp_required_scopes,
    get_mcp_response_size_config,
    get_mcp_service_url_config,
    get_mcp_store_config,
    get_mcp_tool_search_config,
    get_mcp_user_resolver,
    get_screenshot_animation_wait,
    get_screenshot_load_wait,
    get_screenshot_locate_wait,
    get_screenshot_replace_unexpected_errors,
    get_screenshot_selenium_headstart,
    get_superset_admin_role_name,
    get_superset_app_icon,
    get_superset_app_name,
    get_superset_row_limit,
    get_superset_webserver_address,
    get_upload_max_file_size_bytes,
    get_webdriver_baseurl_user_friendly,
    get_webdriver_pool_config,
    get_webdriver_type,
    is_mcp_jwt_configured,
)


def test_get_superset_app_name_reads_supplied_config() -> None:
    assert get_superset_app_name({"APP_NAME": "AX BI"}) == "AX BI"


def test_get_superset_app_name_uses_default_for_missing_key() -> None:
    assert get_superset_app_name({}) == "Superset"


def test_get_superset_app_name_supports_custom_default() -> None:
    assert get_superset_app_name({}, default="Analytics") == "Analytics"


def test_get_superset_app_icon_reads_supplied_config() -> None:
    assert get_superset_app_icon({"APP_ICON": "/static/icon.png"}) == "/static/icon.png"


def test_get_superset_app_icon_defaults_to_empty_string() -> None:
    assert get_superset_app_icon({}) == ""


def test_get_superset_admin_role_name_reads_supplied_config() -> None:
    assert get_superset_admin_role_name({"AUTH_ROLE_ADMIN": "Superuser"}) == "Superuser"


def test_get_superset_admin_role_name_preserves_missing_key_error() -> None:
    with pytest.raises(KeyError):
        get_superset_admin_role_name({})


def test_get_superset_webserver_address_reads_supplied_config() -> None:
    assert (
        get_superset_webserver_address(
            {"SUPERSET_WEBSERVER_ADDRESS": "https://superset.example"}
        )
        == "https://superset.example"
    )


def test_get_superset_webserver_address_reads_environment_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SUPERSET_WEBSERVER_ADDRESS", "http://127.0.0.1:8080")

    assert get_superset_webserver_address({}) == "http://127.0.0.1:8080"


def test_get_superset_webserver_address_prefers_config_over_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SUPERSET_WEBSERVER_ADDRESS", "http://127.0.0.1:8080")

    assert (
        get_superset_webserver_address(
            {"SUPERSET_WEBSERVER_ADDRESS": "https://superset.example"}
        )
        == "https://superset.example"
    )


def test_get_superset_webserver_address_defaults_to_empty_string(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("SUPERSET_WEBSERVER_ADDRESS", raising=False)

    assert get_superset_webserver_address({}) == ""


def test_screenshot_timing_helpers_read_supplied_config() -> None:
    config = {
        "SCREENSHOT_SELENIUM_HEADSTART": 1,
        "SCREENSHOT_LOCATE_WAIT": 2,
        "SCREENSHOT_LOAD_WAIT": 3,
        "SCREENSHOT_SELENIUM_ANIMATION_WAIT": 4,
    }

    assert get_screenshot_selenium_headstart(config) == 1
    assert get_screenshot_locate_wait(config) == 2
    assert get_screenshot_load_wait(config) == 3
    assert get_screenshot_animation_wait(config) == 4


@pytest.mark.parametrize(
    "helper",
    [
        get_screenshot_selenium_headstart,
        get_screenshot_locate_wait,
        get_screenshot_load_wait,
        get_screenshot_animation_wait,
    ],
)
def test_screenshot_timing_helpers_preserve_missing_key_error(helper) -> None:
    with pytest.raises(KeyError):
        helper({})


def test_get_screenshot_replace_unexpected_errors_reads_supplied_config() -> None:
    assert (
        get_screenshot_replace_unexpected_errors(
            {"SCREENSHOT_REPLACE_UNEXPECTED_ERRORS": True}
        )
        is True
    )


def test_get_screenshot_replace_unexpected_errors_returns_none_when_unset() -> None:
    assert get_screenshot_replace_unexpected_errors({}) is None


def test_get_webdriver_type_reads_supplied_config() -> None:
    assert get_webdriver_type({"WEBDRIVER_TYPE": "chrome"}) == "chrome"


def test_get_webdriver_type_defaults_to_firefox() -> None:
    assert get_webdriver_type({}) == "firefox"


def test_get_webdriver_pool_config_reads_supplied_config() -> None:
    pool_config = {"MAX_POOL_SIZE": 7}

    assert get_webdriver_pool_config({"WEBDRIVER_POOL": pool_config}) is pool_config


def test_get_webdriver_pool_config_defaults_to_empty_dict() -> None:
    assert get_webdriver_pool_config({}) == {}


def test_get_webdriver_pool_config_preserves_raw_config_value() -> None:
    assert get_webdriver_pool_config({"WEBDRIVER_POOL": None}) is None


def test_get_webdriver_baseurl_user_friendly_reads_supplied_config() -> None:
    assert (
        get_webdriver_baseurl_user_friendly(
            {"WEBDRIVER_BASEURL_USER_FRIENDLY": "https://superset.example"}
        )
        == "https://superset.example"
    )


def test_get_webdriver_baseurl_user_friendly_preserves_missing_key_error() -> None:
    with pytest.raises(KeyError):
        get_webdriver_baseurl_user_friendly({})


def test_get_mcp_service_url_config_reads_supplied_config() -> None:
    assert (
        get_mcp_service_url_config({"MCP_SERVICE_URL": "https://mcp.example"})
        == "https://mcp.example"
    )


def test_get_mcp_service_url_config_returns_none_when_unset() -> None:
    assert get_mcp_service_url_config({}) is None


def test_get_mcp_cache_config_reads_supplied_config() -> None:
    cache_config = {"enabled": True}

    assert get_mcp_cache_config({"MCP_CACHE_CONFIG": cache_config}) is cache_config


def test_get_mcp_cache_config_defaults_to_empty_dict() -> None:
    assert get_mcp_cache_config({}) == {}


def test_get_mcp_store_config_reads_supplied_config() -> None:
    store_config = {"enabled": True}

    assert get_mcp_store_config({"MCP_STORE_CONFIG": store_config}) is store_config


def test_get_mcp_store_config_defaults_to_empty_dict() -> None:
    assert get_mcp_store_config({}) == {}


def test_get_mcp_response_size_config_reads_supplied_config() -> None:
    response_size_config = {"enabled": False}

    assert (
        get_mcp_response_size_config(
            {"MCP_RESPONSE_SIZE_CONFIG": response_size_config},
            default={"enabled": True},
        )
        is response_size_config
    )


def test_get_mcp_response_size_config_uses_supplied_default() -> None:
    default = {"enabled": True}

    assert get_mcp_response_size_config({}, default=default) is default


def test_get_mcp_response_size_config_defaults_to_empty_dict() -> None:
    assert get_mcp_response_size_config({}) == {}


def test_get_mcp_response_size_config_preserves_empty_default() -> None:
    default: dict[str, Any] = {}

    assert get_mcp_response_size_config({}, default=default) is default


def test_get_mcp_rate_limit_config_reads_supplied_config() -> None:
    rate_limit_config = {"enabled": True}

    assert (
        get_mcp_rate_limit_config({"MCP_RATE_LIMIT_CONFIG": rate_limit_config})
        is rate_limit_config
    )


def test_get_mcp_rate_limit_config_uses_supplied_default() -> None:
    default = {"enabled": False}

    assert get_mcp_rate_limit_config({}, default=default) is default


def test_get_mcp_rate_limit_config_defaults_to_empty_dict() -> None:
    assert get_mcp_rate_limit_config({}) == {}


def test_get_mcp_disabled_tools_reads_supplied_config() -> None:
    disabled_tools = {"health_check"}

    assert (
        get_mcp_disabled_tools({"MCP_DISABLED_TOOLS": disabled_tools}) is disabled_tools
    )


def test_get_mcp_disabled_tools_defaults_to_empty_set() -> None:
    assert get_mcp_disabled_tools({}) == set()


def test_get_mcp_disabled_tools_preserves_raw_config_value() -> None:
    assert get_mcp_disabled_tools({"MCP_DISABLED_TOOLS": ["health_check"]}) == [
        "health_check"
    ]


def test_get_mcp_debug_enabled_reads_supplied_config() -> None:
    assert get_mcp_debug_enabled({"MCP_DEBUG": True}) is True


def test_get_mcp_debug_enabled_returns_none_when_unset() -> None:
    assert get_mcp_debug_enabled({}) is None


def test_get_mcp_hello_page_config_reads_supplied_config() -> None:
    hello_page = {"title": "AX BI MCP"}

    assert get_mcp_hello_page_config({"MCP_HELLO_PAGE": hello_page}) is hello_page


def test_get_mcp_hello_page_config_returns_none_when_unset() -> None:
    assert get_mcp_hello_page_config({}) is None


def test_get_mcp_tool_search_config_reads_supplied_config() -> None:
    tool_search_config = {"enabled": True}

    assert (
        get_mcp_tool_search_config({"MCP_TOOL_SEARCH_CONFIG": tool_search_config})
        is tool_search_config
    )


def test_get_mcp_tool_search_config_uses_supplied_default() -> None:
    default = {"enabled": True}

    assert get_mcp_tool_search_config({}, default=default) is default


def test_get_mcp_tool_search_config_preserves_empty_default() -> None:
    default: dict[str, Any] = {}

    assert get_mcp_tool_search_config({}, default=default) is default


def test_get_mcp_tool_search_config_defaults_to_empty_dict() -> None:
    assert get_mcp_tool_search_config({}) == {}


def test_get_mcp_bug_report_contact_reads_supplied_config() -> None:
    assert (
        get_mcp_bug_report_contact({"MCP_BUG_REPORT_CONTACT": "support@example.com"})
        == "support@example.com"
    )


def test_get_mcp_bug_report_contact_returns_none_when_unset() -> None:
    assert get_mcp_bug_report_contact({}) is None


def test_get_mcp_bug_report_contact_preserves_blank_value() -> None:
    assert get_mcp_bug_report_contact({"MCP_BUG_REPORT_CONTACT": "   "}) == "   "


def test_get_mcp_auth_enabled_defaults_to_false() -> None:
    assert get_mcp_auth_enabled({}) is False


def test_get_mcp_auth_enabled_preserves_raw_config_value() -> None:
    assert get_mcp_auth_enabled({"MCP_AUTH_ENABLED": "yes"}) == "yes"


def test_get_mcp_auth_factory_reads_supplied_config() -> None:
    def auth_factory(app):
        return app

    assert get_mcp_auth_factory({"MCP_AUTH_FACTORY": auth_factory}) is auth_factory


def test_get_mcp_auth_factory_returns_none_when_unset() -> None:
    assert get_mcp_auth_factory({}) is None


def test_get_mcp_api_key_enabled_flag_defaults_to_false() -> None:
    assert get_mcp_api_key_enabled_flag({}) is False


def test_get_mcp_api_key_enabled_flag_supports_custom_default() -> None:
    assert get_mcp_api_key_enabled_flag({}, default=None) is None


def test_get_mcp_api_key_enabled_flag_preserves_raw_config_value() -> None:
    assert get_mcp_api_key_enabled_flag({"MCP_API_KEY_ENABLED": "yes"}) == "yes"


def test_get_fab_api_key_enabled_defaults_to_false() -> None:
    assert get_fab_api_key_enabled({}) is False


def test_get_fab_api_key_enabled_preserves_raw_config_value() -> None:
    assert get_fab_api_key_enabled({"FAB_API_KEY_ENABLED": "yes"}) == "yes"


def test_get_fab_api_key_prefixes_reads_supplied_config() -> None:
    prefixes = ["sst_", "pat_"]

    assert get_fab_api_key_prefixes({"FAB_API_KEY_PREFIXES": prefixes}) is prefixes


def test_get_fab_api_key_prefixes_preserves_string_value() -> None:
    assert get_fab_api_key_prefixes({"FAB_API_KEY_PREFIXES": "sst_"}) == "sst_"


def test_get_fab_api_key_prefixes_defaults_to_sst_prefix() -> None:
    assert get_fab_api_key_prefixes({}) == ["sst_"]


def test_get_mcp_dev_username_reads_supplied_config() -> None:
    assert get_mcp_dev_username({"MCP_DEV_USERNAME": "admin"}) == "admin"


def test_get_mcp_dev_username_reads_environment_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MCP_DEV_USERNAME", "admin")

    assert get_mcp_dev_username({}) == "admin"


def test_get_mcp_dev_username_prefers_config_over_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MCP_DEV_USERNAME", "env_admin")

    assert get_mcp_dev_username({"MCP_DEV_USERNAME": "config_admin"}) == "config_admin"


def test_get_mcp_dev_username_returns_none_when_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("MCP_DEV_USERNAME", raising=False)

    assert get_mcp_dev_username({}) is None


def test_get_mcp_api_key_create_url_reads_supplied_config() -> None:
    assert (
        get_mcp_api_key_create_url({"MCP_API_KEY_CREATE_URL": "/profile/api-key/"})
        == "/profile/api-key/"
    )


def test_get_mcp_api_key_create_url_defaults_to_profile() -> None:
    assert get_mcp_api_key_create_url({}) == "/profile/"


@pytest.mark.parametrize(
    "key",
    ["MCP_JWKS_URI", "MCP_JWT_PUBLIC_KEY", "MCP_JWT_SECRET"],
)
def test_is_mcp_jwt_configured_accepts_any_key_source(key: str) -> None:
    assert is_mcp_jwt_configured({key: "configured"}) is True


def test_is_mcp_jwt_configured_returns_false_when_unset() -> None:
    assert is_mcp_jwt_configured({}) is False


def test_get_mcp_jwt_audience_reads_supplied_config() -> None:
    assert get_mcp_jwt_audience({"MCP_JWT_AUDIENCE": "ax-bi-mcp"}) == "ax-bi-mcp"


def test_get_mcp_jwt_audience_returns_none_when_unset() -> None:
    assert get_mcp_jwt_audience({}) is None


def test_get_mcp_jwks_uri_reads_supplied_config() -> None:
    assert get_mcp_jwks_uri({"MCP_JWKS_URI": "https://issuer/jwks"}) == (
        "https://issuer/jwks"
    )


def test_get_mcp_jwks_uri_returns_none_when_unset() -> None:
    assert get_mcp_jwks_uri({}) is None


def test_get_mcp_jwt_public_key_reads_supplied_config() -> None:
    assert get_mcp_jwt_public_key({"MCP_JWT_PUBLIC_KEY": "public"}) == "public"


def test_get_mcp_jwt_public_key_returns_none_when_unset() -> None:
    assert get_mcp_jwt_public_key({}) is None


def test_get_mcp_jwt_secret_reads_supplied_config() -> None:
    assert get_mcp_jwt_secret({"MCP_JWT_SECRET": "secret"}) == "secret"


def test_get_mcp_jwt_secret_returns_none_when_unset() -> None:
    assert get_mcp_jwt_secret({}) is None


def test_get_mcp_jwt_algorithm_reads_supplied_config() -> None:
    assert get_mcp_jwt_algorithm({"MCP_JWT_ALGORITHM": "RS256"}) == "RS256"


def test_get_mcp_jwt_algorithm_returns_none_when_unset() -> None:
    assert get_mcp_jwt_algorithm({}) is None


def test_get_mcp_jwt_algorithm_with_default_reads_supplied_config() -> None:
    assert get_mcp_jwt_algorithm_with_default({"MCP_JWT_ALGORITHM": "HS256"}) == "HS256"


def test_get_mcp_jwt_algorithm_with_default_defaults_to_rs256() -> None:
    assert get_mcp_jwt_algorithm_with_default({}) == "RS256"


def test_get_mcp_jwt_debug_errors_reads_supplied_config() -> None:
    assert get_mcp_jwt_debug_errors({"MCP_JWT_DEBUG_ERRORS": True}) is True


def test_get_mcp_jwt_debug_errors_defaults_to_false() -> None:
    assert get_mcp_jwt_debug_errors({}) is False


def test_get_mcp_jwt_issuer_reads_supplied_config() -> None:
    assert get_mcp_jwt_issuer({"MCP_JWT_ISSUER": "issuer-a"}) == "issuer-a"


def test_get_mcp_jwt_issuer_returns_none_when_unset() -> None:
    assert get_mcp_jwt_issuer({}) is None


def test_get_mcp_required_scopes_reads_supplied_config() -> None:
    scopes = ["superset:read"]

    assert get_mcp_required_scopes({"MCP_REQUIRED_SCOPES": scopes}) is scopes


def test_get_mcp_required_scopes_defaults_to_empty_list() -> None:
    assert get_mcp_required_scopes({}) == []


def test_get_mcp_user_resolver_reads_supplied_config() -> None:
    def resolver(app, token):
        return (app, token)

    assert get_mcp_user_resolver({"MCP_USER_RESOLVER": resolver}) is resolver


def test_get_mcp_user_resolver_uses_supplied_default() -> None:
    def resolver(app, token):
        return (app, token)

    assert get_mcp_user_resolver({}, default=resolver) is resolver


def test_get_mcp_user_resolver_returns_none_when_unset() -> None:
    assert get_mcp_user_resolver({}) is None


def test_get_mcp_rbac_enabled_defaults_to_true() -> None:
    assert get_mcp_rbac_enabled({}) is True


@pytest.mark.parametrize("value", [False, None, 0, ""])
def test_get_mcp_rbac_enabled_falsey_values_disable_rbac(value: object) -> None:
    assert get_mcp_rbac_enabled({"MCP_RBAC_ENABLED": value}) is False


@pytest.mark.parametrize("value", [True, 1, "false"])
def test_get_mcp_rbac_enabled_truthy_values_enable_rbac(value: object) -> None:
    assert get_mcp_rbac_enabled({"MCP_RBAC_ENABLED": value}) is True


def test_get_superset_row_limit_reads_supplied_config() -> None:
    assert get_superset_row_limit({"ROW_LIMIT": 1234}) == 1234


def test_get_superset_row_limit_preserves_missing_key_error() -> None:
    with pytest.raises(KeyError):
        get_superset_row_limit({})


def test_get_upload_max_file_size_bytes_reads_supplied_config() -> None:
    assert get_upload_max_file_size_bytes({"UPLOAD_MAX_FILE_SIZE_BYTES": 1024}) == 1024


def test_get_upload_max_file_size_bytes_returns_none_when_unset() -> None:
    assert get_upload_max_file_size_bytes({}) is None

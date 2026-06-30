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

from collections.abc import Mapping
from typing import Any

from flask import current_app


def get_superset_app_name(
    config: Mapping[str, Any] | None = None,
    default: str = "Superset",
) -> str:
    """Read Superset's configured app name behind the MCP config boundary."""
    source = config if config is not None else current_app.config
    return str(source.get("APP_NAME", default))


def get_superset_app_icon(config: Mapping[str, Any] | None = None) -> Any:
    """Read Superset's configured app icon URL/path."""
    source = config if config is not None else current_app.config
    return source.get("APP_ICON", "")


def get_superset_admin_role_name(config: Mapping[str, Any] | None = None) -> Any:
    """Read Superset's configured admin role name."""
    source = config if config is not None else current_app.config
    return source["AUTH_ROLE_ADMIN"]


def get_superset_webserver_address(config: Mapping[str, Any] | None = None) -> Any:
    """Read Superset's configured public webserver address."""
    source = config if config is not None else current_app.config
    return source.get("SUPERSET_WEBSERVER_ADDRESS", "")


def get_screenshot_selenium_headstart(
    config: Mapping[str, Any] | None = None,
) -> Any:
    """Read the screenshot Selenium head-start delay."""
    source = config if config is not None else current_app.config
    return source["SCREENSHOT_SELENIUM_HEADSTART"]


def get_screenshot_locate_wait(config: Mapping[str, Any] | None = None) -> Any:
    """Read the screenshot element-location wait timeout."""
    source = config if config is not None else current_app.config
    return source["SCREENSHOT_LOCATE_WAIT"]


def get_screenshot_load_wait(config: Mapping[str, Any] | None = None) -> Any:
    """Read the screenshot page-load wait timeout."""
    source = config if config is not None else current_app.config
    return source["SCREENSHOT_LOAD_WAIT"]


def get_screenshot_animation_wait(config: Mapping[str, Any] | None = None) -> Any:
    """Read the screenshot animation wait delay."""
    source = config if config is not None else current_app.config
    return source["SCREENSHOT_SELENIUM_ANIMATION_WAIT"]


def get_screenshot_replace_unexpected_errors(
    config: Mapping[str, Any] | None = None,
) -> Any:
    """Read whether screenshots should replace unexpected frontend errors."""
    source = config if config is not None else current_app.config
    return source.get("SCREENSHOT_REPLACE_UNEXPECTED_ERRORS")


def get_webdriver_type(config: Mapping[str, Any] | None = None) -> Any:
    """Read the configured Selenium WebDriver type."""
    source = config if config is not None else current_app.config
    return source.get("WEBDRIVER_TYPE", "firefox")


def get_webdriver_pool_config(config: Mapping[str, Any] | None = None) -> Any:
    """Read the configured WebDriver pool settings."""
    source = config if config is not None else current_app.config
    return source.get("WEBDRIVER_POOL", {})


def get_webdriver_baseurl_user_friendly(
    config: Mapping[str, Any] | None = None,
) -> Any:
    """Read the user-facing WebDriver base URL."""
    source = config if config is not None else current_app.config
    return source["WEBDRIVER_BASEURL_USER_FRIENDLY"]


def get_mcp_service_url_config(config: Mapping[str, Any] | None = None) -> Any:
    """Read the explicit MCP service URL override."""
    source = config if config is not None else current_app.config
    return source.get("MCP_SERVICE_URL")


def get_mcp_cache_config(config: Mapping[str, Any] | None = None) -> Any:
    """Read the MCP response-cache settings."""
    source = config if config is not None else current_app.config
    return source.get("MCP_CACHE_CONFIG", {})


def get_mcp_store_config(config: Mapping[str, Any] | None = None) -> Any:
    """Read the shared MCP Redis store settings."""
    source = config if config is not None else current_app.config
    return source.get("MCP_STORE_CONFIG", {})


def get_mcp_response_size_config(
    config: Mapping[str, Any] | None = None,
    default: Mapping[str, Any] | None = None,
) -> Any:
    """Read the MCP response-size guard settings."""
    source = config if config is not None else current_app.config
    return source.get("MCP_RESPONSE_SIZE_CONFIG", {} if default is None else default)


def get_mcp_rate_limit_config(
    config: Mapping[str, Any] | None = None,
    default: Mapping[str, Any] | None = None,
) -> Any:
    """Read the MCP rate-limiting settings."""
    source = config if config is not None else current_app.config
    return source.get("MCP_RATE_LIMIT_CONFIG", {} if default is None else default)


def get_mcp_disabled_tools(config: Mapping[str, Any] | None = None) -> Any:
    """Read the configured MCP tool names to suppress."""
    source = config if config is not None else current_app.config
    return source.get("MCP_DISABLED_TOOLS", set())


def get_mcp_debug_enabled(config: Mapping[str, Any] | None = None) -> Any:
    """Read whether MCP debug output is enabled."""
    source = config if config is not None else current_app.config
    return source.get("MCP_DEBUG")


def get_mcp_hello_page_config(config: Mapping[str, Any] | None = None) -> Any:
    """Read MCP browser hello-page override settings."""
    source = config if config is not None else current_app.config
    return source.get("MCP_HELLO_PAGE")


def get_mcp_tool_search_config(
    config: Mapping[str, Any] | None = None,
    default: Mapping[str, Any] | None = None,
) -> Any:
    """Read MCP tool-search settings."""
    source = config if config is not None else current_app.config
    return source.get("MCP_TOOL_SEARCH_CONFIG", {} if default is None else default)


def get_mcp_bug_report_contact(config: Mapping[str, Any] | None = None) -> Any:
    """Read the MCP bug-report support contact from Superset config."""
    source = config if config is not None else current_app.config
    return source.get("MCP_BUG_REPORT_CONTACT")


def get_mcp_auth_enabled(config: Mapping[str, Any] | None = None) -> Any:
    """Read the raw MCP auth-enabled config value."""
    source = config if config is not None else current_app.config
    return source.get("MCP_AUTH_ENABLED", False)


def get_mcp_auth_factory(config: Mapping[str, Any] | None = None) -> Any:
    """Read the optional MCP auth-provider factory."""
    source = config if config is not None else current_app.config
    return source.get("MCP_AUTH_FACTORY")


def get_mcp_api_key_enabled_flag(
    config: Mapping[str, Any] | None = None,
    default: Any = False,
) -> Any:
    """Read the raw MCP API-key auth enabled flag."""
    source = config if config is not None else current_app.config
    return source.get("MCP_API_KEY_ENABLED", default)


def get_fab_api_key_enabled(config: Mapping[str, Any] | None = None) -> Any:
    """Read the raw FAB API-key auth enabled flag."""
    source = config if config is not None else current_app.config
    return source.get("FAB_API_KEY_ENABLED", False)


def get_fab_api_key_prefixes(config: Mapping[str, Any] | None = None) -> Any:
    """Read the raw FAB API-key prefix config value."""
    source = config if config is not None else current_app.config
    return source.get("FAB_API_KEY_PREFIXES", ["sst_"])


def get_mcp_dev_username(config: Mapping[str, Any] | None = None) -> Any:
    """Read the configured MCP development username."""
    source = config if config is not None else current_app.config
    return source.get("MCP_DEV_USERNAME")


def is_mcp_jwt_configured(config: Mapping[str, Any] | None = None) -> bool:
    """Return whether any MCP JWT key source is configured."""
    source = config if config is not None else current_app.config
    return bool(
        source.get("MCP_JWKS_URI")
        or source.get("MCP_JWT_PUBLIC_KEY")
        or source.get("MCP_JWT_SECRET")
    )


def get_mcp_jwt_audience(config: Mapping[str, Any] | None = None) -> Any:
    """Read the raw MCP JWT audience config value."""
    source = config if config is not None else current_app.config
    return source.get("MCP_JWT_AUDIENCE")


def get_mcp_jwks_uri(config: Mapping[str, Any] | None = None) -> Any:
    """Read the raw MCP JWKS URI config value."""
    source = config if config is not None else current_app.config
    return source.get("MCP_JWKS_URI")


def get_mcp_jwt_public_key(config: Mapping[str, Any] | None = None) -> Any:
    """Read the raw MCP JWT public-key config value."""
    source = config if config is not None else current_app.config
    return source.get("MCP_JWT_PUBLIC_KEY")


def get_mcp_jwt_secret(config: Mapping[str, Any] | None = None) -> Any:
    """Read the raw MCP JWT shared-secret config value."""
    source = config if config is not None else current_app.config
    return source.get("MCP_JWT_SECRET")


def get_mcp_jwt_algorithm(config: Mapping[str, Any] | None = None) -> Any:
    """Read the raw MCP JWT algorithm config value."""
    source = config if config is not None else current_app.config
    return source.get("MCP_JWT_ALGORITHM")


def get_mcp_jwt_algorithm_with_default(
    config: Mapping[str, Any] | None = None,
) -> Any:
    """Read the MCP JWT algorithm with the verifier default."""
    source = config if config is not None else current_app.config
    return source.get("MCP_JWT_ALGORITHM", "RS256")


def get_mcp_jwt_debug_errors(config: Mapping[str, Any] | None = None) -> Any:
    """Read whether detailed MCP JWT server-side logging is enabled."""
    source = config if config is not None else current_app.config
    return source.get("MCP_JWT_DEBUG_ERRORS", False)


def get_mcp_jwt_issuer(config: Mapping[str, Any] | None = None) -> Any:
    """Read the raw MCP JWT issuer config value."""
    source = config if config is not None else current_app.config
    return source.get("MCP_JWT_ISSUER")


def get_mcp_required_scopes(config: Mapping[str, Any] | None = None) -> Any:
    """Read the MCP required JWT scopes."""
    source = config if config is not None else current_app.config
    return source.get("MCP_REQUIRED_SCOPES", [])


def get_mcp_user_resolver(
    config: Mapping[str, Any] | None = None,
    default: Any = None,
) -> Any:
    """Read the configured MCP JWT user resolver."""
    source = config if config is not None else current_app.config
    return source.get("MCP_USER_RESOLVER", default)


def get_mcp_api_key_create_url(config: Mapping[str, Any] | None = None) -> Any:
    """Read the URL where users can create a new API key."""
    source = config if config is not None else current_app.config
    return source.get("MCP_API_KEY_CREATE_URL", "/profile/")


def get_mcp_rbac_enabled(config: Mapping[str, Any] | None = None) -> bool:
    """Read whether MCP RBAC checks are enabled."""
    source = config if config is not None else current_app.config
    return bool(source.get("MCP_RBAC_ENABLED", True))


def get_superset_row_limit(config: Mapping[str, Any] | None = None) -> Any:
    """Read Superset's configured row limit behind the MCP config boundary."""
    source = config if config is not None else current_app.config
    return source["ROW_LIMIT"]


def get_upload_max_file_size_bytes(config: Mapping[str, Any] | None = None) -> Any:
    """Read Superset's upload file-size limit behind the MCP config boundary."""
    source = config if config is not None else current_app.config
    return source.get("UPLOAD_MAX_FILE_SIZE_BYTES")

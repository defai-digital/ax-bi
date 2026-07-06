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

"""
URL utilities for MCP service
"""

import logging
from urllib.parse import urlparse

from superset.mcp_service.utils.config_utils import (
    get_mcp_service_url_config,
    get_superset_webserver_address,
    get_webdriver_baseurl_user_friendly,
)

logger = logging.getLogger(__name__)

# Hostnames that indicate a development/local environment
LOCAL_HOSTNAMES = {"localhost", "127.0.0.1", "0.0.0.0", "::1"}  # noqa: S104


def _normalize_base_url(url: object) -> str:
    """Normalize a configured base URL, returning empty string for blank values."""
    if url is None:
        return ""
    return str(url).strip().rstrip("/")


def _browser_safe_base_url(url: str) -> str:
    """Return a URL that browser clients can open directly."""
    try:
        parsed = urlparse(url)
    except Exception:
        return url

    if parsed.hostname != "0.0.0.0":
        return url

    netloc = "127.0.0.1"
    if parsed.port:
        netloc = f"{netloc}:{parsed.port}"
    return parsed._replace(netloc=netloc).geturl().rstrip("/")


def _is_local_url(url: str) -> bool:
    """Check if a URL points to a local/development host."""
    try:
        parsed = urlparse(url)
        return parsed.hostname in LOCAL_HOSTNAMES if parsed.hostname else True
    except Exception:
        return True


def get_superset_base_url() -> str:
    """
    Get the Superset base URL from configuration.

    Returns:
        Base URL for Superset web server (e.g., "http://localhost:9001")
    """
    default_url = "http://localhost:9001"

    try:
        if webserver_url := _normalize_base_url(get_superset_webserver_address()):
            return _browser_safe_base_url(webserver_url)
        if user_friendly_url := _normalize_base_url(
            get_webdriver_baseurl_user_friendly()
        ):
            return _browser_safe_base_url(user_friendly_url)
        return default_url
    except Exception:
        return default_url


def extract_permalink_key_from_url(url: str | None) -> str | None:
    """Extract the permalink key from an explore permalink URL.

    Matches the /explore/p/<key>/ pattern produced by
    CreateExplorePermalinkCommand.  Returns the key, or None if the URL
    does not follow that pattern.
    """
    if not url:
        return None
    try:
        path = urlparse(url).path
    except ValueError:
        return None
    parts = [p for p in path.split("/") if p]
    if len(parts) >= 3 and parts[-3] == "explore" and parts[-2] == "p":
        return parts[-1]
    return None


def get_mcp_service_url() -> str:
    """
    Get the MCP service base URL where screenshot endpoints are served.

    In production, the MCP service is typically accessed via the main
    Superset URL with /mcp prefix. In development,
    it's accessed directly on port 5008.

    Returns:
        Base URL for MCP service endpoints
    """
    try:
        # Check for explicit MCP_SERVICE_URL first (allows override)
        mcp_service_url = _normalize_base_url(get_mcp_service_url_config())
        if mcp_service_url:
            return mcp_service_url

        # In production, MCP service is accessed via main URL with /mcp prefix
        # WEBDRIVER_BASEURL_USER_FRIENDLY is the user-facing URL for the instance
        if user_friendly_url := _normalize_base_url(
            get_webdriver_baseurl_user_friendly()
        ):
            if _is_local_url(user_friendly_url):
                return "http://localhost:5008"
            base_url = user_friendly_url
            return f"{base_url}/mcp"

    except Exception as e:
        logger.debug("Config access failed: %s", e)

    # Development fallback - direct access to MCP service on port 5008
    return "http://localhost:5008"

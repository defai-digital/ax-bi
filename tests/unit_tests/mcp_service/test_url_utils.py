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

from axbi.mcp_service.utils import url_utils
from axbi.mcp_service.utils.url_utils import (
    extract_permalink_key_from_url,
    get_axbi_base_url,
    get_mcp_service_url,
)


def test_extract_permalink_key_from_url_with_trailing_slash():
    url = "http://localhost:8088/explore/p/abc123/"
    assert extract_permalink_key_from_url(url) == "abc123"


def test_extract_permalink_key_from_url_without_trailing_slash():
    url = "http://localhost:8088/explore/p/abc123"
    assert extract_permalink_key_from_url(url) == "abc123"


def test_extract_permalink_key_from_url_no_match():
    url = "http://localhost:8088/explore/?form_data_key=abc123"
    assert extract_permalink_key_from_url(url) is None


def test_extract_permalink_key_from_url_none():
    assert extract_permalink_key_from_url(None) is None


def test_extract_permalink_key_from_url_empty():
    assert extract_permalink_key_from_url("") is None


def test_extract_permalink_key_from_url_malformed_url():
    assert extract_permalink_key_from_url("http://[invalid/explore/p/abc123/") is None


def test_extract_permalink_key_from_url_with_path_prefix():
    url = "https://example.com/ax-bi/explore/p/xyz789/"
    assert extract_permalink_key_from_url(url) == "xyz789"


def test_get_axbi_base_url_reads_user_friendly_url(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(url_utils, "get_axbi_webserver_address", lambda: "")
    monkeypatch.setattr(
        url_utils,
        "get_webdriver_baseurl_user_friendly",
        lambda: "https://ax-bi.example/",
    )

    assert get_axbi_base_url() == "https://ax-bi.example"


def test_get_axbi_base_url_prefers_webserver_address(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(
        url_utils,
        "get_axbi_webserver_address",
        lambda: "http://127.0.0.1:8080/",
    )
    monkeypatch.setattr(
        url_utils,
        "get_webdriver_baseurl_user_friendly",
        lambda: "http://127.0.0.1:8080/",
    )

    assert get_axbi_base_url() == "http://127.0.0.1:8080"


def test_get_axbi_base_url_strips_whitespace(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(url_utils, "get_axbi_webserver_address", lambda: "")
    monkeypatch.setattr(
        url_utils,
        "get_webdriver_baseurl_user_friendly",
        lambda: " https://ax-bi.example/ ",
    )

    assert get_axbi_base_url() == "https://ax-bi.example"


def test_get_axbi_base_url_falls_back_for_blank_config(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(url_utils, "get_axbi_webserver_address", lambda: "")
    monkeypatch.setattr(
        url_utils,
        "get_webdriver_baseurl_user_friendly",
        lambda: "   ",
    )

    assert get_axbi_base_url() == "http://localhost:9001"


def test_get_axbi_base_url_falls_back_when_config_read_fails(
    monkeypatch: pytest.MonkeyPatch,
):
    def raise_key_error():
        raise KeyError("WEBDRIVER_BASEURL_USER_FRIENDLY")

    monkeypatch.setattr(url_utils, "get_axbi_webserver_address", lambda: "")
    monkeypatch.setattr(
        url_utils,
        "get_webdriver_baseurl_user_friendly",
        raise_key_error,
    )

    assert get_axbi_base_url() == "http://localhost:9001"


def test_get_mcp_service_url_prefers_explicit_override(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(
        url_utils,
        "get_mcp_service_url_config",
        lambda: "https://mcp.example",
    )
    monkeypatch.setattr(
        url_utils,
        "get_webdriver_baseurl_user_friendly",
        lambda: "https://ax-bi.example",
    )

    assert get_mcp_service_url() == "https://mcp.example"


def test_get_mcp_service_url_normalizes_explicit_override(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(
        url_utils,
        "get_mcp_service_url_config",
        lambda: "https://mcp.example/",
    )

    assert get_mcp_service_url() == "https://mcp.example"


def test_get_mcp_service_url_strips_whitespace_from_explicit_override(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(
        url_utils,
        "get_mcp_service_url_config",
        lambda: " https://mcp.example/ ",
    )

    assert get_mcp_service_url() == "https://mcp.example"


def test_get_mcp_service_url_ignores_blank_explicit_override(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(url_utils, "get_mcp_service_url_config", lambda: "   ")
    monkeypatch.setattr(
        url_utils,
        "get_webdriver_baseurl_user_friendly",
        lambda: "https://ax-bi.example/",
    )

    assert get_mcp_service_url() == "https://ax-bi.example/mcp"


def test_get_mcp_service_url_uses_public_axbi_url_for_remote_host(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(url_utils, "get_mcp_service_url_config", lambda: None)
    monkeypatch.setattr(
        url_utils,
        "get_webdriver_baseurl_user_friendly",
        lambda: "https://ax-bi.example/",
    )

    assert get_mcp_service_url() == "https://ax-bi.example/mcp"


def test_get_mcp_service_url_falls_back_for_local_host(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(url_utils, "get_mcp_service_url_config", lambda: None)
    monkeypatch.setattr(
        url_utils,
        "get_webdriver_baseurl_user_friendly",
        lambda: "http://localhost:9001",
    )

    assert get_mcp_service_url() == "http://localhost:5008"


def test_get_mcp_service_url_falls_back_for_ipv6_loopback(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(url_utils, "get_mcp_service_url_config", lambda: None)
    monkeypatch.setattr(
        url_utils,
        "get_webdriver_baseurl_user_friendly",
        lambda: "http://[::1]:9001",
    )

    assert get_mcp_service_url() == "http://localhost:5008"


def test_get_mcp_service_url_falls_back_when_config_read_fails(
    monkeypatch: pytest.MonkeyPatch,
):
    def raise_runtime_error():
        raise RuntimeError("no flask context")

    monkeypatch.setattr(url_utils, "get_mcp_service_url_config", raise_runtime_error)

    assert get_mcp_service_url() == "http://localhost:5008"

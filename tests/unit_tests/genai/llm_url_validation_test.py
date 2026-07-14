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
"""SSRF tests for LLM base URL validation."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from axbi.genai.llm_errors import LLMSsrfBlockedError
from axbi.genai.llm_url_validation import validate_llm_base_url


def _fake_addrinfo(ip: str):
    return [(0, 0, 0, "", (ip, 0))]


def test_rejects_non_http_scheme() -> None:
    with pytest.raises(LLMSsrfBlockedError, match="scheme"):
        validate_llm_base_url("file:///etc/passwd")


def test_rejects_embedded_credentials() -> None:
    with pytest.raises(LLMSsrfBlockedError, match="credentials"):
        validate_llm_base_url("https://user:pass@api.openai.com/v1")


def test_rejects_http_when_not_allowed() -> None:
    with patch(
        "axbi.genai.llm_url_validation.socket.getaddrinfo",
        return_value=_fake_addrinfo("1.2.3.4"),
    ):
        with patch(
            "axbi.genai.llm_url_validation.is_safe_host", return_value=True
        ):
            with pytest.raises(LLMSsrfBlockedError, match="HTTP"):
                validate_llm_base_url("http://api.example.com/v1", allow_http=False)


def test_blocks_metadata_ip_even_with_private_allowed() -> None:
    with patch(
        "axbi.genai.llm_url_validation.socket.getaddrinfo",
        return_value=_fake_addrinfo("169.254.169.254"),
    ):
        with pytest.raises(LLMSsrfBlockedError, match="blocked"):
            validate_llm_base_url(
                "http://metadata.internal/v1",
                allow_http=True,
                allow_private_network=True,
            )


def test_blocks_private_without_flag() -> None:
    with patch(
        "axbi.genai.llm_url_validation.socket.getaddrinfo",
        return_value=_fake_addrinfo("10.0.0.5"),
    ):
        with patch(
            "axbi.genai.llm_url_validation.is_safe_host", return_value=False
        ):
            with pytest.raises(LLMSsrfBlockedError, match="not a public address"):
                validate_llm_base_url(
                    "http://10.0.0.5:11434/v1",
                    allow_http=True,
                    allow_private_network=False,
                )


def test_allows_private_when_flag_set() -> None:
    with patch(
        "axbi.genai.llm_url_validation.socket.getaddrinfo",
        return_value=_fake_addrinfo("10.0.0.5"),
    ):
        url = validate_llm_base_url(
            "http://10.0.0.5:11434/v1/",
            allow_http=True,
            allow_private_network=True,
        )
    assert url == "http://10.0.0.5:11434/v1"


def test_allowlist_rejects_other_hosts() -> None:
    with patch(
        "axbi.genai.llm_url_validation.socket.getaddrinfo",
        return_value=_fake_addrinfo("1.2.3.4"),
    ):
        with patch(
            "axbi.genai.llm_url_validation.is_safe_host", return_value=True
        ):
            with pytest.raises(LLMSsrfBlockedError, match="allowlist"):
                validate_llm_base_url(
                    "https://evil.example.com/v1",
                    host_allowlist=["api.openai.com"],
                )


def test_allowlist_accepts_suffix() -> None:
    with patch(
        "axbi.genai.llm_url_validation.socket.getaddrinfo",
        return_value=_fake_addrinfo("1.2.3.4"),
    ):
        with patch(
            "axbi.genai.llm_url_validation.is_safe_host", return_value=True
        ):
            url = validate_llm_base_url(
                "https://api.openai.com/v1",
                host_allowlist=["openai.com"],
            )
    assert url.endswith("/v1")

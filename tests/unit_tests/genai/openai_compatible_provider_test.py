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
"""Tests for the OpenAI-compatible LLM provider."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from pydantic import BaseModel

from axbi.genai import provider_factory
from axbi.genai.llm_errors import LLMInvalidResponseError, LLMProviderError
from axbi.genai.llm_provider import StubLLMProvider
from axbi.genai.openai_compatible_provider import OpenAICompatibleProvider


class _Result(BaseModel):
    answer: str


def _config(**overrides: object) -> dict:
    base = {
        "provider": "openai_compatible",
        "base_url": "http://10.0.0.5:11434/v1",
        "model": "llama3.1",
        "api_key": "",
        "allow_http": True,
        "allow_private_network": True,
        "timeout_seconds": 5,
        "max_retries": 0,
        "verify_tls": True,
        "url_allowlist": [],
        "extra_headers": {},
    }
    base.update(overrides)
    return base


def test_complete_json_success() -> None:
    with patch(
        "axbi.genai.openai_compatible_provider.validate_llm_base_url",
        return_value="http://10.0.0.5:11434/v1",
    ):
        provider = OpenAICompatibleProvider(_config())

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": '{"answer": "ok"}'}}]
    }

    with patch(
        "axbi.genai.openai_compatible_provider.requests.post",
        return_value=mock_response,
    ) as post:
        result = provider.complete_json(
            system_prompt="sys",
            user_prompt="user",
            response_schema=_Result,
            metadata={},
        )

    assert result.answer == "ok"
    assert post.called
    assert post.call_args.kwargs["allow_redirects"] is False
    # Authorization header must not be sent when api_key empty
    headers = post.call_args.kwargs["headers"]
    assert "Authorization" not in headers


def test_complete_json_sends_bearer_when_key_set() -> None:
    with patch(
        "axbi.genai.openai_compatible_provider.validate_llm_base_url",
        return_value="https://api.openai.com/v1",
    ):
        provider = OpenAICompatibleProvider(
            _config(
                base_url="https://api.openai.com/v1",
                api_key="sk-test",
                allow_http=False,
                allow_private_network=False,
            )
        )

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": '{"answer": "x"}'}}]
    }
    with patch(
        "axbi.genai.openai_compatible_provider.requests.post",
        return_value=mock_response,
    ) as post:
        provider.complete_json(
            system_prompt="s",
            user_prompt="u",
            response_schema=_Result,
            metadata={},
        )
    assert post.call_args.kwargs["headers"]["Authorization"] == "Bearer sk-test"


def test_invalid_json_content_raises() -> None:
    with patch(
        "axbi.genai.openai_compatible_provider.validate_llm_base_url",
        return_value="http://10.0.0.5:11434/v1",
    ):
        provider = OpenAICompatibleProvider(_config())
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "not-json"}}]
    }
    with patch(
        "axbi.genai.openai_compatible_provider.requests.post",
        return_value=mock_response,
    ):
        with pytest.raises(LLMInvalidResponseError):
            provider.complete_json(
                system_prompt="s",
                user_prompt="u",
                response_schema=_Result,
                metadata={},
            )


def test_http_error_raises_provider_error() -> None:
    with patch(
        "axbi.genai.openai_compatible_provider.validate_llm_base_url",
        return_value="http://10.0.0.5:11434/v1",
    ):
        provider = OpenAICompatibleProvider(_config())
    mock_response = MagicMock()
    mock_response.status_code = 500
    with patch(
        "axbi.genai.openai_compatible_provider.requests.post",
        return_value=mock_response,
    ):
        with pytest.raises(LLMProviderError, match="HTTP 500"):
            provider.complete_json(
                system_prompt="s",
                user_prompt="u",
                response_schema=_Result,
                metadata={},
            )


def test_factory_dispatches_openai_compatible() -> None:
    provider_factory.reset_provider()
    raw = {
        "provider": "openai_compatible",
        "base_url": "http://10.0.0.5:11434/v1",
        "model": "llama3.1",
        "allow_http": True,
        "allow_private_network": True,
    }
    with patch.object(provider_factory, "has_app_context", return_value=True):
        with patch.object(
            provider_factory, "get_raw_provider_config", return_value=raw
        ):
            with patch(
                "axbi.genai.openai_compatible_provider.validate_llm_base_url",
                return_value="http://10.0.0.5:11434/v1",
            ):
                provider = provider_factory.get_llm_provider()
    provider_factory.reset_provider()
    assert provider.provider_name() == "openai_compatible"
    assert not isinstance(provider, StubLLMProvider)


def test_factory_disabled_returns_stub() -> None:
    provider_factory.reset_provider()
    raw = {
        "provider": "openai_compatible",
        "enabled": False,
        "base_url": "http://10.0.0.5:11434/v1",
        "model": "x",
    }
    with patch.object(provider_factory, "has_app_context", return_value=True):
        with patch.object(
            provider_factory, "get_raw_provider_config", return_value=raw
        ):
            provider = provider_factory.get_llm_provider()
    provider_factory.reset_provider()
    assert isinstance(provider, StubLLMProvider)

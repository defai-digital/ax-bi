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
"""Tests for the Anthropic LLM provider and factory dispatch."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest
from pydantic import BaseModel

from axbi.genai import provider_factory
from axbi.genai.anthropic_provider import (
    AnthropicProvider,
    AnthropicProviderError,
)


class _Result(BaseModel):
    answer: str


def _provider_with_client(response: MagicMock) -> AnthropicProvider:
    provider = AnthropicProvider({"model": "claude-opus-4-8", "max_tokens": 1024})
    client = MagicMock()
    client.messages.parse.return_value = response
    provider._client = client  # noqa: SLF001 - inject a fake client
    return provider


def test_complete_json_returns_parsed_output() -> None:
    parsed = _Result(answer="ok")
    response = MagicMock(stop_reason="end_turn", parsed_output=parsed)
    provider = _provider_with_client(response)

    result = provider.complete_json(
        system_prompt="sys",
        user_prompt="user",
        response_schema=_Result,
        metadata={},
    )

    assert result is parsed
    client = provider._client  # noqa: SLF001
    assert client is not None
    _, kwargs = client.messages.parse.call_args
    assert kwargs["model"] == "claude-opus-4-8"
    assert kwargs["output_format"] is _Result
    assert kwargs["system"] == "sys"


def test_refusal_raises() -> None:
    response = MagicMock(stop_reason="refusal", parsed_output=None)
    provider = _provider_with_client(response)
    with pytest.raises(AnthropicProviderError):
        provider.complete_json(
            system_prompt="s", user_prompt="u", response_schema=_Result, metadata={}
        )


def test_missing_parsed_output_raises() -> None:
    response = MagicMock(stop_reason="end_turn", parsed_output=None)
    provider = _provider_with_client(response)
    with pytest.raises(AnthropicProviderError):
        provider.complete_json(
            system_prompt="s", user_prompt="u", response_schema=_Result, metadata={}
        )


def test_missing_sdk_raises_clear_error() -> None:
    provider = AnthropicProvider({})
    # Simulate the anthropic package not being installed.
    with patch.dict(sys.modules, {"anthropic": None}):
        with pytest.raises(AnthropicProviderError, match="anthropic"):
            provider._get_client()  # noqa: SLF001


def test_provider_identity() -> None:
    provider = AnthropicProvider({})
    assert provider.provider_name() == "anthropic"
    assert provider.model_name() == "claude-opus-4-8"  # default


def test_factory_dispatches_to_anthropic() -> None:
    provider_factory.reset_provider()
    raw = {
        "provider": "anthropic",
        "model": "claude-opus-4-8",
    }
    with patch.object(provider_factory, "has_app_context", return_value=True):
        with patch.object(
            provider_factory, "get_raw_provider_config", return_value=raw
        ):
            provider = provider_factory.get_llm_provider()
    provider_factory.reset_provider()
    assert isinstance(provider, AnthropicProvider)

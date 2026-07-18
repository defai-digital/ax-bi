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
"""Unit tests for GenAI Admin LLM helper contracts used by the API layer."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from pydantic import BaseModel

from axbi.genai.llm_config import (
    merge_provider_update,
    public_llm_capability,
    redact_provider_config,
)
from axbi.genai.llm_errors import LLMInvalidConfigError, LLMNotConfiguredError
from axbi.genai.llm_provider import StubLLMProvider
from axbi.genai.provider_factory import build_provider_from_config


class _Probe(BaseModel):
    ok: bool


def test_redacted_settings_never_include_secret() -> None:
    redacted = redact_provider_config(
        {
            "provider": "openai",
            "model": "gpt-4o-mini",
            "api_key": "sk-live-secret",
            "base_url": "https://api.openai.com/v1",
        }
    )
    assert redacted["api_key_set"] is True
    assert "api_key" not in redacted
    assert "sk-live" not in str(redacted)


def test_public_capability_hides_base_url() -> None:
    cap = public_llm_capability(
        {
            "provider": "openai_compatible",
            "base_url": "http://internal:11434/v1",
            "model": "llama3.1",
            "allow_http": True,
            "allow_private_network": True,
        }
    )
    assert cap["llm_configured"] is True
    assert "base_url" not in cap
    assert "api_key" not in cap
    assert "genai_features" in cap
    assert cap["genai_features"]["semantic_assist"] is True
    assert "bounded_samples_allowed" in cap


def test_merge_update_replaces_key_when_provided() -> None:
    existing = {"provider": "openai", "api_key": "old", "model": "a"}
    merged = merge_provider_update(
        existing, {"provider": "openai", "api_key": "new-key", "model": "b"}
    )
    assert merged["api_key"] == "new-key"
    assert merged["model"] == "b"


def test_build_provider_from_config_stub_path_raises_on_empty() -> None:
    with pytest.raises(LLMInvalidConfigError, match="not configured"):
        build_provider_from_config({})


def test_stub_provider_code() -> None:
    stub = StubLLMProvider()
    with pytest.raises(LLMNotConfiguredError) as exc:
        stub.complete_json(
            system_prompt="s",
            user_prompt="u",
            response_schema=_Probe,
            metadata={},
        )
    assert exc.value.code == "LLM_NOT_CONFIGURED"


def test_build_openai_compatible_uses_url_validation() -> None:
    with patch(
        "axbi.genai.openai_compatible_provider.validate_llm_base_url",
        return_value="http://10.0.0.5:11434/v1",
    ) as validate:
        provider = build_provider_from_config(
            {
                "provider": "openai_compatible",
                "base_url": "http://10.0.0.5:11434/v1",
                "model": "llama3.1",
                "allow_http": True,
                "allow_private_network": True,
            }
        )
    assert provider.provider_name() == "openai_compatible"
    assert validate.called
    assert not isinstance(provider, StubLLMProvider)


def test_build_rejects_ssrf() -> None:
    with patch(
        "axbi.genai.openai_compatible_provider.validate_llm_base_url",
        side_effect=Exception("blocked"),
    ):
        with pytest.raises(Exception, match="blocked"):
            build_provider_from_config(
                {
                    "provider": "openai_compatible",
                    "base_url": "http://169.254.169.254/",
                    "model": "x",
                    "allow_http": True,
                    "allow_private_network": True,
                }
            )

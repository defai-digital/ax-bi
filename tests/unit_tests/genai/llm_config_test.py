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
"""Tests for Admin/operator LLM config normalization and redaction."""

from __future__ import annotations

import pytest

from axbi.genai.llm_config import (
    build_provider_config_from_env,
    is_llm_configured,
    merge_provider_update,
    normalize_provider_config,
    public_llm_capability,
    redact_provider_config,
    validate_normalized_config,
)
from axbi.genai.llm_errors import LLMInvalidConfigError


def test_build_from_env_empty() -> None:
    assert build_provider_config_from_env({}) == {}


def test_build_from_env_openai_compatible() -> None:
    cfg = build_provider_config_from_env(
        {
            "GENAI_LLM_PROVIDER": "openai_compatible",
            "GENAI_LLM_BASE_URL": "http://ollama:11434/v1",
            "GENAI_LLM_MODEL": "llama3.1",
            "GENAI_LLM_ALLOW_HTTP": "true",
            "GENAI_LLM_ALLOW_PRIVATE_NETWORK": "1",
            "GENAI_LLM_API_KEY": "",
        }
    )
    assert cfg["provider"] == "openai_compatible"
    assert cfg["base_url"] == "http://ollama:11434/v1"
    assert cfg["allow_http"] is True or cfg["allow_http"] == "true"
    assert cfg["model"] == "llama3.1"


def test_normalize_disabled() -> None:
    assert normalize_provider_config({"provider": "anthropic", "enabled": False}) == {}


def test_normalize_openai_default_base() -> None:
    cfg = normalize_provider_config(
        {"provider": "openai", "model": "gpt-4o-mini", "api_key": "sk-test"}
    )
    assert cfg["base_url"] == "https://api.openai.com/v1"
    validate_normalized_config(cfg)


def test_validate_requires_base_for_compatible() -> None:
    cfg = normalize_provider_config(
        {"provider": "openai_compatible", "model": "x", "api_key": ""}
    )
    with pytest.raises(LLMInvalidConfigError, match="base_url"):
        validate_normalized_config(cfg)


def test_redact_never_includes_api_key() -> None:
    redacted = redact_provider_config(
        {
            "provider": "anthropic",
            "model": "claude-sonnet-4-20250514",
            "api_key": "super-secret",
        }
    )
    assert "api_key" not in redacted
    assert redacted["api_key_set"] is True
    assert redacted["configured"] is True


def test_public_capability_omits_base_url() -> None:
    cap = public_llm_capability(
        {
            "provider": "openai_compatible",
            "base_url": "http://secret-host:11434/v1",
            "model": "llama3.1",
            "allow_http": True,
            "allow_private_network": True,
        }
    )
    assert cap["llm_configured"] is True
    assert cap["llm_provider_type"] == "openai_compatible"
    assert "base_url" not in cap
    assert "api_key" not in cap
    assert "genai_features" in cap
    # Feature flags default off in unit tests unless overridden.
    assert isinstance(cap["genai_features"]["plan_dashboard"], bool)


def test_merge_keeps_api_key_when_omitted() -> None:
    existing = {"provider": "openai", "api_key": "keep-me", "model": "gpt-4o-mini"}
    merged = merge_provider_update(
        existing, {"provider": "openai", "model": "gpt-4o", "api_key": ""}
    )
    assert merged["api_key"] == "keep-me"
    assert merged["model"] == "gpt-4o"


def test_is_llm_configured_false_for_empty() -> None:
    assert is_llm_configured({}) is False

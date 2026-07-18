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
"""Durable Admin LLM settings store tests."""

from __future__ import annotations

from unittest.mock import patch

from axbi.genai.settings_store import (
    config_fingerprint,
    load_durable_provider_config,
    save_durable_provider_config,
)


def test_config_fingerprint_stable_and_secret_sensitive() -> None:
    a = {"enabled": True, "provider": "openai", "model": "m", "api_key": "sk-1"}
    b = {"enabled": True, "provider": "openai", "model": "m", "api_key": "sk-1"}
    c = {"enabled": True, "provider": "openai", "model": "m", "api_key": "sk-2"}
    assert config_fingerprint(a) == config_fingerprint(b)
    assert config_fingerprint(a) != config_fingerprint(c)
    assert config_fingerprint({}) == "empty"
    assert config_fingerprint(None) == "empty"


def test_save_encrypts_api_key_and_load_decrypts(app_context: None) -> None:
    stored: dict = {}

    def fake_get(_key):  # noqa: ANN001
        return dict(stored) if stored else None

    def fake_upsert(_key, value):  # noqa: ANN001
        stored.clear()
        stored.update(value)

    with (
        patch(
            "axbi.genai.settings_store.get_shared_value",
            side_effect=fake_get,
        ),
        patch(
            "axbi.genai.settings_store.upsert_shared_value",
            side_effect=fake_upsert,
        ),
    ):
        save_durable_provider_config(
            {
                "enabled": True,
                "provider": "openai_compatible",
                "base_url": "http://10.0.0.5:11434/v1",
                "model": "llama3.1",
                "api_key": "super-secret-token",
                "timeout_seconds": 45,
                "allow_http": True,
                "allow_private_network": True,
            }
        )
        assert "api_key" not in stored
        assert "api_key_encrypted" in stored
        assert stored["api_key_encrypted"] != "super-secret-token"
        assert stored["model"] == "llama3.1"

        loaded = load_durable_provider_config()
        assert loaded is not None
        assert loaded["api_key"] == "super-secret-token"
        assert loaded["timeout_seconds"] == 45
        assert loaded["enabled"] is True


def test_save_preserves_encrypted_key_when_blank(app_context: None) -> None:
    stored: dict = {}

    def fake_get(_key):  # noqa: ANN001
        return dict(stored) if stored else None

    def fake_upsert(_key, value):  # noqa: ANN001
        stored.clear()
        stored.update(value)

    with (
        patch(
            "axbi.genai.settings_store.get_shared_value",
            side_effect=fake_get,
        ),
        patch(
            "axbi.genai.settings_store.upsert_shared_value",
            side_effect=fake_upsert,
        ),
    ):
        save_durable_provider_config(
            {
                "enabled": True,
                "provider": "anthropic",
                "model": "claude",
                "api_key": "keep-me",
            }
        )
        encrypted = stored["api_key_encrypted"]

        save_durable_provider_config(
            {
                "enabled": False,
                "provider": "anthropic",
                "model": "claude",
                "api_key": "",
            }
        )
        assert stored["api_key_encrypted"] == encrypted
        assert stored["enabled"] is False


def test_load_returns_none_when_missing(app_context: None) -> None:
    with patch(
        "axbi.genai.settings_store.get_shared_value",
        return_value=None,
    ):
        assert load_durable_provider_config() is None


def test_get_raw_prefers_durable_over_app_config(app_context: None) -> None:
    from flask import current_app

    from axbi.genai.llm_config import get_raw_provider_config

    current_app.config["GENAI_LLM_PROVIDER_CONFIG"] = {
        "provider": "openai",
        "model": "from-env",
        "api_key": "env-key",
        "enabled": True,
    }
    with patch(
        "axbi.genai.settings_store.load_durable_provider_config",
        return_value={
            "provider": "anthropic",
            "model": "from-db",
            "api_key": "db-key",
            "enabled": True,
        },
    ):
        raw = get_raw_provider_config()
    assert raw["model"] == "from-db"
    assert raw["provider"] == "anthropic"


def test_get_raw_falls_back_to_app_config(app_context: None) -> None:
    from flask import current_app

    from axbi.genai.llm_config import get_raw_provider_config

    current_app.config["GENAI_LLM_PROVIDER_CONFIG"] = {
        "provider": "openai",
        "model": "from-env",
        "api_key": "env-key",
        "enabled": True,
    }
    with patch(
        "axbi.genai.settings_store.load_durable_provider_config",
        return_value=None,
    ):
        raw = get_raw_provider_config()
    assert raw["model"] == "from-env"


def test_redact_keeps_timeout_when_disabled() -> None:
    from axbi.genai.llm_config import redact_provider_config

    redacted = redact_provider_config(
        {
            "enabled": False,
            "provider": "openai_compatible",
            "base_url": "http://x",
            "model": "m",
            "api_key": "secret",
            "timeout_seconds": 120,
            "allow_http": True,
        }
    )
    assert redacted["enabled"] is False
    assert redacted["configured"] is False
    assert redacted["timeout_seconds"] == 120
    assert redacted["api_key_set"] is True
    assert "api_key" not in redacted


def test_provider_cache_invalidates_on_fingerprint_change(app_context: None) -> None:
    from axbi.genai import provider_factory
    from axbi.genai.llm_provider import StubLLMProvider

    provider_factory.reset_provider()
    with patch(
        "axbi.genai.provider_factory.get_raw_provider_config",
        return_value={},
    ):
        first = provider_factory.get_llm_provider()
        assert isinstance(first, StubLLMProvider)
        # Same fingerprint returns same instance
        again = provider_factory.get_llm_provider()
        assert again is first

    with patch(
        "axbi.genai.provider_factory.get_raw_provider_config",
        return_value={
            "enabled": False,
            "provider": "openai",
            "model": "x",
        },
    ):
        # Fingerprint changed → rebuild (still stub when disabled)
        rebuilt = provider_factory.get_llm_provider()
        assert isinstance(rebuilt, StubLLMProvider)
        assert rebuilt is not first

    provider_factory.reset_provider()


def test_merge_ignores_null_provider_on_disable() -> None:
    from axbi.genai.llm_config import merge_provider_update

    existing = {
        "enabled": True,
        "provider": "openai_compatible",
        "model": "llama3.1",
        "api_key": "k",
    }
    merged = merge_provider_update(
        existing, {"enabled": False, "provider": None, "model": None}
    )
    assert merged["enabled"] is False
    assert merged["provider"] == "openai_compatible"
    assert merged["model"] == "llama3.1"
    assert merged["api_key"] == "k"

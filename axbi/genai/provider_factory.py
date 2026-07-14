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
"""Factory for obtaining the Admin/operator-configured LLM provider.

Reads ``GENAI_LLM_PROVIDER_CONFIG`` from the AxBI configuration and returns
the appropriate ``LLMProvider`` instance. Falls back to ``StubLLMProvider``
when no provider is configured. Only deployment/Admin configuration is used;
request payloads must never supply inference URLs or tokens.
"""

from __future__ import annotations

import logging
import threading
from typing import Any

from flask import current_app, has_app_context

from axbi.genai.llm_config import (
    normalize_provider_config,
    validate_normalized_config,
)
from axbi.genai.llm_errors import LLMInvalidConfigError, LLMSsrfBlockedError
from axbi.genai.llm_provider import LLMProvider, StubLLMProvider

logger = logging.getLogger(__name__)

# Module-level singleton to avoid re-creating the provider on every call.
_provider_instance: LLMProvider | None = None
_provider_lock = threading.Lock()


def _load_raw_config() -> dict[str, Any]:
    if not has_app_context():
        return {}
    try:
        raw = current_app.config.get("GENAI_LLM_PROVIDER_CONFIG", {})
    except RuntimeError:
        return {}
    if not isinstance(raw, dict):
        return {}
    return dict(raw)


def _build_provider(raw: dict[str, Any]) -> LLMProvider:
    try:
        config = normalize_provider_config(raw)
        if not config:
            return StubLLMProvider()
        validate_normalized_config(config)
    except LLMInvalidConfigError as ex:
        logger.warning("Invalid GENAI_LLM_PROVIDER_CONFIG: %s", ex)
        return StubLLMProvider()

    provider_name = config["provider"]

    if provider_name == "anthropic":
        from axbi.genai.anthropic_provider import AnthropicProvider

        # Anthropic provider historically used ``timeout`` not timeout_seconds.
        anthropic_config = {
            **config,
            "timeout": config.get("timeout_seconds"),
        }
        return AnthropicProvider(anthropic_config)

    if provider_name in {"openai", "openai_compatible"}:
        from axbi.genai.openai_compatible_provider import (
            OpenAICompatibleProvider,
        )

        try:
            return OpenAICompatibleProvider(config)
        except LLMSsrfBlockedError as ex:
            logger.error("LLM base URL blocked by egress policy: %s", ex)
            return StubLLMProvider()
        except LLMInvalidConfigError as ex:
            logger.warning("OpenAI-compatible provider config invalid: %s", ex)
            return StubLLMProvider()

    logger.warning(
        "Unknown LLM provider '%s'; returning StubLLMProvider. "
        "Supported: anthropic, openai, openai_compatible.",
        provider_name,
    )
    return StubLLMProvider()


def get_llm_provider() -> LLMProvider:
    """Return the configured LLM provider (cached singleton).

    If the config is empty, disabled, or invalid, returns ``StubLLMProvider``.
    Call ``reset_provider()`` after Admin updates so the next call rebuilds.
    """
    global _provider_instance  # noqa: PLW0603
    if _provider_instance is not None:
        return _provider_instance

    with _provider_lock:
        if _provider_instance is not None:
            return _provider_instance

        raw = _load_raw_config()
        if not raw:
            logger.debug("No GENAI_LLM_PROVIDER_CONFIG; using StubLLMProvider")
            _provider_instance = StubLLMProvider()
            return _provider_instance

        _provider_instance = _build_provider(raw)
        return _provider_instance


def reset_provider() -> None:
    """Reset the cached provider instance.

    Useful for testing or when Admin/operator configuration changes at runtime.
    """
    global _provider_instance  # noqa: PLW0603
    with _provider_lock:
        _provider_instance = None


def build_provider_from_config(raw: dict[str, Any]) -> LLMProvider:
    """Build a provider from an explicit config (e.g. Admin connection test).

    Does not replace the process-wide singleton. Raises config/SSRF errors
    instead of swallowing them into a stub.
    """
    config = normalize_provider_config(raw)
    validate_normalized_config(config)
    provider_name = config["provider"]
    if provider_name == "anthropic":
        from axbi.genai.anthropic_provider import AnthropicProvider

        return AnthropicProvider({**config, "timeout": config.get("timeout_seconds")})
    if provider_name in {"openai", "openai_compatible"}:
        from axbi.genai.openai_compatible_provider import (
            OpenAICompatibleProvider,
        )

        return OpenAICompatibleProvider(config)
    raise LLMInvalidConfigError(f"Unsupported LLM provider {provider_name!r}")

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
"""Factory for obtaining the configured LLM provider.

Reads ``GENAI_LLM_PROVIDER_CONFIG`` from the Superset configuration
and returns the appropriate ``LLMProvider`` instance. Falls back to
``StubLLMProvider`` when no provider is configured.
"""

from __future__ import annotations

import logging
from typing import Any

from flask import current_app

from superset.mcp_service.ai.llm_provider import LLMProvider, StubLLMProvider

logger = logging.getLogger(__name__)

# Module-level singleton to avoid re-creating the provider on every call.
_provider_instance: LLMProvider | None = None


def get_llm_provider() -> LLMProvider:
    """Return the configured LLM provider.

    Reads ``GENAI_LLM_PROVIDER_CONFIG`` from the Flask app config.
    If the config is empty or the provider is unrecognized, returns
    a ``StubLLMProvider`` that raises ``NotImplementedError`` on use.

    The provider instance is cached as a module-level singleton.
    Call ``reset_provider()`` to force re-creation (useful in tests).
    """
    global _provider_instance  # noqa: PLW0603
    if _provider_instance is not None:
        return _provider_instance

    config: dict[str, Any] = {}
    try:
        config = current_app.config.get("GENAI_LLM_PROVIDER_CONFIG", {})
    except RuntimeError:
        # Outside app context — fall back to stub
        logger.debug("No Flask app context; returning StubLLMProvider")

    if not config:
        _provider_instance = StubLLMProvider()
        return _provider_instance

    provider_name = config.get("provider", "").lower()

    if provider_name == "anthropic":
        from superset.mcp_service.ai.anthropic_provider import AnthropicProvider

        _provider_instance = AnthropicProvider(config)
        return _provider_instance

    logger.warning(
        "Unknown LLM provider '%s'; returning StubLLMProvider. "
        "Supported providers will be added in future iterations.",
        provider_name,
    )
    _provider_instance = StubLLMProvider()
    return _provider_instance


def reset_provider() -> None:
    """Reset the cached provider instance.

    Useful for testing or when the configuration changes at runtime.
    """
    global _provider_instance  # noqa: PLW0603
    _provider_instance = None

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
"""Anthropic (Claude) implementation of the GenAI BI LLM provider.

Uses the official ``anthropic`` SDK and structured outputs
(``client.messages.parse``) so the model is constrained to the caller's
Pydantic response schema. Enable it via ``GENAI_LLM_PROVIDER_CONFIG``::

    GENAI_LLM_PROVIDER_CONFIG = {
        "provider": "anthropic",
        "model": "claude-opus-4-8",   # default
        "max_tokens": 4096,
        # "api_key": "...",           # optional; the SDK also reads the env
    }
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from axbi.mcp_service.ai.llm_provider import LLMProvider

DEFAULT_MODEL = "claude-opus-4-8"


class AnthropicProviderError(RuntimeError):
    """Raised when the Anthropic provider cannot produce a structured result."""


class AnthropicProvider(LLMProvider):
    """LLM provider backed by Anthropic's Claude models."""

    def __init__(self, config: dict[str, Any]) -> None:
        self._model = config.get("model") or DEFAULT_MODEL
        self._max_tokens = int(config.get("max_tokens", 4096))
        self._api_key = config.get("api_key")
        self._timeout = config.get("timeout")
        self._client: Any | None = None

    def _get_client(self) -> Any:
        """Lazily construct the Anthropic client so the SDK stays optional."""

        if self._client is None:
            try:
                import anthropic
            except ImportError as ex:  # pragma: no cover - import guard
                raise AnthropicProviderError(
                    "The 'anthropic' package is required for the Anthropic LLM "
                    "provider. Install it with 'pip install anthropic'."
                ) from ex

            client_kwargs: dict[str, Any] = {}
            if self._api_key:
                client_kwargs["api_key"] = self._api_key
            if self._timeout is not None:
                client_kwargs["timeout"] = self._timeout
            # A bare Anthropic() resolves credentials from the environment or an
            # `ant auth login` profile when no explicit api_key is supplied.
            self._client = anthropic.Anthropic(**client_kwargs)
        return self._client

    def complete_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_schema: type[BaseModel],
        metadata: dict[str, Any],
    ) -> Any:
        """Return a validated ``response_schema`` instance from Claude."""

        client = self._get_client()
        response = client.messages.parse(
            model=self._model,
            max_tokens=self._max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
            output_format=response_schema,
        )

        if getattr(response, "stop_reason", None) == "refusal":
            raise AnthropicProviderError(
                "Anthropic model declined the request (stop_reason=refusal)."
            )

        parsed = getattr(response, "parsed_output", None)
        if parsed is None:
            raise AnthropicProviderError(
                "Anthropic response did not contain a parsed structured object."
            )
        return parsed

    def provider_name(self) -> str:
        return "anthropic"

    def model_name(self) -> str:
        return self._model

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
"""OpenAI-compatible HTTP LLM provider (Ollama, LM Studio, vLLM, OpenAI API)."""

from __future__ import annotations

import logging
from typing import Any

import requests
from pydantic import BaseModel, ValidationError

from axbi.genai.llm_errors import (
    LLMInvalidResponseError,
    LLMProviderError,
    LLMTimeoutError,
)
from axbi.genai.llm_provider import LLMProvider
from axbi.genai.llm_url_validation import validate_llm_base_url
from axbi.utils import json

logger = logging.getLogger(__name__)


class OpenAICompatibleProvider(LLMProvider):
    """Chat Completions client that returns validated Pydantic models."""

    def __init__(self, config: dict[str, Any]) -> None:
        self._provider_label = str(config.get("provider") or "openai_compatible")
        self._model = str(config.get("model") or "")
        self._api_key = str(config.get("api_key") or "")
        self._timeout = float(
            config.get("timeout_seconds") or config.get("timeout") or 60
        )
        self._max_retries = int(config.get("max_retries") or 0)
        self._verify_tls = bool(config.get("verify_tls", True))
        self._extra_headers = dict(config.get("extra_headers") or {})
        allow_http = bool(config.get("allow_http", False))
        allow_private = bool(config.get("allow_private_network", False))
        allowlist = list(config.get("url_allowlist") or [])
        base_url = config.get("base_url") or ""
        self._base_url = validate_llm_base_url(
            str(base_url),
            allow_http=allow_http,
            allow_private_network=allow_private,
            host_allowlist=allowlist,
        )

    def complete_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_schema: type[BaseModel],
        metadata: dict[str, Any],
    ) -> Any:
        """Call chat/completions and validate the JSON body as ``response_schema``."""
        schema_json = json.dumps(response_schema.model_json_schema())
        system = (
            f"{system_prompt}\n\n"
            "You must respond with a single JSON object only (no markdown) "
            "that validates against this JSON Schema:\n"
            f"{schema_json}"
        )
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user_prompt},
        ]
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "temperature": 0,
        }
        # Prefer JSON mode when the gateway supports it; fall back without it.
        payload_with_format = {
            **payload,
            "response_format": {"type": "json_object"},
        }

        last_error: Exception | None = None
        attempts = max(1, self._max_retries + 1)
        for attempt in range(attempts):
            try:
                content = self._post_chat(payload_with_format)
                return self._parse_content(content, response_schema)
            except LLMInvalidResponseError:
                raise
            except LLMProviderError as ex:
                # Retry without response_format once if the gateway rejects it.
                if "response_format" in payload_with_format and attempt == 0:
                    try:
                        content = self._post_chat(payload)
                        return self._parse_content(content, response_schema)
                    except Exception as inner:  # noqa: BLE001 - map below
                        last_error = inner
                else:
                    last_error = ex
            except Exception as ex:  # noqa: BLE001 - normalize to LLM errors
                last_error = ex
        assert last_error is not None
        if isinstance(
            last_error, (LLMProviderError, LLMTimeoutError, LLMInvalidResponseError)
        ):
            raise last_error
        raise LLMProviderError(str(last_error)) from last_error

    def _headers(self) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            **{str(k): str(v) for k, v in self._extra_headers.items()},
        }
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        return headers

    def _post_chat(self, payload: dict[str, Any]) -> str:
        url = f"{self._base_url}/chat/completions"
        try:
            response = requests.post(
                url,
                headers=self._headers(),
                json=payload,
                timeout=self._timeout,
                verify=self._verify_tls,
                allow_redirects=False,
            )
        except requests.Timeout as ex:
            raise LLMTimeoutError(
                f"LLM request timed out after {self._timeout}s"
            ) from ex
        except requests.RequestException as ex:
            # Never include headers (Authorization) in the message.
            raise LLMProviderError(
                f"LLM request failed: {ex.__class__.__name__}"
            ) from ex

        if response.status_code >= 400:
            # Avoid echoing body that might contain prompt echoes with secrets.
            raise LLMProviderError(f"LLM provider returned HTTP {response.status_code}")

        try:
            data = response.json()
        except ValueError as ex:
            raise LLMInvalidResponseError(
                "LLM provider returned non-JSON response"
            ) from ex

        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as ex:
            raise LLMInvalidResponseError(
                "LLM provider response missing choices[0].message.content"
            ) from ex

        if not isinstance(content, str) or not content.strip():
            raise LLMInvalidResponseError("LLM provider returned empty content")
        return content

    @staticmethod
    def _parse_content(content: str, response_schema: type[BaseModel]) -> Any:
        text = content.strip()
        # Strip common markdown fences from local models.
        if text.startswith("```"):
            lines = text.split("\n")
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines).strip()
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as ex:
            raise LLMInvalidResponseError(
                "LLM provider content is not valid JSON"
            ) from ex
        try:
            return response_schema.model_validate(payload)
        except ValidationError as ex:
            raise LLMInvalidResponseError(
                "LLM provider JSON failed schema validation"
            ) from ex

    def provider_name(self) -> str:
        return self._provider_label

    def model_name(self) -> str:
        return self._model

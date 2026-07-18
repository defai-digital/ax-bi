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
"""Abstract LLM provider interface for GenAI BI.

The provider abstraction allows the GenAI BI pipeline to work with
different LLM backends (OpenAI, Anthropic, local models, etc.)
without hard-coding any specific SDK.
"""

from __future__ import annotations

import abc
from typing import Any

from pydantic import BaseModel


class LLMProvider(abc.ABC):
    """Abstract base class for LLM providers.

    Implementations must support structured JSON output via Pydantic
    schemas, timeout/retry controls, and redaction hooks.
    """

    @abc.abstractmethod
    def complete_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_schema: type[BaseModel],
        metadata: dict[str, Any],
    ) -> Any:
        """Send a prompt to the LLM and return a structured JSON response.

        :param system_prompt: System-level instruction for the LLM.
        :param user_prompt: User-level prompt content.
        :param response_schema: Pydantic model class for response validation.
        :param metadata: Arbitrary metadata for tracing/logging.
        :returns: An instance of ``response_schema``.
        """

    @abc.abstractmethod
    def provider_name(self) -> str:
        """Return the name of the LLM provider (e.g. 'openai', 'anthropic')."""

    @abc.abstractmethod
    def model_name(self) -> str:
        """Return the model identifier (e.g. 'gpt-4', 'claude-3-sonnet')."""


class StubLLMProvider(LLMProvider):
    """Stub provider used when no Admin/operator LLM is configured.

    Raises :class:`LLMNotConfiguredError` (also a ``NotImplementedError``)
    so existing ``except NotImplementedError`` handlers keep working while
    callers can branch on ``error.code == "LLM_NOT_CONFIGURED"``.
    """

    def complete_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_schema: type[BaseModel],
        metadata: dict[str, Any],
    ) -> Any:
        from axbi.genai.llm_errors import LLMNotConfiguredError

        raise LLMNotConfiguredError()

    def provider_name(self) -> str:
        return "stub"

    def model_name(self) -> str:
        return "none"

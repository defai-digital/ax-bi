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
"""Stable error codes and exceptions for the GenAI LLM provider layer."""

from __future__ import annotations

LLM_NOT_CONFIGURED = "LLM_NOT_CONFIGURED"
LLM_PROVIDER_ERROR = "LLM_PROVIDER_ERROR"
LLM_TIMEOUT = "LLM_TIMEOUT"
LLM_INVALID_RESPONSE = "LLM_INVALID_RESPONSE"
LLM_SSRF_BLOCKED = "LLM_SSRF_BLOCKED"
LLM_FORBIDDEN_CONFIG = "LLM_FORBIDDEN_CONFIG"
LLM_INVALID_CONFIG = "LLM_INVALID_CONFIG"


class LLMError(RuntimeError):
    """Base error for LLM provider failures with a stable machine code."""

    code: str = LLM_PROVIDER_ERROR
    retryable: bool = False

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message)
        if code is not None:
            self.code = code


class LLMNotConfiguredError(LLMError, NotImplementedError):
    """Raised when no Admin/operator LLM provider is configured."""

    code = LLM_NOT_CONFIGURED
    retryable = False

    def __init__(
        self,
        message: str | None = None,
    ) -> None:
        super().__init__(
            message
            or (
                "No LLM provider configured. An administrator must set "
                "GENAI_LLM_PROVIDER_CONFIG (or Admin GenAI LLM settings). "
                "Core AX BI works without an LLM."
            ),
            code=LLM_NOT_CONFIGURED,
        )


class LLMProviderError(LLMError):
    """Upstream provider or network failure."""

    code = LLM_PROVIDER_ERROR
    retryable = True


class LLMTimeoutError(LLMError):
    """Provider call exceeded the configured timeout."""

    code = LLM_TIMEOUT
    retryable = True


class LLMInvalidResponseError(LLMError):
    """Provider response could not be validated against the schema."""

    code = LLM_INVALID_RESPONSE
    retryable = False


class LLMSsrfBlockedError(LLMError):
    """Configured base URL failed SSRF / egress policy checks."""

    code = LLM_SSRF_BLOCKED
    retryable = False


class LLMInvalidConfigError(LLMError):
    """Provider configuration is incomplete or invalid."""

    code = LLM_INVALID_CONFIG
    retryable = False

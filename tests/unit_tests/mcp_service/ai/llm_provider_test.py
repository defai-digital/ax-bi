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
"""Unit tests for the GenAI BI LLM provider abstraction."""

from __future__ import annotations

import pytest
from pydantic import BaseModel

from axbi.mcp_service.ai.llm_provider import LLMProvider, StubLLMProvider
from axbi.mcp_service.ai.provider_factory import (
    get_llm_provider,
    reset_provider,
)


class DummyResponse(BaseModel):
    """Minimal schema for testing complete_json."""

    answer: str


def test_stub_provider_name() -> None:
    stub = StubLLMProvider()
    assert stub.provider_name() == "stub"


def test_stub_provider_model_name() -> None:
    stub = StubLLMProvider()
    assert stub.model_name() == "none"


def test_stub_provider_raises_on_complete_json() -> None:
    stub = StubLLMProvider()
    with pytest.raises(NotImplementedError, match="No LLM provider configured"):
        stub.complete_json(
            system_prompt="test",
            user_prompt="test",
            response_schema=DummyResponse,
            metadata={},
        )


def test_llm_provider_is_abstract() -> None:
    """LLMProvider cannot be instantiated directly."""
    with pytest.raises(TypeError):
        LLMProvider()  # type: ignore[abstract]


def test_get_llm_provider_returns_stub_without_config() -> None:
    """Outside an app context, factory returns StubLLMProvider."""
    reset_provider()
    provider = get_llm_provider()
    assert isinstance(provider, StubLLMProvider)
    reset_provider()


def test_reset_provider_clears_singleton() -> None:
    reset_provider()
    p1 = get_llm_provider()
    reset_provider()
    p2 = get_llm_provider()
    # After reset, a new instance is created
    assert p1 is not p2
    reset_provider()

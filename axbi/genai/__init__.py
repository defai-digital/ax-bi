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
"""GenAI product surface: Admin LLM configuration, providers, and APIs.

This package is transport-neutral. MCP tools import providers via
``axbi.mcp_service.ai`` re-exports; REST and authoring commands import from
``axbi.genai`` directly so the command layer never depends on MCP.
"""

from axbi.genai.llm_config import (
    build_provider_config_from_env,
    is_llm_configured,
    public_llm_capability,
    redact_provider_config,
)
from axbi.genai.llm_provider import LLMProvider, StubLLMProvider
from axbi.genai.provider_factory import (
    build_provider_from_config,
    get_llm_provider,
    reset_provider,
)

__all__ = [
    "LLMProvider",
    "StubLLMProvider",
    "build_provider_config_from_env",
    "build_provider_from_config",
    "get_llm_provider",
    "is_llm_configured",
    "public_llm_capability",
    "redact_provider_config",
    "reset_provider",
]

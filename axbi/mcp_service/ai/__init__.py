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
"""GenAI BI AI package for MCP service.

Provides LLM provider abstraction, Pydantic schemas for tool contracts,
and supporting utilities for the GenAI BI pipeline.
"""

from axbi.mcp_service.ai.llm_provider import LLMProvider, StubLLMProvider
from axbi.mcp_service.ai.provider_factory import get_llm_provider

__all__ = [
    "LLMProvider",
    "StubLLMProvider",
    "get_llm_provider",
]

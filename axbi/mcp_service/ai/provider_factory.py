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
"""Backward-compatible re-export of the Admin LLM provider factory.

Implementation lives in ``axbi.genai.provider_factory`` so commands and REST
do not depend on the MCP package.
"""

from axbi.genai.provider_factory import (
    build_provider_from_config,
    get_llm_provider,
    reset_provider,
)

__all__ = [
    "build_provider_from_config",
    "get_llm_provider",
    "reset_provider",
]

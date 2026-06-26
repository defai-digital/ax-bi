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

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from superset.extensions import event_logger


def mcp_event_log(**kwargs: Any) -> None:
    """Write an MCP event through the Superset event logger boundary."""
    event_logger.log(**kwargs)


@contextmanager
def mcp_event_log_context(action: str) -> Iterator[None]:
    """Wrap Superset event logging behind an MCP utility boundary."""
    with event_logger.log_context(action=action):
        yield


@contextmanager
def mcp_list_serialization_log_context(resource_name: str) -> Iterator[None]:
    """Build the standard MCP list serialization logging context."""
    action_name = resource_name.lower().replace(" ", "_")
    with mcp_event_log_context(action=f"mcp.list_{action_name}.serialization"):
        yield

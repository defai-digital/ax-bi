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

from axbi.mcp_service.utils import logging_utils


class FakeEventLogger:
    def __init__(self) -> None:
        self.actions: list[tuple[str, str]] = []
        self.events: list[dict[str, object]] = []

    def log(self, **kwargs: object) -> None:
        self.events.append(kwargs)

    @contextmanager
    def log_context(self, *, action: str) -> Iterator[None]:
        self.actions.append(("enter", action))
        yield
        self.actions.append(("exit", action))


def test_mcp_event_log_context_delegates_to_axbi_event_logger(monkeypatch):
    fake_event_logger = FakeEventLogger()
    monkeypatch.setattr(logging_utils, "event_logger", fake_event_logger)

    with logging_utils.mcp_event_log_context("mcp.test.action"):
        fake_event_logger.actions.append(("inside", "mcp.test.action"))

    assert fake_event_logger.actions == [
        ("enter", "mcp.test.action"),
        ("inside", "mcp.test.action"),
        ("exit", "mcp.test.action"),
    ]


def test_mcp_event_log_delegates_to_axbi_event_logger(monkeypatch):
    fake_event_logger = FakeEventLogger()
    monkeypatch.setattr(logging_utils, "event_logger", fake_event_logger)

    logging_utils.mcp_event_log(
        user_id=123,
        action="mcp.test.event",
        curated_payload={"tool": "test_tool"},
    )

    assert fake_event_logger.events == [
        {
            "user_id": 123,
            "action": "mcp.test.event",
            "curated_payload": {"tool": "test_tool"},
        }
    ]


def test_mcp_list_serialization_log_context_uses_standard_action(monkeypatch):
    fake_event_logger = FakeEventLogger()
    monkeypatch.setattr(logging_utils, "event_logger", fake_event_logger)

    with logging_utils.mcp_list_serialization_log_context("Saved Queries"):
        pass

    assert fake_event_logger.actions == [
        ("enter", "mcp.list_saved_queries.serialization"),
        ("exit", "mcp.list_saved_queries.serialization"),
    ]

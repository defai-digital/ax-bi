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
"""Unit tests for GenAI LLM audit helpers."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from pydantic import BaseModel

from axbi.genai.audit import (
    ACTION_COMPLETION,
    ACTION_CONFIG_UPDATED,
    ACTION_TEST_CONNECTION,
    base_host_from_url,
    log_llm_completion,
    log_llm_config_updated,
    log_llm_test_connection,
    timed_complete_json,
)
from axbi.genai.llm_errors import LLMNotConfiguredError
from axbi.genai.llm_provider import StubLLMProvider


class _Probe(BaseModel):
    ok: bool


def test_base_host_strips_path_and_userinfo() -> None:
    assert (
        base_host_from_url("https://user:secret@api.openai.com/v1/chat")
        == "api.openai.com"
    )
    assert base_host_from_url(None) is None


def test_config_updated_event_has_no_secret() -> None:
    with patch("axbi.genai.audit.event_logger") as el, patch(
        "axbi.genai.audit.stats_logger_manager"
    ) as sl:
        sl.instance.incr = MagicMock()
        log_llm_config_updated(
            provider="openai",
            enabled=True,
            base_url="https://api.openai.com/v1",
            model="gpt-4o-mini",
            user_id=7,
        )
        assert el.log.called
        args, kwargs = el.log.call_args
        assert args[1] == ACTION_CONFIG_UPDATED
        records = kwargs.get("records") or args[2] if len(args) > 2 else None
        # kwargs form used by helper
        records = kwargs.get("records")
        assert records is not None
        payload = str(records)
        assert "sk-" not in payload
        assert "api_key" not in payload
        assert records[0]["base_host"] == "api.openai.com"
        assert records[0]["provider_type"] == "openai"


def test_test_connection_and_completion_actions() -> None:
    with patch("axbi.genai.audit.event_logger") as el, patch(
        "axbi.genai.audit.stats_logger_manager"
    ) as sl:
        sl.instance.incr = MagicMock()
        log_llm_test_connection(success=True, provider="openai", model="m")
        log_llm_completion(
            operation="plan_dashboard",
            status="ok",
            provider_type="openai",
            model="m",
            latency_ms=12,
        )
        actions = [c.args[1] for c in el.log.call_args_list]
        assert ACTION_TEST_CONNECTION in actions
        assert ACTION_COMPLETION in actions


def test_timed_complete_json_stub_logs_not_configured() -> None:
    with patch("axbi.genai.audit.event_logger") as el, patch(
        "axbi.genai.audit.stats_logger_manager"
    ) as sl:
        sl.instance.incr = MagicMock()
        stub = StubLLMProvider()
        try:
            timed_complete_json(
                stub,
                system_prompt="s",
                user_prompt="u",
                response_schema=_Probe,
                metadata={"operation": "unit_test"},
            )
            raise AssertionError("expected LLMNotConfiguredError")
        except LLMNotConfiguredError:
            pass
        assert el.log.called
        records = el.log.call_args.kwargs["records"]
        assert records[0]["status"] == "LLM_NOT_CONFIGURED"

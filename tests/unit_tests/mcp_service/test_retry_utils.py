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

from typing import Any

import pytest

from axbi.mcp_service.utils import retry_utils


def test_retryable_operation_context_manager_api_removed() -> None:
    """Verify the broken retry context-manager API is not exported."""
    assert not hasattr(retry_utils, "RetryableOperation")


def test_retry_on_exception_retries_until_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify the supported sync decorator reruns the wrapped callable."""
    attempts: list[int] = []
    sleep_calls: list[float] = []

    monkeypatch.setattr(retry_utils.time, "sleep", sleep_calls.append)

    @retry_utils.retry_on_exception(
        max_attempts=3,
        base_delay=0.5,
        exceptions=(ValueError,),
        jitter=False,
    )
    def flaky_operation() -> str:
        attempts.append(len(attempts) + 1)
        if len(attempts) < 3:
            raise ValueError("transient")
        return "ok"

    assert flaky_operation() == "ok"
    assert attempts == [1, 2, 3]
    assert sleep_calls == [0.5, 1.0]


async def test_async_retry_on_exception_retries_until_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify the supported async decorator reruns the wrapped callable."""
    attempts: list[int] = []
    sleep_calls: list[float] = []

    async def fake_sleep(delay: float, *_args: Any, **_kwargs: Any) -> None:
        sleep_calls.append(delay)

    monkeypatch.setattr(retry_utils.asyncio, "sleep", fake_sleep)

    @retry_utils.async_retry_on_exception(
        max_attempts=3,
        base_delay=0.5,
        exceptions=(ValueError,),
        jitter=False,
    )
    async def flaky_operation() -> str:
        attempts.append(len(attempts) + 1)
        if len(attempts) < 3:
            raise ValueError("transient")
        return "ok"

    assert await flaky_operation() == "ok"
    assert attempts == [1, 2, 3]
    assert sleep_calls == [0.5, 1.0]

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
"""Unit tests for TaskContext throttle lock + deferred flush resilience."""

from __future__ import annotations

import threading
import time
import uuid
from typing import Any
from unittest.mock import MagicMock

import pytest

from axbi.tasks.context import TaskContext


def _mock_task() -> MagicMock:
    task = MagicMock()
    task.uuid = uuid.uuid4()
    task.properties_dict = {}
    task.payload_dict = {}
    return task


def _make_context(
    *,
    write_side_effect: Any = None,
) -> tuple[TaskContext, MagicMock]:
    ctx = TaskContext(_mock_task())
    write = MagicMock(side_effect=write_side_effect)
    ctx._write_to_db = write  # type: ignore[method-assign]
    return ctx, write


class TestUpdateTaskLockScope:
    def test_cache_merges_under_throttle_lock(self, app: Any) -> None:
        """Cache updates must not race the deferred-flush timer (dict resize)."""
        with app.app_context():
            app.config["TASK_PROGRESS_UPDATE_THROTTLE_INTERVAL"] = 60.0
            ctx, write = _make_context()

            # First update writes immediately
            ctx.update_task(progress=0.1, payload={"a": 1})
            assert write.call_count == 1
            assert ctx._payload_cache.get("a") == 1

            # Second update within window should defer
            ctx.update_task(progress=0.2, payload={"b": 2})
            assert ctx._has_pending_updates is True
            assert "b" in ctx._payload_cache

            # Concurrent reader under lock (simulates deferred flush snapshot)
            err: list[BaseException] = []

            def _reader() -> None:
                try:
                    with ctx._throttle_lock:
                        _ = dict(ctx._payload_cache)
                        _ = dict(ctx._properties_cache)
                except Exception as ex:  # noqa: BLE001
                    err.append(ex)

            def _writer() -> None:
                for i in range(50):
                    ctx.update_task(payload={f"k{i}": i})

            t1 = threading.Thread(target=_writer)
            t2 = threading.Thread(target=_reader)
            t1.start()
            t2.start()
            t1.join(timeout=5)
            t2.join(timeout=5)
            assert not err, f"dict race: {err}"


class TestDeferredFlushResilience:
    def test_deferred_flush_swallows_db_error_and_keeps_pending(
        self, app: Any
    ) -> None:
        with app.app_context():
            app.config["TASK_PROGRESS_UPDATE_THROTTLE_INTERVAL"] = 0.05
            ctx, write = _make_context()
            # First write succeeds; deferred flush fails
            write.side_effect = [None, RuntimeError("db down")]

            ctx.update_task(progress=0.1)
            ctx.update_task(progress=0.5)
            assert ctx._has_pending_updates is True

            time.sleep(0.25)
            # After failed deferred flush, pending remains True for retry
            assert ctx._has_pending_updates is True
            assert write.call_count >= 2

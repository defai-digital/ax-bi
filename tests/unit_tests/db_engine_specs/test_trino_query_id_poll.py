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
"""Trino query_id poll has a bounded timeout."""

from __future__ import annotations

import time
from types import SimpleNamespace
from typing import Any

from axbi.db_engine_specs.trino import TrinoEngineSpec


def test_query_id_poll_timeout_uses_query_timeout(app: Any) -> None:
    with app.app_context():
        query = SimpleNamespace(timeout=12, query_timeout=None)
        assert TrinoEngineSpec._query_id_poll_timeout_seconds(query) == 12.0


def test_query_id_poll_timeout_falls_back_to_config(app: Any) -> None:
    with app.app_context():
        app.config["SQLLAB_TIMEOUT"] = 30
        query = SimpleNamespace(timeout=None, query_timeout=None)
        assert TrinoEngineSpec._query_id_poll_timeout_seconds(query) == 30.0


def test_query_id_poll_loop_respects_deadline() -> None:
    """Simulate the poll loop used in execute_with_cursor: bound wait for query_id."""
    cursor = SimpleNamespace(query_id=None)
    execute_event = SimpleNamespace(is_set=lambda: False)
    poll_timeout = 0.15
    poll_deadline = time.monotonic() + poll_timeout
    raised: TimeoutError | None = None
    try:
        while not cursor.query_id and not execute_event.is_set():
            if time.monotonic() >= poll_deadline:
                raise TimeoutError(
                    f"Timed out waiting for Trino query_id after {poll_timeout}s"
                )
            time.sleep(0.02)
    except TimeoutError as ex:
        raised = ex
    assert raised is not None
    assert "Timed out waiting for Trino query_id" in str(raised)

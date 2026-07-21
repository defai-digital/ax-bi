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
"""Chart-data path must single-flight warehouse recompute under DistributedLock."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import timedelta
from unittest.mock import MagicMock

import pandas as pd
from pytest_mock import MockerFixture

from axbi.common.db_query_status import QueryStatus
from axbi.common.query_context_processor import QueryContextProcessor
from axbi.common.utils.query_cache_manager import QueryCacheManager
from axbi.exceptions import AcquireDistributedLockFailedException
from axbi.models.helpers import QueryResult


def _make_processor() -> QueryContextProcessor:
    qc = MagicMock()
    qc.force = False
    qc.datasource = MagicMock()
    qc.datasource.uid = "ds-1"
    qc.datasource.column_names = ["a"]
    return QueryContextProcessor(qc)


def _query_obj() -> MagicMock:
    query_obj = MagicMock()
    query_obj.columns = []
    query_obj.metrics = []
    query_obj.filter = []
    query_obj.validate = MagicMock()
    return query_obj


def test_get_df_payload_uses_distributed_lock_on_cache_miss(
    mocker: MockerFixture, app_context: None
) -> None:
    proc = _make_processor()
    query_obj = _query_obj()

    cold = QueryCacheManager(status=QueryStatus.PENDING, is_loaded=False)
    warm = QueryCacheManager(
        df=pd.DataFrame({"a": [1]}),
        status=QueryStatus.SUCCESS,
        is_loaded=True,
        is_cached=True,
    )

    mocker.patch.object(proc, "query_cache_key", return_value="ck-1")
    mocker.patch.object(proc, "get_cache_timeout", return_value=60)
    get_mock = mocker.patch(
        "axbi.common.query_context_processor.QueryCacheManager.get",
        side_effect=[cold, warm],
    )
    compute = mocker.patch.object(proc, "get_query_result")
    mocker.patch.object(proc, "get_annotation_data", return_value={})
    set_qr = mocker.patch.object(QueryCacheManager, "set_query_result")

    lock_entered = {"n": 0}

    @contextmanager
    def fake_lock(*_a, **_k):
        lock_entered["n"] += 1
        yield MagicMock()

    mocker.patch(
        "axbi.distributed_lock.DistributedLock",
        side_effect=lambda *a, **k: fake_lock(),
    )

    payload = proc.get_df_payload(query_obj)
    assert lock_entered["n"] == 1
    compute.assert_not_called()
    set_qr.assert_not_called()
    assert get_mock.call_count >= 2
    assert payload["status"] == QueryStatus.SUCCESS


def test_waiter_polls_until_warm_without_recompute(
    mocker: MockerFixture, app_context: None
) -> None:
    """Second waiter must NOT recompute when the lock holder fills cache mid-wait."""
    proc = _make_processor()
    # Short poll/wait so the test stays fast; still multi-step poll path.
    mocker.patch.object(QueryContextProcessor, "_CHART_DATA_WAIT_MAX_SECONDS", 5.0)
    mocker.patch.object(QueryContextProcessor, "_CHART_DATA_WAIT_POLL_SECONDS", 0.01)
    mocker.patch.object(
        QueryContextProcessor, "_CHART_DATA_WAIT_POLL_MAX_SECONDS", 0.02
    )

    query_obj = _query_obj()
    cold = QueryCacheManager(status=QueryStatus.PENDING, is_loaded=False)
    warm = QueryCacheManager(
        df=pd.DataFrame({"a": [1]}),
        status=QueryStatus.SUCCESS,
        is_loaded=True,
        is_cached=True,
    )

    mocker.patch.object(proc, "query_cache_key", return_value="ck-wait")
    mocker.patch.object(proc, "get_cache_timeout", return_value=60)

    # Initial cold miss in get_df_payload, then waiter polls: cold, cold, warm.
    get_mock = mocker.patch(
        "axbi.common.query_context_processor.QueryCacheManager.get",
        side_effect=[cold, cold, cold, warm],
    )
    compute = mocker.patch.object(proc, "get_query_result")
    mocker.patch.object(proc, "get_annotation_data", return_value={})
    mocker.patch.object(QueryCacheManager, "set_query_result")
    mocker.patch(
        "axbi.distributed_lock.DistributedLock",
        side_effect=AcquireDistributedLockFailedException("taken"),
    )
    sleep_mock = mocker.patch("time.sleep")

    payload = proc.get_df_payload(query_obj)

    compute.assert_not_called()
    assert sleep_mock.call_count >= 1
    assert get_mock.call_count >= 3
    assert payload["status"] == QueryStatus.SUCCESS


def test_waiter_last_resort_recomputes_only_after_wait_budget(
    mocker: MockerFixture, app_context: None
) -> None:
    """Unlocked recompute only after wait budget; not after a single short sleep."""
    proc = _make_processor()
    mocker.patch.object(QueryContextProcessor, "_CHART_DATA_WAIT_MAX_SECONDS", 0.05)
    mocker.patch.object(QueryContextProcessor, "_CHART_DATA_WAIT_POLL_SECONDS", 0.02)
    mocker.patch.object(
        QueryContextProcessor, "_CHART_DATA_WAIT_POLL_MAX_SECONDS", 0.02
    )

    query_obj = _query_obj()
    cold = QueryCacheManager(status=QueryStatus.PENDING, is_loaded=False)

    mocker.patch.object(proc, "query_cache_key", return_value="ck-timeout")
    mocker.patch.object(proc, "get_cache_timeout", return_value=60)
    mocker.patch(
        "axbi.common.query_context_processor.QueryCacheManager.get",
        return_value=cold,
    )
    mocker.patch(
        "axbi.distributed_lock.DistributedLock",
        side_effect=AcquireDistributedLockFailedException("taken"),
    )
    # Advance monotonic past the wait budget after a few polls.
    times = iter([0.0, 0.0, 0.03, 0.06, 0.06, 0.06])
    mocker.patch("time.monotonic", side_effect=lambda: next(times, 1.0))
    mocker.patch("time.sleep")

    qr = QueryResult(
        query="SELECT 1",
        status=QueryStatus.SUCCESS,
        df=pd.DataFrame({"a": [1]}),
        duration=timedelta(milliseconds=10),
    )
    compute_mock = mocker.patch.object(proc, "get_query_result", return_value=qr)
    mocker.patch.object(proc, "get_annotation_data", return_value={})
    mocker.patch.object(QueryCacheManager, "set_query_result")

    proc.get_df_payload(query_obj)
    compute_mock.assert_called()

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
"""SQLLAB_ASYNC_TIME_LIMIT_SEC must drive Celery soft_time_limit at enqueue time."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from axbi.async_events.async_query_manager import AsyncQueryManager
from axbi.tasks.async_queries import (
    bind_async_query_soft_time_limits,
    get_async_query_soft_time_limit,
    load_chart_data_into_cache,
    load_explore_json_into_cache,
)


def test_get_async_query_soft_time_limit_reads_config(app: Any) -> None:
    with app.app_context():
        app.config["SQLLAB_ASYNC_TIME_LIMIT_SEC"] = 1234
        assert get_async_query_soft_time_limit() == 1234


def test_bind_async_query_soft_time_limits_updates_task_attrs(app: Any) -> None:
    with app.app_context():
        app.config["SQLLAB_ASYNC_TIME_LIMIT_SEC"] = 4321
        bind_async_query_soft_time_limits()
        assert load_chart_data_into_cache.soft_time_limit == 4321
        assert load_explore_json_into_cache.soft_time_limit == 4321


def test_enqueue_passes_config_soft_time_limit(app: Any) -> None:
    with app.app_context():
        app.config["SQLLAB_ASYNC_TIME_LIMIT_SEC"] = 999
        task = MagicMock()
        task.name = "load_chart_data_into_cache"
        AsyncQueryManager._enqueue_async_query_job(task, {"job": 1}, {"fd": True})
        task.apply_async.assert_called_once()
        _args, kwargs = task.apply_async.call_args
        assert kwargs["soft_time_limit"] == 999
        assert task.soft_time_limit == 999

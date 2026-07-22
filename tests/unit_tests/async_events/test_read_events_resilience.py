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
"""read_events: skip poisoned entries; map Redis errors to AsyncQueryJobException."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from axbi.async_events.async_query_manager import (
    AsyncQueryJobException,
    AsyncQueryManager,
)
from axbi.async_events.cache_backend import RedisCacheBackend


def _mgr_with_cache(cache: MagicMock) -> AsyncQueryManager:
    mgr = AsyncQueryManager()
    mgr._cache = cache
    mgr._stream_prefix = "async-events-"
    return mgr


def test_read_events_skips_malformed_payload() -> None:
    cache = MagicMock()
    # Make isinstance checks treat this as RedisCacheBackend
    cache.__class__ = RedisCacheBackend  # type: ignore[misc]
    cache.xrange.return_value = [
        (b"1-0", {b"data": b'{"status": "done"}'}),
        (b"1-1", {b"data": b"not-json"}),
        (b"1-2", {b"data": b'{"status": "error"}'}),
    ]
    mgr = _mgr_with_cache(cache)

    events = mgr.read_events("chan", None)
    assert len(events) == 2
    assert events[0]["status"] == "done"
    assert events[1]["status"] == "error"


def test_read_events_maps_redis_error() -> None:
    cache = MagicMock()
    cache.__class__ = RedisCacheBackend  # type: ignore[misc]
    cache.xrange.side_effect = ConnectionError("redis down")
    mgr = _mgr_with_cache(cache)

    with pytest.raises(AsyncQueryJobException, match="temporarily unavailable"):
        mgr.read_events("chan", "1-0")

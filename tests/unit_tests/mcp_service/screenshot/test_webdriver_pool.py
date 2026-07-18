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
"""Unit tests for WebDriver pool cleanup behavior."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from axbi.mcp_service.screenshot.webdriver_pool import (
    PooledWebDriver,
    WebDriverPool,
)


def _pooled(driver_id: str, *, healthy: bool = True) -> PooledWebDriver:
    driver = SimpleNamespace(id=driver_id, close=MagicMock(), quit=MagicMock())
    return PooledWebDriver(
        driver=driver,  # type: ignore[arg-type]
        created_at=0.0,
        last_used=0.0,
        window_size=(800, 600),  # type: ignore[arg-type]
        is_healthy=healthy,
        usage_count=0,
    )


def test_cleanup_expired_drivers_drains_entire_pool() -> None:
    """Expired drivers behind a valid one must still be destroyed.

    A break-on-first-valid cleanup left later expired instances stranded in
    the queue, defeating TTL eviction and leaking browser processes.
    """
    pool = WebDriverPool(max_pool_size=5)
    valid = _pooled("valid")
    expired_a = _pooled("expired-a")
    expired_b = _pooled("expired-b")

    # Queue order: valid first, then expired — the bug stopped after valid.
    for item in (valid, expired_a, expired_b):
        pool._pool.put_nowait(item)

    destroyed: list[str] = []

    def _is_valid(pooled: PooledWebDriver) -> bool:
        return pooled.driver.id == "valid"  # type: ignore[attr-defined]

    def _destroy(pooled: PooledWebDriver) -> None:
        destroyed.append(pooled.driver.id)  # type: ignore[attr-defined]

    with (
        patch.object(pool, "_is_driver_valid", side_effect=_is_valid),
        patch.object(pool, "_destroy_driver", side_effect=_destroy),
    ):
        pool._cleanup_expired_drivers()

    assert sorted(destroyed) == ["expired-a", "expired-b"]
    assert pool._pool.qsize() == 1
    remaining = pool._pool.get_nowait()
    assert remaining.driver.id == "valid"  # type: ignore[attr-defined]

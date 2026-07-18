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
"""Unit tests for pooled screenshot isolation on cookie-clear failure."""

from __future__ import annotations

from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from axbi.mcp_service.screenshot.pooled_screenshot import PooledBaseScreenshot


class _ConcretePooledScreenshot(PooledBaseScreenshot):
    """Minimal concrete subclass for driving _get_screenshot_internal."""

    def get_screenshot(self, user, window_size=None):  # type: ignore[no-untyped-def]
        return self._get_screenshot_internal(user, window_size)

    def _take_screenshot(self, driver, user):  # type: ignore[no-untyped-def]
        return b"png"


def test_get_screenshot_aborts_when_cookie_clear_fails() -> None:
    """Cookie clear failure must not continue into re-auth (cross-user risk)."""
    shot = _ConcretePooledScreenshot(
        url="http://example.test/dashboard/1/",
        digest="test-digest",
    )
    driver = MagicMock()
    driver.delete_all_cookies.side_effect = RuntimeError("session dead")
    auth = MagicMock()

    @contextmanager
    def _fake_get_driver(_window_size, _user_id=None):  # type: ignore[no-untyped-def]
        yield driver

    pool = SimpleNamespace(get_driver=_fake_get_driver)
    user = SimpleNamespace(id=7, username="alice")

    with (
        patch(
            "axbi.mcp_service.screenshot.pooled_screenshot.get_webdriver_pool",
            return_value=pool,
        ),
        patch(
            "axbi.mcp_service.screenshot.pooled_screenshot."
            "machine_auth_provider_factory"
        ) as factory,
    ):
        factory.instance = auth
        with pytest.raises(RuntimeError, match="cookie clear failed"):
            shot._get_screenshot_internal(user)  # type: ignore[arg-type]

    auth.authenticate_webdriver.assert_not_called()
    driver.get.assert_not_called()

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
"""WebDriver pool creation timeout: SIGALRM guard + typed error."""

from __future__ import annotations

import threading
from unittest.mock import MagicMock, patch

import pytest

from axbi.mcp_service.screenshot.webdriver_pool import (
    WebDriverCreationError,
    WebDriverPool,
)


def test_create_driver_raises_typed_error_on_timeout_main_thread() -> None:
    pool = WebDriverPool(creation_timeout_seconds=1)
    mock_selenium = MagicMock()
    mock_selenium.create.side_effect = WebDriverCreationError("timed out")

    with (
        patch(
            "axbi.mcp_service.screenshot.webdriver_pool.get_webdriver_type",
            return_value="chrome",
        ),
        patch(
            "axbi.mcp_service.screenshot.webdriver_pool.WebDriverSelenium",
            return_value=mock_selenium,
        ),
        patch("axbi.mcp_service.screenshot.webdriver_pool.signal.signal"),
        patch("axbi.mcp_service.screenshot.webdriver_pool.signal.alarm"),
        patch(
            "axbi.mcp_service.screenshot.webdriver_pool.threading.current_thread",
            return_value=threading.main_thread(),
        ),
    ):
        with pytest.raises(WebDriverCreationError, match="timed out"):
            pool._create_driver(window_size=(800, 600))


def test_create_driver_works_off_main_thread_without_sigalrm() -> None:
    """Non-main threads must not call signal.signal(SIGALRM)."""
    pool = WebDriverPool(creation_timeout_seconds=5)
    fake_driver = MagicMock()
    mock_selenium = MagicMock()
    mock_selenium.create.return_value = fake_driver

    errors: list[BaseException] = []
    result: list[object] = []
    signal_calls: list[object] = []

    def _worker() -> None:
        try:
            with (
                patch(
                    "axbi.mcp_service.screenshot.webdriver_pool.get_webdriver_type",
                    return_value="chrome",
                ),
                patch(
                    "axbi.mcp_service.screenshot.webdriver_pool.WebDriverSelenium",
                    return_value=mock_selenium,
                ),
                patch(
                    "axbi.mcp_service.screenshot.webdriver_pool.signal.signal",
                    side_effect=lambda *a, **k: signal_calls.append(a),
                ),
            ):
                result.append(pool._create_driver(window_size=(800, 600)))
        except BaseException as ex:  # noqa: BLE001
            errors.append(ex)

    t = threading.Thread(target=_worker)
    t.start()
    t.join(timeout=5)
    assert not errors, errors
    assert result
    assert result[0].driver is fake_driver  # type: ignore[attr-defined]
    # SIGALRM must not be registered off the main thread
    assert signal_calls == []

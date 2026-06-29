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

"""Tests for health_check MCP tool."""

from unittest.mock import MagicMock

import pytest
from flask import current_app

from superset.mcp_service.system.schemas import HealthCheckResponse
from superset.mcp_service.system.tool.health_check import health_check


def test_health_check_response_schema():
    """Test that HealthCheckResponse has required fields."""
    response = HealthCheckResponse(
        status="healthy",
        timestamp="2025-11-10T19:00:00",
        service="Test MCP Service",
        version="4.0.0",
        python_version="3.11.0",
        platform="Darwin",
    )

    assert response.status == "healthy"
    assert response.service == "Test MCP Service"
    assert response.version == "4.0.0"
    assert response.python_version == "3.11.0"
    assert response.platform == "Darwin"
    assert response.timestamp is not None
    assert response.uptime_seconds is None  # Optional field


def test_health_check_response_with_uptime():
    """Test HealthCheckResponse with optional uptime field."""
    response = HealthCheckResponse(
        status="healthy",
        timestamp="2025-11-10T19:00:00",
        service="Test MCP Service",
        version="4.0.0",
        python_version="3.11.0",
        platform="Darwin",
        uptime_seconds=123.45,
    )

    assert response.uptime_seconds == 123.45


@pytest.mark.asyncio
async def test_health_check_emits_runtime_modernization_metrics(
    app_context: None,
    mocker,
):
    """Health check emits baseline runtime modernization metrics."""

    stats_logger = MagicMock()
    current_app.config["STATS_LOGGER"] = stats_logger
    current_app.config["MCP_DEV_USERNAME"] = "admin"
    mocker.patch(
        "superset.mcp_service.auth.load_user_with_relationships",
        return_value=MagicMock(),
    )
    mocker.patch(
        "superset.mcp_service.system.tool.health_check.get_version_metadata",
        return_value={"version_string": "test-version"},
    )

    response = await health_check()

    assert response.status == "healthy"
    stats_logger.incr.assert_called_once_with(
        "runtime_modernization.mcp_orchestration.health_check.success"
    )
    stats_logger.timing.assert_called_once()
    assert stats_logger.timing.call_args.args[0] == (
        "runtime_modernization.mcp_orchestration.health_check.duration"
    )

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
"""Unit tests for the add_dashboard_filter MCP tool."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
from fastmcp import Client

from superset.mcp_service.app import mcp
from superset.utils import json


@pytest.fixture
def mcp_server() -> object:
    """Return the FastMCP app instance for use in MCP client tests."""
    return mcp


@pytest.fixture(autouse=True)
def mock_auth():
    """Mock authentication for all tests."""
    with patch("superset.mcp_service.auth.get_user_from_request") as mock_get_user:
        mock_user = Mock()
        mock_user.id = 1
        mock_user.username = "admin"
        mock_get_user.return_value = mock_user
        yield mock_get_user


def _dashboard(json_metadata: str | None) -> SimpleNamespace:
    return SimpleNamespace(
        id=1,
        dashboard_title="Sales Dashboard",
        json_metadata=json_metadata,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "json_metadata",
    [
        "[]",
        '{"native_filter_configuration": "bad"}',
    ],
)
async def test_bad_existing_metadata_starts_clean_filter_config(
    json_metadata: str,
    mcp_server: object,
) -> None:
    dashboard = _dashboard(json_metadata)
    update_command = Mock()
    update_command.run.return_value = dashboard

    with (
        patch(
            "superset.daos.dashboard.DashboardDAO.find_by_id",
            return_value=dashboard,
        ),
        patch("superset.security_manager.raise_for_ownership", return_value=None),
        patch(
            "superset.commands.dashboard.update.UpdateDashboardCommand",
            return_value=update_command,
        ) as update_cls,
    ):
        async with Client(mcp_server) as client:
            result = await client.call_tool(
                "add_dashboard_filter",
                {
                    "request": {
                        "dashboard_id": 1,
                        "filter_type": "filter_select",
                        "name": "Region",
                        "targets": [{"dataset_id": 7, "column_name": "country"}],
                    }
                },
            )

    content = result.structured_content
    assert content["error"] is None
    assert content["dashboard_id"] == 1

    update_payload = update_cls.call_args.args[1]
    metadata = json.loads(update_payload["json_metadata"])
    filters = metadata["native_filter_configuration"]
    assert len(filters) == 1
    assert filters[0]["name"] == "Region"
    assert filters[0]["targets"] == [{"datasetId": 7, "column": {"name": "country"}}]

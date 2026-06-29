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

import importlib
import logging
from unittest.mock import MagicMock, Mock, patch

import pytest
from fastmcp import Client
from flask import current_app
from pydantic import ValidationError

from superset.mcp_service.app import mcp
from superset.mcp_service.rls.schemas import ListRlsFiltersRequest, RlsColumnFilter
from superset.runtime_modernization.ax_services import AxServicesResponse
from superset.utils import json

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

list_rls_filters_module = importlib.import_module(
    "superset.mcp_service.rls.tool.list_rls_filters"
)


def create_mock_rls_filter(
    filter_id: int = 1,
    name: str = "test_filter",
    filter_type: str = "Regular",
    clause: str = "user_id = {{current_user_id()}}",
    group_key: str | None = None,
) -> MagicMock:
    rls_filter = MagicMock()
    rls_filter.id = filter_id
    rls_filter.name = name
    rls_filter.filter_type = filter_type
    rls_filter.clause = clause
    rls_filter.group_key = group_key
    rls_filter.changed_on = None

    table = MagicMock()
    table.id = 1
    table.table_name = "sales"
    rls_filter.tables = [table]

    role = MagicMock()
    role.id = 1
    role.name = "Alpha"
    rls_filter.roles = [role]

    return rls_filter


@pytest.fixture
def mcp_server():
    return mcp


@pytest.fixture(autouse=True)
def mock_auth():
    with patch("superset.mcp_service.auth.get_user_from_request") as mock_get_user:
        mock_user = Mock()
        mock_user.id = 1
        mock_user.username = "admin"
        mock_get_user.return_value = mock_user
        yield mock_get_user


class TestRlsColumnFilterSchema:
    def test_invalid_filter_column_rejected(self):
        with pytest.raises(ValidationError):
            RlsColumnFilter(col="clause", opr="eq", value="test")

    def test_valid_name_filter(self):
        f = RlsColumnFilter(col="name", opr="eq", value="test")
        assert f.col == "name"

    def test_valid_filter_type_filter(self):
        f = RlsColumnFilter(col="filter_type", opr="eq", value="Regular")
        assert f.col == "filter_type"


@patch("superset.daos.security.RLSDAO.list")
@pytest.mark.asyncio
async def test_list_rls_filters_basic(mock_list, mcp_server):
    rls_filter = create_mock_rls_filter()
    mock_list.return_value = ([rls_filter], 1)

    async with Client(mcp_server) as client:
        result = await client.call_tool("list_rls_filters", {})
        assert result.content is not None
        data = json.loads(result.content[0].text)
        assert "rls_filters" in data
        assert len(data["rls_filters"]) == 1
        assert data["rls_filters"][0]["id"] == 1
        assert data["rls_filters"][0]["name"] == "test_filter"


@patch("superset.daos.security.RLSDAO.list")
@pytest.mark.asyncio
async def test_list_rls_filters_with_request(mock_list, mcp_server):
    rls_filter = create_mock_rls_filter()
    mock_list.return_value = ([rls_filter], 1)

    async with Client(mcp_server) as client:
        request = ListRlsFiltersRequest(page=1, page_size=10)
        result = await client.call_tool(
            "list_rls_filters", {"request": request.model_dump()}
        )
        data = json.loads(result.content[0].text)
        assert data["count"] == 1
        assert data["total_count"] == 1


@patch("superset.daos.security.RLSDAO.list")
@pytest.mark.asyncio
async def test_list_rls_filters_with_search(mock_list, mcp_server):
    rls_filter = create_mock_rls_filter(name="user_filter")
    mock_list.return_value = ([rls_filter], 1)

    async with Client(mcp_server) as client:
        request = ListRlsFiltersRequest(page=1, page_size=10, search="user")
        result = await client.call_tool(
            "list_rls_filters", {"request": request.model_dump()}
        )
        data = json.loads(result.content[0].text)
        assert data["rls_filters"][0]["name"] == "user_filter"


@patch("superset.daos.security.RLSDAO.list")
@pytest.mark.asyncio
async def test_list_rls_filters_returns_tables_and_roles(mock_list, mcp_server):
    rls_filter = create_mock_rls_filter()
    mock_list.return_value = ([rls_filter], 1)

    async with Client(mcp_server) as client:
        request = ListRlsFiltersRequest(
            page=1,
            page_size=10,
            select_columns=["id", "name", "tables", "roles"],
        )
        result = await client.call_tool(
            "list_rls_filters", {"request": request.model_dump()}
        )
        data = json.loads(result.content[0].text)
        item = data["rls_filters"][0]
        assert "tables" in item
        assert item["tables"][0]["table_name"] == "sales"
        assert "roles" in item
        assert item["roles"][0]["name"] == "Alpha"


@patch("superset.daos.security.RLSDAO.list")
@pytest.mark.asyncio
async def test_list_rls_filters_empty(mock_list, mcp_server):
    mock_list.return_value = ([], 0)

    async with Client(mcp_server) as client:
        result = await client.call_tool("list_rls_filters", {})
        data = json.loads(result.content[0].text)
        assert data["count"] == 0
        assert data["rls_filters"] == []


@patch("superset.daos.security.RLSDAO.find_by_id")
@pytest.mark.asyncio
async def test_get_rls_filter_info_basic(mock_find, mcp_server):
    rls_filter = create_mock_rls_filter()
    mock_find.return_value = rls_filter

    async with Client(mcp_server) as client:
        result = await client.call_tool(
            "get_rls_filter_info", {"request": {"identifier": 1}}
        )
        data = json.loads(result.content[0].text)
        assert data["id"] == 1
        assert data["name"] == "test_filter"
        assert data["filter_type"] == "Regular"
        assert data["clause"] == "user_id = {{current_user_id()}}"


@patch("superset.daos.security.RLSDAO.find_by_id")
@pytest.mark.asyncio
async def test_get_rls_filter_info_not_found(mock_find, mcp_server):
    mock_find.return_value = None

    async with Client(mcp_server) as client:
        result = await client.call_tool(
            "get_rls_filter_info", {"request": {"identifier": 999}}
        )
        data = json.loads(result.content[0].text)
        assert data["error_type"] == "not_found"


@patch("superset.daos.security.RLSDAO.find_by_id")
@pytest.mark.asyncio
async def test_get_rls_filter_info_includes_tables_and_roles(mock_find, mcp_server):
    rls_filter = create_mock_rls_filter()
    mock_find.return_value = rls_filter

    async with Client(mcp_server) as client:
        result = await client.call_tool(
            "get_rls_filter_info", {"request": {"identifier": 1}}
        )
        data = json.loads(result.content[0].text)
        assert data["tables"][0]["table_name"] == "sales"
        assert data["roles"][0]["name"] == "Alpha"


def test_list_rls_filters_request_rejects_search_and_filters():
    with pytest.raises(ValidationError):
        ListRlsFiltersRequest(
            search="test",
            filters=[{"col": "name", "opr": "eq", "value": "x"}],
        )


@patch("superset.daos.security.RLSDAO.list")
@pytest.mark.asyncio
async def test_list_rls_filters_roles_only_select_columns(mock_list, mcp_server):
    """Regression: select_columns=['roles'] must not raise ValueError.

    'roles' is in USER_DIRECTORY_FIELDS so ModelListCore would raise if it
    were the sole column passed to run_tool. The tool must strip it before
    calling run_tool and restore it in the model_dump context.
    """
    rls_filter = create_mock_rls_filter()
    mock_list.return_value = ([rls_filter], 1)

    async with Client(mcp_server) as client:
        request = ListRlsFiltersRequest(page=1, page_size=10, select_columns=["roles"])
        result = await client.call_tool(
            "list_rls_filters", {"request": request.model_dump()}
        )
        data = json.loads(result.content[0].text)
        item = data["rls_filters"][0]
        assert "roles" in item
        assert item["roles"][0]["name"] == "Alpha"


@pytest.mark.asyncio
async def test_list_rls_filters_serves_valid_sidecar_response(mcp_server):
    """RLS filter listing can serve a valid TypeScript sidecar response."""

    stats_logger = MagicMock()

    class MockAxServicesClient:
        def __init__(self, _config):
            pass

        def list_rls_filters(self, payload):
            assert payload["contractVersion"] == "rls-list.v1"
            return AxServicesResponse(
                ok=True,
                status_code=200,
                payload={
                    "contractVersion": "rls-list.v1",
                    "rlsFilters": [
                        {
                            "id": 42,
                            "name": "regional_sales",
                            "filterType": "Regular",
                            "tables": [{"id": 7, "tableName": "sales"}],
                            "roles": [{"id": 3, "name": "Alpha"}],
                            "clause": "region = 'EMEA'",
                            "groupKey": "region",
                            "changedOn": "2026-01-01T00:00:00",
                        }
                    ],
                    "count": 1,
                    "totalCount": 1,
                    "page": 1,
                    "pageSize": 10,
                    "totalPages": 1,
                    "hasNext": False,
                    "hasPrevious": False,
                    "columnsRequested": [
                        "id",
                        "name",
                        "filter_type",
                        "tables",
                        "roles",
                        "clause",
                        "group_key",
                    ],
                    "columnsLoaded": [
                        "id",
                        "name",
                        "filter_type",
                        "tables",
                        "roles",
                        "clause",
                        "group_key",
                    ],
                    "warnings": [],
                },
            )

    with (
        patch.object(
            list_rls_filters_module,
            "is_feature_enabled",
            side_effect=lambda flag: flag
            in {
                "TS_MCP_ORCHESTRATION",
                "TS_RLS_FILTER_LIST_SERVING",
            },
        ),
        patch.object(list_rls_filters_module, "AxServicesClient", MockAxServicesClient),
        patch.dict(current_app.config, {"STATS_LOGGER": stats_logger}),
    ):
        async with Client(mcp_server) as client:
            request = ListRlsFiltersRequest(
                page=1,
                page_size=10,
                select_columns=[
                    "id",
                    "name",
                    "filter_type",
                    "tables",
                    "roles",
                    "clause",
                    "group_key",
                ],
            )
            result = await client.call_tool(
                "list_rls_filters", {"request": request.model_dump()}
            )
            data = json.loads(result.content[0].text)

    item = data["rls_filters"][0]
    assert item["id"] == 42
    assert item["name"] == "regional_sales"
    assert item["filter_type"] == "Regular"
    assert item["tables"][0]["table_name"] == "sales"
    assert item["roles"][0]["name"] == "Alpha"
    assert item["clause"] == "region = 'EMEA'"
    assert item["group_key"] == "region"
    stats_logger.incr.assert_any_call(
        "runtime_modernization.mcp_orchestration.list_rls_filters.served_candidate"
    )


@patch("superset.daos.security.RLSDAO.list")
@pytest.mark.asyncio
async def test_list_rls_filters_falls_back_on_candidate_warning(mock_list, mcp_server):
    """Sidecar RLS warnings fall back to the authoritative Python path."""

    stats_logger = MagicMock()
    rls_filter = create_mock_rls_filter()
    mock_list.return_value = ([rls_filter], 1)

    class MockAxServicesClient:
        def __init__(self, _config):
            pass

        def list_rls_filters(self, _payload):
            return AxServicesResponse(
                ok=True,
                status_code=200,
                payload={
                    "contractVersion": "rls-list.v1",
                    "rlsFilters": [],
                    "count": 0,
                    "totalCount": 0,
                    "page": 1,
                    "pageSize": 10,
                    "totalPages": 0,
                    "hasNext": False,
                    "hasPrevious": False,
                    "columnsRequested": ["id", "name"],
                    "columnsLoaded": [],
                    "warnings": ["RLS filter list returned status 504 from Superset"],
                },
            )

    with (
        patch.object(
            list_rls_filters_module,
            "is_feature_enabled",
            side_effect=lambda flag: flag
            in {
                "TS_MCP_ORCHESTRATION",
                "TS_RLS_FILTER_LIST_SERVING",
            },
        ),
        patch.object(list_rls_filters_module, "AxServicesClient", MockAxServicesClient),
        patch.dict(current_app.config, {"STATS_LOGGER": stats_logger}),
    ):
        async with Client(mcp_server) as client:
            request = ListRlsFiltersRequest(page=1, page_size=10)
            result = await client.call_tool(
                "list_rls_filters", {"request": request.model_dump()}
            )
            data = json.loads(result.content[0].text)

    assert data["rls_filters"][0]["id"] == 1
    mock_list.assert_called_once()
    stats_logger.incr.assert_any_call(
        "runtime_modernization.mcp_orchestration.list_rls_filters.fallback"
    )

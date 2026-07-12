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
from unittest.mock import MagicMock, patch

import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError
from flask import current_app
from pydantic import ValidationError

from axbi.mcp_service.app import mcp
from axbi.mcp_service.tag.schemas import ListTagsRequest, TagFilter
from axbi.runtime_modernization.ax_services import AxServicesResponse
from axbi.utils import json

logger = logging.getLogger(__name__)
list_tags_module = importlib.import_module("axbi.mcp_service.tag.tool.list_tags")


class TestTagFilterSchema:
    """Tests for TagFilter schema — filterable columns."""

    def test_invalid_filter_column_rejected(self):
        with pytest.raises(ValidationError):
            TagFilter(col="not_a_real_column", opr="eq", value="x")

    def test_valid_name_filter(self):
        f = TagFilter(col="name", opr="ct", value="finance")
        assert f.col == "name"

    def test_valid_type_filter(self):
        f = TagFilter(col="type", opr="eq", value="custom")
        assert f.col == "type"


def create_mock_tag(
    tag_id: int = 1,
    name: str = "finance",
    type_name: str = "custom",
    description: str = "Finance related",
) -> MagicMock:
    tag = MagicMock()
    tag.id = tag_id
    tag.name = name
    mock_type = MagicMock()
    mock_type.name = type_name
    tag.type = mock_type
    tag.description = description
    tag.changed_on = None
    tag.created_on = None
    tag.changed_by = None
    tag.created_by = None
    return tag


@pytest.fixture
def mcp_server():
    return mcp


@pytest.fixture(autouse=True)
def mock_auth():
    from unittest.mock import Mock

    with patch("axbi.mcp_service.auth.get_user_from_request") as mock_get_user:
        mock_user = Mock()
        mock_user.id = 1
        mock_user.username = "admin"
        mock_get_user.return_value = mock_user
        yield mock_get_user


@patch("axbi.daos.tag.TagDAO.list")
@pytest.mark.asyncio
async def test_list_tags_basic(mock_list, mcp_server):
    """Test basic tag listing functionality."""
    tag = create_mock_tag()
    mock_list.return_value = ([tag], 1)
    async with Client(mcp_server) as client:
        request = ListTagsRequest(page=1, page_size=10)
        result = await client.call_tool("list_tags", {"request": request.model_dump()})
        assert result.content is not None
        data = json.loads(result.content[0].text)
        assert data["tags"] is not None
        assert len(data["tags"]) == 1
        assert data["tags"][0]["id"] == 1
        assert "finance" in data["tags"][0]["name"]


@patch("axbi.daos.tag.TagDAO.list")
@pytest.mark.asyncio
async def test_list_tags_without_request(mock_list, mcp_server):
    """Test listing tags with no request payload uses defaults."""
    tag = create_mock_tag()
    mock_list.return_value = ([tag], 1)
    async with Client(mcp_server) as client:
        result = await client.call_tool("list_tags", {})
        data = json.loads(result.content[0].text)
        assert data["tags"] is not None


@patch("axbi.daos.tag.TagDAO.list")
@pytest.mark.asyncio
async def test_list_tags_with_search(mock_list, mcp_server):
    """Test tag listing with search functionality."""
    tag = create_mock_tag(name="sales")
    mock_list.return_value = ([tag], 1)
    async with Client(mcp_server) as client:
        request = ListTagsRequest(page=1, page_size=10, search="sales")
        result = await client.call_tool("list_tags", {"request": request.model_dump()})
        data = json.loads(result.content[0].text)
        assert "sales" in data["tags"][0]["name"]


@patch("axbi.daos.tag.TagDAO.list")
@pytest.mark.asyncio
async def test_list_tags_with_filters(mock_list, mcp_server):
    """Test tag listing with column filters."""
    tag = create_mock_tag(type_name="custom")
    mock_list.return_value = ([tag], 1)
    async with Client(mcp_server) as client:
        request = ListTagsRequest(
            page=1,
            page_size=10,
            filters=[{"col": "type", "opr": "eq", "value": "custom"}],
        )
        result = await client.call_tool("list_tags", {"request": request.model_dump()})
        data = json.loads(result.content[0].text)
        assert len(data["tags"]) == 1


@patch("axbi.daos.tag.TagDAO.list")
@pytest.mark.asyncio
async def test_list_tags_empty_results(mock_list, mcp_server):
    """Test tag listing with no results."""
    mock_list.return_value = ([], 0)
    async with Client(mcp_server) as client:
        request = ListTagsRequest(page=1, page_size=10)
        result = await client.call_tool("list_tags", {"request": request.model_dump()})
        data = json.loads(result.content[0].text)
        assert data["tags"] == []
        assert data["total_count"] == 0


@patch("axbi.daos.tag.TagDAO.list")
@pytest.mark.asyncio
async def test_list_tags_api_error(mock_list, mcp_server):
    """Test error handling when DAO raises an exception."""
    mock_list.side_effect = ToolError("Tag DAO error")
    async with Client(mcp_server) as client:
        request = ListTagsRequest(page=1, page_size=10)
        with pytest.raises(ToolError) as excinfo:  # noqa: PT012
            await client.call_tool("list_tags", {"request": request.model_dump()})
        assert "Tag DAO error" in str(excinfo.value)


def test_list_tags_search_and_filters_mutually_exclusive():
    """Test that search and filters cannot be used together."""
    with pytest.raises(ValidationError):
        ListTagsRequest(
            search="finance",
            filters=[{"col": "name", "opr": "eq", "value": "finance"}],
        )


@patch("axbi.daos.tag.TagDAO.find_by_id")
@pytest.mark.asyncio
async def test_get_tag_info_basic(mock_find, mcp_server):
    """Test basic get tag info functionality."""
    tag = create_mock_tag()
    mock_find.return_value = tag
    async with Client(mcp_server) as client:
        result = await client.call_tool("get_tag_info", {"request": {"identifier": 1}})
        assert result.content is not None
        data = json.loads(result.content[0].text)
        assert data["id"] == 1
        assert "finance" in data["name"]
        assert data["type"] == "custom"
        assert "Finance related" in data["description"]


@patch("axbi.daos.tag.TagDAO.find_by_id")
@pytest.mark.asyncio
async def test_get_tag_info_sanitizes_user_controlled_fields(mock_find, mcp_server):
    """name and description are wrapped in UNTRUSTED-CONTENT for LLM data boundary."""
    tag = create_mock_tag()
    mock_find.return_value = tag
    async with Client(mcp_server) as client:
        result = await client.call_tool("get_tag_info", {"request": {"identifier": 1}})
        data = json.loads(result.content[0].text)
        assert "<UNTRUSTED-CONTENT>" in data["name"]
        assert "</UNTRUSTED-CONTENT>" in data["name"]
        assert "<UNTRUSTED-CONTENT>" in data["description"]
        assert "</UNTRUSTED-CONTENT>" in data["description"]


@patch("axbi.daos.tag.TagDAO.find_by_id")
@pytest.mark.asyncio
async def test_get_tag_info_not_found(mock_find, mcp_server):
    """Test get tag info when tag does not exist."""
    mock_find.return_value = None
    async with Client(mcp_server) as client:
        result = await client.call_tool(
            "get_tag_info", {"request": {"identifier": 999}}
        )
        data = json.loads(result.content[0].text)
        assert data["error_type"] == "not_found"


@patch("axbi.daos.tag.TagDAO.find_by_id")
@pytest.mark.asyncio
async def test_get_tag_info_serializes_type_name(mock_find, mcp_server):
    """Test that the tag type enum is serialized as its name string."""
    tag = create_mock_tag(type_name="owner")
    mock_find.return_value = tag
    async with Client(mcp_server) as client:
        result = await client.call_tool("get_tag_info", {"request": {"identifier": 2}})
        data = json.loads(result.content[0].text)
        assert data["type"] == "owner"


@patch("axbi.daos.tag.TagDAO.list")
@pytest.mark.asyncio
async def test_list_tags_select_columns_filters_response(mock_list, mcp_server):
    """select_columns restricts the fields returned in each tag object."""
    tag = create_mock_tag()
    mock_list.return_value = ([tag], 1)
    async with Client(mcp_server) as client:
        request = ListTagsRequest(page=1, page_size=10, select_columns=["id", "name"])
        result = await client.call_tool("list_tags", {"request": request.model_dump()})
        data = json.loads(result.content[0].text)
        assert data["columns_requested"] == ["id", "name"]
        tag_obj = data["tags"][0]
        assert set(tag_obj.keys()) == {"id", "name"}
        assert "type" not in tag_obj
        assert "description" not in tag_obj
        assert "changed_on" not in tag_obj


@patch("axbi.daos.tag.TagDAO.list")
@pytest.mark.asyncio
async def test_list_tags_default_columns_are_id_name_type(mock_list, mcp_server):
    """Default response includes id, name, type but not description or timestamps."""
    tag = create_mock_tag()
    mock_list.return_value = ([tag], 1)
    async with Client(mcp_server) as client:
        result = await client.call_tool("list_tags", {})
        data = json.loads(result.content[0].text)
        tag_obj = data["tags"][0]
        assert "id" in tag_obj
        assert "name" in tag_obj
        assert "type" in tag_obj
        assert "description" not in tag_obj
        assert "changed_on" not in tag_obj


@patch("axbi.daos.tag.TagDAO.list")
@pytest.mark.asyncio
async def test_list_tags_serves_valid_sidecar_response(
    mock_list,
    mcp_server,
    app_context: None,
):
    """Tag listing can serve valid TypeScript sidecar results."""

    stats_logger = MagicMock()
    current_app.config["STATS_LOGGER"] = stats_logger

    with (
        patch.object(
            list_tags_module,
            "is_feature_enabled",
            side_effect=lambda flag: flag
            in {"TS_MCP_ORCHESTRATION", "TS_TAG_LIST_SERVING"},
        ),
        patch.object(list_tags_module, "AxServicesClient") as client_class,
    ):
        client_class.return_value.list_tags.return_value = AxServicesResponse(
            ok=True,
            status_code=200,
            payload={
                "contractVersion": "tag-list.v1",
                "tags": [
                    {
                        "id": 19,
                        "name": "finance",
                        "type": "custom",
                    }
                ],
                "count": 1,
                "totalCount": 1,
                "page": 1,
                "pageSize": 10,
                "totalPages": 1,
                "hasNext": False,
                "hasPrevious": False,
                "columnsRequested": ["id", "name", "type"],
                "columnsLoaded": ["id", "name", "type"],
                "warnings": [],
            },
        )

        async with Client(mcp_server) as client:
            result = await client.call_tool(
                "list_tags",
                {"request": ListTagsRequest(page=1, page_size=10).model_dump()},
            )

    mock_list.assert_not_called()
    data = json.loads(result.content[0].text)
    assert data["tags"][0]["id"] == 19
    assert "<UNTRUSTED-CONTENT>" in data["tags"][0]["name"]
    assert data["tags"][0]["type"] == "custom"
    stats_logger.incr.assert_any_call(
        "runtime_modernization.mcp_orchestration.list_tags.served_candidate"
    )


@patch("axbi.daos.tag.TagDAO.list")
@pytest.mark.asyncio
async def test_list_tags_serving_falls_back_on_invalid_candidate(
    mock_list,
    mcp_server,
    app_context: None,
):
    """Tag listing falls back to Python when sidecar output is invalid."""

    stats_logger = MagicMock()
    current_app.config["STATS_LOGGER"] = stats_logger
    mock_list.return_value = ([], 0)

    with (
        patch.object(
            list_tags_module,
            "is_feature_enabled",
            side_effect=lambda flag: flag
            in {"TS_MCP_ORCHESTRATION", "TS_TAG_LIST_SERVING"},
        ),
        patch.object(list_tags_module, "AxServicesClient") as client_class,
    ):
        client_class.return_value.list_tags.return_value = AxServicesResponse(
            ok=True,
            status_code=200,
            payload={
                "contractVersion": "tag-list.v1",
                "tags": [{"name": "missing id"}],
            },
        )

        async with Client(mcp_server) as client:
            result = await client.call_tool(
                "list_tags",
                {"request": ListTagsRequest(page=1, page_size=10).model_dump()},
            )

    mock_list.assert_called_once()
    data = json.loads(result.content[0].text)
    assert data["tags"] == []
    stats_logger.incr.assert_any_call(
        "runtime_modernization.mcp_orchestration.list_tags.fallback"
    )

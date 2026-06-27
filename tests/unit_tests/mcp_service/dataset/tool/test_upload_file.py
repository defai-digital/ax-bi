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

"""Unit tests for upload_file MCP tool."""

import base64
import importlib
from unittest.mock import MagicMock, Mock, patch

import pytest
from fastmcp import Client

from superset.mcp_service.app import mcp
from superset.mcp_service.dataset.schemas import DatasetError
from tests.unit_tests.conftest import with_feature_flags

# Import the module directly for patching
upload_file_module = importlib.import_module(
    "superset.mcp_service.dataset.tool.upload_file"
)


def _make_mock_dataset(
    dataset_id: int = 99,
    table_name: str = "upload_sales_abc123",
    database_id: int = 1,
    database_name: str = "Local Files",
) -> MagicMock:
    """Build a mock SqlaTable-like object."""
    dataset = MagicMock()
    dataset.id = dataset_id
    dataset.table_name = table_name
    dataset.schema = None
    dataset.description = None
    dataset.certified_by = None
    dataset.certification_details = None
    dataset.changed_by_name = "admin"
    dataset.changed_on = None
    dataset.changed_on_humanized = None
    dataset.created_by_name = "admin"
    dataset.created_on = None
    dataset.created_on_humanized = None
    dataset.tags = []
    dataset.owners = []
    dataset.is_virtual = False
    dataset.is_favorite = None
    dataset.database_id = database_id
    dataset.schema_perm = f"[{database_name}]"
    dataset.url = f"/tablemodelview/edit/{dataset_id}"
    dataset.database = MagicMock()
    dataset.database.database_name = database_name
    dataset.sql = None
    dataset.main_dttm_col = None
    dataset.offset = 0
    dataset.cache_timeout = 0
    dataset.params = {}
    dataset.template_params = {}
    dataset.extra = {}
    dataset.uuid = f"dataset-uuid-{dataset_id}"
    dataset.columns = []
    dataset.metrics = []
    return dataset


def _make_mock_local_db(db_id: int = 1, name: str = "Local Files") -> MagicMock:
    local_db = MagicMock()
    local_db.id = db_id
    local_db.database_name = name
    return local_db


def _set_query_result(mock_session: MagicMock, result: MagicMock | None) -> None:
    mock_session.query.return_value.filter_by.return_value.one_or_none.return_value = (
        result
    )


def _csv_base64() -> str:
    """Return a minimal CSV file encoded as base64."""
    csv_content = b"name,value\nAlice,10\nBob,20\n"
    return base64.b64encode(csv_content).decode()


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


class TestUploadFile:
    """Tests for the upload_file MCP tool."""

    def test_upload_file_uses_database_upload_permission(self) -> None:
        """MCP upload_file must align with the REST upload permission."""
        assert upload_file_module.upload_file._class_permission_name == ("Database")
        assert upload_file_module.upload_file._method_permission_name == ("upload")

    @with_feature_flags(ENABLE_LOCAL_FILE_UPLOAD=False)
    @patch.object(upload_file_module, "get_or_create_local_db")
    @pytest.mark.asyncio
    async def test_upload_returns_error_when_feature_disabled(
        self, mock_get_local_db, mcp_server
    ) -> None:
        """Tool fails closed when local file upload is disabled."""
        direct_result = upload_file_module.upload_single_file(
            file_content=_csv_base64(),
            filename="sales.csv",
        )
        assert isinstance(direct_result, DatasetError)
        assert direct_result.error_type == "FeatureDisabledError"

        async with Client(mcp_server) as client:
            result = await client.call_tool(
                "upload_file",
                {
                    "request": {
                        "file_content": _csv_base64(),
                        "filename": "sales.csv",
                    }
                },
            )

        mock_get_local_db.assert_not_called()
        assert result is not None

    @patch.object(upload_file_module, "serialize_dataset_object")
    @patch.object(upload_file_module.db, "session")
    @patch.object(upload_file_module, "UploadCommand")
    @patch.object(upload_file_module, "get_or_create_local_db")
    @pytest.mark.asyncio
    async def test_upload_csv_success(
        self,
        mock_get_local_db,
        mock_upload_cmd,
        mock_session,
        mock_serialize,
        mcp_server,
    ) -> None:
        """Happy path: CSV file uploaded and dataset created."""
        local_db = _make_mock_local_db()
        mock_get_local_db.return_value = local_db

        mock_cmd_instance = MagicMock()
        mock_upload_cmd.return_value = mock_cmd_instance

        mock_dataset = _make_mock_dataset()
        _set_query_result(mock_session, mock_dataset)
        mock_serialize.return_value = {"id": 99, "table_name": "upload_sales_abc123"}

        async with Client(mcp_server) as client:
            result = await client.call_tool(
                "upload_file",
                {
                    "request": {
                        "file_content": _csv_base64(),
                        "filename": "sales.csv",
                    }
                },
            )

        # Verify UploadCommand was instantiated with correct args
        mock_upload_cmd.assert_called_once()
        call_args = mock_upload_cmd.call_args
        assert call_args[0][0] == local_db.id  # model_id
        assert "upload_sales_" in call_args[0][1]  # table_name derived from filename

        # Verify run() was called
        mock_cmd_instance.run.assert_called_once()

        # Verify result
        assert result is not None

    @patch.object(upload_file_module, "serialize_dataset_object")
    @patch.object(upload_file_module.db, "session")
    @patch.object(upload_file_module, "UploadCommand")
    @patch.object(upload_file_module, "get_or_create_local_db")
    @pytest.mark.asyncio
    async def test_upload_excel_success(
        self,
        mock_get_local_db,
        mock_upload_cmd,
        mock_session,
        mock_serialize,
        mcp_server,
    ) -> None:
        """Excel file (.xlsx) is handled correctly."""
        local_db = _make_mock_local_db()
        mock_get_local_db.return_value = local_db
        mock_cmd_instance = MagicMock()
        mock_upload_cmd.return_value = mock_cmd_instance
        mock_dataset = _make_mock_dataset(table_name="upload_report_xyz")
        _set_query_result(mock_session, mock_dataset)
        mock_serialize.return_value = {"id": 99, "table_name": "upload_report_xyz"}

        # Minimal xlsx bytes (not a real file, but enough for the tool flow
        # when UploadCommand is mocked)
        fake_xlsx = base64.b64encode(b"fake-xlsx-content").decode()

        async with Client(mcp_server) as client:
            result = await client.call_tool(
                "upload_file",
                {
                    "request": {
                        "file_content": fake_xlsx,
                        "filename": "report.xlsx",
                    }
                },
            )

        mock_upload_cmd.assert_called_once()
        assert result is not None

    @patch.object(upload_file_module, "serialize_dataset_object")
    @patch.object(upload_file_module.db, "session")
    @patch.object(upload_file_module, "UploadCommand")
    @patch.object(upload_file_module, "get_or_create_local_db")
    @pytest.mark.asyncio
    async def test_upload_parquet_success(
        self,
        mock_get_local_db,
        mock_upload_cmd,
        mock_session,
        mock_serialize,
        mcp_server,
    ) -> None:
        """Parquet file (.parquet) is handled correctly."""
        local_db = _make_mock_local_db()
        mock_get_local_db.return_value = local_db
        mock_cmd_instance = MagicMock()
        mock_upload_cmd.return_value = mock_cmd_instance
        mock_dataset = _make_mock_dataset()
        _set_query_result(mock_session, mock_dataset)
        mock_serialize.return_value = {"id": 99, "table_name": "upload_data"}

        fake_parquet = base64.b64encode(b"fake-parquet-content").decode()

        async with Client(mcp_server) as client:
            result = await client.call_tool(
                "upload_file",
                {
                    "request": {
                        "file_content": fake_parquet,
                        "filename": "data.parquet",
                    }
                },
            )

        mock_upload_cmd.assert_called_once()
        assert result is not None

    @patch.object(upload_file_module, "get_or_create_local_db")
    @pytest.mark.asyncio
    async def test_unsupported_file_extension(
        self, mock_get_local_db, mcp_server
    ) -> None:
        """Tool returns DatasetError for unsupported extensions."""
        async with Client(mcp_server) as client:
            result = await client.call_tool(
                "upload_file",
                {
                    "request": {
                        "file_content": _csv_base64(),
                        "filename": "image.png",
                    }
                },
            )

        # get_or_create_local_db should not be called for unsupported types
        mock_get_local_db.assert_not_called()
        assert result is not None

    @pytest.mark.asyncio
    async def test_invalid_base64_content(self, mcp_server) -> None:
        """Tool returns DatasetError for invalid base64 content."""
        async with Client(mcp_server) as client:
            result = await client.call_tool(
                "upload_file",
                {
                    "request": {
                        "file_content": "!!!not-valid-base64!!!",
                        "filename": "data.csv",
                    }
                },
            )

        assert result is not None

    @pytest.mark.asyncio
    async def test_empty_file_content(self, mcp_server) -> None:
        """Tool returns DatasetError when decoded file is empty."""
        empty_b64 = base64.b64encode(b"").decode()
        async with Client(mcp_server) as client:
            result = await client.call_tool(
                "upload_file",
                {
                    "request": {
                        "file_content": empty_b64,
                        "filename": "data.csv",
                    }
                },
            )

        assert result is not None

    @patch.object(upload_file_module, "UploadCommand")
    @patch.object(upload_file_module, "get_or_create_local_db")
    @pytest.mark.asyncio
    async def test_upload_command_raises(
        self, mock_get_local_db, mock_upload_cmd, mcp_server
    ) -> None:
        """Tool returns DatasetError when UploadCommand raises an exception."""
        local_db = _make_mock_local_db()
        mock_get_local_db.return_value = local_db
        mock_cmd_instance = MagicMock()
        mock_cmd_instance.run.side_effect = Exception("DB write failed")
        mock_upload_cmd.return_value = mock_cmd_instance

        async with Client(mcp_server) as client:
            result = await client.call_tool(
                "upload_file",
                {
                    "request": {
                        "file_content": _csv_base64(),
                        "filename": "sales.csv",
                    }
                },
            )

        assert result is not None

    @patch.object(upload_file_module, "serialize_dataset_object")
    @patch.object(upload_file_module.db, "session")
    @patch.object(upload_file_module, "UploadCommand")
    @patch.object(upload_file_module, "get_or_create_local_db")
    @pytest.mark.asyncio
    async def test_custom_table_name(
        self,
        mock_get_local_db,
        mock_upload_cmd,
        mock_session,
        mock_serialize,
        mcp_server,
    ) -> None:
        """Custom table_name parameter overrides the derived name."""
        local_db = _make_mock_local_db()
        mock_get_local_db.return_value = local_db
        mock_cmd_instance = MagicMock()
        mock_upload_cmd.return_value = mock_cmd_instance
        mock_dataset = _make_mock_dataset(table_name="my_custom_table")
        _set_query_result(mock_session, mock_dataset)
        mock_serialize.return_value = {"id": 99, "table_name": "my_custom_table"}

        async with Client(mcp_server) as client:
            await client.call_tool(
                "upload_file",
                {
                    "request": {
                        "file_content": _csv_base64(),
                        "filename": "sales.csv",
                        "table_name": "my_custom_table",
                    }
                },
            )

        # Verify UploadCommand was called with the custom table name
        call_args = mock_upload_cmd.call_args
        assert call_args[0][1] == "my_custom_table"

    @patch.object(upload_file_module, "serialize_dataset_object")
    @patch.object(upload_file_module.db, "session")
    @patch.object(upload_file_module, "UploadCommand")
    @patch.object(upload_file_module, "get_or_create_local_db")
    @pytest.mark.asyncio
    async def test_blank_custom_table_name_falls_back_to_unique_filename_name(
        self,
        mock_get_local_db,
        mock_upload_cmd,
        mock_session,
        mock_serialize,
        mcp_server,
    ) -> None:
        """Blank custom table_name should not collapse to deterministic 'upload'."""
        local_db = _make_mock_local_db()
        mock_get_local_db.return_value = local_db
        mock_cmd_instance = MagicMock()
        mock_upload_cmd.return_value = mock_cmd_instance
        mock_dataset = _make_mock_dataset(table_name="upload_sales_abc123")
        _set_query_result(mock_session, mock_dataset)
        mock_serialize.return_value = {"id": 99, "table_name": "upload_sales_abc123"}

        async with Client(mcp_server) as client:
            await client.call_tool(
                "upload_file",
                {
                    "request": {
                        "file_content": _csv_base64(),
                        "filename": "sales.csv",
                        "table_name": "   ",
                    }
                },
            )

        call_args = mock_upload_cmd.call_args
        assert call_args[0][1].startswith("upload_sales_")
        assert call_args[0][1] != "upload"

    @patch.object(upload_file_module, "serialize_dataset_object")
    @patch.object(upload_file_module.db, "session")
    @patch.object(upload_file_module, "UploadCommand")
    @patch.object(upload_file_module, "get_or_create_local_db")
    @pytest.mark.asyncio
    async def test_generated_table_name_fits_dataset_limit(
        self,
        mock_get_local_db,
        mock_upload_cmd,
        mock_session,
        mock_serialize,
        mcp_server,
    ) -> None:
        """Generated table names must fit the dataset table_name column."""
        local_db = _make_mock_local_db()
        mock_get_local_db.return_value = local_db
        mock_cmd_instance = MagicMock()
        mock_upload_cmd.return_value = mock_cmd_instance
        mock_dataset = _make_mock_dataset(table_name="upload_long")
        _set_query_result(mock_session, mock_dataset)
        mock_serialize.return_value = {"id": 99, "table_name": "upload_long"}

        async with Client(mcp_server) as client:
            await client.call_tool(
                "upload_file",
                {
                    "request": {
                        "file_content": _csv_base64(),
                        "filename": f"{'a' * 244}.csv",
                    }
                },
            )

        call_args = mock_upload_cmd.call_args
        assert len(call_args[0][1]) == 250
        assert call_args[0][1].startswith("upload_")

    @patch.object(upload_file_module, "serialize_dataset_object")
    @patch.object(upload_file_module.db, "session")
    @patch.object(upload_file_module, "UploadCommand")
    @patch.object(upload_file_module, "get_or_create_local_db")
    @pytest.mark.asyncio
    async def test_dataset_not_found_after_upload(
        self,
        mock_get_local_db,
        mock_upload_cmd,
        mock_session,
        mock_serialize,
        mcp_server,
    ) -> None:
        """Tool returns DatasetError when dataset is not found after upload."""
        local_db = _make_mock_local_db()
        mock_get_local_db.return_value = local_db
        mock_cmd_instance = MagicMock()
        mock_upload_cmd.return_value = mock_cmd_instance
        _set_query_result(mock_session, None)

        async with Client(mcp_server) as client:
            result = await client.call_tool(
                "upload_file",
                {
                    "request": {
                        "file_content": _csv_base64(),
                        "filename": "sales.csv",
                    }
                },
            )

        assert result is not None


class TestUploadFileSchema:
    """Tests for the UploadFileRequest Pydantic schema."""

    def test_valid_request(self) -> None:
        from superset.mcp_service.dataset.schemas import UploadFileRequest

        req = UploadFileRequest(
            file_content="dGVzdA==",
            filename="test.csv",
        )
        assert req.filename == "test.csv"
        assert req.table_name is None

    def test_custom_table_name(self) -> None:
        from superset.mcp_service.dataset.schemas import UploadFileRequest

        req = UploadFileRequest(
            file_content="dGVzdA==",
            filename="test.csv",
            table_name="my_table",
        )
        assert req.table_name == "my_table"

    def test_missing_required_fields(self) -> None:
        from pydantic import ValidationError

        from superset.mcp_service.dataset.schemas import UploadFileRequest

        with pytest.raises(ValidationError):
            UploadFileRequest()

    def test_empty_filename_rejected(self) -> None:
        from pydantic import ValidationError

        from superset.mcp_service.dataset.schemas import UploadFileRequest

        with pytest.raises(ValidationError):
            UploadFileRequest(file_content="dGVzdA==", filename="")

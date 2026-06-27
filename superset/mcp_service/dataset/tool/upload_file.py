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

"""
Upload file FastMCP tool

Upload a CSV, Excel, or Parquet file and create a dataset from it with
zero configuration — the local DuckDB database is auto-provisioned on first
use. This is the MCP equivalent of the Upload Data page in the web UI.

The resulting dataset can be fed directly into generate_chart,
create_chart_from_intent, or query_dataset.
"""

import base64
import io
import logging
import os
import re
import uuid
from typing import Any

from fastmcp import Context
from superset_core.mcp.decorators import tool, ToolAnnotations
from werkzeug.datastructures import FileStorage

from superset.commands.database.uploaders.base import (
    BaseDataReader,
    UploadCommand,
    UploadFileType,
)
from superset.commands.database.uploaders.columnar_reader import ColumnarReader
from superset.commands.database.uploaders.csv_reader import CSVReader
from superset.commands.database.uploaders.excel_reader import ExcelReader
from superset.commands.database.uploaders.local_db import get_or_create_local_db
from superset.connectors.sqla.models import SqlaTable
from superset.mcp_service.dataset.schemas import (
    DatasetError,
    DatasetInfo,
    UploadFileRequest,
    serialize_dataset_object,
)
from superset.mcp_service.utils.logging_utils import mcp_event_log_context
from superset import db

logger = logging.getLogger(__name__)

# Map of file extension -> UploadFileType
FILE_TYPE_MAP: dict[str, UploadFileType] = {
    ".csv": UploadFileType.CSV,
    ".tsv": UploadFileType.CSV,
    ".txt": UploadFileType.CSV,
    ".xls": UploadFileType.EXCEL,
    ".xlsx": UploadFileType.EXCEL,
    ".parquet": UploadFileType.COLUMNAR,
}

SUPPORTED_EXTENSIONS = ", ".join(FILE_TYPE_MAP.keys())


def _build_file_storage(file_bytes: bytes, filename: str) -> FileStorage:
    """Wrap raw bytes in a werkzeug FileStorage for UploadCommand."""
    stream = io.BytesIO(file_bytes)
    return FileStorage(stream=stream, filename=filename)


def _sanitize_table_name(raw_name: str) -> str:
    """Derive a safe table name from a filename stem."""
    sanitized = re.sub(r"[^\w]", "_", raw_name).strip("_").lower()
    if not sanitized:
        sanitized = "upload"
    short_id = uuid.uuid4().hex[:6]
    return f"upload_{sanitized}_{short_id}"


def upload_single_file(
    file_content: str,
    filename: str,
    table_name: str | None = None,
) -> DatasetInfo | DatasetError:
    """Upload a single file and return DatasetInfo or DatasetError.

    Shared by both the ``upload_file`` (single) and ``upload_files`` (batch)
    MCP tools. This function is synchronous and meant to be called from an
    async wrapper.
    """
    ext = os.path.splitext(filename)[1].lower()
    file_type = FILE_TYPE_MAP.get(ext)

    if file_type is None:
        return DatasetError.create(
            error=f"Unsupported file extension '{ext}'. Supported: {SUPPORTED_EXTENSIONS}",
            error_type="UnsupportedFileTypeError",
        )

    try:
        file_bytes = base64.b64decode(file_content, validate=True)
    except Exception:
        return DatasetError.create(
            error="file_content is not valid base64-encoded data",
            error_type="InvalidBase64Error",
        )

    if not file_bytes:
        return DatasetError.create(
            error="file_content is empty after decoding",
            error_type="EmptyFileError",
        )

    if table_name:
        derived_name = re.sub(r"[^\w]", "_", table_name).strip("_").lower()
        if not derived_name:
            derived_name = "upload"
    else:
        stem = os.path.splitext(filename)[0]
        derived_name = _sanitize_table_name(stem)

    try:
        file_storage = _build_file_storage(file_bytes, filename)
        local_db = get_or_create_local_db()

        reader_options: dict[str, Any] = {"already_exists": "replace"}
        reader: BaseDataReader
        if file_type == UploadFileType.CSV:
            reader = CSVReader(reader_options)
        elif file_type == UploadFileType.EXCEL:
            reader = ExcelReader(reader_options)
        elif file_type == UploadFileType.COLUMNAR:
            reader = ColumnarReader(reader_options)
        else:
            return DatasetError.create(
                error="Unexpected file type", error_type="UnsupportedFileTypeError"
            )

        with mcp_event_log_context(action="mcp.upload_file.create"):
            UploadCommand(
                local_db.id,
                derived_name,
                file_storage,
                None,
                reader,
            ).run()

        sqla_table: SqlaTable | None = (
            db.session.query(SqlaTable)
            .filter_by(table_name=derived_name, database_id=local_db.id)
            .one_or_none()
        )

        if sqla_table is None:
            return DatasetError.create(
                error="Upload succeeded but dataset could not be found",
                error_type="SerializationError",
            )

        result = serialize_dataset_object(sqla_table)
        if result is None:
            return DatasetError.create(
                error="Dataset was created but could not be serialized",
                error_type="SerializationError",
            )
        return result

    except Exception as exc:
        logger.exception("upload_single_file failed for '%s'", filename)
        return DatasetError.create(
            error="Upload failed: %s" % str(exc),
            error_type="UploadFailedError",
        )


@tool(
    tags=["mutate"],
    class_permission_name="Dataset",
    method_permission_name="write",
    annotations=ToolAnnotations(
        title="Upload file and create dataset",
        readOnlyHint=False,
        destructiveHint=False,
    ),
)
async def upload_file(
    request: UploadFileRequest, ctx: Context
) -> DatasetInfo | DatasetError:
    """Upload a CSV, Excel, or Parquet file and create a dataset with zero config.

    Automatically provisions a local DuckDB database on first use, so no database
    connection needs to be configured beforehand. The file is detected from its
    extension and loaded into a table; a Superset dataset is then registered on
    top of that table.

    Required fields:
    - file_content: Base64-encoded file bytes.
    - filename: Original filename including extension (determines file type and
      derives the table name).

    Optional fields:
    - table_name: Custom table name override. If omitted, a name is derived from
      the filename with a random suffix to avoid collisions.

    Supported file types: .csv, .tsv, .txt (CSV), .xls, .xlsx (Excel), .parquet

    Example workflow:
    1. upload_file(request={"file_content": "<base64>", "filename": "sales.csv"})
       -> returns DatasetInfo with id, table_name, database_id, columns
    2. generate_chart(request={"dataset_id": <id>, ...})
       -> chart built on the uploaded data

    Returns DatasetInfo on success or DatasetError on failure.
    For multiple files, use the upload_files tool instead.
    """
    await ctx.info(
        "Uploading file '%s' (%d bytes)"
        % (request.filename, len(request.file_content))
    )

    result = upload_single_file(
        file_content=request.file_content,
        filename=request.filename,
        table_name=request.table_name,
    )

    if isinstance(result, DatasetError):
        await ctx.error("Upload failed for '%s'" % request.filename)
    else:
        await ctx.info(
            "Dataset created from uploaded file '%s'" % request.filename
        )
    return result

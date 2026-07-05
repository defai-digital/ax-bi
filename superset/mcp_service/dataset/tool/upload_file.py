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

from fastmcp import Context
from superset_core.mcp.decorators import tool, ToolAnnotations
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from superset import db, is_feature_enabled
from superset.commands.database.uploaders.base import (
    BaseDataReader,
    build_type_preserving_upload_options,
    FileMetadata,
    UploadCommand,
    UploadFileType,
)
from superset.commands.database.uploaders.columnar_reader import (
    ColumnarReader,
    ColumnarReaderOptions,
)
from superset.commands.database.uploaders.csv_reader import CSVReader, CSVReaderOptions
from superset.commands.database.uploaders.excel_reader import (
    ExcelReader,
    ExcelReaderOptions,
)
from superset.commands.database.uploaders.local_db import get_or_create_local_db
from superset.commands.database.uploaders.structured_reader import (
    StructuredReader,
    StructuredReaderOptions,
)
from superset.connectors.sqla.models import SqlaTable
from superset.mcp_service.dataset.schemas import (
    DatasetError,
    DatasetInfo,
    serialize_dataset_object,
    UploadFileRequest,
)
from superset.mcp_service.utils.config_utils import get_upload_max_file_size_bytes
from superset.mcp_service.utils.logging_utils import mcp_event_log_context

logger = logging.getLogger(__name__)

# Map of file extension -> UploadFileType
FILE_TYPE_MAP: dict[str, UploadFileType] = {
    ".ann": UploadFileType.STRUCTURED,
    ".arrow": UploadFileType.COLUMNAR,
    ".asc": UploadFileType.STRUCTURED,
    ".avro": UploadFileType.STRUCTURED,
    ".croissant.json": UploadFileType.STRUCTURED,
    ".csv": UploadFileType.CSV,
    ".csv.gz": UploadFileType.CSV,
    ".dat": UploadFileType.STRUCTURED,
    ".db": UploadFileType.STRUCTURED,
    ".dta": UploadFileType.STRUCTURED,
    ".dump": UploadFileType.STRUCTURED,
    ".faiss": UploadFileType.STRUCTURED,
    ".feather": UploadFileType.COLUMNAR,
    ".fwf": UploadFileType.STRUCTURED,
    ".geojson": UploadFileType.STRUCTURED,
    ".gguf": UploadFileType.STRUCTURED,
    ".gpkg": UploadFileType.STRUCTURED,
    ".hnsw": UploadFileType.STRUCTURED,
    ".htm": UploadFileType.STRUCTURED,
    ".html": UploadFileType.STRUCTURED,
    ".index": UploadFileType.STRUCTURED,
    ".ipc": UploadFileType.COLUMNAR,
    ".json": UploadFileType.STRUCTURED,
    ".jsonl": UploadFileType.STRUCTURED,
    ".jsonl.gz": UploadFileType.STRUCTURED,
    ".lance": UploadFileType.STRUCTURED,
    ".lance.zip": UploadFileType.STRUCTURED,
    ".mlflow.zip": UploadFileType.STRUCTURED,
    ".mlruns.zip": UploadFileType.STRUCTURED,
    ".ndjson": UploadFileType.STRUCTURED,
    ".ndjson.gz": UploadFileType.STRUCTURED,
    ".npy": UploadFileType.STRUCTURED,
    ".npz": UploadFileType.STRUCTURED,
    ".ods": UploadFileType.EXCEL,
    ".onnx": UploadFileType.STRUCTURED,
    ".orc": UploadFileType.COLUMNAR,
    ".parquet": UploadFileType.COLUMNAR,
    ".sas7bdat": UploadFileType.STRUCTURED,
    ".sav": UploadFileType.STRUCTURED,
    ".safetensors": UploadFileType.STRUCTURED,
    ".shp.zip": UploadFileType.STRUCTURED,
    ".sql": UploadFileType.STRUCTURED,
    ".sqlite": UploadFileType.STRUCTURED,
    ".sqlite3": UploadFileType.STRUCTURED,
    ".tar": UploadFileType.STRUCTURED,
    ".tar.gz": UploadFileType.STRUCTURED,
    ".tgz": UploadFileType.STRUCTURED,
    ".tsv": UploadFileType.CSV,
    ".tsv.gz": UploadFileType.CSV,
    ".txt": UploadFileType.CSV,
    ".txt.gz": UploadFileType.CSV,
    ".xls": UploadFileType.EXCEL,
    ".xlsx": UploadFileType.EXCEL,
    ".xml": UploadFileType.STRUCTURED,
    ".xpt": UploadFileType.STRUCTURED,
    ".yaml": UploadFileType.STRUCTURED,
    ".yml": UploadFileType.STRUCTURED,
    ".yolo.zip": UploadFileType.STRUCTURED,
    ".zip": UploadFileType.COLUMNAR,
}

SUPPORTED_EXTENSIONS = ", ".join(FILE_TYPE_MAP.keys())
MAX_TABLE_NAME_LENGTH = 63


def _detect_upload_file_type(filename: str) -> tuple[str, UploadFileType] | None:
    """Return the normalized extension and upload type for a filename."""
    lowered = filename.lower()
    if lowered == "mlmodel":
        return ".mlmodel", UploadFileType.STRUCTURED
    for extension in sorted(FILE_TYPE_MAP, key=len, reverse=True):
        if lowered.endswith(extension) and len(lowered) > len(extension):
            return extension, FILE_TYPE_MAP[extension]
    return None


def _safe_upload_filename(filename: str) -> str:
    """Return a path-free filename for downstream upload readers."""
    detected_file_type = _detect_upload_file_type(filename)
    safe_filename = secure_filename(filename)
    if detected_file_type:
        ext, _file_type = detected_file_type
        stem = safe_filename[: -len(ext)].strip("._")
        if not stem or stem.lower() == ext.lstrip(".") or filename.lower() == "mlmodel":
            stem = "upload"
        return f"{stem}{ext}"
    return safe_filename or "upload"


def _decoded_base64_size(file_content: str) -> int | None:
    """Return decoded byte length for padded base64, or None if malformed."""
    stripped = file_content.strip()
    if not stripped or len(stripped) % 4:
        return None
    padding = len(stripped) - len(stripped.rstrip("="))
    if padding > 2:
        return None
    return (len(stripped) // 4) * 3 - padding


def _reject_oversized_base64(file_content: str) -> DatasetError | None:
    """Reject payloads that exceed the configured decoded upload limit."""
    max_size = get_upload_max_file_size_bytes()
    if max_size is None:
        return None
    decoded_size = _decoded_base64_size(file_content)
    if decoded_size is not None and decoded_size > max_size:
        return DatasetError.create(
            error="file_content exceeds the configured upload size limit",
            error_type="FileTooLargeError",
        )
    return None


def _build_file_storage(file_bytes: bytes, filename: str) -> FileStorage:
    """Wrap raw bytes in a werkzeug FileStorage for UploadCommand."""
    stream = io.BytesIO(file_bytes)
    return FileStorage(stream=stream, filename=filename)


def _sanitize_identifier(raw_name: str, default: str = "upload") -> str:
    """Return a database-safe identifier fragment."""
    sanitized = re.sub(r"[^\w]", "_", raw_name).strip("_").lower()
    if not sanitized:
        return default
    return sanitized


def _truncate_identifier_bytes(identifier: str, max_bytes: int) -> str:
    """Truncate an identifier to a byte limit without splitting UTF-8."""
    encoded = identifier.encode("utf-8")
    if len(encoded) <= max_bytes:
        return identifier

    truncated = encoded[:max_bytes]
    while truncated:
        try:
            return truncated.decode("utf-8").rstrip("_") or "upload"
        except UnicodeDecodeError as ex:
            truncated = truncated[: ex.start]
    return "upload"


def _sanitize_table_name(raw_name: str) -> str:
    """Derive a safe, unique physical table name from a filename stem."""
    sanitized = _sanitize_identifier(raw_name)
    short_id = uuid.uuid4().hex[:6]
    suffix = f"_{short_id}"
    prefix = "upload_"
    max_name_bytes = (
        MAX_TABLE_NAME_LENGTH
        - len(prefix.encode("utf-8"))
        - len(suffix.encode("utf-8"))
    )
    return f"{prefix}{_truncate_identifier_bytes(sanitized, max_name_bytes)}{suffix}"


def upload_single_file(  # noqa: C901
    file_content: str,
    filename: str,
    table_name: str | None = None,
    sheet_name: str | None = None,
) -> DatasetInfo | DatasetError:
    """Upload a single file and return DatasetInfo or DatasetError.

    Shared by both the ``upload_file`` (single) and ``upload_files`` (batch)
    MCP tools. This function is synchronous and meant to be called from an
    async wrapper.
    """
    if not is_feature_enabled("ENABLE_LOCAL_FILE_UPLOAD"):
        return DatasetError.create(
            error="Local file upload is disabled",
            error_type="FeatureDisabledError",
        )

    detected_file_type = _detect_upload_file_type(filename)

    if detected_file_type is None:
        return DatasetError.create(
            error=(
                f"Unsupported file extension for '{filename}'. "
                f"Supported: {SUPPORTED_EXTENSIONS}"
            ),
            error_type="UnsupportedFileTypeError",
        )
    _ext, file_type = detected_file_type

    if oversized_error := _reject_oversized_base64(file_content):
        return oversized_error

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
        derived_name = _sanitize_identifier(table_name, default="")
        if not derived_name:
            stem = os.path.splitext(filename)[0]
            derived_name = _sanitize_table_name(stem)
        else:
            derived_name = _truncate_identifier_bytes(
                derived_name,
                MAX_TABLE_NAME_LENGTH,
            )
    else:
        stem = os.path.splitext(filename)[0]
        derived_name = _sanitize_table_name(stem)

    try:
        safe_filename = _safe_upload_filename(filename)
        file_storage = _build_file_storage(file_bytes, safe_filename)
        local_db = get_or_create_local_db()

        reader: BaseDataReader
        excel_metadata: FileMetadata | None = None
        if file_type == UploadFileType.CSV:
            csv_reader_options: CSVReaderOptions = {"already_exists": "replace"}
            csv_metadata = CSVReader(csv_reader_options).file_metadata(file_storage)
            file_storage.seek(0)
            if column_data_types := build_type_preserving_upload_options(csv_metadata):
                csv_reader_options["column_data_types"] = column_data_types
            reader = CSVReader(csv_reader_options)
        elif file_type == UploadFileType.EXCEL:
            excel_reader_options: ExcelReaderOptions = {"already_exists": "replace"}
            if sheet_name:
                excel_reader_options["sheet_name"] = sheet_name
            excel_metadata = ExcelReader(excel_reader_options).file_metadata(
                file_storage
            )
            file_storage.seek(0)
            if column_data_types := build_type_preserving_upload_options(
                excel_metadata
            ):
                excel_reader_options["column_data_types"] = column_data_types
            reader = ExcelReader(excel_reader_options)
        elif file_type == UploadFileType.COLUMNAR:
            columnar_reader_options: ColumnarReaderOptions = {
                "already_exists": "replace"
            }
            reader = ColumnarReader(columnar_reader_options)
        elif file_type == UploadFileType.STRUCTURED:
            structured_reader_options: StructuredReaderOptions = {
                "already_exists": "replace"
            }
            reader = StructuredReader(structured_reader_options)
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

        # For Excel files, include sheet names from metadata in the response
        if file_type == UploadFileType.EXCEL and excel_metadata:
            sheet_names: list[str] = []
            for item in excel_metadata.get("items", []):
                name = item.get("sheet_name")
                if isinstance(name, str) and name:
                    sheet_names.append(name)
            if sheet_names and hasattr(result, "model_dump"):
                result.sheet_names = sheet_names
            elif sheet_names and isinstance(result, dict):
                result["sheet_names"] = sheet_names

        return result

    except Exception as exc:
        logger.exception("upload_single_file failed for '%s'", filename)
        return DatasetError.create(
            error=f"Upload failed: {str(exc)}",
            error_type="UploadFailedError",
        )


@tool(
    tags=["mutate"],
    class_permission_name="Database",
    method_permission_name="upload",
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
        f"Uploading file '{request.filename}' ({len(request.file_content)} bytes)"
    )

    result = upload_single_file(
        file_content=request.file_content,
        filename=request.filename,
        table_name=request.table_name,
        sheet_name=request.sheet_name,
    )

    if isinstance(result, DatasetError):
        await ctx.error(f"Upload failed for '{request.filename}'")
    else:
        await ctx.info(f"Dataset created from uploaded file '{request.filename}'")
    return result

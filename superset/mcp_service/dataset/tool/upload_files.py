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
Upload files (batch) FastMCP tool

Upload multiple CSV, Excel, or Parquet files in a single call and create
a dataset for each. Each file is processed independently — a failure in one
file does not block the others.

This is the batch counterpart to the single-file ``upload_file`` tool.
"""

import logging

from fastmcp import Context
from superset_core.mcp.decorators import tool, ToolAnnotations

from superset.mcp_service.common.error_schemas import MCPResourceError
from superset.mcp_service.dataset.schemas import (
    DatasetError,
    DatasetInfo,
    FileUploadResult,
    UploadFilesRequest,
    UploadFilesResponse,
)
from superset.mcp_service.dataset.tool.upload_file import upload_single_file

logger = logging.getLogger(__name__)


@tool(
    tags=["mutate"],
    class_permission_name="Dataset",
    method_permission_name="write",
    annotations=ToolAnnotations(
        title="Upload multiple files and create datasets",
        readOnlyHint=False,
        destructiveHint=False,
    ),
)
async def upload_files(
    request: UploadFilesRequest, ctx: Context
) -> UploadFilesResponse | MCPResourceError:
    """Upload multiple CSV/Excel/Parquet files and create a dataset for each.

    Each file is processed independently — a failure in one does not block the
    others. A local DuckDB database is auto-provisioned on first use.

    Use this tool when the user provides multiple files at once. For a single
    file, prefer ``upload_file`` which has a simpler request/response shape.

    Required fields:
    - files: List of file objects. Each must include:
        - file_content: Base64-encoded file bytes
        - filename: Original filename including extension

    Optional per-file fields:
    - table_name: Custom table name override

    Limits:
    - Maximum 10 files per batch
    - Supported types: .csv, .tsv, .txt, .xls, .xlsx, .parquet

    Example:
    ```json
    {
        "files": [
            {"file_content": "<base64>", "filename": "sales.csv"},
            {"file_content": "<base64>", "filename": "inventory.xlsx"}
        ]
    }
    ```

    Returns UploadFilesResponse with per-file results, total/succeeded/failed counts.
    Each successful file result includes a full DatasetInfo that can be fed into
    generate_chart, query_dataset, or compose_dashboard.
    """
    await ctx.info(
        "Batch uploading %d file(s)" % len(request.files)
    )

    results: list[FileUploadResult] = []
    succeeded = 0
    failed = 0

    for file_item in request.files:
        result = upload_single_file(
            file_content=file_item.file_content,
            filename=file_item.filename,
            table_name=file_item.table_name,
        )

        if isinstance(result, DatasetError):
            failed += 1
            results.append(
                FileUploadResult(
                    filename=file_item.filename,
                    success=False,
                    dataset=None,
                    error=result.error,
                )
            )
            await ctx.warning(
                "Failed to upload '%s': %s"
                % (file_item.filename, result.error)
            )
        elif isinstance(result, DatasetInfo):
            succeeded += 1
            results.append(
                FileUploadResult(
                    filename=file_item.filename,
                    success=True,
                    dataset=result,
                    error=None,
                )
            )
            await ctx.info(
                "Uploaded '%s' -> dataset id=%s"
                % (file_item.filename, result.id)
            )
        else:
            # Unexpected response type — treat as failure
            failed += 1
            results.append(
                FileUploadResult(
                    filename=file_item.filename,
                    success=False,
                    dataset=None,
                    error="Unexpected response from upload",
                )
            )

    await ctx.info(
        "Batch upload complete: %d succeeded, %d failed"
        % (succeeded, failed)
    )

    return UploadFilesResponse(
        results=results,
        total=len(request.files),
        succeeded=succeeded,
        failed=failed,
    )

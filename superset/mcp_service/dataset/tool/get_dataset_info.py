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
Get dataset info FastMCP tool

This module contains the FastMCP tool for getting detailed information
about a specific dataset.
"""

import logging
from typing import Any

from fastmcp import Context
from sqlalchemy.orm import joinedload, subqueryload
from superset_core.mcp.decorators import tool, ToolAnnotations

from superset.mcp_service.dataset.schemas import (
    DatasetError,
    DatasetInfo,
    GetDatasetInfoRequest,
    serialize_dataset_object,
)
from superset.mcp_service.mcp_core import ModelGetInfoCore
from superset.mcp_service.privacy import (
    DATA_MODEL_METADATA_ERROR_TYPE,
    requires_data_model_metadata_access,
    user_can_view_data_model_metadata,
)
from superset.mcp_service.utils.logging_utils import mcp_event_log_context
from superset.mcp_service.utils.response_utils import dump_model_with_select_columns

logger = logging.getLogger(__name__)


@tool(
    tags=["discovery"],
    class_permission_name="Dataset",
    annotations=ToolAnnotations(
        title="Get dataset info",
        readOnlyHint=True,
        destructiveHint=False,
    ),
)
@requires_data_model_metadata_access
async def get_dataset_info(
    request: GetDatasetInfoRequest, ctx: Context
) -> dict[str, Any] | DatasetError:
    """Get dataset metadata by ID or UUID.

    Returns columns, metrics, and schema details.

    IMPORTANT FOR LLM CLIENTS:
    - Use numeric ID (e.g., 123) or UUID string (e.g., "a1b2c3d4-...")
    - DO NOT use schema.table_name format (e.g., "public.customers")
    - To find a dataset ID, use the list_datasets tool first

    IMPORTANT - Saved Metrics vs Columns:
    The response includes both 'columns' (raw database columns) and 'metrics'
    (pre-defined saved metrics). When building chart configs, use saved_metric=true
    for metrics — do not treat them as columns. See instructions for details.

    Example usage:
    ```json
    {
        "identifier": 123
    }
    ```

    Or with UUID:
    ```json
    {
        "identifier": "a1b2c3d4-5678-90ab-cdef-1234567890ab"
    }
    ```
    """
    await ctx.info(f"Retrieving dataset information: identifier={request.identifier}")
    await ctx.debug(
        f"Metadata cache settings: use_cache={request.use_cache} "
        f"refresh_metadata={request.refresh_metadata} "
        f"force_refresh={request.force_refresh}"
    )

    # The decorator hides this tool from search; this check enforces direct calls.
    if not user_can_view_data_model_metadata():
        await ctx.warning("Dataset metadata lookup blocked by privacy controls")
        return DatasetError.create(
            error="You don't have permission to access dataset details for your role.",
            error_type=DATA_MODEL_METADATA_ERROR_TYPE,
        )

    try:
        from superset.connectors.sqla.models import SqlaTable
        from superset.daos.dataset import DatasetDAO

        # Eager load columns, metrics, and database to avoid N+1 queries.
        # Without this, serialize_dataset_object triggers lazy loads for each
        # relationship, which can time out on datasets with many columns.
        eager_options = [
            subqueryload(SqlaTable.columns),
            subqueryload(SqlaTable.metrics),
            joinedload(SqlaTable.database),
        ]

        with mcp_event_log_context(action="mcp.get_dataset_info.lookup"):
            tool = ModelGetInfoCore(
                dao_class=DatasetDAO,
                output_schema=DatasetInfo,
                error_schema=DatasetError,
                serializer=serialize_dataset_object,
                supports_slug=False,  # Datasets don't have slugs
                logger=logger,
                query_options=eager_options,
            )

            result = tool.run_tool(request.identifier)

        if isinstance(result, DatasetInfo):
            await ctx.info(
                "Dataset information retrieved successfully: "
                f"dataset_id={result.id}, table_name={result.table_name}, "
                f"columns_count={len(result.columns) if result.columns else 0}, "
                f"metrics_count={len(result.metrics) if result.metrics else 0}"
            )
            await ctx.debug(
                f"Filtering response: select_columns={request.select_columns}, "
                f"column_fields={request.column_fields}"
            )
            with mcp_event_log_context(action="mcp.get_dataset_info.serialization"):
                return dump_model_with_select_columns(
                    result,
                    request.select_columns,
                    by_alias=True,
                    extra_context={"column_fields": request.column_fields},
                )
        else:
            await ctx.warning(
                f"Dataset retrieval failed: error_type={result.error_type}, "
                f"error={result.error}"
            )

        return result

    except Exception as e:
        await ctx.error(
            "Dataset information retrieval failed: "
            f"identifier={request.identifier}, error={str(e)}, "
            f"error_type={type(e).__name__}"
        )
        return DatasetError.create(
            error=f"Failed to get dataset info: {str(e)}",
            error_type="InternalError",
        )

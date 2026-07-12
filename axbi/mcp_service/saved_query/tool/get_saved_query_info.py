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
Get saved query info FastMCP tool

This module contains the FastMCP tool for getting detailed information
about a specific saved SQL query.
"""

import logging

from axbi_core.mcp.decorators import tool, ToolAnnotations
from fastmcp import Context

from axbi.mcp_service.mcp_core import ModelGetInfoCore
from axbi.mcp_service.saved_query.schemas import (
    GetSavedQueryInfoRequest,
    SavedQueryError,
    SavedQueryInfo,
    serialize_saved_query_object,
)
from axbi.mcp_service.utils.logging_utils import mcp_event_log_context

logger = logging.getLogger(__name__)


@tool(
    tags=["discovery"],
    class_permission_name="SavedQuery",
    annotations=ToolAnnotations(
        title="Get saved query info",
        readOnlyHint=True,
        destructiveHint=False,
    ),
)
async def get_saved_query_info(
    request: GetSavedQueryInfoRequest, ctx: Context
) -> SavedQueryInfo | SavedQueryError:
    """Get saved query details by ID or UUID.

    Returns the full saved query including SQL text, label, database,
    schema, and timestamps.

    IMPORTANT FOR LLM CLIENTS:
    - Use numeric ID (e.g., 42) or UUID string (e.g., "a1b2c3d4-...")
    - To find a saved query ID, use the list_saved_queries tool first

    Example usage:
    ```json
    {
        "identifier": 42
    }
    ```

    Or with UUID:
    ```json
    {
        "identifier": "a1b2c3d4-5678-90ab-cdef-1234567890ab"
    }
    ```
    """
    await ctx.info(
        f"Retrieving saved query information: identifier={request.identifier}"
    )

    try:
        from axbi.daos.query import SavedQueryDAO

        with mcp_event_log_context(action="mcp.get_saved_query_info.lookup"):
            get_tool = ModelGetInfoCore(
                dao_class=SavedQueryDAO,
                output_schema=SavedQueryInfo,
                error_schema=SavedQueryError,
                serializer=serialize_saved_query_object,
                supports_slug=False,
                logger=logger,
            )

            result = get_tool.run_tool(request.identifier)

        if isinstance(result, SavedQueryInfo):
            await ctx.info(
                "Saved query information retrieved successfully: "
                f"saved_query_id={result.id}, label={result.label}, "
                f"db_id={result.db_id}"
            )
        else:
            await ctx.warning(
                f"Saved query retrieval failed: error_type={result.error_type}, "
                f"error={result.error}"
            )

        return result

    except Exception as e:
        await ctx.error(
            "Saved query information retrieval failed: "
            f"identifier={request.identifier}, error={str(e)}, "
            f"error_type={type(e).__name__}"
        )
        return SavedQueryError.create(
            error="Failed to get saved query info",
            error_type="InternalError",
        )

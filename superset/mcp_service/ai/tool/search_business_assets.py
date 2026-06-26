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
"""MCP tool: search_business_assets

Searches across datasets, charts, and dashboards using text matching.
Returns ranked results with relevance scores and reasons.
"""

from __future__ import annotations

import logging
from typing import Any

from superset_core.mcp.decorators import tool, ToolAnnotations

try:
    from fastmcp import Context
except ModuleNotFoundError:
    Context = Any  # type: ignore[misc, assignment]

from superset.mcp_service.ai.asset_search import search_assets
from superset.mcp_service.ai.schemas import AssetSearchRequest, AssetSearchResponse
from superset.mcp_service.privacy import (
    requires_data_model_metadata_access,
    user_can_view_data_model_metadata,
)
from superset.mcp_service.utils.logging_utils import mcp_event_log_context

logger = logging.getLogger(__name__)


@tool(
    tags=["discovery", "ai"],
    class_permission_name="Dataset",
    annotations=ToolAnnotations(
        title="Search business assets",
        readOnlyHint=True,
        destructiveHint=False,
    ),
)
@requires_data_model_metadata_access
async def search_business_assets(
    request: AssetSearchRequest, ctx: Context
) -> dict[str, Any]:
    """Search for datasets, charts, and dashboards by natural language query.

    Returns ranked results with relevance scores and reasons.
    Uses existing RBAC filters — only accessible assets are returned.

    IMPORTANT FOR LLM CLIENTS:
    - Use this tool to discover assets before building charts or dashboards
    - Results include datasets, charts, and dashboards by default
    - Filter by asset_types to narrow the search scope
    - Set include_certified_only=true for production-quality assets

    Example usage:
    ```json
    {
        "query": "sales dashboard by region",
        "asset_types": ["dataset", "dashboard"],
        "include_certified_only": false,
        "limit": 10
    }
    ```
    """
    await ctx.info(
        "Searching business assets: query='%s', types=%s, certified_only=%s, limit=%d"
        % (
            request.query,
            request.asset_types,
            request.include_certified_only,
            request.limit,
        )
    )

    # Privacy check
    if not user_can_view_data_model_metadata():
        await ctx.warning("Asset search blocked by privacy controls")
        return AssetSearchResponse(
            assets=[],
            warnings=["You don't have permission to search business assets."],
        ).model_dump()

    try:
        with mcp_event_log_context(action="mcp.search_business_assets.search"):
            results = search_assets(
                query=request.query,
                asset_types=request.asset_types or None,
                include_certified_only=request.include_certified_only,
                limit=request.limit,
            )

        await ctx.info("Asset search completed: found %d results" % len(results))

        response = AssetSearchResponse(assets=results, warnings=[])
        return response.model_dump()

    except Exception as e:
        await ctx.error(
            "Asset search failed: query='%s', error=%s, error_type=%s"
            % (request.query, str(e), type(e).__name__)
        )
        return AssetSearchResponse(
            assets=[],
            warnings=[f"Search failed: {str(e)}"],
        ).model_dump()

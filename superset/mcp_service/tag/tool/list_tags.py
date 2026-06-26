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
List tags FastMCP tool

This module contains the FastMCP tool for listing tags with filtering,
search, and pagination support.
"""

import logging

from fastmcp import Context
from superset_core.mcp.decorators import tool, ToolAnnotations

from superset.mcp_service.mcp_core import (
    ModelListCore,
    request_or_default,
    to_zero_based_page,
)
from superset.mcp_service.tag.schemas import (
    ListTagsRequest,
    serialize_tag_object,
    TagError,
    TagFilter,
    TagInfo,
    TagList,
)
from superset.mcp_service.utils.logging_utils import mcp_event_log_context
from superset.mcp_service.utils.response_utils import finalize_list_response

logger = logging.getLogger(__name__)

DEFAULT_TAG_COLUMNS = ["id", "name", "type"]
SORTABLE_TAG_COLUMNS = ["id", "name", "changed_on", "created_on"]
ALL_TAG_COLUMNS = [
    "id",
    "name",
    "type",
    "description",
    "changed_on",
    "changed_on_humanized",
    "created_on",
    "created_on_humanized",
]

_DEFAULT_LIST_TAGS_REQUEST = ListTagsRequest()


@tool(
    tags=["core"],
    class_permission_name="Tag",
    annotations=ToolAnnotations(
        title="List tags",
        readOnlyHint=True,
        destructiveHint=False,
    ),
)
async def list_tags(
    request: ListTagsRequest | None = None,
    ctx: Context | None = None,
) -> TagList | TagError:
    """List tags with filtering and search.

    Returns tag metadata including name, type, and description.

    Tag types: custom (user-created), type (implicit by object type),
    owner (implicit by ownership), favorited_by (implicit by favorites).

    Sortable columns for order_column: id, name, changed_on, created_on
    """
    if ctx is None:
        raise RuntimeError("FastMCP context is required for list_tags")

    request = request_or_default(request, _DEFAULT_LIST_TAGS_REQUEST)

    await ctx.info(
        "Listing tags: page=%s, page_size=%s, search=%s"
        % (request.page, request.page_size, request.search)
    )
    await ctx.debug(
        "Tag listing parameters: filters=%s, order_column=%s, "
        "order_direction=%s, select_columns=%s"
        % (
            request.filters,
            request.order_column,
            request.order_direction,
            request.select_columns,
        )
    )

    try:
        from superset.daos.tag import TagDAO

        def _serialize_tag(obj: object, cols: list[str] | None) -> TagInfo | None:
            return serialize_tag_object(obj)

        list_tool = ModelListCore(
            dao_class=TagDAO,
            output_schema=TagInfo,
            item_serializer=_serialize_tag,
            filter_type=TagFilter,
            default_columns=DEFAULT_TAG_COLUMNS,
            search_columns=["name"],
            list_field_name="tags",
            output_list_schema=TagList,
            all_columns=ALL_TAG_COLUMNS,
            sortable_columns=SORTABLE_TAG_COLUMNS,
            logger=logger,
        )

        with mcp_event_log_context(action="mcp.list_tags.query"):
            result = list_tool.run_tool(
                filters=request.filters,
                search=request.search,
                select_columns=request.select_columns,
                order_column=request.order_column,
                order_direction=request.order_direction,
                page=to_zero_based_page(request.page),
                page_size=request.page_size,
            )

        return await finalize_list_response(result, "tags", "Tags", ctx)

    except Exception as e:
        await ctx.error(
            "Tag listing failed: page=%s, page_size=%s, error=%s, error_type=%s"
            % (request.page, request.page_size, str(e), type(e).__name__)
        )
        raise

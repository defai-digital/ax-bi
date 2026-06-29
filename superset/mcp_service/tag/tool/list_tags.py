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
from typing import Any

from fastmcp import Context
from flask import current_app
from superset_core.mcp.decorators import tool, ToolAnnotations

from superset import is_feature_enabled
from superset.mcp_service.mcp_core import (
    ModelListCore,
    request_or_default,
    to_zero_based_page,
)
from superset.mcp_service.system.schemas import PaginationInfo
from superset.mcp_service.tag.schemas import (
    ListTagsRequest,
    serialize_tag_object,
    TagError,
    TagFilter,
    TagInfo,
    TagList,
)
from superset.mcp_service.utils import sanitize_for_llm_context
from superset.mcp_service.utils.logging_utils import mcp_event_log_context
from superset.mcp_service.utils.response_utils import (
    dump_model_with_select_columns,
    finalize_list_response,
)
from superset.runtime_modernization.ax_services import (
    AxServicesClient,
    AxServicesConfig,
    AxServicesResponse,
)
from superset.runtime_modernization.measurement import measure_runtime_candidate
from superset.runtime_modernization.shadow import (
    execute_with_shadow,
    ShadowMismatchReport,
)

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
_TAG_LIST_CONTRACT_VERSION = "tag-list.v1"


def _tag_list_request_payload(request: ListTagsRequest) -> dict[str, Any]:
    """Build an ax-services tag list request payload."""

    return {
        "contractVersion": _TAG_LIST_CONTRACT_VERSION,
        "filters": [filter_.model_dump(mode="json") for filter_ in request.filters],
        "selectColumns": list(request.select_columns),
        "search": request.search,
        "orderColumn": request.order_column,
        "orderDirection": request.order_direction,
        "page": request.page,
        "pageSize": request.page_size,
    }


def _ax_services_tag_list_candidate(request: ListTagsRequest) -> AxServicesResponse:
    """Run the TypeScript sidecar tag list candidate."""

    client = AxServicesClient(AxServicesConfig.from_mapping(current_app.config))
    return client.list_tags(_tag_list_request_payload(request))


def _optional_string(value: Any) -> str | None:
    """Return a string value or None."""

    return value if isinstance(value, str) else None


def _tag_info_from_ax_services(payload: dict[str, Any]) -> TagInfo | None:
    """Convert one valid ax-services tag item to the MCP tag schema."""

    tag_id = payload.get("id")
    if not isinstance(tag_id, int):
        return None

    tag = TagInfo(
        id=tag_id,
        name=_optional_string(payload.get("name")),
        type=_optional_string(payload.get("type")),
        description=_optional_string(payload.get("description")),
        changed_on=_optional_string(payload.get("changedOn")),
        changed_on_humanized=_optional_string(payload.get("changedOnHumanized")),
        created_on=_optional_string(payload.get("createdOn")),
        created_on_humanized=_optional_string(payload.get("createdOnHumanized")),
    )
    tag_payload = tag.model_dump(mode="python")
    for field_name in ("name", "description"):
        tag_payload[field_name] = sanitize_for_llm_context(
            tag_payload.get(field_name),
            field_path=(field_name,),
        )
    return TagInfo(**tag_payload)


def _is_string_list(value: Any) -> bool:
    """Return whether a value is a list of strings."""

    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def _tag_list_from_ax_services_response(
    response: AxServicesResponse,
) -> dict[str, Any] | None:
    """Convert a valid ax-services tag list response to the MCP schema."""

    payload = response.payload or {}
    if not response.ok or payload.get("contractVersion") != _TAG_LIST_CONTRACT_VERSION:
        return None

    raw_tags = payload.get("tags")
    if not isinstance(raw_tags, list):
        return None

    tags = []
    for raw_tag in raw_tags:
        if not isinstance(raw_tag, dict):
            return None
        tag = _tag_info_from_ax_services(raw_tag)
        if tag is None:
            return None
        tags.append(tag)

    count = payload.get("count")
    total_count = payload.get("totalCount")
    page = payload.get("page")
    page_size = payload.get("pageSize")
    total_pages = payload.get("totalPages")
    has_next = payload.get("hasNext")
    has_previous = payload.get("hasPrevious")
    columns_requested = payload.get("columnsRequested")
    columns_loaded = payload.get("columnsLoaded")
    if (
        not isinstance(count, int)
        or not isinstance(total_count, int)
        or not isinstance(page, int)
        or not isinstance(page_size, int)
        or not isinstance(total_pages, int)
        or not isinstance(has_next, bool)
        or not isinstance(has_previous, bool)
        or not _is_string_list(columns_requested)
        or not _is_string_list(columns_loaded)
    ):
        return None

    tag_list = TagList(
        tags=tags,
        count=count,
        total_count=total_count,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        has_next=has_next,
        has_previous=has_previous,
        columns_requested=columns_requested,
        columns_loaded=columns_loaded,
        columns_available=[],
        sortable_columns=SORTABLE_TAG_COLUMNS,
        filters_applied=[],
        pagination=PaginationInfo(
            page=page,
            page_size=page_size,
            total_count=total_count,
            total_pages=total_pages,
            has_next=has_next,
            has_previous=has_previous,
        ),
    )
    return dump_model_with_select_columns(tag_list, columns_requested)


def _tag_keys_from_mcp_response(response: dict[str, Any]) -> list[int]:
    """Return tag IDs from an MCP tag list response."""

    tags = response.get("tags")
    if not isinstance(tags, list):
        return []
    return [
        tag["id"]
        for tag in tags
        if isinstance(tag, dict) and isinstance(tag.get("id"), int)
    ]


def _tag_keys_from_ax_services_response(response: AxServicesResponse) -> list[int]:
    """Return tag IDs from an ax-services tag list response."""

    payload = response.payload or {}
    tags = payload.get("tags") if isinstance(payload, dict) else None
    if not isinstance(tags, list):
        return []
    return [
        tag["id"]
        for tag in tags
        if isinstance(tag, dict) and isinstance(tag.get("id"), int)
    ]


def _tag_list_shadow_matches(
    authoritative: dict[str, Any],
    candidate: AxServicesResponse,
) -> bool:
    """Compare Python and TypeScript tag list outputs by ID order."""

    return candidate.ok and _tag_keys_from_mcp_response(
        authoritative
    ) == _tag_keys_from_ax_services_response(candidate)


def _summarize_tag_list_response(response: dict[str, Any]) -> dict[str, object]:
    """Summarize Python tag list results for shadow mismatch reports."""

    return {
        "count": len(_tag_keys_from_mcp_response(response)),
        "ids": _tag_keys_from_mcp_response(response),
    }


def _summarize_ax_services_tag_list_response(
    response: AxServicesResponse,
) -> dict[str, object]:
    """Summarize ax-services tag list results for shadow mismatch reports."""

    payload = response.payload or {}
    return {
        "ok": response.ok,
        "status_code": response.status_code,
        "contract_version": payload.get("contractVersion")
        if isinstance(payload, dict)
        else None,
        "count": len(_tag_keys_from_ax_services_response(response)),
        "ids": _tag_keys_from_ax_services_response(response),
        "error": response.error,
    }


def _report_tag_list_shadow_mismatch(report: ShadowMismatchReport) -> None:
    """Log a compact tag list shadow mismatch report."""

    logger.warning(
        "Runtime modernization tag list shadow mismatch: %s",
        report.to_dict(),
    )


def _tag_list_shadow_enabled() -> bool:
    """Return whether tag listing should shadow through ax-services."""

    return is_feature_enabled("RUNTIME_SHADOW_EXECUTION") and is_feature_enabled(
        "TS_MCP_ORCHESTRATION"
    )


def _tag_list_serving_enabled() -> bool:
    """Return whether tag listing should be served through ax-services."""

    return is_feature_enabled("TS_MCP_ORCHESTRATION") and is_feature_enabled(
        "TS_TAG_LIST_SERVING"
    )


def _record_tag_list_metric(metric: str) -> None:
    """Record a tag-list migration metric."""

    current_app.config["STATS_LOGGER"].incr(
        f"runtime_modernization.mcp_orchestration.list_tags.{metric}"
    )


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
) -> TagList | TagError | dict[str, Any]:
    """List tags with filtering and search.

    Returns tag metadata including name, type, and description.

    Tag types: custom (user-created), type (implicit by object type),
    owner (implicit by ownership), favorited_by (implicit by favorites).

    Sortable columns for order_column: id, name, changed_on, created_on
    """
    if ctx is None:
        raise RuntimeError("FastMCP context is required for list_tags")

    request = request_or_default(request, _DEFAULT_LIST_TAGS_REQUEST)

    with measure_runtime_candidate(
        "mcp_orchestration",
        "list_tags",
        current_app.config["STATS_LOGGER"],
    ):
        if _tag_list_serving_enabled():
            candidate_response = _ax_services_tag_list_candidate(request)
            candidate_tags = _tag_list_from_ax_services_response(candidate_response)
            if candidate_tags is not None:
                _record_tag_list_metric("served_candidate")
                return candidate_tags

            _record_tag_list_metric("fallback")
            return await _list_tags_python(request, ctx)

        python_response = await _list_tags_python(request, ctx)
        return execute_with_shadow(
            area="mcp_orchestration",
            operation="list_tags",
            authoritative=lambda: python_response,
            candidate=lambda: _ax_services_tag_list_candidate(request),
            compare=_tag_list_shadow_matches,
            stats_logger=current_app.config["STATS_LOGGER"],
            shadow_enabled=_tag_list_shadow_enabled(),
            report_mismatch=_report_tag_list_shadow_mismatch,
            summarize_authoritative=_summarize_tag_list_response,
            summarize_candidate=_summarize_ax_services_tag_list_response,
        )


async def _list_tags_python(
    request: ListTagsRequest,
    ctx: Context,
) -> dict[str, Any]:
    """Run the authoritative Python tag list path."""

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

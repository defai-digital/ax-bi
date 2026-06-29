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

"""List annotations within a layer FastMCP tool."""

import logging
from typing import Any

from fastmcp import Context
from flask import current_app
from superset_core.mcp.decorators import tool, ToolAnnotations

from superset import is_feature_enabled
from superset.daos.base import ColumnOperator, ColumnOperatorEnum
from superset.mcp_service.annotation_layer.schemas import (
    AnnotationFilter,
    AnnotationInfo,
    AnnotationLayerError,
    AnnotationList,
    DEFAULT_ANNOTATION_COLUMNS,
    ListLayerAnnotationsRequest,
    serialize_annotation,
)
from superset.mcp_service.mcp_core import ModelListCore, to_zero_based_page
from superset.mcp_service.system.schemas import PaginationInfo
from superset.mcp_service.utils import sanitize_for_llm_context
from superset.mcp_service.utils.logging_utils import mcp_event_log_context
from superset.mcp_service.utils.response_utils import dump_model_with_select_columns
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
from superset.utils import json as json_utils

logger = logging.getLogger(__name__)

_ALL_ANNOTATION_COLUMNS = [
    "id",
    "short_descr",
    "long_descr",
    "start_dttm",
    "end_dttm",
    "json_metadata",
    "layer_id",
]
_SORTABLE_ANNOTATION_COLUMNS = ["id", "short_descr", "start_dttm", "end_dttm"]
_ANNOTATION_LIST_CONTRACT_VERSION = "annotation-list.v1"


def _annotation_list_request_payload(
    request: ListLayerAnnotationsRequest,
) -> dict[str, Any]:
    """Build an ax-services annotation list request payload."""

    return {
        "contractVersion": _ANNOTATION_LIST_CONTRACT_VERSION,
        "layerId": request.layer_id,
        "filters": [filter_.model_dump(mode="json") for filter_ in request.filters],
        "selectColumns": list(request.select_columns),
        "search": request.search,
        "orderColumn": request.order_column,
        "orderDirection": request.order_direction,
        "page": request.page,
        "pageSize": request.page_size,
    }


def _ax_services_annotation_list_candidate(
    request: ListLayerAnnotationsRequest,
) -> AxServicesResponse:
    """Run the TypeScript sidecar annotation list candidate."""

    client = AxServicesClient(AxServicesConfig.from_mapping(current_app.config))
    return client.list_annotations(_annotation_list_request_payload(request))


def _optional_string(value: Any) -> str | None:
    """Return a string value or None."""

    return value if isinstance(value, str) else None


def _sanitize_annotation_json_metadata(raw: Any) -> str | None:
    """Canonicalize and sanitize annotation metadata before LLM exposure."""

    if raw is None:
        return None
    if isinstance(raw, str):
        try:
            canonical: str = json_utils.dumps(json_utils.loads(raw))
        except (TypeError, ValueError):
            canonical = raw
    else:
        try:
            canonical = json_utils.dumps(raw)
        except (TypeError, ValueError):
            canonical = str(raw)
    return sanitize_for_llm_context(
        canonical,
        field_path=("json_metadata",),
        excluded_field_names=frozenset(),
    )


def _annotation_info_from_ax_services(
    payload: dict[str, Any],
) -> AnnotationInfo | None:
    """Convert one valid ax-services annotation item to the MCP schema."""

    annotation_id = payload.get("id")
    if not isinstance(annotation_id, int):
        return None

    layer_id = payload.get("layerId")
    annotation = AnnotationInfo(
        id=annotation_id,
        short_descr=sanitize_for_llm_context(
            _optional_string(payload.get("shortDescr")),
            field_path=("short_descr",),
        ),
        long_descr=sanitize_for_llm_context(
            _optional_string(payload.get("longDescr")),
            field_path=("long_descr",),
        ),
        start_dttm=_optional_string(payload.get("startDttm")),
        end_dttm=_optional_string(payload.get("endDttm")),
        json_metadata=_sanitize_annotation_json_metadata(payload.get("jsonMetadata")),
        layer_id=layer_id if isinstance(layer_id, int) else None,
    )
    return annotation


def _is_string_list(value: Any) -> bool:
    """Return whether a value is a list of strings."""

    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def _annotation_list_from_ax_services_response(
    response: AxServicesResponse,
) -> dict[str, Any] | None:
    """Convert a valid ax-services annotation list response to the MCP schema."""

    payload = response.payload or {}
    if (
        not response.ok
        or payload.get("contractVersion") != _ANNOTATION_LIST_CONTRACT_VERSION
    ):
        return None
    if payload.get("warnings"):
        return None

    raw_annotations = payload.get("annotations")
    if not isinstance(raw_annotations, list):
        return None

    annotations = []
    for raw_annotation in raw_annotations:
        if not isinstance(raw_annotation, dict):
            return None
        annotation = _annotation_info_from_ax_services(raw_annotation)
        if annotation is None:
            return None
        annotations.append(annotation)

    count = payload.get("count")
    total_count = payload.get("totalCount")
    page = payload.get("page")
    page_size = payload.get("pageSize")
    total_pages = payload.get("totalPages")
    has_next = payload.get("hasNext")
    has_previous = payload.get("hasPrevious")
    layer_id = payload.get("layerId")
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
        or not isinstance(layer_id, int)
        or not _is_string_list(columns_requested)
        or not _is_string_list(columns_loaded)
    ):
        return None

    annotation_list = AnnotationList(
        annotations=annotations,
        count=count,
        total_count=total_count,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        has_next=has_next,
        has_previous=has_previous,
        layer_id=layer_id,
        columns_requested=columns_requested,
        columns_loaded=columns_loaded,
        columns_available=_ALL_ANNOTATION_COLUMNS,
        sortable_columns=_SORTABLE_ANNOTATION_COLUMNS,
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
    return dump_model_with_select_columns(annotation_list, columns_requested)


def _annotation_keys_from_mcp_response(response: dict[str, Any]) -> list[int]:
    """Return annotation IDs from an MCP annotation list response."""

    annotations = response.get("annotations")
    if not isinstance(annotations, list):
        return []
    return [
        annotation["id"]
        for annotation in annotations
        if isinstance(annotation, dict) and isinstance(annotation.get("id"), int)
    ]


def _annotation_keys_from_ax_services_response(
    response: AxServicesResponse,
) -> list[int]:
    """Return annotation IDs from an ax-services annotation list response."""

    payload = response.payload or {}
    annotations = payload.get("annotations") if isinstance(payload, dict) else None
    if not isinstance(annotations, list):
        return []
    return [
        annotation["id"]
        for annotation in annotations
        if isinstance(annotation, dict) and isinstance(annotation.get("id"), int)
    ]


def _annotation_list_shadow_matches(
    authoritative: dict[str, Any],
    candidate: AxServicesResponse,
) -> bool:
    """Compare Python and TypeScript annotation list outputs by ID order."""

    return (
        "annotations" in authoritative
        and candidate.ok
        and _annotation_keys_from_mcp_response(authoritative)
        == _annotation_keys_from_ax_services_response(candidate)
    )


def _summarize_annotation_list_response(response: dict[str, Any]) -> dict[str, object]:
    """Summarize Python annotation list results for shadow mismatch reports."""

    return {
        "count": len(_annotation_keys_from_mcp_response(response)),
        "ids": _annotation_keys_from_mcp_response(response),
    }


def _summarize_ax_services_annotation_list_response(
    response: AxServicesResponse,
) -> dict[str, object]:
    """Summarize ax-services annotation list results for shadow mismatch reports."""

    payload = response.payload or {}
    return {
        "ok": response.ok,
        "status_code": response.status_code,
        "contract_version": payload.get("contractVersion")
        if isinstance(payload, dict)
        else None,
        "count": len(_annotation_keys_from_ax_services_response(response)),
        "ids": _annotation_keys_from_ax_services_response(response),
        "error": response.error,
    }


def _annotation_list_shadow_mismatch(report: ShadowMismatchReport) -> None:
    """Log a compact annotation list shadow mismatch report."""

    logger.warning(
        "Runtime modernization annotation list shadow mismatch: %s",
        report.to_dict(),
    )


def _annotation_list_shadow_enabled() -> bool:
    """Return whether annotation listing should shadow through ax-services."""

    return is_feature_enabled("RUNTIME_SHADOW_EXECUTION") and is_feature_enabled(
        "TS_MCP_ORCHESTRATION"
    )


def _annotation_list_serving_enabled() -> bool:
    """Return whether annotation listing should be served through ax-services."""

    return is_feature_enabled("TS_MCP_ORCHESTRATION") and is_feature_enabled(
        "TS_LAYER_ANNOTATION_LIST_SERVING"
    )


def _record_annotation_list_metric(metric: str) -> None:
    """Record an annotation-list migration metric."""

    current_app.config["STATS_LOGGER"].incr(
        f"runtime_modernization.mcp_orchestration.list_layer_annotations.{metric}"
    )


@tool(
    tags=["core"],
    class_permission_name="Annotation",
    annotations=ToolAnnotations(
        title="List annotations in a layer",
        readOnlyHint=True,
        destructiveHint=False,
    ),
)
async def list_layer_annotations(
    request: ListLayerAnnotationsRequest,
    ctx: Context,
) -> AnnotationList | AnnotationLayerError | dict[str, Any]:
    """List annotations within a specific annotation layer.

    The layer_id parameter is required and scopes all results to that layer.

    Sortable columns for order_column: id, short_descr, start_dttm, end_dttm

    Example:
    ```json
    {"layer_id": 1, "page": 1, "page_size": 25}
    ```
    """
    with measure_runtime_candidate(
        "mcp_orchestration",
        "list_layer_annotations",
        current_app.config["STATS_LOGGER"],
    ):
        if _annotation_list_serving_enabled():
            candidate_response = _ax_services_annotation_list_candidate(request)
            candidate_annotations = _annotation_list_from_ax_services_response(
                candidate_response
            )
            if candidate_annotations is not None:
                _record_annotation_list_metric("served_candidate")
                return candidate_annotations

            _record_annotation_list_metric("fallback")
            return await _list_layer_annotations_python(request, ctx)

        python_response = await _list_layer_annotations_python(request, ctx)
        return execute_with_shadow(
            area="mcp_orchestration",
            operation="list_layer_annotations",
            authoritative=lambda: python_response,
            candidate=lambda: _ax_services_annotation_list_candidate(request),
            compare=_annotation_list_shadow_matches,
            stats_logger=current_app.config["STATS_LOGGER"],
            shadow_enabled=_annotation_list_shadow_enabled(),
            report_mismatch=_annotation_list_shadow_mismatch,
            summarize_authoritative=_summarize_annotation_list_response,
            summarize_candidate=_summarize_ax_services_annotation_list_response,
        )


async def _list_layer_annotations_python(
    request: ListLayerAnnotationsRequest,
    ctx: Context,
) -> dict[str, Any]:
    """Run the authoritative Python layer annotation list path."""

    await ctx.info(
        "Listing annotations: layer_id=%s, page=%s, page_size=%s, search=%s"
        % (request.layer_id, request.page, request.page_size, request.search)
    )

    try:
        from superset.daos.annotation_layer import AnnotationDAO, AnnotationLayerDAO

        # Verify the layer exists before listing
        layer = AnnotationLayerDAO.find_by_id(request.layer_id)
        if layer is None:
            await ctx.warning("Annotation layer not found: id=%s" % (request.layer_id,))
            return AnnotationLayerError.create(
                error=f"Annotation layer with id '{request.layer_id}' not found",
                error_type="not_found",
            ).model_dump(mode="json")

        # Prepend the layer_id filter so results are scoped to this layer
        layer_filter = ColumnOperator(
            col="layer_id", opr=ColumnOperatorEnum.eq, value=request.layer_id
        )
        combined_filters: list[ColumnOperator] = [layer_filter] + list(request.filters)

        def _serialize(obj: object, cols: list[str] | None) -> AnnotationInfo | None:
            return serialize_annotation(obj)

        list_tool = ModelListCore(
            dao_class=AnnotationDAO,
            output_schema=AnnotationInfo,
            item_serializer=_serialize,
            filter_type=AnnotationFilter,
            default_columns=DEFAULT_ANNOTATION_COLUMNS,
            search_columns=["short_descr", "long_descr"],
            list_field_name="annotations",
            output_list_schema=AnnotationList,
            all_columns=_ALL_ANNOTATION_COLUMNS,
            sortable_columns=_SORTABLE_ANNOTATION_COLUMNS,
            logger=logger,
        )

        with mcp_event_log_context(action="mcp.list_layer_annotations.query"):
            result = list_tool.run_tool(
                filters=combined_filters,
                search=request.search,
                select_columns=request.select_columns,
                order_column=request.order_column,
                order_direction=request.order_direction,
                page=to_zero_based_page(request.page),
                page_size=request.page_size,
            )

        result.layer_id = request.layer_id

        await ctx.info(
            "Annotations listed: layer_id=%s, count=%s, total_count=%s"
            % (
                request.layer_id,
                len(result.annotations) if hasattr(result, "annotations") else 0,
                getattr(result, "total_count", None),
            )
        )
        return result.model_dump(mode="json")

    except Exception as e:
        await ctx.error(
            "Annotation listing failed: layer_id=%s, error=%s, error_type=%s"
            % (request.layer_id, str(e), type(e).__name__)
        )
        raise

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

"""List annotation layers FastMCP tool."""

import logging
from typing import Any

from fastmcp import Context
from flask import current_app
from superset_core.mcp.decorators import tool, ToolAnnotations

from superset import is_feature_enabled
from superset.mcp_service.annotation_layer.schemas import (
    AnnotationLayerError,
    AnnotationLayerFilter,
    AnnotationLayerInfo,
    AnnotationLayerList,
    DEFAULT_LAYER_COLUMNS,
    ListAnnotationLayersRequest,
    serialize_annotation_layer,
)
from superset.mcp_service.mcp_core import (
    ModelListCore,
    request_or_default,
    to_zero_based_page,
)
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

logger = logging.getLogger(__name__)

_DEFAULT_REQUEST = ListAnnotationLayersRequest()

_ALL_LAYER_COLUMNS = ["id", "name", "descr", "changed_on", "created_on"]
_SORTABLE_LAYER_COLUMNS = ["id", "name", "changed_on", "created_on"]
_ANNOTATION_LAYER_LIST_CONTRACT_VERSION = "annotation-layer-list.v1"


def _annotation_layer_list_request_payload(
    request: ListAnnotationLayersRequest,
) -> dict[str, Any]:
    """Build an ax-services annotation layer list request payload."""

    return {
        "contractVersion": _ANNOTATION_LAYER_LIST_CONTRACT_VERSION,
        "filters": [filter_.model_dump(mode="json") for filter_ in request.filters],
        "selectColumns": list(request.select_columns),
        "search": request.search,
        "orderColumn": request.order_column,
        "orderDirection": request.order_direction,
        "page": request.page,
        "pageSize": request.page_size,
    }


def _ax_services_annotation_layer_list_candidate(
    request: ListAnnotationLayersRequest,
) -> AxServicesResponse:
    """Run the TypeScript sidecar annotation layer list candidate."""

    client = AxServicesClient(AxServicesConfig.from_mapping(current_app.config))
    return client.list_annotation_layers(
        _annotation_layer_list_request_payload(request)
    )


def _optional_string(value: Any) -> str | None:
    """Return a string value or None."""

    return value if isinstance(value, str) else None


def _annotation_layer_info_from_ax_services(
    payload: dict[str, Any],
) -> AnnotationLayerInfo | None:
    """Convert one valid ax-services annotation layer item to the MCP schema."""

    layer_id = payload.get("id")
    if not isinstance(layer_id, int):
        return None

    layer = AnnotationLayerInfo(
        id=layer_id,
        name=_optional_string(payload.get("name")),
        descr=_optional_string(payload.get("descr")),
        changed_on=_optional_string(payload.get("changedOn")),
        created_on=_optional_string(payload.get("createdOn")),
    )
    layer_payload = layer.model_dump(mode="python")
    for field_name in ("name", "descr"):
        layer_payload[field_name] = sanitize_for_llm_context(
            layer_payload.get(field_name),
            field_path=(field_name,),
        )
    return AnnotationLayerInfo(**layer_payload)


def _is_string_list(value: Any) -> bool:
    """Return whether a value is a list of strings."""

    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def _annotation_layer_list_from_ax_services_response(
    response: AxServicesResponse,
) -> dict[str, Any] | None:
    """Convert a valid ax-services annotation layer list response."""

    payload = response.payload or {}
    if (
        not response.ok
        or payload.get("contractVersion") != _ANNOTATION_LAYER_LIST_CONTRACT_VERSION
    ):
        return None

    raw_layers = payload.get("annotationLayers")
    if not isinstance(raw_layers, list):
        return None

    layers = []
    for raw_layer in raw_layers:
        if not isinstance(raw_layer, dict):
            return None
        layer = _annotation_layer_info_from_ax_services(raw_layer)
        if layer is None:
            return None
        layers.append(layer)

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

    layer_list = AnnotationLayerList(
        annotation_layers=layers,
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
        sortable_columns=_SORTABLE_LAYER_COLUMNS,
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
    return dump_model_with_select_columns(layer_list, columns_requested)


def _annotation_layer_keys_from_mcp_response(response: dict[str, Any]) -> list[int]:
    """Return annotation layer IDs from an MCP response."""

    layers = response.get("annotation_layers")
    if not isinstance(layers, list):
        return []
    return [
        layer["id"]
        for layer in layers
        if isinstance(layer, dict) and isinstance(layer.get("id"), int)
    ]


def _annotation_layer_keys_from_ax_services_response(
    response: AxServicesResponse,
) -> list[int]:
    """Return annotation layer IDs from an ax-services response."""

    payload = response.payload or {}
    layers = payload.get("annotationLayers") if isinstance(payload, dict) else None
    if not isinstance(layers, list):
        return []
    return [
        layer["id"]
        for layer in layers
        if isinstance(layer, dict) and isinstance(layer.get("id"), int)
    ]


def _annotation_layer_list_shadow_matches(
    authoritative: dict[str, Any],
    candidate: AxServicesResponse,
) -> bool:
    """Compare Python and TypeScript annotation layer outputs by ID order."""

    return candidate.ok and _annotation_layer_keys_from_mcp_response(
        authoritative
    ) == _annotation_layer_keys_from_ax_services_response(candidate)


def _summarize_annotation_layer_list_response(
    response: dict[str, Any],
) -> dict[str, object]:
    """Summarize Python annotation layer list results."""

    return {
        "count": len(_annotation_layer_keys_from_mcp_response(response)),
        "ids": _annotation_layer_keys_from_mcp_response(response),
    }


def _summarize_ax_services_annotation_layer_list_response(
    response: AxServicesResponse,
) -> dict[str, object]:
    """Summarize ax-services annotation layer list results."""

    payload = response.payload or {}
    return {
        "ok": response.ok,
        "status_code": response.status_code,
        "contract_version": payload.get("contractVersion")
        if isinstance(payload, dict)
        else None,
        "count": len(_annotation_layer_keys_from_ax_services_response(response)),
        "ids": _annotation_layer_keys_from_ax_services_response(response),
        "error": response.error,
    }


def _annotation_layer_list_shadow_mismatch(report: ShadowMismatchReport) -> None:
    """Log a compact annotation layer list shadow mismatch report."""

    logger.warning(
        "Runtime modernization annotation layer list shadow mismatch: %s",
        report.to_dict(),
    )


def _annotation_layer_list_shadow_enabled() -> bool:
    """Return whether annotation layer listing should shadow through ax-services."""

    return is_feature_enabled("RUNTIME_SHADOW_EXECUTION") and is_feature_enabled(
        "TS_MCP_ORCHESTRATION"
    )


def _annotation_layer_list_serving_enabled() -> bool:
    """Return whether annotation layer listing should be served through ax-services."""

    return is_feature_enabled("TS_MCP_ORCHESTRATION") and is_feature_enabled(
        "TS_ANNOTATION_LAYER_LIST_SERVING"
    )


def _record_annotation_layer_list_metric(metric: str) -> None:
    """Record an annotation-layer-list migration metric."""

    current_app.config["STATS_LOGGER"].incr(
        f"runtime_modernization.mcp_orchestration.list_annotation_layers.{metric}"
    )


@tool(
    tags=["core"],
    class_permission_name="Annotation",
    annotations=ToolAnnotations(
        title="List annotation layers",
        readOnlyHint=True,
        destructiveHint=False,
    ),
)
async def list_annotation_layers(
    request: ListAnnotationLayersRequest | None = None,
    ctx: Context | None = None,
) -> AnnotationLayerList | AnnotationLayerError | dict[str, Any]:
    """List annotation layers with filtering, search, and pagination.

    Returns annotation layer metadata including name and description.

    Sortable columns for order_column: id, name, changed_on, created_on
    """
    if ctx is None:
        raise RuntimeError("FastMCP context is required for list_annotation_layers")

    request = request_or_default(request, _DEFAULT_REQUEST)

    with measure_runtime_candidate(
        "mcp_orchestration",
        "list_annotation_layers",
        current_app.config["STATS_LOGGER"],
    ):
        if _annotation_layer_list_serving_enabled():
            candidate_response = _ax_services_annotation_layer_list_candidate(request)
            candidate_layers = _annotation_layer_list_from_ax_services_response(
                candidate_response
            )
            if candidate_layers is not None:
                _record_annotation_layer_list_metric("served_candidate")
                return candidate_layers

            _record_annotation_layer_list_metric("fallback")
            return await _list_annotation_layers_python(request, ctx)

        python_response = await _list_annotation_layers_python(request, ctx)
        return execute_with_shadow(
            area="mcp_orchestration",
            operation="list_annotation_layers",
            authoritative=lambda: python_response,
            candidate=lambda: _ax_services_annotation_layer_list_candidate(request),
            compare=_annotation_layer_list_shadow_matches,
            stats_logger=current_app.config["STATS_LOGGER"],
            shadow_enabled=_annotation_layer_list_shadow_enabled(),
            report_mismatch=_annotation_layer_list_shadow_mismatch,
            summarize_authoritative=_summarize_annotation_layer_list_response,
            summarize_candidate=_summarize_ax_services_annotation_layer_list_response,
        )


async def _list_annotation_layers_python(
    request: ListAnnotationLayersRequest,
    ctx: Context,
) -> dict[str, Any]:
    """Run the authoritative Python annotation layer list path."""

    await ctx.info(
        f"Listing annotation layers: page={request.page}, "
        f"page_size={request.page_size}, search={request.search}"
    )

    try:
        from superset.daos.annotation_layer import AnnotationLayerDAO

        def _serialize(
            obj: object, cols: list[str] | None
        ) -> AnnotationLayerInfo | None:
            return serialize_annotation_layer(obj)

        list_tool = ModelListCore(
            dao_class=AnnotationLayerDAO,
            output_schema=AnnotationLayerInfo,
            item_serializer=_serialize,
            filter_type=AnnotationLayerFilter,
            default_columns=DEFAULT_LAYER_COLUMNS,
            search_columns=["name", "descr"],
            list_field_name="annotation_layers",
            output_list_schema=AnnotationLayerList,
            all_columns=_ALL_LAYER_COLUMNS,
            sortable_columns=_SORTABLE_LAYER_COLUMNS,
            logger=logger,
        )

        with mcp_event_log_context(action="mcp.list_annotation_layers.query"):
            result = list_tool.run_tool(
                filters=request.filters,
                search=request.search,
                select_columns=request.select_columns,
                order_column=request.order_column,
                order_direction=request.order_direction,
                page=to_zero_based_page(request.page),
                page_size=request.page_size,
            )

        annotation_layer_count = (
            len(result.annotation_layers) if hasattr(result, "annotation_layers") else 0
        )
        await ctx.info(
            "Annotation layers listed: "
            f"count={annotation_layer_count}, "
            f"total_count={getattr(result, 'total_count', None)}"
        )
        return result.model_dump(mode="json")

    except Exception as e:
        await ctx.error(
            f"Annotation layer listing failed: error={str(e)}, "
            f"error_type={type(e).__name__}"
        )
        raise

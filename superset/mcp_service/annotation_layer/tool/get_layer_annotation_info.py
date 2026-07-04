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

"""Get a single annotation within a layer FastMCP tool."""

import logging

from fastmcp import Context
from superset_core.mcp.decorators import tool, ToolAnnotations

from superset.mcp_service.annotation_layer.schemas import (
    AnnotationInfo,
    AnnotationLayerError,
    GetLayerAnnotationInfoRequest,
    serialize_annotation,
)
from superset.mcp_service.utils.logging_utils import mcp_event_log_context

logger = logging.getLogger(__name__)


@tool(
    tags=["discovery"],
    class_permission_name="Annotation",
    annotations=ToolAnnotations(
        title="Get annotation info",
        readOnlyHint=True,
        destructiveHint=False,
    ),
)
async def get_layer_annotation_info(
    request: GetLayerAnnotationInfoRequest,
    ctx: Context,
) -> AnnotationInfo | AnnotationLayerError:
    """Get detailed information about a specific annotation within a layer.

    Both layer_id and annotation_id are required. Returns an error if the
    annotation does not belong to the specified layer.

    Example:
    ```json
    {"layer_id": 1, "annotation_id": 42}
    ```
    """
    await ctx.info(
        f"Retrieving annotation: layer_id={request.layer_id}, "
        f"annotation_id={request.annotation_id}"
    )

    try:
        from superset.daos.annotation_layer import AnnotationDAO, AnnotationLayerDAO

        # Verify the layer exists
        with mcp_event_log_context(action="mcp.get_layer_annotation_info.layer_lookup"):
            layer = AnnotationLayerDAO.find_by_id(request.layer_id)

        if layer is None:
            await ctx.warning(f"Annotation layer not found: id={request.layer_id}")
            return AnnotationLayerError.create(
                error=f"Annotation layer with id '{request.layer_id}' not found",
                error_type="not_found",
            )

        # Fetch the annotation
        with mcp_event_log_context(
            action="mcp.get_layer_annotation_info.annotation_lookup"
        ):
            annotation = AnnotationDAO.find_by_id(request.annotation_id)

        if annotation is None:
            await ctx.warning(
                f"Annotation not found: annotation_id={request.annotation_id}"
            )
            return AnnotationLayerError.create(
                error=f"Annotation with id '{request.annotation_id}' not found",
                error_type="not_found",
            )

        # Verify the annotation belongs to the requested layer
        if getattr(annotation, "layer_id", None) != request.layer_id:
            await ctx.warning(
                f"Annotation {request.annotation_id} does not belong to "
                f"layer {request.layer_id}"
            )
            return AnnotationLayerError.create(
                error=(
                    f"Annotation '{request.annotation_id}' does not belong to "
                    f"layer '{request.layer_id}'"
                ),
                error_type="not_found",
            )

        result = serialize_annotation(annotation)
        await ctx.info(
            f"Annotation retrieved: id={result.id if result else None}, "
            f"short_descr={result.short_descr if result else None}"
        )
        return result or AnnotationLayerError.create(
            error="Failed to serialize annotation",
            error_type="SerializationError",
        )

    except Exception as e:
        await ctx.error(
            f"Annotation lookup failed: layer_id={request.layer_id}, "
            f"annotation_id={request.annotation_id}, error={str(e)}, "
            f"error_type={type(e).__name__}"
        )
        return AnnotationLayerError.create(
            error=f"Failed to get annotation info: {str(e)}",
            error_type="InternalError",
        )

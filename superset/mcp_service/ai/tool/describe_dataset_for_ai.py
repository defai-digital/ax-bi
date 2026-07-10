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
"""MCP tool: describe_dataset_for_ai

Returns an AI-optimized description of a dataset with compact output,
semantic alias lookup, and privacy controls.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import joinedload, subqueryload
from superset_core.mcp.decorators import tool, ToolAnnotations

try:
    from fastmcp import Context
except ModuleNotFoundError:
    Context = Any

from superset.mcp_service.ai.schemas import (
    ColumnDescription,
    DatasetDescription,
    DatasetDescriptionRequest,
    DatasetDescriptionResponse,
    MetricDescription,
)
from superset.mcp_service.privacy import (
    requires_data_model_metadata_access,
    user_can_view_data_model_metadata,
)
from superset.mcp_service.utils.logging_utils import mcp_event_log_context

logger = logging.getLogger(__name__)


def _get_aliases_for_object(
    object_type: str,
    object_name: str,
    dataset_id: int | None = None,
) -> list[str]:
    """Look up semantic aliases for a dataset object."""
    try:
        from superset.models.ai import AISemanticAlias

        query_filters = [
            AISemanticAlias.object_type == object_type,
            AISemanticAlias.alias.isnot(None),
        ]

        if dataset_id is not None:
            query_filters.append(AISemanticAlias.dataset_id == dataset_id)
        else:
            # Cross-dataset lookup
            query_filters.append(AISemanticAlias.object_name == object_name)

        from superset.extensions import db

        results = db.session.query(AISemanticAlias).filter(*query_filters).all()
        return [r.alias for r in results if r.alias]
    except Exception:
        # Alias table may not exist yet (pre-migration)
        return []


def _describe_dataset(
    dataset: Any,
    include_sample_values: bool = False,
) -> DatasetDescription:
    """Build an AI-optimized description from a dataset ORM object."""
    columns: list[ColumnDescription] = []
    for col in getattr(dataset, "columns", []) or []:
        col_name = getattr(col, "column_name", "") or ""
        col_type = getattr(col, "type", None)
        type_str = str(col_type) if col_type else "UNKNOWN"
        description = getattr(col, "description", None) or ""

        # Look up aliases for this column
        aliases = _get_aliases_for_object("column", col_name, dataset_id=dataset.id)

        # Heuristic: columns with few distinct values are dimensions
        is_dimension = not getattr(col, "is_dttm", False) and not getattr(
            col, "expression", None
        )

        columns.append(
            ColumnDescription(
                name=col_name,
                type=type_str,
                description=description,
                aliases=aliases,
                is_dimension=is_dimension,
            )
        )

    metrics: list[MetricDescription] = []
    for metric in getattr(dataset, "metrics", []) or []:
        metric_name = getattr(metric, "metric_name", "") or ""
        expression = getattr(metric, "expression", "") or ""
        description = getattr(metric, "description", None) or ""

        # Look up aliases for this metric
        aliases = _get_aliases_for_object("metric", metric_name, dataset_id=dataset.id)

        metrics.append(
            MetricDescription(
                name=metric_name,
                expression=expression,
                description=description,
            )
        )

    # Determine main time column
    main_time_col = getattr(dataset, "main_dttm_col", None)
    if not main_time_col:
        # Fall back to first datetime column
        for col in getattr(dataset, "columns", []) or []:
            if getattr(col, "is_dttm", False):
                main_time_col = getattr(col, "column_name", None)
                break

    # Build privacy metadata
    privacy: dict[str, Any] = {
        "sample_values_included": include_sample_values,
        "metadata_scope": "role_allowed",
    }

    certified_by = getattr(dataset, "certified_by", None)

    return DatasetDescription(
        id=dataset.id,
        name=getattr(dataset, "table_name", "") or "",
        description=getattr(dataset, "description", None) or "",
        certified=bool(certified_by),
        main_time_column=main_time_col,
        columns=columns,
        metrics=metrics,
        privacy=privacy,
    )


@tool(
    tags=["discovery", "ai"],
    class_permission_name="Dataset",
    feature_flags=["GENAI_BI", "GENAI_BI_MCP_TOOLS"],
    annotations=ToolAnnotations(
        title="Describe dataset for AI",
        readOnlyHint=True,
        destructiveHint=False,
    ),
)
@requires_data_model_metadata_access
async def describe_dataset_for_ai(
    request: DatasetDescriptionRequest, ctx: Context
) -> dict[str, Any]:
    """Get an AI-optimized description of a dataset.

    Returns compact column/metric metadata with semantic aliases,
    suitable for LLM context windows. Respects privacy controls.

    IMPORTANT FOR LLM CLIENTS:
    - Use this after search_business_assets to understand a dataset
    - Response includes columns, saved metrics, and time column info
    - Semantic aliases help map business terms to technical names
    - Sample values are excluded by default for privacy

    Example usage:
    ```json
    {
        "dataset_id": 42,
        "include_sample_values": false,
        "include_usage_stats": true
    }
    ```
    """
    await ctx.info(
        f"Describing dataset for AI: dataset_id={request.dataset_id}, "
        f"sample_values={request.include_sample_values}"
    )

    # Privacy check
    if not user_can_view_data_model_metadata():
        await ctx.warning("Dataset description blocked by privacy controls")
        return DatasetDescriptionResponse(
            dataset=DatasetDescription(
                id=request.dataset_id,
                name="",
                description="",
                certified=False,
            ),
            warnings=["You don't have permission to access dataset metadata."],
        ).model_dump()

    try:
        from superset.connectors.sqla.models import SqlaTable
        from superset.daos.dataset import DatasetDAO

        eager_options = [
            subqueryload(SqlaTable.columns),
            subqueryload(SqlaTable.metrics),
            joinedload(SqlaTable.database),
        ]

        with mcp_event_log_context(action="mcp.describe_dataset_for_ai.lookup"):
            dataset = DatasetDAO.find_by_id(
                request.dataset_id,
                query_options=eager_options,
            )

        if not dataset:
            await ctx.warning(f"Dataset not found: dataset_id={request.dataset_id}")
            return DatasetDescriptionResponse(
                dataset=DatasetDescription(
                    id=request.dataset_id,
                    name="",
                    description="",
                    certified=False,
                ),
                warnings=[f"Dataset {request.dataset_id} not found."],
            ).model_dump()

        with mcp_event_log_context(action="mcp.describe_dataset_for_ai.describe"):
            description = _describe_dataset(
                dataset,
                include_sample_values=request.include_sample_values,
            )

        await ctx.info(
            f"Dataset described successfully: name={description.name}, "
            f"columns={len(description.columns)}, metrics={len(description.metrics)}"
        )

        response = DatasetDescriptionResponse(dataset=description, warnings=[])
        return response.model_dump()

    except Exception as e:
        await ctx.error(
            f"Dataset description failed: dataset_id={request.dataset_id}, "
            f"error={e}, error_type={type(e).__name__}"
        )
        return DatasetDescriptionResponse(
            dataset=DatasetDescription(
                id=request.dataset_id,
                name="",
                description="",
                certified=False,
            ),
            warnings=[f"Failed to describe dataset: {str(e)}"],
        ).model_dump()

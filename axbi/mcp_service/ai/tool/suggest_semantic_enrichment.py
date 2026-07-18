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
"""MCP tool: suggest_semantic_enrichment

Draft descriptions, synonyms, and relationship hints for a dataset using the
Admin-configured LLM factory (heuristic fallback when unconfigured).
"""

from __future__ import annotations

import logging
from typing import Any

from axbi_core.mcp.decorators import tool, ToolAnnotations
from sqlalchemy.orm import joinedload, subqueryload

from axbi.genai.semantic_assist import (
    suggest_semantic_enrichment as run_semantic_assist,
)
from axbi.mcp_service.ai.schemas import (
    SemanticEnrichmentRequest,
    SemanticEnrichmentResponse,
    SemanticEnrichmentSuggestion,
)
from axbi.mcp_service.privacy import (
    requires_data_model_metadata_access,
    user_can_view_data_model_metadata,
)
from axbi.mcp_service.utils.logging_utils import mcp_event_log_context

try:
    from fastmcp import Context
except ModuleNotFoundError:
    Context = Any

logger = logging.getLogger(__name__)


@tool(
    tags=["discovery", "ai"],
    class_permission_name="Dataset",
    feature_flags=["GENAI_BI", "GENAI_BI_MCP_TOOLS"],
    annotations=ToolAnnotations(
        title="Suggest semantic enrichment",
        readOnlyHint=True,
        destructiveHint=False,
    ),
)
@requires_data_model_metadata_access
async def suggest_semantic_enrichment(
    request: SemanticEnrichmentRequest, ctx: Context
) -> dict[str, Any]:
    """Suggest draft semantic enrichments for a dataset.

    Uses the Admin/operator-configured server LLM when available; otherwise
    returns heuristic drafts. Suggestions are **never auto-applied** to
    certified semantic fields — humans must approve.

    IMPORTANT FOR LLM CLIENTS:
    - Call after describe_dataset_for_ai when metadata is thin
    - Treat all suggestions as drafts (draft_only=true)
    - Prefer approved AISemanticAlias / certified metrics over drafts
    """
    await ctx.info(
        f"Semantic enrichment: dataset_id={request.dataset_id}, focus={request.focus!r}"
    )

    if not user_can_view_data_model_metadata():
        await ctx.warning("Semantic enrichment blocked by privacy controls")
        return SemanticEnrichmentResponse(
            suggestions=[],
            warnings=["You don't have permission to access dataset metadata."],
            used_llm=False,
            draft_only=True,
        ).model_dump()

    try:
        from axbi.connectors.sqla.models import SqlaTable
        from axbi.daos.dataset import DatasetDAO

        eager_options = [
            subqueryload(SqlaTable.columns),
            subqueryload(SqlaTable.metrics),
            joinedload(SqlaTable.database),
        ]

        with mcp_event_log_context(action="mcp.suggest_semantic_enrichment.lookup"):
            dataset = DatasetDAO.find_by_id(
                request.dataset_id,
                query_options=eager_options,
            )

        if not dataset:
            return SemanticEnrichmentResponse(
                suggestions=[],
                warnings=[f"Dataset {request.dataset_id} not found."],
                used_llm=False,
                draft_only=True,
            ).model_dump()

        with mcp_event_log_context(action="mcp.suggest_semantic_enrichment.run"):
            result = run_semantic_assist(dataset, focus=request.focus)

        suggestions = [
            SemanticEnrichmentSuggestion(
                object_type=s.object_type,
                object_name=s.object_name,
                suggestion_type=s.suggestion_type,
                value=s.value,
                related_object=s.related_object,
                confidence=s.confidence,
                rationale=s.rationale,
            )
            for s in result.suggestions
        ]

        await ctx.info(
            f"Semantic enrichment done: suggestions={len(suggestions)}, "
            f"used_llm={result.used_llm}"
        )
        return SemanticEnrichmentResponse(
            suggestions=suggestions,
            warnings=list(result.warnings),
            used_llm=result.used_llm,
            provider_type=result.provider_type,
            model=result.model,
            draft_only=True,
        ).model_dump()

    except Exception as exc:  # pylint: disable=broad-except
        logger.exception("suggest_semantic_enrichment failed")
        await ctx.error(f"Semantic enrichment failed: {exc}")
        return SemanticEnrichmentResponse(
            suggestions=[],
            warnings=[f"Failed to suggest enrichments: {exc}"],
            used_llm=False,
            draft_only=True,
        ).model_dump()

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
"""MCP tool: create_chart_from_intent

Accepts a natural language description of what the user wants to visualize,
discovers the best dataset, resolves metrics/dimensions, and creates a chart.
Replaces the multi-step list_datasets -> get_dataset_info -> generate_chart flow
with a single intent-driven call.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from superset_core.mcp.decorators import tool, ToolAnnotations

try:
    from fastmcp import Context
except ModuleNotFoundError:
    Context = Any

from superset.mcp_service.ai.schemas import (
    CreateChartFromIntentRequest,
    CreateChartFromIntentResponse,
)
from superset.mcp_service.privacy import (
    requires_data_model_metadata_access,
    user_can_view_data_model_metadata,
)
from superset.mcp_service.utils.logging_utils import mcp_event_log_context

logger = logging.getLogger(__name__)

_CHART_NAME_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"\bname\s+it\s+['\"]?(.+?)['\"]?"
        r"(?=[.!?]\s+(?:return|do not|don't|keep|use|show)\b|[.!?]\s*$|$)",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bnamed\s+['\"]?(.+?)['\"]?"
        r"(?=[.!?]\s+(?:return|do not|don't|keep|use|show)\b|[.!?]\s*$|$)",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bcalled\s+['\"]?(.+?)['\"]?"
        r"(?=[.!?]\s+(?:return|do not|don't|keep|use|show)\b|[.!?]\s*$|$)",
        re.IGNORECASE,
    ),
)
_DATASET_NAME_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"\b(?:dataset|from|table)\s+['\"]?([A-Za-z0-9_.-]+)['\"]?",
        re.IGNORECASE,
    ),
    re.compile(r"\b([A-Za-z0-9]+(?:_[A-Za-z0-9]+)+)\b"),
)


def _extract_chart_name(prompt: str) -> str | None:
    """Extract an explicit chart title from natural language when present."""
    for pattern in _CHART_NAME_PATTERNS:
        match = pattern.search(prompt)
        if match:
            chart_name = match.group(1).strip(" '\"")
            return chart_name or None
    return None


def _dataset_name_candidates(prompt: str) -> list[str]:
    """Extract likely dataset/table names mentioned directly in a prompt."""
    candidates: list[str] = []
    seen: set[str] = set()

    for pattern in _DATASET_NAME_PATTERNS:
        for match in pattern.finditer(prompt):
            candidate = match.group(1).strip(" '\".,;:!?")
            key = candidate.lower()
            if candidate and key not in seen:
                candidates.append(candidate)
                seen.add(key)

    return candidates


def _discover_dataset_by_name(prompt: str) -> Any | None:
    """Resolve a dataset when the prompt directly names a table/dataset."""
    from superset.daos.dataset import DatasetDAO

    candidates = _dataset_name_candidates(prompt)
    for candidate in candidates:
        dataset = DatasetDAO.find_one_or_none(table_name=candidate)
        if dataset is not None:
            return dataset

    normalized_candidates = {candidate.lower() for candidate in candidates}
    if not normalized_candidates:
        return None

    for dataset in DatasetDAO.find_all():
        table_name = getattr(dataset, "table_name", "")
        if table_name.lower() in normalized_candidates:
            return dataset

    return None


def _discover_best_dataset(
    prompt: str,
    dataset_id: int | str | None = None,
) -> tuple[Any | None, list[str]]:
    """Find the best matching dataset for the given prompt.

    When ``dataset_id`` is provided, look it up directly. Otherwise use
    ``search_assets`` to find candidate datasets and return the top match.

    Returns:
        Tuple of (dataset ORM object or None, list of warning strings).
    """
    warnings: list[str] = []

    from superset.connectors.sqla.models import SqlaTable
    from superset.daos.dataset import DatasetDAO

    if dataset_id is not None:
        # Direct lookup
        from sqlalchemy.orm import subqueryload

        eager = [subqueryload(SqlaTable.columns), subqueryload(SqlaTable.metrics)]
        if isinstance(dataset_id, str) and not dataset_id.isdigit():
            dataset = DatasetDAO.find_by_id(
                dataset_id, id_column="uuid", query_options=eager
            )
        else:
            dataset = DatasetDAO.find_by_id(int(dataset_id), query_options=eager)

        if dataset is None:
            warnings.append(f"Dataset {dataset_id} not found or not accessible.")
        return dataset, warnings

    dataset = _discover_dataset_by_name(prompt)
    if dataset is not None:
        return dataset, warnings

    # Auto-discover via asset search
    from superset.mcp_service.ai.asset_search import search_assets

    results = search_assets(
        query=prompt,
        asset_types=["dataset"],
        include_certified_only=False,
        limit=5,
    )

    if not results:
        warnings.append(
            "No datasets found matching the prompt. "
            "Try specifying a dataset_id or rephrasing."
        )
        return None, warnings

    # Pick the top-scoring dataset
    top_result = results[0]
    from sqlalchemy.orm import subqueryload

    eager = [subqueryload(SqlaTable.columns), subqueryload(SqlaTable.metrics)]
    dataset = DatasetDAO.find_by_id(top_result.id, query_options=eager)
    if dataset is None:
        warnings.append(f"Top dataset '{top_result.name}' could not be loaded.")
        return None, warnings

    if len(results) > 1:
        other_names = ", ".join(r.name for r in results[1:3])
        warnings.append(
            f"Selected dataset '{top_result.name}'. "
            f"Other candidates: {other_names}. "
            f"Pass dataset_id to pin a specific one."
        )

    return dataset, warnings


def _resolve_chart_config_from_intent(
    prompt: str,
    dataset: Any,
) -> tuple[dict[str, Any] | None, str, float, str, list[str]]:
    """Map natural language intent to a chart configuration.

    Uses the configured LLM provider to translate the prompt into a
    structured chart config. Falls back to heuristic mapping when no
    LLM provider is available.

    Returns:
        Tuple of (config_dict, chart_type, confidence, explanation, warnings).
    """
    warnings: list[str] = []

    # Try the LLM provider first
    try:
        from superset.mcp_service.ai.intent_mapper import (
            map_intent_to_chart,
        )
        from superset.mcp_service.ai.provider_factory import get_llm_provider

        result = map_intent_to_chart(prompt, dataset, get_llm_provider())
        return (
            result.config,
            result.chart_type,
            result.confidence,
            result.explanation,
            warnings,
        )
    except NotImplementedError:
        # No LLM provider configured — fall back to heuristic
        warnings.append(
            "No LLM provider configured. Using heuristic intent mapping. "
            "Configure GENAI_LLM_PROVIDER_CONFIG for better results."
        )
    except Exception as e:
        warnings.append(f"LLM intent mapping failed ({e}). Falling back to heuristic.")

    # Heuristic fallback: build a basic table chart from the dataset
    from superset.mcp_service.ai.intent_heuristic import heuristic_chart_config

    return heuristic_chart_config(prompt, dataset, warnings)


def _governance_violations(dataset: Any, config: dict[str, Any] | None) -> list[Any]:
    """Return governance-policy violations for a resolved chart config.

    Builds the dataset's grounding contract and checks the config against its
    structured policies. Returns an empty list if the semantic layer is
    unavailable so chart creation never depends on it being configured.
    """
    try:
        from superset.semantic_index.governance import (
            load_dataset_aliases,
            load_dataset_instructions,
            load_dataset_policies,
        )
        from superset.semantic_index.grounding import build_grounding_contract
        from superset.semantic_index.guardrail import check_config

        contract = build_grounding_contract(
            dataset,
            aliases=load_dataset_aliases(dataset.id),
            instructions=load_dataset_instructions(dataset),
            policies=load_dataset_policies(dataset),
        )
        return check_config(config, contract)
    except Exception:  # pylint: disable=broad-except
        logger.debug("Governance guardrail unavailable", exc_info=True)
        return []


@tool(
    tags=["mutate", "ai"],
    class_permission_name="Chart",
    annotations=ToolAnnotations(
        title="Create chart from intent",
        readOnlyHint=False,
        destructiveHint=False,
    ),
)
@requires_data_model_metadata_access
async def create_chart_from_intent(  # noqa: C901
    request: CreateChartFromIntentRequest, ctx: Context
) -> dict[str, Any]:
    """Create a chart from a natural language description.

    Accepts plain English intent, discovers the best dataset, resolves
    metrics/dimensions/filters, and creates a chart. Replaces the multi-step
    flow of list_datasets -> get_dataset_info -> generate_chart.

    IMPORTANT FOR LLM CLIENTS:
    - Use this tool when the user describes what they want to see in plain English
    - The tool handles dataset discovery, metric resolution, and chart type selection
    - Returns a confidence score and explanation of why choices were made
    - When confidence is low, the explanation includes what was ambiguous

    Example usage:
    ```json
    {
        "prompt": "Show me monthly revenue trend for the last year",
        "save_chart": true
    }
    ```

    Pin to a specific dataset:
    ```json
    {
        "prompt": "Top 10 products by quantity sold",
        "dataset_id": 42,
        "save_chart": true
    }
    ```
    """
    await ctx.info(
        "Creating chart from intent: prompt='%s', dataset_id=%s, save=%s"
        % (request.prompt[:80], request.dataset_id, request.save_chart)
    )

    if not user_can_view_data_model_metadata():
        await ctx.warning("Chart creation from intent blocked by privacy controls")
        return CreateChartFromIntentResponse(
            warnings=["You don't have permission to access dataset metadata."],
        ).model_dump()

    all_warnings: list[str] = []

    # Step 1: Discover / resolve dataset
    await ctx.report_progress(1, 4, "Discovering dataset")
    with mcp_event_log_context(action="mcp.create_chart_from_intent.discover"):
        dataset, discover_warnings = _discover_best_dataset(
            request.prompt, request.dataset_id
        )
    all_warnings.extend(discover_warnings)

    if dataset is None:
        await ctx.warning(
            "No dataset found for intent: prompt='%s'" % request.prompt[:80]
        )
        return CreateChartFromIntentResponse(
            warnings=all_warnings,
            explanation="Could not find a suitable dataset for this request.",
        ).model_dump()

    dataset_info = {
        "id": dataset.id,
        "name": getattr(dataset, "table_name", "") or "",
    }
    await ctx.info(
        "Dataset resolved: id=%s, name=%s" % (dataset.id, dataset_info["name"])
    )

    # Surface governed rules so they reach the caller even on the heuristic path.
    try:
        from superset.semantic_index.governance import load_dataset_instructions

        for instruction in load_dataset_instructions(dataset):
            all_warnings.append(f"Governed rule: {instruction}")
    except Exception:  # pylint: disable=broad-except
        logger.debug("Governed instructions unavailable", exc_info=True)

    # Step 2: Map intent to chart config
    await ctx.report_progress(2, 4, "Mapping intent to chart configuration")
    with mcp_event_log_context(action="mcp.create_chart_from_intent.resolve"):
        config, chart_type, confidence, explanation, resolve_warnings = (
            _resolve_chart_config_from_intent(request.prompt, dataset)
        )
    all_warnings.extend(resolve_warnings)

    if config is None:
        await ctx.warning("Could not resolve chart config from intent")
        return CreateChartFromIntentResponse(
            dataset_used=dataset_info,
            warnings=all_warnings,
            explanation=explanation
            or "Could not map the request to a valid chart configuration.",
            confidence=confidence,
        ).model_dump()

    # Governance guardrail: deterministically enforce structured policies on the
    # resolved config, independent of whether an LLM produced it. A prompt rule
    # is a suggestion; this is the enforcement.
    blocking_violations: list[str] = []
    for violation in _governance_violations(dataset, config):
        all_warnings.append(f"Governance violation: {violation.message}")
        if violation.severity == "block":
            blocking_violations.append(violation.message)

    if blocking_violations:
        await ctx.warning(
            "Chart blocked by governance policy: %s" % blocking_violations[0]
        )
        return CreateChartFromIntentResponse(
            dataset_used=dataset_info,
            chart_type_selected=chart_type,
            explanation=(
                "Blocked by a governance policy. " + (explanation or "")
            ).strip(),
            confidence=confidence,
            warnings=all_warnings,
            alternatives=_suggest_alternatives(chart_type),
        ).model_dump()

    # Step 3: Generate the chart via existing generate_chart tool
    await ctx.report_progress(3, 4, "Generating chart")
    with mcp_event_log_context(action="mcp.create_chart_from_intent.generate"):
        from superset.mcp_service.chart.schemas import GenerateChartRequest

        chart_request = GenerateChartRequest(
            dataset_id=dataset.id,
            config=config,
            chart_name=_extract_chart_name(request.prompt),
            save_chart=request.save_chart,
            generate_preview=False,
        )

        # Import and call generate_chart directly (in-process, not via MCP).
        # The @tool wrapper injects ctx itself, so we pass only the request —
        # passing ctx here collides ("multiple values for argument 'ctx'").
        from superset.mcp_service.chart.tool.generate_chart import generate_chart

        chart_response = await generate_chart(chart_request)

    # Step 4: Build response
    await ctx.report_progress(4, 4, "Building response")
    response_dict = (
        chart_response.model_dump()
        if hasattr(chart_response, "model_dump")
        else chart_response
    )

    chart_data = response_dict.get("chart")
    explore_url = response_dict.get("explore_url")
    success = response_dict.get("success", False)

    if not success:
        error_info = response_dict.get("error")
        error_msg = ""
        if isinstance(error_info, dict):
            error_msg = error_info.get("message", str(error_info))
        elif error_info:
            error_msg = str(error_info)
        all_warnings.append(f"Chart generation failed: {error_msg}")
        return CreateChartFromIntentResponse(
            dataset_used=dataset_info,
            chart_type_selected=chart_type,
            explanation=explanation,
            confidence=confidence,
            warnings=all_warnings,
            alternatives=_suggest_alternatives(chart_type),
        ).model_dump()

    # Extract alternatives
    alternatives = _suggest_alternatives(chart_type)

    await ctx.info(
        "Chart created from intent: chart_id=%s, type=%s, confidence=%.2f"
        % (
            chart_data.get("id") if chart_data else None,
            chart_type,
            confidence,
        )
    )

    return CreateChartFromIntentResponse(
        chart=chart_data,
        dataset_used=dataset_info,
        chart_type_selected=chart_type,
        explanation=explanation,
        confidence=confidence,
        warnings=all_warnings,
        preview_url=explore_url,
        alternatives=alternatives,
    ).model_dump()


def _suggest_alternatives(chart_type: str) -> list[str]:
    """Suggest alternative chart types the user might prefer."""
    alternatives_map: dict[str, list[str]] = {
        "echarts_timeseries_line": [
            "Try 'bar' kind for easier category comparison",
            "Try 'area' kind to emphasize volume",
        ],
        "echarts_timeseries_bar": [
            "Try 'line' kind for trend visualization",
            "Try 'scatter' for correlation analysis",
        ],
        "table": [
            "Try 'echarts_timeseries_bar' for visual category comparison",
            "Try 'pie' for proportional data",
        ],
        "big_number": [
            "Try adding show_trendline=True for trend context",
            "Try 'echarts_timeseries_line' for detailed trend view",
        ],
        "pie": [
            "Try 'echarts_timeseries_bar' for comparing many categories",
            "Try 'table' for detailed breakdown",
        ],
    }
    return alternatives_map.get(
        chart_type, ["Try a different chart type for a different perspective"]
    )

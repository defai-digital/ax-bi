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
"""MCP tool: validate_chart

Validates a chart configuration against a dataset without creating any
artifacts. Uses the same ValidationPipeline that generate_chart uses
internally, exposed as a standalone read-only tool so LLM clients can
pre-flight chart intents from plan_dashboard before committing to chart
creation.
"""

from __future__ import annotations

import logging
from typing import Any

from superset_core.mcp.decorators import tool, ToolAnnotations

try:
    from fastmcp import Context
except ModuleNotFoundError:
    Context = Any

from superset.mcp_service.ai.schemas import (
    ValidateChartRequest,
    ValidateChartResponse,
)
from superset.mcp_service.utils.logging_utils import mcp_event_log_context

logger = logging.getLogger(__name__)


def _extract_errors(error: Any) -> list[str]:
    """Extract human-readable error messages from a validation error."""
    if error is None:
        return []
    if hasattr(error, "message"):
        return [str(error.message)]
    if hasattr(error, "error_type"):
        return [f"{error.error_type}: {getattr(error, 'suggestion', '')}"]
    return [str(error)]


def _extract_warnings(warnings: dict[str, Any] | None) -> list[str]:
    """Flatten a warnings dict into a list of strings."""
    if not warnings:
        return []
    result: list[str] = []
    for key, val in warnings.items():
        if isinstance(val, dict):
            for sub_key, sub_val in val.items():
                if sub_val:
                    result.append(f"{sub_key}: {sub_val}")
        elif val:
            result.append(f"{key}: {val}")
    return result


def _extract_normalized_config(result: Any) -> dict[str, Any] | None:
    """Pull the normalized config from a validation result, or None."""
    if not (result.request and hasattr(result.request, "config")):
        return None
    try:
        return result.request.config.model_dump(exclude_none=True)
    except Exception:  # noqa: BLE001
        return None


def _run_validation(
    dataset_id: int,
    config: dict[str, Any],
) -> dict[str, Any]:
    """Run the validation pipeline and return a raw result dict.

    Extracted as a testable helper so unit tests can mock the pipeline
    without needing Flask auth context.

    Returns:
        Dict with keys: is_valid, errors, warnings, normalized_config.
    """
    try:
        from superset.mcp_service.chart.validation.pipeline import (
            ValidationPipeline,
        )

        request_data = {
            "dataset_id": dataset_id,
            "config": config,
            "save_chart": False,
            "generate_preview": False,
        }

        result = ValidationPipeline.validate_request_with_warnings(request_data)

        if not result.is_valid:
            return {
                "is_valid": False,
                "errors": _extract_errors(result.error),
                "warnings": [],
                "normalized_config": None,
            }

        return {
            "is_valid": True,
            "errors": [],
            "warnings": _extract_warnings(result.warnings),
            "normalized_config": _extract_normalized_config(result),
        }

    except ImportError:
        logger.warning("Validation pipeline not available", exc_info=True)
        return {
            "is_valid": True,
            "errors": [],
            "warnings": [
                "Validation pipeline unavailable. "
                "Config was not validated against the dataset."
            ],
            "normalized_config": None,
        }
    except Exception as e:
        logger.error("Chart validation error: %s", e, exc_info=True)
        return {
            "is_valid": False,
            "errors": [f"Validation system error: {e}"],
            "warnings": [],
            "normalized_config": None,
        }


@tool(
    tags=["discovery", "ai"],
    class_permission_name="Chart",
    annotations=ToolAnnotations(
        title="Validate chart",
        readOnlyHint=True,
        destructiveHint=False,
    ),
)
async def validate_chart(request: ValidateChartRequest, ctx: Context) -> dict[str, Any]:
    """Validate a chart configuration against a dataset without creating anything.

    Runs the full validation pipeline (schema, dataset, runtime) on the
    provided config and dataset_id. Returns whether the config is valid,
    any errors, warnings, and a normalized config (column names corrected
    to match the dataset).

    Use this to pre-flight chart intents from plan_dashboard before calling
    create_chart_from_intent, or to verify a hand-crafted config.

    IMPORTANT FOR LLM CLIENTS:
    - This is a READ-ONLY tool -- nothing is created
    - is_valid=True means the config can be passed to generate_chart safely
    - errors contain blocking issues (invalid column, missing metric, etc.)
    - warnings contain non-blocking suggestions (performance, compatibility)
    - normalized_config has column names corrected to match the dataset

    Example usage:
    ```json
    {
        "dataset_id": 42,
        "config": {
            "chart_type": "xy",
            "kind": "line",
            "x": {"name": "order_date"},
            "y": [{"name": "revenue", "aggregate": "SUM"}],
            "time_grain": "P1M"
        }
    }
    ```
    """
    await ctx.info(
        "Validating chart config: dataset_id=%s, chart_type=%s"
        % (
            request.dataset_id,
            request.config.get("chart_type", "unknown"),
        )
    )

    with mcp_event_log_context(action="mcp.validate_chart.run"):
        result = _run_validation(request.dataset_id, request.config)

        if result["is_valid"]:
            await ctx.info("Chart validation passed")
        else:
            await ctx.warning(
                "Chart validation failed: %d error(s)" % len(result["errors"])
            )

        return ValidateChartResponse(
            is_valid=result["is_valid"],
            errors=result["errors"],
            warnings=result["warnings"],
            normalized_config=result["normalized_config"],
        ).model_dump()

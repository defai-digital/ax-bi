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

"""Simple health check tool for testing MCP service."""

import datetime
import logging
import platform
import time

from flask import current_app
from superset_core.mcp.decorators import tool, ToolAnnotations

from superset import is_feature_enabled
from superset.mcp_service.common.error_schemas import mcp_error_timestamp
from superset.mcp_service.system.schemas import HealthCheckResponse
from superset.mcp_service.utils.config_utils import get_superset_app_name
from superset.mcp_service.utils.logging_utils import mcp_event_log_context
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
from superset.utils.version import get_version_metadata

logger = logging.getLogger(__name__)

_start_time = time.monotonic()


def _build_health_response(service_name: str) -> HealthCheckResponse:
    """Build the authoritative Python MCP health response."""

    try:
        with mcp_event_log_context(action="mcp.health_check.status"):
            # Get version from Superset version metadata
            version_metadata = get_version_metadata()
            version = version_metadata.get("version_string", "unknown")

        response = HealthCheckResponse(
            status="healthy",
            timestamp=mcp_error_timestamp().isoformat(),
            service=service_name,
            version=version,
            python_version=platform.python_version(),
            platform=platform.system(),
            uptime_seconds=round(time.monotonic() - _start_time, 1),
        )

        logger.info("Health check completed successfully")
        return response

    except Exception as e:
        logger.error("Health check failed: %s", e)
        # Return error status but don't raise to keep tool working
        return HealthCheckResponse(
            status="error",
            timestamp=mcp_error_timestamp().isoformat(),
            service=service_name,
            version="unknown",
            python_version=platform.python_version(),
            platform=platform.system(),
        )


def _ax_services_health_candidate() -> AxServicesResponse:
    """Run the TypeScript sidecar health candidate."""

    client = AxServicesClient(AxServicesConfig.from_mapping(current_app.config))
    return client.health()


def _health_response_from_ax_services(
    service_name: str,
    candidate: AxServicesResponse,
) -> HealthCheckResponse | None:
    """Convert a valid ax-services health response to the MCP health schema."""

    payload = candidate.payload or {}
    if not candidate.ok or payload.get("contractVersion") != "runtime.v1":
        return None
    if payload.get("service") != "ax-services" or payload.get("status") != "ok":
        return None

    return HealthCheckResponse(
        status="healthy",
        timestamp=str(payload.get("timestamp") or datetime.datetime.now().isoformat()),
        service=service_name,
        version=str(payload.get("version") or "unknown"),
        python_version=str(payload.get("nodeVersion") or "unknown"),
        platform=str(payload.get("platform") or "unknown"),
        uptime_seconds=float(payload["uptimeSeconds"])
        if isinstance(payload.get("uptimeSeconds"), (int, float))
        else None,
    )


def _health_shadow_matches(
    authoritative: HealthCheckResponse,
    candidate: AxServicesResponse,
) -> bool:
    """Compare Python MCP health with the TypeScript sidecar candidate."""

    return authoritative.status == "healthy" and candidate.ok


def _summarize_health_response(response: HealthCheckResponse) -> dict[str, object]:
    """Summarize the Python health response for shadow mismatch reports."""

    return {
        "status": response.status,
        "service": response.service,
        "version": response.version,
    }


def _summarize_ax_services_health_response(
    response: AxServicesResponse,
) -> dict[str, object]:
    """Summarize the ax-services health response for shadow mismatch reports."""

    payload = response.payload or {}
    if not isinstance(payload, dict):
        payload = {}

    return {
        "ok": response.ok,
        "status_code": response.status_code,
        "contract_version": payload.get("contractVersion"),
        "service": payload.get("service"),
        "status": payload.get("status"),
        "error": response.error,
    }


def _report_health_shadow_mismatch(report: ShadowMismatchReport) -> None:
    """Log a compact health shadow mismatch report."""

    logger.warning(
        "Runtime modernization health shadow mismatch: %s",
        report.to_dict(),
    )


def _health_shadow_enabled() -> bool:
    """Return whether MCP health should shadow through ax-services."""

    return is_feature_enabled("RUNTIME_SHADOW_EXECUTION") and is_feature_enabled(
        "TS_MCP_ORCHESTRATION"
    )


def _health_serving_enabled() -> bool:
    """Return whether MCP health should be served through ax-services."""

    return is_feature_enabled("TS_MCP_ORCHESTRATION") and is_feature_enabled(
        "TS_HEALTH_CHECK_SERVING"
    )


def _record_health_metric(metric: str) -> None:
    current_app.config["STATS_LOGGER"].incr(
        f"runtime_modernization.mcp_orchestration.health_check.{metric}"
    )


@tool(
    tags=["core"],
    annotations=ToolAnnotations(
        title="Health check",
        readOnlyHint=True,
        destructiveHint=False,
    ),
)
async def health_check() -> HealthCheckResponse:
    """
    Simple health check tool for testing the MCP service.

    IMPORTANT: This tool takes NO parameters. Call it without any arguments.

    Returns basic system information and confirms the service is running.
    This is useful for testing connectivity and basic functionality.

    Parameters:
        None - This tool does not accept any parameters

    Returns:
        HealthCheckResponse: Health status and system information including:
            - status: "healthy" or "error"
            - timestamp: ISO format timestamp
            - service: Service name derived from APP_NAME config
            - version: Application version string
            - python_version: Python version
            - platform: Operating system platform

    Example:
        # Correct - no parameters
        health_check()

        # Incorrect - do not pass any arguments
        # health_check(request={})  # This will cause validation errors
    """
    # Get app name from config (safe to do outside try block)
    app_name = get_superset_app_name()
    service_name = f"{app_name} MCP Service"

    with measure_runtime_candidate(
        "mcp_orchestration",
        "health_check",
        current_app.config["STATS_LOGGER"],
    ):
        if _health_serving_enabled():
            candidate_response = _ax_services_health_candidate()
            candidate_health = _health_response_from_ax_services(
                service_name,
                candidate_response,
            )
            if candidate_health is not None:
                _record_health_metric("served_candidate")
                return candidate_health

            _record_health_metric("fallback")
            return _build_health_response(service_name)

        return execute_with_shadow(
            area="mcp_orchestration",
            operation="health_check",
            authoritative=lambda: _build_health_response(service_name),
            candidate=_ax_services_health_candidate,
            compare=_health_shadow_matches,
            stats_logger=current_app.config["STATS_LOGGER"],
            shadow_enabled=_health_shadow_enabled(),
            report_mismatch=_report_health_shadow_mismatch,
            summarize_authoritative=_summarize_health_response,
            summarize_candidate=_summarize_ax_services_health_response,
        )

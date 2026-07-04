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
List reports (alerts & reports) FastMCP tool.
"""

import logging
from typing import Any, TYPE_CHECKING

from fastmcp import Context
from flask import current_app
from superset_core.mcp.decorators import tool, ToolAnnotations

if TYPE_CHECKING:
    from superset.reports.models import ReportSchedule

from superset import is_feature_enabled
from superset.mcp_service.common.schema_discovery import (
    REPORT_DEFAULT_COLUMNS,
    REPORT_SEARCH_COLUMNS,
    REPORT_SORTABLE_COLUMNS,
)
from superset.mcp_service.mcp_core import (
    ModelListCore,
    request_or_default,
    to_zero_based_page,
)
from superset.mcp_service.report.schemas import (
    ListReportsRequest,
    ReportError,
    ReportFilter,
    ReportInfo,
    ReportList,
    serialize_report_object,
)
from superset.mcp_service.system.schemas import PaginationInfo
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


_DEFAULT_LIST_REPORTS_REQUEST = ListReportsRequest()
_REPORT_LIST_CONTRACT_VERSION = "report-list.v1"


def _report_list_request_payload(request: ListReportsRequest) -> dict[str, Any]:
    """Build an ax-services report list request payload."""

    return {
        "contractVersion": _REPORT_LIST_CONTRACT_VERSION,
        "filters": [filter_.model_dump(mode="json") for filter_ in request.filters],
        "selectColumns": list(request.select_columns),
        "search": request.search,
        "orderColumn": request.order_column,
        "orderDirection": request.order_direction,
        "page": request.page,
        "pageSize": request.page_size,
    }


def _ax_services_report_list_candidate(
    request: ListReportsRequest,
) -> AxServicesResponse:
    """Run the TypeScript sidecar report list candidate."""

    client = AxServicesClient(AxServicesConfig.from_mapping(current_app.config))
    return client.list_reports(_report_list_request_payload(request))


def _optional_string(value: Any) -> str | None:
    """Return a string value or None."""

    return value if isinstance(value, str) else None


def _optional_int(value: Any) -> int | None:
    """Return an int value or None."""

    return value if isinstance(value, int) else None


def _optional_bool(value: Any) -> bool | None:
    """Return a bool value or None."""

    return value if isinstance(value, bool) else None


def _report_info_from_ax_services(payload: dict[str, Any]) -> ReportInfo | None:
    """Convert one valid ax-services report item to the MCP schema."""

    report_id = payload.get("id")
    if not isinstance(report_id, int):
        return None

    report = ReportInfo(
        id=report_id,
        name=_optional_string(payload.get("name")),
        description=_optional_string(payload.get("description")),
        type=_optional_string(payload.get("type")),
        active=_optional_bool(payload.get("active")),
        crontab=_optional_string(payload.get("crontab")),
        dashboard_id=_optional_int(payload.get("dashboardId")),
        chart_id=_optional_int(payload.get("chartId")),
        last_eval_dttm=_optional_string(payload.get("lastEvalDttm")),
        last_eval_dttm_humanized=_optional_string(payload.get("lastEvalDttmHumanized")),
        last_state=_optional_string(payload.get("lastState")),
        creation_method=_optional_string(payload.get("creationMethod")),
        owners=None,
        changed_on=_optional_string(payload.get("changedOn")),
        changed_on_humanized=_optional_string(payload.get("changedOnHumanized")),
        created_on=_optional_string(payload.get("createdOn")),
        created_on_humanized=_optional_string(payload.get("createdOnHumanized")),
    )
    report_payload = report.model_dump(mode="python")
    for field_name in ("name", "description"):
        report_payload[field_name] = sanitize_for_llm_context(
            report_payload.get(field_name),
            field_path=(field_name,),
        )
    return ReportInfo(**report_payload)


def _is_string_list(value: Any) -> bool:
    """Return whether a value is a list of strings."""

    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def _report_list_from_ax_services_response(
    response: AxServicesResponse,
) -> dict[str, Any] | None:
    """Convert a valid ax-services report list response to the MCP schema."""

    payload = response.payload or {}
    if (
        not response.ok
        or payload.get("contractVersion") != _REPORT_LIST_CONTRACT_VERSION
    ):
        return None

    raw_reports = payload.get("reports")
    if not isinstance(raw_reports, list):
        return None

    reports = []
    for raw_report in raw_reports:
        if not isinstance(raw_report, dict):
            return None
        report = _report_info_from_ax_services(raw_report)
        if report is None:
            return None
        reports.append(report)

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

    report_list = ReportList(
        reports=reports,
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
        sortable_columns=REPORT_SORTABLE_COLUMNS,
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
    return dump_model_with_select_columns(report_list, columns_requested)


def _report_keys_from_mcp_response(response: dict[str, Any]) -> list[int]:
    """Return report IDs from an MCP report list response."""

    reports = response.get("reports")
    if not isinstance(reports, list):
        return []
    return [
        report["id"]
        for report in reports
        if isinstance(report, dict) and isinstance(report.get("id"), int)
    ]


def _report_keys_from_ax_services_response(response: AxServicesResponse) -> list[int]:
    """Return report IDs from an ax-services report list response."""

    payload = response.payload or {}
    reports = payload.get("reports") if isinstance(payload, dict) else None
    if not isinstance(reports, list):
        return []
    return [
        report["id"]
        for report in reports
        if isinstance(report, dict) and isinstance(report.get("id"), int)
    ]


def _report_list_shadow_matches(
    authoritative: dict[str, Any],
    candidate: AxServicesResponse,
) -> bool:
    """Compare Python and TypeScript report list outputs by ID order."""

    return candidate.ok and _report_keys_from_mcp_response(
        authoritative
    ) == _report_keys_from_ax_services_response(candidate)


def _summarize_report_list_response(response: dict[str, Any]) -> dict[str, object]:
    """Summarize Python report list results for shadow mismatch reports."""

    return {
        "count": len(_report_keys_from_mcp_response(response)),
        "ids": _report_keys_from_mcp_response(response),
    }


def _summarize_ax_services_report_list_response(
    response: AxServicesResponse,
) -> dict[str, object]:
    """Summarize ax-services report list results for shadow mismatch reports."""

    payload = response.payload or {}
    return {
        "ok": response.ok,
        "status_code": response.status_code,
        "contract_version": payload.get("contractVersion")
        if isinstance(payload, dict)
        else None,
        "count": len(_report_keys_from_ax_services_response(response)),
        "ids": _report_keys_from_ax_services_response(response),
        "error": response.error,
    }


def _report_list_shadow_mismatch(report: ShadowMismatchReport) -> None:
    """Log a compact report list shadow mismatch report."""

    logger.warning(
        "Runtime modernization report list shadow mismatch: %s",
        report.to_dict(),
    )


def _report_list_shadow_enabled() -> bool:
    """Return whether report listing should shadow through ax-services."""

    return is_feature_enabled("RUNTIME_SHADOW_EXECUTION") and is_feature_enabled(
        "TS_MCP_ORCHESTRATION"
    )


def _report_list_serving_enabled() -> bool:
    """Return whether report listing should be served through ax-services."""

    return is_feature_enabled("TS_MCP_ORCHESTRATION") and is_feature_enabled(
        "TS_REPORT_LIST_SERVING"
    )


def _record_report_list_metric(metric: str) -> None:
    """Record a report-list migration metric."""

    current_app.config["STATS_LOGGER"].incr(
        f"runtime_modernization.mcp_orchestration.list_reports.{metric}"
    )


@tool(
    tags=["core"],
    class_permission_name="ReportSchedule",
    annotations=ToolAnnotations(
        title="List reports",
        readOnlyHint=True,
        destructiveHint=False,
    ),
)
async def list_reports(
    request: ListReportsRequest | None = None,
    ctx: Context | None = None,
) -> ReportList | ReportError | dict[str, Any]:
    """List alerts and reports with filtering and search.

    Returns schedule metadata including name, type (Alert/Report), active
    status, and cron expression.

    Sortable columns for order_column: id, name, type, active, last_eval_dttm,
    changed_on, created_on
    """
    if ctx is None:
        raise RuntimeError("FastMCP context is required for list_reports")

    request = request_or_default(request, _DEFAULT_LIST_REPORTS_REQUEST)

    if not is_feature_enabled("ALERT_REPORTS"):
        return ReportError.create(
            error="The Alerts & Reports feature is disabled on this instance.",
            error_type="FeatureDisabled",
        )

    with measure_runtime_candidate(
        "mcp_orchestration",
        "list_reports",
        current_app.config["STATS_LOGGER"],
    ):
        if _report_list_serving_enabled():
            candidate_response = _ax_services_report_list_candidate(request)
            candidate_reports = _report_list_from_ax_services_response(
                candidate_response
            )
            if candidate_reports is not None:
                _record_report_list_metric("served_candidate")
                return candidate_reports

            _record_report_list_metric("fallback")
            return await _list_reports_python(request, ctx)

        python_response = await _list_reports_python(request, ctx)
        return execute_with_shadow(
            area="mcp_orchestration",
            operation="list_reports",
            authoritative=lambda: python_response,
            candidate=lambda: _ax_services_report_list_candidate(request),
            compare=_report_list_shadow_matches,
            stats_logger=current_app.config["STATS_LOGGER"],
            shadow_enabled=_report_list_shadow_enabled(),
            report_mismatch=_report_list_shadow_mismatch,
            summarize_authoritative=_summarize_report_list_response,
            summarize_candidate=_summarize_ax_services_report_list_response,
        )


async def _list_reports_python(
    request: ListReportsRequest,
    ctx: Context,
) -> dict[str, Any]:
    """Run the authoritative Python report list path."""

    await ctx.info(
        f"Listing reports: page={request.page}, "
        f"page_size={request.page_size}, search={request.search}"
    )
    await ctx.debug(
        f"Report listing parameters: filters={request.filters}, "
        f"order_column={request.order_column}, "
        f"order_direction={request.order_direction}, "
        f"select_columns={request.select_columns}"
    )

    try:
        from superset.daos.report import ReportScheduleDAO

        def _serialize_report(
            obj: "ReportSchedule | None", _cols: list[str] | None
        ) -> ReportInfo | None:
            return serialize_report_object(obj)

        list_tool = ModelListCore(
            dao_class=ReportScheduleDAO,
            output_schema=ReportInfo,
            item_serializer=_serialize_report,
            filter_type=ReportFilter,
            default_columns=REPORT_DEFAULT_COLUMNS,
            search_columns=REPORT_SEARCH_COLUMNS,
            list_field_name="reports",
            output_list_schema=ReportList,
            all_columns=list(ReportInfo.model_fields.keys()),
            sortable_columns=REPORT_SORTABLE_COLUMNS,
            owner_filter_column="owners.id",
            logger=logger,
        )

        with mcp_event_log_context(action="mcp.list_reports.query"):
            result = list_tool.run_tool(
                filters=request.filters,
                search=request.search,
                select_columns=request.select_columns,
                order_column=request.order_column,
                order_direction=request.order_direction,
                page=to_zero_based_page(request.page),
                page_size=request.page_size,
                created_by_me=request.created_by_me,
                owned_by_me=request.owned_by_me,
            )

        return await finalize_list_response(result, "reports", "Reports", ctx)

    except Exception as e:  # noqa: BLE001
        await ctx.error(
            f"Report listing failed: page={request.page}, "
            f"page_size={request.page_size}, error={str(e)}, "
            f"error_type={type(e).__name__}"
        )
        return ReportError.create(
            error=f"Failed to list reports: {str(e)}",
            error_type="InternalError",
        )

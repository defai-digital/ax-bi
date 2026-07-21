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
MCP tool: create_report

Create a scheduled email or Slack report for a dashboard or chart.
"""

import logging
from typing import Any, Literal

from axbi_core.mcp.decorators import tool, ToolAnnotations
from fastmcp import Context
from pydantic import BaseModel, Field
from sqlalchemy.exc import SQLAlchemyError

from axbi.mcp_service.common.error_schemas import SanitizeOptionalErrorMixin
from axbi.mcp_service.utils.logging_utils import mcp_event_log_context
from axbi.mcp_service.utils.session_utils import rollback_session_safely

logger = logging.getLogger(__name__)


class RecipientConfig(BaseModel):
    """Recipient configuration for a report."""

    type: Literal["Email", "Slack", "SlackV2"] = Field(
        default="Email",
        description="Recipient type: Email, Slack, or SlackV2",
    )
    target: str = Field(
        ...,
        description="Email address or Slack channel name/ID",
    )


class CreateReportRequest(BaseModel):
    """Request schema for create_report."""

    name: str = Field(
        ...,
        description="Unique name for this report schedule",
    )
    report_type: Literal["Report", "Alert"] = Field(
        default="Report",
        description="'Report' for scheduled reports, 'Alert' for threshold alerts",
    )
    description: str | None = Field(
        default=None,
        description="Description of the report",
    )
    crontab: str = Field(
        default="0 8 * * 1",
        description=(
            "Cron expression for scheduling. Default: every Monday at 8am UTC. "
            "Examples: '0 8 * * *' (daily 8am), '0 */6 * * *' (every 6 hours), "
            "'0 8 * * 1-5' (weekdays 8am)"
        ),
    )
    timezone: str = Field(
        default="UTC",
        description="Timezone for the schedule (e.g. 'US/Eastern', 'Europe/London')",
    )
    active: bool = Field(
        default=True,
        description="Whether the report schedule is active",
    )
    dashboard_id: int | None = Field(
        default=None,
        description="Dashboard ID to report on. Use either dashboard_id or chart_id.",
    )
    chart_id: int | None = Field(
        default=None,
        description="Chart ID to report on. Use either dashboard_id or chart_id.",
    )
    report_format: Literal["PNG", "PDF", "CSV", "TEXT"] = Field(
        default="PNG",
        description="Format for the report content",
    )
    recipients: list[RecipientConfig] = Field(
        default_factory=list,
        description=(
            "List of recipients. When empty, defaults to the current user's email."
        ),
    )
    email_subject: str | None = Field(
        default=None,
        description="Custom email subject (defaults to report name)",
    )
    # Alert-specific fields
    sql: str | None = Field(
        default=None,
        description="SQL query for alert value (Alert type only)",
    )
    database_id: int | None = Field(
        default=None,
        description="Database ID for the alert SQL query (Alert type only)",
    )
    validator_type: Literal["not null", "operator"] | None = Field(
        default=None,
        description="Alert validator type: 'not null' or 'operator'",
    )
    validator_config: dict[str, Any] | None = Field(
        default=None,
        description="Validator config (e.g. {'op': '>', 'value': 100} for operator)",
    )


class CreateReportResponse(SanitizeOptionalErrorMixin):
    """Response schema for create_report."""

    report: dict[str, Any] | None = Field(
        default=None,
        description="Created report schedule metadata",
    )
    report_id: int | None = Field(default=None)
    error: str | None = Field(default=None)


@tool(
    tags=["mutate"],
    class_permission_name="ReportSchedule",
    annotations=ToolAnnotations(
        title="Create report/alert",
        readOnlyHint=False,
        destructiveHint=False,
    ),
)
def create_report(  # noqa: C901
    request: CreateReportRequest,
    ctx: Context,
) -> CreateReportResponse:
    """Create a scheduled report or alert.

    Schedule email/Slack delivery of dashboard screenshots or chart data.
    For reports, specify a dashboard_id or chart_id. For alerts, specify
    a SQL query and database_id with validator configuration.

    Example: Weekly dashboard report:
    ```json
    {
        "name": "Weekly Sales Report",
        "report_type": "Report",
        "dashboard_id": 5,
        "crontab": "0 8 * * 1",
        "recipients": [{"type": "Email", "target": "team@company.com"}]
    }
    ```

    Example: Threshold alert:
    ```json
    {
        "name": "Revenue Alert",
        "report_type": "Alert",
        "sql": "SELECT SUM(revenue) FROM orders WHERE date = CURRENT_DATE",
        "database_id": 1,
        "validator_type": "operator",
        "validator_config": {"op": "<", "value": 10000}
    }
    ```
    """
    try:
        from axbi import is_feature_enabled

        if not is_feature_enabled("ALERT_REPORTS"):
            return CreateReportResponse(
                error="The Alerts & Reports feature is disabled on this instance."
            )

        from axbi.commands.report.create import CreateReportScheduleCommand
        from axbi.reports.models import (
            ReportCreationMethod,
        )

        # Validate that either dashboard or chart is specified for reports
        if (
            request.report_type == "Report"
            and not request.dashboard_id
            and not request.chart_id
        ):
            return CreateReportResponse(
                error="Reports require either dashboard_id or chart_id."
            )

        # Build recipients
        recipients: list[dict[str, Any]] = []
        for r in request.recipients:
            recipients.append(
                {
                    "type": r.type,
                    "recipient_config_json": {"target": r.target},
                }
            )

        # Determine creation_method
        if request.chart_id:
            creation_method = ReportCreationMethod.CHARTS
        elif request.dashboard_id:
            creation_method = ReportCreationMethod.DASHBOARDS
        else:
            creation_method = ReportCreationMethod.ALERTS_REPORTS

        # Build attributes for the command
        with mcp_event_log_context(action="mcp.create_report.build"):
            attributes: dict[str, Any] = {
                "type": request.report_type,
                "name": request.name,
                "description": request.description or "",
                "active": request.active,
                "crontab": request.crontab,
                "timezone": request.timezone,
                "report_format": request.report_format,
                "creation_method": creation_method,
                "recipients": recipients if recipients else None,
            }

            if request.dashboard_id:
                attributes["dashboard"] = request.dashboard_id
            if request.chart_id:
                attributes["chart"] = request.chart_id
            if request.email_subject:
                attributes["email_subject"] = request.email_subject

            # Alert-specific fields
            if request.report_type == "Alert":
                if request.sql:
                    attributes["sql"] = request.sql
                if request.database_id:
                    attributes["database"] = request.database_id
                if request.validator_type:
                    attributes["validator_type"] = request.validator_type
                if request.validator_config:
                    from axbi.utils import json as sjson

                    attributes["validator_config_json"] = sjson.dumps(
                        request.validator_config
                    )

        # Create the report schedule
        with mcp_event_log_context(action="mcp.create_report.db_write"):
            command = CreateReportScheduleCommand(attributes)
            report_schedule = command.run()

        logger.info(
            "Created report schedule %s (ID: %s)", request.name, report_schedule.id
        )

        return CreateReportResponse(
            report={
                "id": report_schedule.id,
                "name": report_schedule.name,
                "type": report_schedule.type,
                "active": report_schedule.active,
                "crontab": report_schedule.crontab,
                "timezone": report_schedule.timezone,
            },
            report_id=report_schedule.id,
            error=None,
        )

    except SQLAlchemyError as e:
        rollback_session_safely(context="report creation error handling")
        logger.error("Error creating report: %s", e)
        return CreateReportResponse(error=f"Failed to create report: {str(e)}")
    except Exception as e:  # noqa: BLE001
        logger.error("Error creating report: %s", e)
        return CreateReportResponse(error=f"Failed to create report: {str(e)}")

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
import logging
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from datetime import datetime, timedelta
from time import monotonic
from typing import Any, cast
from uuid import UUID

import pandas as pd
from celery.exceptions import SoftTimeLimitExceeded
from flask import current_app as app

from axbi import db, security_manager
from axbi.commands.base import BaseCommand
from axbi.commands.dashboard.permalink.create import CreateDashboardPermalinkCommand
from axbi.commands.exceptions import CommandException, UpdateFailedError
from axbi.commands.report.alert import AlertCommand
from axbi.commands.report.exceptions import (
    ReportScheduleAlertGracePeriodError,
    ReportScheduleClientErrorsException,
    ReportScheduleCsvFailedError,
    ReportScheduleCsvTimeout,
    ReportScheduleDataFrameFailedError,
    ReportScheduleDataFrameTimeout,
    ReportScheduleExecuteUnexpectedError,
    ReportScheduleNotFoundError,
    ReportSchedulePreviousWorkingError,
    ReportScheduleScreenshotFailedError,
    ReportScheduleScreenshotTimeout,
    ReportScheduleStateNotFoundError,
    ReportScheduleSystemErrorsException,
    ReportScheduleUnexpectedError,
    ReportScheduleWorkingTimeoutError,
)
from axbi.common.chart_data import ChartDataResultFormat, ChartDataResultType
from axbi.daos.report import (
    REPORT_SCHEDULE_ERROR_NOTIFICATION_MARKER,
    ReportExecutionLogDAO,
    ReportScheduleDAO,
)
from axbi.dashboards.permalink.types import DashboardPermalinkState
from axbi.errors import AxBIError, AxBIErrorType, ErrorLevel
from axbi.exceptions import AxBIErrorsException, AxBIException
from axbi.extensions import feature_flag_manager, machine_auth_provider_factory
from axbi.reports.models import (
    ReportDataFormat,
    ReportRecipients,
    ReportRecipientType,
    ReportSchedule,
    ReportScheduleType,
    ReportSourceFormat,
    ReportState,
)
from axbi.reports.notifications import create_notification
from axbi.reports.notifications.base import NotificationContent
from axbi.reports.notifications.exceptions import (
    NotificationError,
    NotificationParamException,
    SlackV1NotificationError,
)
from axbi.tasks.utils import get_executor
from axbi.utils import json
from axbi.utils.core import HeaderDataType, override_user, recipients_string_to_list
from axbi.utils.csv import get_chart_csv_data, get_chart_dataframe
from axbi.utils.dates import naive_utcnow
from axbi.utils.decorators import logs_context, transaction
from axbi.utils.file import sanitize_title
from axbi.utils.pdf import build_pdf_from_screenshots
from axbi.utils.screenshots import ChartScreenshot, DashboardScreenshot
from axbi.utils.slack import get_channels_with_search, SlackChannelTypes
from axbi.utils.urls import get_url_path

logger = logging.getLogger(__name__)


def _get_slack_channel_name_and_id(channel: object) -> tuple[str, str] | None:
    if not isinstance(channel, dict):
        return None

    name = channel.get("name")
    channel_id = channel.get("id")
    if not isinstance(name, str) or not isinstance(channel_id, str):
        return None

    return name, channel_id


@contextmanager
def _log_timed_operation(operation: str, execution_id: UUID) -> Iterator[None]:
    """Log a report operation's monotonic duration on completion or failure."""
    started_at = monotonic()
    try:
        yield
    except SoftTimeLimitExceeded:
        logger.warning(
            "%s timed out after %.2fs - execution_id: %s",
            operation,
            monotonic() - started_at,
            execution_id,
        )
        raise
    except Exception:
        logger.exception(
            "%s failed after %.2fs - execution_id: %s",
            operation,
            monotonic() - started_at,
            execution_id,
        )
        raise
    else:
        logger.info(
            "%s completed in %.2fs - execution_id: %s",
            operation,
            monotonic() - started_at,
            execution_id,
        )


class BaseReportState:
    current_states: list[ReportState] = []
    initial: bool = False

    @logs_context()
    def __init__(
        self,
        report_schedule: ReportSchedule,
        scheduled_dttm: datetime,
        execution_id: UUID,
    ) -> None:
        self._report_schedule = report_schedule
        self._scheduled_dttm = scheduled_dttm
        self._start_dttm = naive_utcnow()
        self._execution_id = execution_id
        self._filter_warnings: list[str] = []

    def update_report_schedule_and_log(
        self,
        state: ReportState,
        error_message: str | None = None,
    ) -> None:
        """
        Update the report schedule state et al. and reflect the change in the execution
        log.
        """
        self.update_report_schedule(state)
        self.create_log(error_message)

    def update_report_schedule(self, state: ReportState) -> None:
        """
        Update the report schedule state et al.

        When the report state is WORKING we must ensure that the values from the last
        execution run are cleared to ensure that they are not propagated to the
        execution log.
        """

        ReportScheduleDAO.set_execution_state(
            self._report_schedule,
            state,
            evaluated_at=naive_utcnow(),
        )

    def update_report_schedule_slack_v2(self) -> None:
        """
        Update the report schedule type and channels for all slack recipients to v2.
        V2 uses ids instead of names for channels.
        """
        original_recipients = [
            (recipient, recipient.type, recipient.recipient_config_json)
            for recipient in self._report_schedule.recipients
        ]
        try:
            for recipient in self._report_schedule.recipients:
                if recipient.type == ReportRecipientType.SLACK:
                    recipient.type = ReportRecipientType.SLACKV2
                    slack_recipients = json.loads(recipient.recipient_config_json)
                    # V1 method allowed to use leading `#` in the channel name
                    channel_names = (slack_recipients["target"] or "").replace("#", "")
                    # we need to ensure that existing reports can also fetch
                    # ids from private channels
                    channels = get_channels_with_search(
                        search_string=channel_names,
                        types=[
                            SlackChannelTypes.PRIVATE,
                            SlackChannelTypes.PUBLIC,
                        ],
                        exact_match=True,
                    )
                    channels_list = recipients_string_to_list(channel_names)
                    channel_names_and_ids = [
                        name_and_id
                        for channel in channels
                        if (name_and_id := _get_slack_channel_name_and_id(channel))
                    ]
                    if len(channels_list) != len(channel_names_and_ids):
                        missing_channels = set(channels_list) - {
                            name for name, _ in channel_names_and_ids
                        }
                        msg = (
                            "Could not find the following channels: "
                            f"{', '.join(missing_channels)}"
                        )
                        raise UpdateFailedError(msg)
                    channel_ids = ",".join(
                        channel_id for _, channel_id in channel_names_and_ids
                    )
                    recipient.recipient_config_json = json.dumps(
                        {
                            "target": channel_ids,
                        }
                    )
        except Exception as ex:
            # Revert all in-memory recipient mutations to preserve configuration.
            for (
                original_recipient,
                original_type,
                original_config,
            ) in original_recipients:
                original_recipient.type = original_type
                original_recipient.recipient_config_json = original_config
            msg = f"Failed to update slack recipients to v2: {str(ex)}"
            logger.exception(msg)
            raise UpdateFailedError(msg) from ex

    def create_log(self, error_message: str | None = None) -> None:
        """
        Creates a Report execution log, uses the current computed last_value for Alerts
        """
        from sqlalchemy.orm.exc import StaleDataError

        try:
            ReportExecutionLogDAO.create_for_schedule(
                report_schedule=self._report_schedule,
                scheduled_dttm=self._scheduled_dttm,
                start_dttm=self._start_dttm,
                end_dttm=naive_utcnow(),
                error_message=error_message,
                execution_id=self._execution_id,
            )
            db.session.commit()  # pylint: disable=consider-using-transaction
        except StaleDataError as ex:
            # Report schedule was modified or deleted by another process
            db.session.rollback()  # pylint: disable=consider-using-transaction
            logger.warning(
                "Report schedule (execution %s) was modified or deleted "
                "during execution. This can occur when a report is deleted "
                "while running.",
                self._execution_id,
            )
            raise ReportScheduleUnexpectedError(
                "Report schedule was modified or deleted by another process "
                "during execution"
            ) from ex

    def _get_url(
        self,
        user_friendly: bool = False,
        result_format: ChartDataResultFormat | None = None,
        **kwargs: Any,
    ) -> str:
        """
        Get the url for this report schedule: chart or dashboard
        """
        force = "true" if self._report_schedule.force_screenshot else "false"
        if self._report_schedule.chart:
            if result_format in {
                ChartDataResultFormat.CSV,
                ChartDataResultFormat.JSON,
            }:
                return get_url_path(
                    "ChartDataRestApi.get_data",
                    pk=self._report_schedule.chart_id,
                    format=result_format.value,
                    type=ChartDataResultType.POST_PROCESSED.value,
                    force=force,
                )
            return get_url_path(
                "ExploreView.root",
                user_friendly=user_friendly,
                form_data=json.dumps({"slice_id": self._report_schedule.chart_id}),
                force=force,
                **kwargs,
            )
        # If we need to render dashboard in a specific state, use stateful permalink
        if (
            dashboard_state := self._report_schedule.extra.get("dashboard")
        ) and feature_flag_manager.is_feature_enabled("ALERT_REPORT_TABS"):
            return self._get_tab_url(dashboard_state, user_friendly=user_friendly)

        dashboard = self._report_schedule.dashboard
        dashboard_id_or_slug = (
            dashboard.uuid if dashboard and dashboard.uuid else dashboard.id
        )
        return get_url_path(
            "AxBI.dashboard",
            user_friendly=user_friendly,
            dashboard_id_or_slug=dashboard_id_or_slug,
            force=force,
            **kwargs,
        )

    @staticmethod
    def _normalize_dashboard_anchor(
        dashboard_state: DashboardPermalinkState,
    ) -> tuple[DashboardPermalinkState, str | None]:
        anchor = dashboard_state.get("anchor")
        if not anchor:
            return dashboard_state, None
        if isinstance(anchor, str):
            return dashboard_state, anchor

        logger.debug("Ignoring malformed dashboard tab anchor")
        sanitized_dashboard_state = cast(DashboardPermalinkState, {**dashboard_state})
        sanitized_dashboard_state.pop("anchor", None)
        return sanitized_dashboard_state, None

    def get_dashboard_urls(
        self, user_friendly: bool = False, **kwargs: Any
    ) -> list[str]:
        """
        Retrieve the URL for the dashboard tabs, or return the dashboard URL if no tabs are available.
        """  # noqa: E501
        force = "true" if self._report_schedule.force_screenshot else "false"
        extra = self._report_schedule.extra
        dashboard_state = extra.get("dashboard", {}) if isinstance(extra, dict) else {}
        if not isinstance(dashboard_state, dict):
            dashboard_state = {}

        if dashboard_state and feature_flag_manager.is_feature_enabled(
            "ALERT_REPORT_TABS"
        ):
            native_filter_params, filter_warnings = (
                self._report_schedule.get_native_filters_params()
            )
            if filter_warnings:
                self._filter_warnings.extend(filter_warnings)
            dashboard_state, anchor = self._normalize_dashboard_anchor(dashboard_state)

            if anchor:
                try:
                    anchor_list = json.loads(anchor)
                    if not isinstance(anchor_list, list) or not all(
                        isinstance(tab_anchor, str) for tab_anchor in anchor_list
                    ):
                        raise json.JSONDecodeError(
                            "Anchor value is not a list", anchor, 0
                        )
                    return self._get_tabs_urls(
                        anchor_list,
                        dashboard_state=dashboard_state,
                        native_filter_params=native_filter_params,
                        user_friendly=user_friendly,
                    )
                except (TypeError, json.JSONDecodeError):
                    logger.debug("Anchor value is not a list, Fall back to single tab")

            # Skip the permalink when there is nothing meaningful to encode —
            # an empty dashboard_state falls through to the plain URL below.
            # A non-empty anchor means a single tab was selected (it failed
            # JSON list parsing above) and still needs a permalink. Non-filter
            # state such as urlParams (e.g. standalone=true) must also be
            # preserved via a permalink.
            if (
                anchor
                or dashboard_state.get("urlParams")
                or (native_filter_params and native_filter_params != "()")
            ):
                state: DashboardPermalinkState = {**dashboard_state}
                state["urlParams"] = self._merge_native_filters_into_url_params(
                    state.get("urlParams"), native_filter_params
                )
                return [
                    self._get_tab_url(
                        state,
                        user_friendly=user_friendly,
                    )
                ]

        native_filter_params, filter_warnings = (
            self._report_schedule.get_native_filters_params()
        )
        if filter_warnings:
            self._filter_warnings.extend(filter_warnings)
        if native_filter_params and native_filter_params != "()":
            # Preserve any urlParams from extra.dashboard (e.g. standalone=true)
            # set via API even when ALERT_REPORT_TABS is off — same merge
            # semantics as the protected branch above.
            return [
                self._get_tab_url(
                    {
                        "urlParams": self._merge_native_filters_into_url_params(
                            dashboard_state.get("urlParams"),
                            native_filter_params,
                        )
                    },
                    user_friendly=user_friendly,
                )
            ]

        dashboard = self._report_schedule.dashboard
        dashboard_id_or_slug = (
            dashboard.uuid if dashboard and dashboard.uuid else dashboard.id
        )

        return [
            get_url_path(
                "AxBI.dashboard",
                user_friendly=user_friendly,
                dashboard_id_or_slug=dashboard_id_or_slug,
                force=force,
                **kwargs,
            )
        ]

    def _get_tab_url(
        self, dashboard_state: DashboardPermalinkState, user_friendly: bool = False
    ) -> str:
        """
        Get one tab url
        """
        permalink_key = CreateDashboardPermalinkCommand(
            dashboard_id=str(self._report_schedule.dashboard.uuid),
            state=dashboard_state,
        ).run()

        return get_url_path(
            "AxBI.dashboard_permalink",
            key=permalink_key,
            user_friendly=user_friendly,
        )

    @staticmethod
    def _merge_native_filters_into_url_params(
        existing: Sequence[Sequence[str]] | None,
        native_filter_params: str | None,
    ) -> list[Sequence[str]]:
        """
        Merge the report's ``native_filters`` into a permalink's existing
        ``urlParams``, deduping any prior ``native_filters`` entry so the
        report's value wins. All other params (e.g. ``standalone=true``)
        survive in their original order.
        """
        merged: list[Sequence[str]] = []
        for param in existing or []:
            if (
                isinstance(param, Sequence)
                and not isinstance(param, str | bytes)
                and param
                and param[0] != "native_filters"
            ):
                merged.append(list(param))
        merged.append(["native_filters", native_filter_params or ""])
        return merged

    def _get_tabs_urls(
        self,
        tab_anchors: list[str],
        dashboard_state: DashboardPermalinkState | None = None,
        native_filter_params: str | None = None,
        user_friendly: bool = False,
    ) -> list[str]:
        """
        Get multiple tabs urls.

        Each per-tab permalink merges the report's ``native_filters`` into
        the original ``dashboard_state.urlParams`` (deduping any prior
        ``native_filters`` entry), so params like ``standalone=true`` are
        preserved — matching the precedence rules of the single-tab branch
        in :meth:`get_dashboard_urls`.
        """
        base_state: DashboardPermalinkState = dashboard_state or {}
        merged_params = self._merge_native_filters_into_url_params(
            base_state.get("urlParams"), native_filter_params
        )
        return [
            self._get_tab_url(
                {
                    "anchor": tab_anchor,
                    "dataMask": None,
                    "activeTabs": None,
                    "urlParams": merged_params,
                },
                user_friendly=user_friendly,
            )
            for tab_anchor in tab_anchors
        ]

    def _get_screenshots(self) -> list[bytes]:
        """
        Get chart or dashboard screenshots
        :raises: ReportScheduleScreenshotFailedError
        """
        _, username = get_executor(
            executors=app.config["ALERT_REPORTS_EXECUTORS"],
            model=self._report_schedule,
        )
        user = security_manager.find_user(username)

        max_width = app.config["ALERT_REPORTS_MAX_CUSTOM_SCREENSHOT_WIDTH"]

        if self._report_schedule.chart:
            url = self._get_url()

            window_width, window_height = app.config["WEBDRIVER_WINDOW"]["slice"]
            width = min(max_width, self._report_schedule.custom_width or window_width)
            height = self._report_schedule.custom_height or window_height
            window_size = (width, height)

            screenshots: list[ChartScreenshot | DashboardScreenshot] = [
                ChartScreenshot(
                    url,
                    self._report_schedule.chart.digest,
                    window_size=window_size,
                    thumb_size=app.config["WEBDRIVER_WINDOW"]["slice"],
                )
            ]
        else:
            urls = self.get_dashboard_urls()
            window_width, window_height = app.config["WEBDRIVER_WINDOW"]["dashboard"]
            width = min(max_width, self._report_schedule.custom_width or window_width)
            height = self._report_schedule.custom_height or window_height
            window_size = (width, height)

            screenshots = [
                DashboardScreenshot(
                    url,
                    self._report_schedule.dashboard.digest,
                    window_size=window_size,
                    thumb_size=app.config["WEBDRIVER_WINDOW"]["dashboard"],
                )
                for url in urls
            ]
        imges: list[bytes] = []
        try:
            with _log_timed_operation("Screenshot capture", self._execution_id):
                for screenshot in screenshots:
                    imge = screenshot.get_screenshot(user=user)
                    if imge is None:
                        raise ReportScheduleScreenshotFailedError(
                            "Screenshot failed; aborting to avoid sending a partial "
                            "report"
                        )
                    imges.append(imge)
        except SoftTimeLimitExceeded as ex:
            raise ReportScheduleScreenshotTimeout() from ex
        except Exception as ex:
            raise ReportScheduleScreenshotFailedError(
                f"Failed taking a screenshot {str(ex)}"
            ) from ex
        if not imges:
            raise ReportScheduleScreenshotFailedError()
        return imges

    def _get_pdf(self) -> bytes:
        """
        Get chart or dashboard pdf
        :raises: ReportSchedulePdfFailedError
        """
        screenshots = self._get_screenshots()
        return build_pdf_from_screenshots(screenshots)

    def _get_csv_data(self) -> bytes:
        url = self._get_url(result_format=ChartDataResultFormat.CSV)
        _, username = get_executor(
            executors=app.config["ALERT_REPORTS_EXECUTORS"],
            model=self._report_schedule,
        )
        user = security_manager.find_user(username)
        auth_cookies = machine_auth_provider_factory.instance.get_auth_cookies(user)

        if self._report_schedule.chart.query_context is None:
            logger.warning("No query context found, taking a screenshot to generate it")
            self._update_query_context()

        csv_data: bytes | None = None
        try:
            operation = f"CSV data generation from {url} as user {username}"
            with _log_timed_operation(operation, self._execution_id):
                csv_data = get_chart_csv_data(
                    chart_url=url,
                    auth_cookies=auth_cookies,
                    timeout=app.config["ALERT_REPORTS_CSV_REQUEST_TIMEOUT"],
                )
        except SoftTimeLimitExceeded as ex:
            raise ReportScheduleCsvTimeout() from ex
        except Exception as ex:
            raise ReportScheduleCsvFailedError(
                f"Failed generating csv {str(ex)}"
            ) from ex
        if not csv_data:
            raise ReportScheduleCsvFailedError()
        return csv_data

    def _get_embedded_data(self) -> pd.DataFrame:
        """
        Return data as a Pandas dataframe, to embed in notifications as a table.
        """
        url = self._get_url(result_format=ChartDataResultFormat.JSON)
        _, username = get_executor(
            executors=app.config["ALERT_REPORTS_EXECUTORS"],
            model=self._report_schedule,
        )
        user = security_manager.find_user(username)
        auth_cookies = machine_auth_provider_factory.instance.get_auth_cookies(user)

        if self._report_schedule.chart.query_context is None:
            logger.warning("No query context found, taking a screenshot to generate it")
            self._update_query_context()

        dataframe: pd.DataFrame | None = None
        try:
            operation = f"DataFrame generation from {url} as user {username}"
            with _log_timed_operation(operation, self._execution_id):
                dataframe = get_chart_dataframe(
                    url,
                    auth_cookies,
                    timeout=app.config["ALERT_REPORTS_CSV_REQUEST_TIMEOUT"],
                )
        except SoftTimeLimitExceeded as ex:
            raise ReportScheduleDataFrameTimeout() from ex
        except Exception as ex:
            raise ReportScheduleDataFrameFailedError(
                f"Failed generating dataframe {str(ex)}"
            ) from ex
        if dataframe is None:
            raise ReportScheduleCsvFailedError()
        return dataframe

    def _update_query_context(self) -> None:
        """
        Update chart query context.

        To load CSV data from the endpoint the chart must have been saved
        with its query context. For charts without saved query context we
        get a screenshot to force the chart to produce and save the query
        context.
        """
        try:
            self._get_screenshots()
        except (
            ReportScheduleScreenshotFailedError,
            ReportScheduleScreenshotTimeout,
        ) as ex:
            raise ReportScheduleCsvFailedError(
                "Unable to fetch data because the chart has no query context "
                "saved, and an error occurred when fetching it via a screenshot. "
                "Please try loading the chart and saving it again."
            ) from ex

    def _get_log_data(self) -> HeaderDataType:
        chart_id = None
        dashboard_id = None
        report_source = None
        slack_channels = None
        if self._report_schedule.chart:
            report_source = ReportSourceFormat.CHART
            chart_id = self._report_schedule.chart_id
        else:
            report_source = ReportSourceFormat.DASHBOARD
            dashboard_id = self._report_schedule.dashboard_id

        if self._report_schedule.recipients:
            slack_channels = [
                recipient.recipient_config_json
                for recipient in self._report_schedule.recipients
                if recipient.type
                in [ReportRecipientType.SLACK, ReportRecipientType.SLACKV2]
            ]

        log_data: HeaderDataType = {
            "notification_type": self._report_schedule.type,
            "notification_source": report_source,
            "notification_format": self._report_schedule.report_format,
            "chart_id": chart_id,
            "dashboard_id": dashboard_id,
            "owners": self._report_schedule.owners,
            "slack_channels": slack_channels,
            "execution_id": str(self._execution_id),
        }
        return log_data

    def _get_notification_content(self) -> NotificationContent:  # noqa: C901
        """
        Gets a notification content, this is composed by a title and a screenshot

        :raises: ReportScheduleScreenshotFailedError
        """
        csv_data = None
        screenshot_data = []
        pdf_data = None
        embedded_data = None
        error_text = None
        header_data = self._get_log_data()
        url = self._get_url(user_friendly=True)

        if (
            feature_flag_manager.is_feature_enabled("ALERTS_ATTACH_REPORTS")
            or self._report_schedule.type == ReportScheduleType.REPORT
        ):
            if self._report_schedule.report_format == ReportDataFormat.PNG:
                screenshot_data = self._get_screenshots()
                if not screenshot_data:
                    error_text = "Unexpected missing screenshot"
            elif self._report_schedule.report_format == ReportDataFormat.PDF:
                pdf_data = self._get_pdf()
                if not pdf_data:
                    error_text = "Unexpected missing pdf"
            elif (
                self._report_schedule.chart
                and self._report_schedule.report_format == ReportDataFormat.CSV
            ):
                csv_data = self._get_csv_data()
                if not csv_data:
                    error_text = "Unexpected missing csv file"
            if error_text:
                return NotificationContent(
                    name=sanitize_title(self._report_schedule.name),
                    text=error_text,
                    header_data=header_data,
                    url=url,
                )

        if (
            self._report_schedule.chart
            and self._report_schedule.report_format == ReportDataFormat.TEXT
        ):
            embedded_data = self._get_embedded_data()

        if self._report_schedule.email_subject:
            name = sanitize_title(self._report_schedule.email_subject)
        else:
            if self._report_schedule.chart:
                name = sanitize_title(
                    f"{self._report_schedule.name}: "
                    f"{self._report_schedule.chart.slice_name}"
                )
            else:
                name = sanitize_title(
                    f"{self._report_schedule.name}: "
                    f"{self._report_schedule.dashboard.dashboard_title}"
                )

        return NotificationContent(
            name=name,
            url=url,
            screenshots=screenshot_data,
            pdf=pdf_data,
            description=self._report_schedule.description,
            csv=csv_data,
            embedded_data=embedded_data,
            header_data=header_data,
        )

    def _send(
        self,
        notification_content: NotificationContent,
        recipients: list[ReportRecipients],
    ) -> None:
        """
        Sends a notification to all recipients

        :raises: CommandException
        """
        notification_errors: list[AxBIError] = []
        for recipient in recipients:
            notification = create_notification(recipient, notification_content)
            try:
                try:
                    if app.config["ALERT_REPORTS_NOTIFICATION_DRY_RUN"]:
                        logger.info(
                            "Would send notification for alert %s, to %s. "
                            "ALERT_REPORTS_NOTIFICATION_DRY_RUN is enabled, "
                            "set it to False to send notifications.",
                            self._report_schedule.name,
                            recipient.recipient_config_json,
                        )
                    else:
                        notification.send()
                except SlackV1NotificationError as ex:
                    # The slack notification should be sent with the v2 api
                    logger.info(
                        "Attempting to upgrade the report to Slackv2: %s", str(ex)
                    )
                    self.update_report_schedule_slack_v2()
                    recipient.type = ReportRecipientType.SLACKV2
                    notification = create_notification(recipient, notification_content)
                    notification.send()
            except (
                UpdateFailedError,
                NotificationParamException,
                NotificationError,
                AxBIException,
            ) as ex:
                # collect errors but keep processing them
                notification_errors.append(
                    AxBIError(
                        message=ex.message,
                        error_type=AxBIErrorType.REPORT_NOTIFICATION_ERROR,
                        level=(
                            ErrorLevel.ERROR if ex.status >= 500 else ErrorLevel.WARNING
                        ),
                    )
                )
        if notification_errors:
            # log all errors but raise based on the most severe
            for error in notification_errors:
                logger.warning(str(error))

            if any(error.level == ErrorLevel.ERROR for error in notification_errors):
                raise ReportScheduleSystemErrorsException(errors=notification_errors)
            if any(error.level == ErrorLevel.WARNING for error in notification_errors):
                raise ReportScheduleClientErrorsException(errors=notification_errors)

    def send(self) -> None:
        """
        Creates the notification content and sends them to all recipients

        :raises: CommandException
        """
        notification_content = self._get_notification_content()
        self._send(notification_content, self._report_schedule.recipients)

    def send_error(self, name: str, message: str) -> None:
        """
        Creates and sends a notification for an error, to all recipients

        :raises: CommandException
        """
        header_data = self._get_log_data()
        url = self._get_url(user_friendly=True)
        logger.info(
            "header_data in notifications for alerts and reports %s, taskid, %s",
            header_data,
            self._execution_id,
        )
        notification_content = NotificationContent(
            name=sanitize_title(name), text=message, header_data=header_data, url=url
        )

        # filter recipients to recipients who are also owners
        owner_recipients = [
            ReportRecipients(
                type=ReportRecipientType.EMAIL,
                recipient_config_json=json.dumps({"target": owner.email}),
            )
            for owner in self._report_schedule.owners
        ]

        self._send(notification_content, owner_recipients)

    def is_in_grace_period(self) -> bool:
        """
        Checks if an alert is in it's grace period
        """
        last_success = ReportScheduleDAO.find_last_success_log(self._report_schedule)
        return (
            last_success is not None
            and self._report_schedule.grace_period
            and naive_utcnow() - timedelta(seconds=self._report_schedule.grace_period)
            < last_success.end_dttm
        )

    def is_in_error_grace_period(self) -> bool:
        """
        Checks if an alert/report on error is in it's notification grace period
        """
        last_success = ReportScheduleDAO.find_last_error_notification(
            self._report_schedule
        )
        if not last_success:
            return False
        return (
            last_success is not None
            and self._report_schedule.grace_period
            and naive_utcnow() - timedelta(seconds=self._report_schedule.grace_period)
            < last_success.end_dttm
        )

    def is_on_working_timeout(self) -> bool:
        """
        Checks if an alert is in a working timeout
        """
        last_working = ReportScheduleDAO.find_last_entered_working_log(
            self._report_schedule
        )
        if not last_working:
            return False
        return (
            self._report_schedule.working_timeout is not None
            and self._report_schedule.last_eval_dttm is not None
            and naive_utcnow()
            - timedelta(seconds=self._report_schedule.working_timeout)
            > last_working.end_dttm
        )

    def next(self) -> None:
        raise NotImplementedError()


class ReportNotTriggeredErrorState(BaseReportState):
    """
    Handle Not triggered and Error state
    next final states:
    - Not Triggered
    - Success
    - Error
    """

    current_states = [ReportState.NOOP, ReportState.ERROR]
    initial = True

    def next(self) -> None:  # noqa: C901
        self.update_report_schedule_and_log(ReportState.WORKING)
        try:
            # If it's an alert check if the alert is triggered
            if self._report_schedule.type == ReportScheduleType.ALERT:
                triggered, message = AlertCommand(
                    self._report_schedule, self._execution_id
                ).run()
                if not triggered:
                    self.update_report_schedule_and_log(
                        ReportState.NOOP, error_message=message
                    )
                    return
            self.send()
            # Include filter warnings in the log if any were collected
            warning_message = (
                ";".join(self._filter_warnings) if self._filter_warnings else None
            )
            self.update_report_schedule_and_log(
                ReportState.SUCCESS, error_message=warning_message
            )
        except (AxBIErrorsException, Exception) as first_ex:
            error_message = str(first_ex)
            if isinstance(first_ex, AxBIErrorsException):
                error_message = ";".join([error.message for error in first_ex.errors])

            try:
                self.update_report_schedule_and_log(
                    ReportState.ERROR, error_message=error_message
                )
            except ReportScheduleUnexpectedError as logging_ex:
                # Logging failed (likely StaleDataError), but we still want to
                # raise the original error so the root cause remains visible
                logger.warning(
                    "Failed to log error for report schedule (execution %s) "
                    "due to database issue",
                    self._execution_id,
                    exc_info=True,
                )
                # Re-raise the original exception, not the logging failure
                raise first_ex from logging_ex

            # TODO (dpgaspar) convert this logic to a new state eg: ERROR_ON_GRACE
            if not self.is_in_error_grace_period():
                second_error_message = REPORT_SCHEDULE_ERROR_NOTIFICATION_MARKER
                try:
                    self.send_error(
                        f"Error occurred for {self._report_schedule.type}:"
                        f" {self._report_schedule.name}",
                        str(first_ex),
                    )

                except AxBIErrorsException as second_ex:
                    second_error_message = ";".join(
                        [error.message for error in second_ex.errors]
                    )
                except ReportScheduleUnexpectedError:
                    # send_error failed due to logging issue, log and continue
                    # to raise the original error
                    logger.warning(
                        "Failed to send error notification due to database issue",
                        exc_info=True,
                    )
                except Exception as second_ex:  # pylint: disable=broad-except
                    second_error_message = str(second_ex)
                finally:
                    try:
                        self.update_report_schedule_and_log(
                            ReportState.ERROR, error_message=second_error_message
                        )
                    except ReportScheduleUnexpectedError:
                        # Logging failed again, log it but don't let it hide first_ex
                        logger.warning(
                            "Failed to log final error state due to database issue",
                            exc_info=True,
                        )
            raise


class ReportWorkingState(BaseReportState):
    """
    Handle Working state
    next states:
    - Error
    - Working
    """

    current_states = [ReportState.WORKING]

    def next(self) -> None:
        if self.is_on_working_timeout():
            last_working = ReportScheduleDAO.find_last_entered_working_log(
                self._report_schedule
            )
            elapsed_seconds = (
                (naive_utcnow() - last_working.end_dttm).total_seconds()
                if last_working
                else None
            )
            logger.error(
                "Working state timeout after %.2fs - execution_id: %s",
                elapsed_seconds if elapsed_seconds else 0,
                self._execution_id,
            )
            exception_timeout = ReportScheduleWorkingTimeoutError()
            self.update_report_schedule_and_log(
                ReportState.ERROR,
                error_message=str(exception_timeout),
            )
            raise exception_timeout
        logger.warning(
            "Report still in working state, refusing to re-compute - execution_id: %s",
            self._execution_id,
        )
        exception_working = ReportSchedulePreviousWorkingError()
        self.update_report_schedule_and_log(
            ReportState.WORKING,
            error_message=str(exception_working),
        )
        raise exception_working


class ReportSuccessState(BaseReportState):
    """
    Handle Success, Grace state
    next states:
    - Grace
    - Not triggered
    - Success
    """

    current_states = [ReportState.SUCCESS, ReportState.GRACE]

    def next(self) -> None:
        if self._report_schedule.type == ReportScheduleType.ALERT:
            if self.is_in_grace_period():
                self.update_report_schedule_and_log(
                    ReportState.GRACE,
                    error_message=str(ReportScheduleAlertGracePeriodError()),
                )
                return
            self.update_report_schedule_and_log(ReportState.WORKING)
            try:
                triggered, message = AlertCommand(
                    self._report_schedule, self._execution_id
                ).run()
                if not triggered:
                    self.update_report_schedule_and_log(
                        ReportState.NOOP, error_message=message
                    )
                    return
            except Exception as ex:
                # Ensure the schedule always transitions out of WORKING to
                # ERROR, even if sending the error notification itself fails —
                # otherwise the schedule is stuck in WORKING until the working
                # timeout. Mirrors ReportNotTriggeredErrorState.next().
                # Only record the marker when the notification was actually
                # delivered; otherwise record the send failure so the grace-
                # period check doesn't incorrectly suppress future notifications.
                error_message = REPORT_SCHEDULE_ERROR_NOTIFICATION_MARKER
                try:
                    self.send_error(
                        f"Error occurred for {self._report_schedule.type}:"
                        f" {self._report_schedule.name}",
                        str(ex),
                    )
                except Exception as send_ex:  # noqa: BLE001  # pylint: disable=broad-except
                    error_message = str(send_ex) or str(ex)
                    logger.warning(
                        "Failed to send error notification for report schedule "
                        "(execution %s)",
                        self._execution_id,
                        exc_info=True,
                    )
                finally:
                    try:
                        self.update_report_schedule_and_log(
                            ReportState.ERROR,
                            error_message=error_message,
                        )
                    except ReportScheduleUnexpectedError:
                        logger.warning(
                            "Failed to log ERROR state for report schedule "
                            "(execution %s) due to database issue",
                            self._execution_id,
                            exc_info=True,
                        )
                raise

        # For REPORT types the ALERT branch above is skipped, so WORKING has not
        # been set yet. Set it before the (potentially slow) send() so a
        # concurrent scheduler tick is blocked by ReportWorkingState, preventing
        # duplicate notifications. ALERT types already set WORKING above.
        if self._report_schedule.type != ReportScheduleType.ALERT:
            self.update_report_schedule_and_log(ReportState.WORKING)

        try:
            self.send()
            # Include filter warnings in the log if any were collected
            warning_message = (
                ";".join(self._filter_warnings) if self._filter_warnings else None
            )
            self.update_report_schedule_and_log(
                ReportState.SUCCESS, error_message=warning_message
            )
        except Exception as ex:  # pylint: disable=broad-except
            try:
                self.update_report_schedule_and_log(
                    ReportState.ERROR, error_message=str(ex)
                )
            except ReportScheduleUnexpectedError as logging_ex:
                # Logging failed (likely StaleDataError), but we still want to
                # raise the original error so the root cause remains visible
                logger.warning(
                    "Failed to log error for report schedule (execution %s) "
                    "due to database issue",
                    self._execution_id,
                    exc_info=True,
                )
                # Re-raise the original exception, not the logging failure
                raise ex from logging_ex
            raise


class ReportScheduleStateMachine:  # pylint: disable=too-few-public-methods
    """
    Simple state machine for Alerts/Reports states
    """

    states_cls = [ReportWorkingState, ReportNotTriggeredErrorState, ReportSuccessState]

    def __init__(
        self,
        task_uuid: UUID,
        report_schedule: ReportSchedule,
        scheduled_dttm: datetime,
    ):
        self._execution_id = task_uuid
        self._report_schedule = report_schedule
        self._scheduled_dttm = scheduled_dttm

    @transaction()
    def run(self) -> None:
        for state_cls in self.states_cls:
            if (self._report_schedule.last_state is None and state_cls.initial) or (
                self._report_schedule.last_state in state_cls.current_states
            ):
                state_cls(
                    self._report_schedule,
                    self._scheduled_dttm,
                    self._execution_id,
                ).next()
                break
        else:
            raise ReportScheduleStateNotFoundError()


class AsyncExecuteReportScheduleCommand(BaseCommand):
    """
    Execute all types of report schedules.
    - On reports takes chart or dashboard screenshots and sends configured notifications
    - On Alerts uses related Command AlertCommand and sends configured notifications
    """

    def __init__(self, task_id: str, model_id: int, scheduled_dttm: datetime):
        self._model_id = model_id
        self._model: ReportSchedule | None = None
        self._scheduled_dttm = scheduled_dttm
        self._execution_id = UUID(task_id)

    @transaction()
    def run(self) -> None:
        try:
            self.validate()
            if not self._model:
                raise ReportScheduleExecuteUnexpectedError()

            _, username = get_executor(
                executors=app.config["ALERT_REPORTS_EXECUTORS"],
                model=self._model,
            )
            user = security_manager.find_user(username)

            operation = f"Report execution as user {username}"
            with _log_timed_operation(operation, self._execution_id):
                with override_user(user):
                    ReportScheduleStateMachine(
                        self._execution_id, self._model, self._scheduled_dttm
                    ).run()
        except CommandException:
            raise
        except Exception as ex:
            raise ReportScheduleUnexpectedError(str(ex)) from ex

    def validate(self) -> None:
        # Validate/populate model exists
        logger.info(
            "session is validated: id %s, executionid: %s",
            self._model_id,
            self._execution_id,
        )
        self._model = ReportScheduleDAO.find_one_or_none(
            skip_base_filter=True,
            id=self._model_id,
        )
        if not self._model:
            raise ReportScheduleNotFoundError()

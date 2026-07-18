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

import json  # noqa: TID251
from datetime import datetime, timedelta
from typing import Any, cast
from unittest.mock import ANY, patch
from uuid import UUID, uuid4

import pytest
from celery.exceptions import SoftTimeLimitExceeded
from pytest_mock import MockerFixture

from axbi.app import AxBIApp
from axbi.commands.exceptions import UpdateFailedError
from axbi.commands.report.exceptions import (
    ReportScheduleAlertGracePeriodError,
    ReportScheduleCsvFailedError,
    ReportScheduleDataFrameFailedError,
    ReportScheduleNotFoundError,
    ReportSchedulePreviousWorkingError,
    ReportScheduleScreenshotFailedError,
    ReportScheduleScreenshotTimeout,
    ReportScheduleStateNotFoundError,
    ReportScheduleUnexpectedError,
    ReportScheduleWorkingTimeoutError,
)
from axbi.commands.report.execute import (
    _log_timed_operation,
    AsyncExecuteReportScheduleCommand,
    BaseReportState,
    ReportNotTriggeredErrorState,
    ReportScheduleStateMachine,
    ReportSuccessState,
    ReportWorkingState,
)
from axbi.daos.report import REPORT_SCHEDULE_ERROR_NOTIFICATION_MARKER
from axbi.dashboards.permalink.types import DashboardPermalinkState
from axbi.reports.models import (
    ReportDataFormat,
    ReportRecipients,
    ReportRecipientType,
    ReportSchedule,
    ReportScheduleType,
    ReportSourceFormat,
    ReportState,
)
from axbi.utils.core import HeaderDataType
from axbi.utils.screenshots import ChartScreenshot
from tests.integration_tests.conftest import with_feature_flags


def test_log_data_with_chart(mocker: MockerFixture) -> None:
    mock_report_schedule: ReportSchedule = mocker.Mock(spec=ReportSchedule)
    mock_report_schedule.chart = True
    mock_report_schedule.chart_id = 123
    mock_report_schedule.dashboard_id = None
    mock_report_schedule.type = "report_type"
    mock_report_schedule.report_format = "report_format"
    mock_report_schedule.owners = [1, 2]
    mock_report_schedule.recipients = []

    class_instance: BaseReportState = BaseReportState(
        mock_report_schedule, "January 1, 2021", "execution_id_example"
    )
    class_instance._report_schedule = mock_report_schedule

    result: HeaderDataType = class_instance._get_log_data()

    expected_result: HeaderDataType = {
        "notification_type": "report_type",
        "notification_source": ReportSourceFormat.CHART,
        "notification_format": "report_format",
        "chart_id": 123,
        "dashboard_id": None,
        "owners": [1, 2],
        "slack_channels": None,
        "execution_id": "execution_id_example",
    }

    assert result == expected_result


def test_timed_operation_logs_monotonic_success(mocker: MockerFixture) -> None:
    """Successful operations log duration from a monotonic clock."""
    execution_id = uuid4()
    mocker.patch(
        "axbi.commands.report.execute.monotonic",
        side_effect=[10.0, 12.5],
    )
    mock_logger = mocker.patch("axbi.commands.report.execute.logger")

    with _log_timed_operation("test operation", execution_id):
        pass

    mock_logger.info.assert_called_once_with(
        "%s completed in %.2fs - execution_id: %s",
        "test operation",
        2.5,
        execution_id,
    )


def test_timed_operation_logs_failure_and_preserves_exception(
    mocker: MockerFixture,
) -> None:
    """Failed operations retain the original exception after duration logging."""
    execution_id = uuid4()
    mocker.patch(
        "axbi.commands.report.execute.monotonic",
        side_effect=[20.0, 21.25],
    )
    mock_logger = mocker.patch("axbi.commands.report.execute.logger")

    with pytest.raises(RuntimeError, match="boom"):
        with _log_timed_operation("test operation", execution_id):
            raise RuntimeError("boom")

    mock_logger.exception.assert_called_once_with(
        "%s failed after %.2fs - execution_id: %s",
        "test operation",
        1.25,
        execution_id,
    )


def test_timed_operation_logs_soft_timeout_separately(
    mocker: MockerFixture,
) -> None:
    """Celery soft timeouts use the timeout log path and remain recognizable."""
    execution_id = uuid4()
    mocker.patch(
        "axbi.commands.report.execute.monotonic",
        side_effect=[30.0, 34.0],
    )
    mock_logger = mocker.patch("axbi.commands.report.execute.logger")

    with pytest.raises(SoftTimeLimitExceeded):
        with _log_timed_operation("test operation", execution_id):
            raise SoftTimeLimitExceeded()

    mock_logger.warning.assert_called_once_with(
        "%s timed out after %.2fs - execution_id: %s",
        "test operation",
        4.0,
        execution_id,
    )
    mock_logger.exception.assert_not_called()


def test_embedded_data_none_raises_dataframe_failure(
    mocker: MockerFixture,
) -> None:
    """A missing dataframe is reported as a dataframe-generation failure."""
    report_schedule = mocker.Mock(spec=ReportSchedule)
    report_schedule.chart.query_context = {}
    state = BaseReportState(
        report_schedule,
        datetime(2026, 7, 12, 12, 0, 0),
        uuid4(),
    )
    mocker.patch.object(state, "_get_url", return_value="/api/v1/chart/data")
    mocker.patch(
        "axbi.commands.report.execute.get_executor",
        return_value=(None, "report-user"),
    )
    mocker.patch("axbi.commands.report.execute.security_manager.find_user")
    auth_factory = mocker.patch(
        "axbi.commands.report.execute.machine_auth_provider_factory"
    )
    auth_factory.instance.get_auth_cookies.return_value = {}
    report_logger = mocker.patch("axbi.commands.report.execute.logger")
    mocker.patch(
        "axbi.commands.report.execute.get_chart_dataframe",
        return_value=None,
    )

    with pytest.raises(ReportScheduleDataFrameFailedError):
        state._get_embedded_data()

    report_logger.exception.assert_called_once()
    report_logger.info.assert_not_called()


def test_csv_data_empty_result_is_logged_as_failure(
    mocker: MockerFixture,
) -> None:
    """An empty CSV response fails inside the timed operation boundary."""
    report_schedule = mocker.Mock(spec=ReportSchedule)
    report_schedule.chart.query_context = {}
    state = BaseReportState(
        report_schedule,
        datetime(2026, 7, 12, 12, 0, 0),
        uuid4(),
    )
    mocker.patch.object(state, "_get_url", return_value="/api/v1/chart/data")
    mocker.patch(
        "axbi.commands.report.execute.get_executor",
        return_value=(None, "report-user"),
    )
    mocker.patch("axbi.commands.report.execute.security_manager.find_user")
    auth_factory = mocker.patch(
        "axbi.commands.report.execute.machine_auth_provider_factory"
    )
    auth_factory.instance.get_auth_cookies.return_value = {}
    report_logger = mocker.patch("axbi.commands.report.execute.logger")
    mocker.patch(
        "axbi.commands.report.execute.get_chart_csv_data",
        return_value=b"",
    )

    with pytest.raises(ReportScheduleCsvFailedError):
        state._get_csv_data()

    report_logger.exception.assert_called_once()
    report_logger.info.assert_not_called()


def test_log_data_with_dashboard(mocker: MockerFixture) -> None:
    mock_report_schedule: ReportSchedule = mocker.Mock(spec=ReportSchedule)
    mock_report_schedule.chart = False
    mock_report_schedule.chart_id = None
    mock_report_schedule.dashboard_id = 123
    mock_report_schedule.type = "report_type"
    mock_report_schedule.report_format = "report_format"
    mock_report_schedule.owners = [1, 2]
    mock_report_schedule.recipients = []

    class_instance: BaseReportState = BaseReportState(
        mock_report_schedule, "January 1, 2021", "execution_id_example"
    )
    class_instance._report_schedule = mock_report_schedule

    result: HeaderDataType = class_instance._get_log_data()

    expected_result: HeaderDataType = {
        "notification_type": "report_type",
        "notification_source": ReportSourceFormat.DASHBOARD,
        "notification_format": "report_format",
        "chart_id": None,
        "dashboard_id": 123,
        "owners": [1, 2],
        "slack_channels": None,
        "execution_id": "execution_id_example",
    }

    assert result == expected_result


def test_log_data_with_email_recipients(mocker: MockerFixture) -> None:
    mock_report_schedule: ReportSchedule = mocker.Mock(spec=ReportSchedule)
    mock_report_schedule.chart = False
    mock_report_schedule.chart_id = None
    mock_report_schedule.dashboard_id = 123
    mock_report_schedule.type = "report_type"
    mock_report_schedule.report_format = "report_format"
    mock_report_schedule.owners = [1, 2]
    mock_report_schedule.recipients = []
    mock_report_schedule.recipients = [
        mocker.Mock(type=ReportRecipientType.EMAIL, recipient_config_json="email_1"),
        mocker.Mock(type=ReportRecipientType.EMAIL, recipient_config_json="email_2"),
    ]

    class_instance: BaseReportState = BaseReportState(
        mock_report_schedule, "January 1, 2021", "execution_id_example"
    )
    class_instance._report_schedule = mock_report_schedule

    result: HeaderDataType = class_instance._get_log_data()

    expected_result: HeaderDataType = {
        "notification_type": "report_type",
        "notification_source": ReportSourceFormat.DASHBOARD,
        "notification_format": "report_format",
        "chart_id": None,
        "dashboard_id": 123,
        "owners": [1, 2],
        "slack_channels": [],
        "execution_id": "execution_id_example",
    }

    assert result == expected_result


def test_log_data_with_slack_recipients(mocker: MockerFixture) -> None:
    mock_report_schedule: ReportSchedule = mocker.Mock(spec=ReportSchedule)
    mock_report_schedule.chart = False
    mock_report_schedule.chart_id = None
    mock_report_schedule.dashboard_id = 123
    mock_report_schedule.type = "report_type"
    mock_report_schedule.report_format = "report_format"
    mock_report_schedule.owners = [1, 2]
    mock_report_schedule.recipients = []
    mock_report_schedule.recipients = [
        mocker.Mock(type=ReportRecipientType.SLACK, recipient_config_json="channel_1"),
        mocker.Mock(type=ReportRecipientType.SLACK, recipient_config_json="channel_2"),
    ]

    class_instance: BaseReportState = BaseReportState(
        mock_report_schedule, "January 1, 2021", "execution_id_example"
    )
    class_instance._report_schedule = mock_report_schedule

    result: HeaderDataType = class_instance._get_log_data()

    expected_result: HeaderDataType = {
        "notification_type": "report_type",
        "notification_source": ReportSourceFormat.DASHBOARD,
        "notification_format": "report_format",
        "chart_id": None,
        "dashboard_id": 123,
        "owners": [1, 2],
        "slack_channels": ["channel_1", "channel_2"],
        "execution_id": "execution_id_example",
    }

    assert result == expected_result


def test_log_data_no_owners(mocker: MockerFixture) -> None:
    mock_report_schedule: ReportSchedule = mocker.Mock(spec=ReportSchedule)
    mock_report_schedule.chart = False
    mock_report_schedule.chart_id = None
    mock_report_schedule.dashboard_id = 123
    mock_report_schedule.type = "report_type"
    mock_report_schedule.report_format = "report_format"
    mock_report_schedule.owners = []
    mock_report_schedule.recipients = [
        mocker.Mock(type=ReportRecipientType.SLACK, recipient_config_json="channel_1"),
        mocker.Mock(type=ReportRecipientType.SLACK, recipient_config_json="channel_2"),
    ]

    class_instance: BaseReportState = BaseReportState(
        mock_report_schedule, "January 1, 2021", "execution_id_example"
    )
    class_instance._report_schedule = mock_report_schedule

    result: HeaderDataType = class_instance._get_log_data()

    expected_result: HeaderDataType = {
        "notification_type": "report_type",
        "notification_source": ReportSourceFormat.DASHBOARD,
        "notification_format": "report_format",
        "chart_id": None,
        "dashboard_id": 123,
        "owners": [],
        "slack_channels": ["channel_1", "channel_2"],
        "execution_id": "execution_id_example",
    }

    assert result == expected_result


def test_log_data_with_missing_values(mocker: MockerFixture) -> None:
    mock_report_schedule: ReportSchedule = mocker.Mock(spec=ReportSchedule)
    mock_report_schedule.chart = None
    mock_report_schedule.chart_id = None
    mock_report_schedule.dashboard_id = None
    mock_report_schedule.type = "report_type"
    mock_report_schedule.report_format = "report_format"
    mock_report_schedule.owners = [1, 2]
    mock_report_schedule.recipients = [
        mocker.Mock(type=ReportRecipientType.SLACK, recipient_config_json="channel_1"),
        mocker.Mock(
            type=ReportRecipientType.SLACKV2, recipient_config_json="channel_2"
        ),
    ]

    class_instance: BaseReportState = BaseReportState(
        mock_report_schedule, "January 1, 2021", "execution_id_example"
    )
    class_instance._report_schedule = mock_report_schedule

    result: HeaderDataType = class_instance._get_log_data()

    expected_result: HeaderDataType = {
        "notification_type": "report_type",
        "notification_source": ReportSourceFormat.DASHBOARD,
        "notification_format": "report_format",
        "chart_id": None,
        "dashboard_id": None,
        "owners": [1, 2],
        "slack_channels": ["channel_1", "channel_2"],
        "execution_id": "execution_id_example",
    }

    assert result == expected_result


@pytest.mark.parametrize(
    "anchors, permalink_side_effect, expected_paths",
    [
        # Test user select multiple tabs to export in a dashboard report
        (
            ["mock_tab_anchor_1", "mock_tab_anchor_2"],
            ["url1", "url2"],
            [
                "ax-bi/dashboard/p/url1/",
                "ax-bi/dashboard/p/url2/",
            ],
        ),
        # Test user select one tab to export in a dashboard report
        (
            "mock_tab_anchor_1",
            ["url1"],
            ["ax-bi/dashboard/p/url1/"],
        ),
        # Test JSON scalar string anchor falls back to single tab
        (
            json.dumps("mock_tab_anchor_1"),
            ["url1"],
            ["ax-bi/dashboard/p/url1/"],
        ),
    ],
)
@patch("axbi.commands.dashboard.permalink.create.CreateDashboardPermalinkCommand.run")
@with_feature_flags(ALERT_REPORT_TABS=True)
def test_get_dashboard_urls_with_multiple_tabs(
    mock_run, mocker: MockerFixture, anchors, permalink_side_effect, expected_paths, app
) -> None:
    mock_report_schedule: ReportSchedule = mocker.Mock(spec=ReportSchedule)
    mock_report_schedule.chart = False
    mock_report_schedule.chart_id = None
    mock_report_schedule.dashboard_id = 123
    mock_report_schedule.type = "report_type"
    mock_report_schedule.report_format = "report_format"
    mock_report_schedule.owners = [1, 2]
    mock_report_schedule.recipients = []
    mock_report_schedule.extra = {
        "dashboard": {
            "anchor": json.dumps(anchors) if isinstance(anchors, list) else anchors,
            "dataMask": None,
            "activeTabs": None,
            "urlParams": None,
        }
    }
    mock_report_schedule.get_native_filters_params.return_value = (  # type: ignore
        "()",
        [],
    )

    class_instance: BaseReportState = BaseReportState(
        mock_report_schedule, "January 1, 2021", "execution_id_example"
    )
    class_instance._report_schedule = mock_report_schedule
    mock_run.side_effect = permalink_side_effect

    result: list[str] = class_instance.get_dashboard_urls()

    # Build expected URIs using the app's configured WEBDRIVER_BASEURL
    # Use urljoin to handle proper URL joining (handles double slashes)
    import urllib.parse

    base_url = app.config.get("WEBDRIVER_BASEURL", "http://0.0.0.0:8080/")
    expected_uris = [urllib.parse.urljoin(base_url, path) for path in expected_paths]
    assert result == expected_uris


@with_feature_flags(ALERT_REPORT_TABS=True)
def test_get_dashboard_urls_with_exporting_dashboard_only(
    mocker: MockerFixture,
) -> None:
    mock_report_schedule: ReportSchedule = mocker.Mock(spec=ReportSchedule)
    mock_report_schedule.chart = False
    mock_report_schedule.chart_id = None
    mock_report_schedule.dashboard_id = 123
    mock_report_schedule.force_screenshot = False
    mock_report_schedule.type = "report_type"
    mock_report_schedule.report_format = "report_format"
    mock_report_schedule.owners = [1, 2]
    mock_report_schedule.recipients = []
    mock_report_schedule.extra = {
        "dashboard": {
            "anchor": "",
            "dataMask": None,
            "activeTabs": None,
            "urlParams": None,
        }
    }
    mock_report_schedule.get_native_filters_params.return_value = (  # type: ignore
        "()",
        [],
    )
    mock_dashboard = mocker.MagicMock()
    mock_dashboard.uuid = UUID("12345678-1234-1234-1234-123456789abc")
    mock_report_schedule.dashboard = mock_dashboard

    class_instance: BaseReportState = BaseReportState(
        mock_report_schedule, "January 1, 2021", "execution_id_example"
    )
    class_instance._report_schedule = mock_report_schedule

    result: list[str] = class_instance.get_dashboard_urls()

    assert len(result) == 1
    assert "/dashboard/p/" not in result[0]
    assert "12345678-1234-1234-1234-123456789abc" in result[0]


@patch("axbi.commands.report.execute.CreateDashboardPermalinkCommand")
@with_feature_flags(ALERT_REPORT_TABS=True)
def test_get_dashboard_urls_empty_dashboard_state_skips_permalink(
    mock_permalink_cls,
    mocker: MockerFixture,
) -> None:
    """When both ALERT_REPORT_TABS and ALERT_REPORTS_FILTER are enabled but the
    report has no tab or filter configured, get_dashboard_urls() must return
    a plain dashboard URL and must not create a permalink.  A permalink with
    nothing to encode causes a server-side redirect that fails the Playwright
    screenshot (domcontentloaded timeout)."""
    mock_report_schedule: ReportSchedule = mocker.Mock(spec=ReportSchedule)
    mock_report_schedule.chart = False
    mock_report_schedule.force_screenshot = False
    mock_report_schedule.extra = {"dashboard": {}}
    mock_report_schedule.get_native_filters_params.return_value = ("()", [])  # type: ignore

    mock_dashboard = mocker.MagicMock()
    mock_dashboard.uuid = UUID("12345678-1234-1234-1234-123456789abc")
    mock_report_schedule.dashboard = mock_dashboard

    class_instance: BaseReportState = BaseReportState(
        mock_report_schedule, "January 1, 2021", "execution_id_example"
    )
    class_instance._report_schedule = mock_report_schedule

    result: list[str] = class_instance.get_dashboard_urls()

    mock_permalink_cls.assert_not_called()
    assert len(result) == 1
    assert "/dashboard/p/" not in result[0]
    assert "12345678-1234-1234-1234-123456789abc" in result[0]


@patch("axbi.commands.report.execute.CreateDashboardPermalinkCommand")
@with_feature_flags(ALERT_REPORT_TABS=True)
def test_get_dashboard_urls_url_params_only_creates_permalink(
    mock_permalink_cls,
    mocker: MockerFixture,
) -> None:
    """When the dashboard state carries no anchor and no native filters but
    does carry meaningful urlParams (e.g. standalone=true), get_dashboard_urls()
    must still build a permalink so that state survives in the screenshot,
    rather than falling through to the plain dashboard URL."""
    mock_permalink_cls.return_value.run.return_value = "key1"
    mock_report_schedule: ReportSchedule = mocker.Mock(spec=ReportSchedule)
    mock_report_schedule.chart = False
    mock_report_schedule.force_screenshot = False
    mock_report_schedule.extra = {
        "dashboard": {
            "anchor": "",
            "dataMask": None,
            "activeTabs": None,
            "urlParams": [["standalone", "true"]],
        }
    }
    mock_report_schedule.get_native_filters_params.return_value = ("()", [])  # type: ignore

    mock_dashboard = mocker.MagicMock()
    mock_dashboard.uuid = UUID("12345678-1234-1234-1234-123456789abc")
    mock_report_schedule.dashboard = mock_dashboard

    class_instance: BaseReportState = BaseReportState(
        mock_report_schedule, "January 1, 2021", "execution_id_example"
    )
    class_instance._report_schedule = mock_report_schedule

    result: list[str] = class_instance.get_dashboard_urls()

    mock_permalink_cls.assert_called_once()
    state = mock_permalink_cls.call_args.kwargs["state"]
    assert ["standalone", "true"] in state["urlParams"]
    assert len(result) == 1
    assert "/dashboard/p/" in result[0]


@patch("axbi.commands.report.execute.CreateDashboardPermalinkCommand")
@with_feature_flags(ALERT_REPORT_TABS=True)
def test_get_dashboard_urls_ignores_non_object_dashboard_state(
    mock_permalink_cls,
    mocker: MockerFixture,
) -> None:
    mock_report_schedule: ReportSchedule = mocker.Mock(spec=ReportSchedule)
    mock_report_schedule.chart = False
    mock_report_schedule.force_screenshot = False
    mock_report_schedule.extra = cast(Any, {"dashboard": []})
    mock_report_schedule.get_native_filters_params.return_value = ("()", [])  # type: ignore

    mock_dashboard = mocker.MagicMock()
    mock_dashboard.uuid = UUID("12345678-1234-1234-1234-123456789abc")
    mock_report_schedule.dashboard = mock_dashboard

    class_instance: BaseReportState = BaseReportState(
        mock_report_schedule, "January 1, 2021", "execution_id_example"
    )
    class_instance._report_schedule = mock_report_schedule

    result: list[str] = class_instance.get_dashboard_urls()

    mock_permalink_cls.assert_not_called()
    assert len(result) == 1
    assert "/dashboard/p/" not in result[0]
    assert "12345678-1234-1234-1234-123456789abc" in result[0]


@patch("axbi.commands.report.execute.CreateDashboardPermalinkCommand")
@with_feature_flags(ALERT_REPORT_TABS=True)
def test_get_dashboard_urls_with_filters_and_tabs(
    mock_permalink_cls,
    mocker: MockerFixture,
    app,
) -> None:
    mock_report_schedule: ReportSchedule = mocker.Mock(spec=ReportSchedule)
    mock_report_schedule.chart = False
    mock_report_schedule.chart_id = None
    mock_report_schedule.dashboard_id = 123
    mock_report_schedule.type = "report_type"
    mock_report_schedule.report_format = "report_format"
    mock_report_schedule.owners = [1, 2]
    mock_report_schedule.recipients = []
    native_filter_rison = "(NATIVE_FILTER-1:(filterType:filter_select))"
    mock_report_schedule.extra = {
        "dashboard": {
            "anchor": json.dumps(["TAB-1", "TAB-2"]),
            "dataMask": {"NATIVE_FILTER-1": {"filterState": {"value": ["Sales"]}}},
            "activeTabs": ["TAB-1", "TAB-2"],
            "urlParams": None,
            "nativeFilters": [  # type: ignore[typeddict-unknown-key]
                {
                    "nativeFilterId": "NATIVE_FILTER-1",
                    "filterType": "filter_select",
                    "columnName": "department",
                    "filterValues": ["Sales"],
                }
            ],
        }
    }
    mock_report_schedule.get_native_filters_params.return_value = (  # type: ignore[attr-defined]
        native_filter_rison,
        [],
    )
    mock_permalink_cls.return_value.run.side_effect = ["key1", "key2"]

    class_instance: BaseReportState = BaseReportState(
        mock_report_schedule, "January 1, 2021", "execution_id_example"
    )
    class_instance._report_schedule = mock_report_schedule

    result: list[str] = class_instance.get_dashboard_urls()

    import urllib.parse

    base_url = app.config.get("WEBDRIVER_BASEURL", "http://0.0.0.0:8080/")
    assert result == [
        urllib.parse.urljoin(base_url, "ax-bi/dashboard/p/key1/"),
        urllib.parse.urljoin(base_url, "ax-bi/dashboard/p/key2/"),
    ]
    mock_report_schedule.get_native_filters_params.assert_called_once()  # type: ignore[attr-defined]
    assert mock_permalink_cls.call_count == 2
    for call in mock_permalink_cls.call_args_list:
        state = call.kwargs["state"]
        assert state["urlParams"] == [["native_filters", native_filter_rison]]
    assert mock_permalink_cls.call_args_list[0].kwargs["state"]["anchor"] == "TAB-1"
    assert mock_permalink_cls.call_args_list[1].kwargs["state"]["anchor"] == "TAB-2"


@patch("axbi.commands.report.execute.CreateDashboardPermalinkCommand")
@with_feature_flags(ALERT_REPORT_TABS=True)
def test_get_dashboard_urls_with_filters_and_tabs_preserves_existing_url_params(
    mock_permalink_cls,
    mocker: MockerFixture,
) -> None:
    mock_report_schedule: ReportSchedule = mocker.Mock(spec=ReportSchedule)
    mock_report_schedule.chart = False
    mock_report_schedule.chart_id = None
    mock_report_schedule.dashboard_id = 123
    mock_report_schedule.type = "report_type"
    mock_report_schedule.report_format = "report_format"
    mock_report_schedule.owners = [1, 2]
    mock_report_schedule.recipients = []
    native_filter_rison = "(NATIVE_FILTER-1:(filterType:filter_select))"
    mock_report_schedule.extra = {
        "dashboard": {
            "anchor": json.dumps(["TAB-1", "TAB-2"]),
            "dataMask": {"NATIVE_FILTER-1": {"filterState": {"value": ["Sales"]}}},
            "activeTabs": ["TAB-1", "TAB-2"],
            "urlParams": [("standalone", "true"), ("show_filters", "0")],
            "nativeFilters": [  # type: ignore[typeddict-unknown-key]
                {
                    "nativeFilterId": "NATIVE_FILTER-1",
                    "filterType": "filter_select",
                    "columnName": "department",
                    "filterValues": ["Sales"],
                }
            ],
        }
    }
    mock_report_schedule.get_native_filters_params.return_value = (  # type: ignore[attr-defined]
        native_filter_rison,
        [],
    )
    mock_permalink_cls.return_value.run.side_effect = ["key1", "key2"]

    class_instance: BaseReportState = BaseReportState(
        mock_report_schedule, "January 1, 2021", "execution_id_example"
    )
    class_instance._report_schedule = mock_report_schedule

    class_instance.get_dashboard_urls()

    for call in mock_permalink_cls.call_args_list:
        state = call.kwargs["state"]
        assert state["urlParams"] == [
            ["standalone", "true"],
            ["show_filters", "0"],
            ["native_filters", native_filter_rison],
        ]


@patch("axbi.commands.report.execute.CreateDashboardPermalinkCommand")
@with_feature_flags(ALERT_REPORT_TABS=True)
def test_get_dashboard_urls_with_filters_and_tabs_deduplicates_stale_native_filters(
    mock_permalink_cls,
    mocker: MockerFixture,
) -> None:
    mock_report_schedule: ReportSchedule = mocker.Mock(spec=ReportSchedule)
    mock_report_schedule.chart = False
    mock_report_schedule.chart_id = None
    mock_report_schedule.dashboard_id = 123
    mock_report_schedule.type = "report_type"
    mock_report_schedule.report_format = "report_format"
    mock_report_schedule.owners = [1, 2]
    mock_report_schedule.recipients = []
    native_filter_rison = "(NATIVE_FILTER-1:(new:value))"
    mock_report_schedule.extra = {
        "dashboard": {
            "anchor": json.dumps(["TAB-1", "TAB-2"]),
            "dataMask": {},
            "activeTabs": ["TAB-1", "TAB-2"],
            "urlParams": [
                ("standalone", "true"),
                ("native_filters", "(old:stale_value)"),
            ],
            "nativeFilters": [],  # type: ignore[typeddict-unknown-key]
        }
    }
    mock_report_schedule.get_native_filters_params.return_value = (  # type: ignore[attr-defined]
        native_filter_rison,
        [],
    )
    mock_permalink_cls.return_value.run.side_effect = ["key1", "key2"]

    class_instance: BaseReportState = BaseReportState(
        mock_report_schedule, "January 1, 2021", "execution_id_example"
    )
    class_instance._report_schedule = mock_report_schedule

    class_instance.get_dashboard_urls()

    for call in mock_permalink_cls.call_args_list:
        state = call.kwargs["state"]
        assert state["urlParams"] == [
            ["standalone", "true"],
            ["native_filters", native_filter_rison],
        ]


@patch("axbi.commands.report.execute.CreateDashboardPermalinkCommand")
@with_feature_flags(ALERT_REPORT_TABS=True)
def test_get_dashboard_urls_with_filters_no_tabs(
    mock_permalink_cls,
    mocker: MockerFixture,
    app,
) -> None:
    mock_report_schedule: ReportSchedule = mocker.Mock(spec=ReportSchedule)
    mock_report_schedule.chart = False
    mock_report_schedule.chart_id = None
    mock_report_schedule.dashboard_id = 123
    mock_report_schedule.type = "report_type"
    mock_report_schedule.report_format = "report_format"
    mock_report_schedule.owners = [1, 2]
    mock_report_schedule.recipients = []
    native_filter_rison = "(NATIVE_FILTER-1:(filterType:filter_select))"
    mock_report_schedule.extra = {
        "dashboard": {
            "anchor": "",
            "dataMask": {"NATIVE_FILTER-1": {"filterState": {"value": ["Sales"]}}},
            "activeTabs": None,
            "urlParams": None,
            "nativeFilters": [  # type: ignore[typeddict-unknown-key]
                {
                    "nativeFilterId": "NATIVE_FILTER-1",
                    "filterType": "filter_select",
                    "columnName": "department",
                    "filterValues": ["Sales"],
                }
            ],
        }
    }
    mock_report_schedule.get_native_filters_params.return_value = (  # type: ignore[attr-defined]
        native_filter_rison,
        [],
    )
    mock_permalink_cls.return_value.run.return_value = "key1"

    class_instance: BaseReportState = BaseReportState(
        mock_report_schedule, "January 1, 2021", "execution_id_example"
    )
    class_instance._report_schedule = mock_report_schedule

    result: list[str] = class_instance.get_dashboard_urls()

    import urllib.parse

    base_url = app.config.get("WEBDRIVER_BASEURL", "http://0.0.0.0:8080/")
    assert result == [
        urllib.parse.urljoin(base_url, "ax-bi/dashboard/p/key1/"),
    ]
    mock_report_schedule.get_native_filters_params.assert_called_once()  # type: ignore[attr-defined]
    assert mock_permalink_cls.call_count == 1
    state = mock_permalink_cls.call_args_list[0].kwargs["state"]
    assert state["urlParams"] == [["native_filters", native_filter_rison]]


@patch("axbi.commands.report.execute.CreateDashboardPermalinkCommand")
@with_feature_flags(ALERT_REPORT_TABS=True)
def test_get_dashboard_urls_preserves_existing_url_params(
    mock_permalink_cls,
    mocker: MockerFixture,
    app,
) -> None:
    """Existing urlParams (e.g. standalone) must survive native_filters merge."""
    mock_report_schedule: ReportSchedule = mocker.Mock(spec=ReportSchedule)
    mock_report_schedule.chart = False
    mock_report_schedule.chart_id = None
    mock_report_schedule.dashboard_id = 123
    mock_report_schedule.type = "report_type"
    mock_report_schedule.report_format = "report_format"
    mock_report_schedule.owners = [1, 2]
    mock_report_schedule.recipients = []
    native_filter_rison = "(NATIVE_FILTER-1:(filterType:filter_select))"
    mock_report_schedule.extra = {
        "dashboard": {
            "anchor": "",
            "dataMask": {},
            "activeTabs": None,
            "urlParams": [("standalone", "true"), ("show_filters", "0")],
            "nativeFilters": [  # type: ignore[typeddict-unknown-key]
                {
                    "nativeFilterId": "NATIVE_FILTER-1",
                    "filterType": "filter_select",
                    "columnName": "dept",
                    "filterValues": ["Sales"],
                }
            ],
        }
    }
    mock_report_schedule.get_native_filters_params.return_value = (  # type: ignore[attr-defined]
        native_filter_rison,
        [],
    )
    mock_permalink_cls.return_value.run.return_value = "key1"

    class_instance: BaseReportState = BaseReportState(
        mock_report_schedule, "January 1, 2021", "execution_id_example"
    )
    class_instance._report_schedule = mock_report_schedule

    class_instance.get_dashboard_urls()

    state = mock_permalink_cls.call_args_list[0].kwargs["state"]
    assert state["urlParams"] == [
        ["standalone", "true"],
        ["show_filters", "0"],
        ["native_filters", native_filter_rison],
    ]


@patch("axbi.commands.report.execute.CreateDashboardPermalinkCommand")
@with_feature_flags(ALERT_REPORT_TABS=True)
def test_get_dashboard_urls_deduplicates_stale_native_filters(
    mock_permalink_cls,
    mocker: MockerFixture,
    app,
) -> None:
    """A stale native_filters entry in urlParams is replaced, not duplicated."""
    mock_report_schedule: ReportSchedule = mocker.Mock(spec=ReportSchedule)
    mock_report_schedule.chart = False
    mock_report_schedule.chart_id = None
    mock_report_schedule.dashboard_id = 123
    mock_report_schedule.type = "report_type"
    mock_report_schedule.report_format = "report_format"
    mock_report_schedule.owners = [1, 2]
    mock_report_schedule.recipients = []
    native_filter_rison = "(NATIVE_FILTER-1:(new:value))"
    mock_report_schedule.extra = {
        "dashboard": {
            "anchor": "",
            "dataMask": {},
            "activeTabs": None,
            "urlParams": [
                ("standalone", "true"),
                ("native_filters", "(old:stale_value)"),
            ],
            "nativeFilters": [],  # type: ignore[typeddict-unknown-key]
        }
    }
    mock_report_schedule.get_native_filters_params.return_value = (  # type: ignore[attr-defined]
        native_filter_rison,
        [],
    )
    mock_permalink_cls.return_value.run.return_value = "key1"

    class_instance: BaseReportState = BaseReportState(
        mock_report_schedule, "January 1, 2021", "execution_id_example"
    )
    class_instance._report_schedule = mock_report_schedule

    class_instance.get_dashboard_urls()

    state = mock_permalink_cls.call_args_list[0].kwargs["state"]
    assert state["urlParams"] == [
        ["standalone", "true"],
        ["native_filters", native_filter_rison],
    ]


@patch("axbi.commands.dashboard.permalink.create.CreateDashboardPermalinkCommand.run")
def test_get_tab_urls(
    mock_run,
    mocker: MockerFixture,
    app,
) -> None:
    mock_report_schedule: ReportSchedule = mocker.Mock(spec=ReportSchedule)
    mock_report_schedule.dashboard_id = 123

    class_instance: BaseReportState = BaseReportState(
        mock_report_schedule, "January 1, 2021", "execution_id_example"
    )
    class_instance._report_schedule = mock_report_schedule
    mock_run.side_effect = ["uri1", "uri2"]
    tab_anchors = ["1", "2"]
    result: list[str] = class_instance._get_tabs_urls(tab_anchors)
    import urllib.parse

    base_url = app.config.get("WEBDRIVER_BASEURL", "http://0.0.0.0:8080/")
    assert result == [
        urllib.parse.urljoin(base_url, "ax-bi/dashboard/p/uri1/"),
        urllib.parse.urljoin(base_url, "ax-bi/dashboard/p/uri2/"),
    ]


@patch("axbi.commands.report.execute.CreateDashboardPermalinkCommand")
@with_feature_flags(ALERT_REPORT_TABS=True)
def test_get_dashboard_urls_multitab_preserves_url_params(
    mock_permalink_cls,
    mocker: MockerFixture,
    app,
) -> None:
    """Multi-tab fan-out must preserve dashboard_state.urlParams (e.g. standalone)
    and replace any pre-existing native_filters entry with the report's value —
    matching the single-tab branch's merge semantics."""
    mock_report_schedule: ReportSchedule = mocker.Mock(spec=ReportSchedule)
    mock_report_schedule.chart = False
    mock_report_schedule.chart_id = None
    mock_report_schedule.dashboard_id = 123
    mock_report_schedule.type = "report_type"
    mock_report_schedule.report_format = "report_format"
    mock_report_schedule.owners = [1, 2]
    mock_report_schedule.recipients = []
    native_filter_rison = "(NATIVE_FILTER-1:(filterType:filter_select))"
    # Use list-of-lists (not tuples) — extra_json deserializes urlParams from
    # JSON arrays. Includes a stale native_filters entry to exercise the
    # dedup-then-append step in the merge.
    mock_report_schedule.extra = {
        "dashboard": {
            "anchor": json.dumps(["TAB-1", "TAB-2"]),
            "urlParams": [
                ["standalone", "true"],
                ["native_filters", "(STALE_FILTER:(filterType:filter_select))"],
                ["show_filters", "0"],
            ],
        }
    }
    mock_report_schedule.get_native_filters_params.return_value = (  # type: ignore[attr-defined]
        native_filter_rison,
        [],
    )
    mock_permalink_cls.return_value.run.side_effect = ["key1", "key2"]

    class_instance: BaseReportState = BaseReportState(
        mock_report_schedule, "January 1, 2021", "execution_id_example"
    )
    class_instance._report_schedule = mock_report_schedule

    class_instance.get_dashboard_urls()

    assert mock_permalink_cls.call_count == 2
    for idx, expected_anchor in enumerate(["TAB-1", "TAB-2"]):
        state = mock_permalink_cls.call_args_list[idx].kwargs["state"]
        # Stale native_filters is replaced (not duplicated); other params
        # survive in their original order; report's native_filters appended.
        assert state["urlParams"] == [
            ["standalone", "true"],
            ["show_filters", "0"],
            ["native_filters", native_filter_rison],
        ]
        # Each per-tab permalink targets exactly that tab.
        assert state["anchor"] == expected_anchor


@patch("axbi.commands.dashboard.permalink.create.CreateDashboardPermalinkCommand.run")
def test_get_tab_url(
    mock_run,
    mocker: MockerFixture,
    app,
) -> None:
    mock_report_schedule: ReportSchedule = mocker.Mock(spec=ReportSchedule)
    mock_report_schedule.dashboard_id = 123

    class_instance: BaseReportState = BaseReportState(
        mock_report_schedule, "January 1, 2021", "execution_id_example"
    )
    class_instance._report_schedule = mock_report_schedule
    mock_run.return_value = "uri"
    dashboard_state = DashboardPermalinkState(
        anchor="1",
        dataMask=None,
        activeTabs=None,
        urlParams=None,
    )
    result: str = class_instance._get_tab_url(dashboard_state)
    import urllib.parse

    base_url = app.config.get("WEBDRIVER_BASEURL", "http://0.0.0.0:8080/")
    assert result == urllib.parse.urljoin(base_url, "ax-bi/dashboard/p/uri/")


@patch("axbi.commands.dashboard.permalink.create.CreateDashboardPermalinkCommand.run")
@with_feature_flags(ALERT_REPORT_TABS=False)
def test_get_dashboard_urls_native_filters_without_tabs(
    mock_run,
    mocker: MockerFixture,
    app,
) -> None:
    """Native filters should be applied even when ALERT_REPORT_TABS is disabled."""
    mock_report_schedule: ReportSchedule = mocker.Mock(spec=ReportSchedule)
    mock_report_schedule.chart = False
    mock_report_schedule.chart_id = None
    mock_report_schedule.dashboard_id = 123
    mock_report_schedule.force_screenshot = False
    extra = {
        "dashboard": {
            "nativeFilters": [
                {
                    "nativeFilterId": "NATIVE_FILTER-abc",
                    "filterType": "filter_select",
                    "columnName": "col1",
                    "filterValues": ["val1"],
                }
            ]
        }
    }
    mock_report_schedule.extra = extra  # type: ignore[assignment]
    mock_report_schedule.get_native_filters_params.return_value = (  # type: ignore
        "(NATIVE_FILTER-abc:!(val1))",
        [],
    )

    mock_dashboard = mocker.MagicMock()
    mock_dashboard.uuid = UUID("12345678-1234-1234-1234-123456789abc")
    mock_report_schedule.dashboard = mock_dashboard

    class_instance: BaseReportState = BaseReportState(
        mock_report_schedule, "January 1, 2021", "execution_id_example"
    )
    class_instance._report_schedule = mock_report_schedule
    mock_run.return_value = "permalink_key"

    result: list[str] = class_instance.get_dashboard_urls()

    assert len(result) == 1
    assert "permalink_key" in result[0]


@patch("axbi.commands.report.execute.CreateDashboardPermalinkCommand")
@with_feature_flags(ALERT_REPORT_TABS=False)
def test_get_dashboard_urls_flag_off_preserves_url_params(
    mock_permalink_cls,
    mocker: MockerFixture,
    app,
) -> None:
    """The post-``if``-block fall-through in ``get_dashboard_urls`` must
    honor any urlParams set in ``extra.dashboard`` (e.g. via API) — same
    merge semantics as the protected branch.

    Reachability: only when ``dashboard_state`` is falsy OR
    ``ALERT_REPORT_TABS=False``. The flag-on / no-anchor case lands in
    the single-tab merge at L290-306, not here.
    """
    mock_report_schedule: ReportSchedule = mocker.Mock(spec=ReportSchedule)
    mock_report_schedule.chart = False
    mock_report_schedule.chart_id = None
    mock_report_schedule.dashboard_id = 123
    native_filter_rison = "(NATIVE_FILTER-abc:!(val1))"
    mock_report_schedule.extra = {
        "dashboard": {
            "urlParams": [
                ["standalone", "true"],
                ["native_filters", "(STALE_FILTER:!(stale))"],
                ["show_filters", "0"],
            ],
        }
    }
    mock_report_schedule.get_native_filters_params.return_value = (  # type: ignore[attr-defined]
        native_filter_rison,
        [],
    )

    class_instance: BaseReportState = BaseReportState(
        mock_report_schedule, "January 1, 2021", "execution_id_example"
    )
    class_instance._report_schedule = mock_report_schedule
    mock_permalink_cls.return_value.run.return_value = "permalink_key"

    class_instance.get_dashboard_urls()

    state = mock_permalink_cls.call_args_list[0].kwargs["state"]
    # Stale native_filters replaced; existing params survive in order;
    # report's native_filters appended.
    assert state["urlParams"] == [
        ["standalone", "true"],
        ["show_filters", "0"],
        ["native_filters", native_filter_rison],
    ]


@patch("axbi.commands.report.execute.CreateDashboardPermalinkCommand")
@with_feature_flags(ALERT_REPORT_TABS=False)
def test_get_dashboard_urls_ignores_malformed_url_params(
    mock_permalink_cls,
    mocker: MockerFixture,
) -> None:
    mock_report_schedule: ReportSchedule = mocker.Mock(spec=ReportSchedule)
    mock_report_schedule.chart = False
    mock_report_schedule.chart_id = None
    mock_report_schedule.dashboard_id = 123
    native_filter_rison = "(NATIVE_FILTER-abc:!(val1))"
    mock_report_schedule.extra = cast(
        Any,
        {
            "dashboard": {
                "urlParams": [
                    "standalone=true",
                    1,
                    [],
                    ["standalone", "true"],
                    ["native_filters", "(STALE_FILTER:!(stale))"],
                ],
            }
        },
    )
    mock_report_schedule.get_native_filters_params.return_value = (  # type: ignore[attr-defined]
        native_filter_rison,
        [],
    )

    class_instance: BaseReportState = BaseReportState(
        mock_report_schedule, "January 1, 2021", "execution_id_example"
    )
    class_instance._report_schedule = mock_report_schedule
    mock_permalink_cls.return_value.run.return_value = "permalink_key"

    class_instance.get_dashboard_urls()

    state = mock_permalink_cls.call_args_list[0].kwargs["state"]
    assert state["urlParams"] == [
        ["standalone", "true"],
        ["native_filters", native_filter_rison],
    ]


@patch("axbi.commands.report.execute.CreateDashboardPermalinkCommand")
@with_feature_flags(ALERT_REPORT_TABS=True)
def test_get_dashboard_urls_ignores_malformed_anchor(
    mock_permalink_cls,
    mocker: MockerFixture,
) -> None:
    mock_report_schedule: ReportSchedule = mocker.Mock(spec=ReportSchedule)
    mock_report_schedule.chart = False
    mock_report_schedule.force_screenshot = False
    mock_report_schedule.extra = cast(Any, {"dashboard": {"anchor": ["TAB-1"]}})
    mock_report_schedule.get_native_filters_params.return_value = ("()", [])  # type: ignore[attr-defined]

    mock_dashboard = mocker.MagicMock()
    mock_dashboard.uuid = UUID("12345678-1234-1234-1234-123456789abc")
    mock_report_schedule.dashboard = mock_dashboard

    class_instance: BaseReportState = BaseReportState(
        mock_report_schedule, "January 1, 2021", "execution_id_example"
    )
    class_instance._report_schedule = mock_report_schedule

    result = class_instance.get_dashboard_urls()

    mock_permalink_cls.assert_not_called()
    assert len(result) == 1
    assert "/dashboard/p/" not in result[0]
    assert "12345678-1234-1234-1234-123456789abc" in result[0]


def test_get_native_filters_params_skips_malformed_filter_entries() -> None:
    report_schedule = ReportSchedule()
    report_schedule.extra = cast(
        Any,
        {"dashboard": {"nativeFilters": ["bad-filter"]}},
    )

    native_filter_params, warnings = report_schedule.get_native_filters_params()

    assert native_filter_params == "()"
    assert warnings == ["Skipping malformed native filter: bad-filter"]


def create_report_schedule(
    mocker: MockerFixture,
    custom_width: int | None = None,
    custom_height: int | None = None,
) -> ReportSchedule:
    """Helper function to create a ReportSchedule instance with specified dimensions."""
    schedule = ReportSchedule()
    schedule.type = ReportScheduleType.REPORT
    schedule.name = "Test Report"
    schedule.description = "Test Description"
    schedule.chart = mocker.MagicMock()
    schedule.chart.id = 1
    schedule.dashboard = None
    schedule.database = None
    schedule.custom_width = custom_width
    schedule.custom_height = custom_height
    return schedule


@pytest.mark.parametrize(
    "test_id,custom_width,max_width,window_width,expected_width",
    [
        # Test when custom width exceeds max width
        ("exceeds_max", 2000, 1600, 800, 1600),
        # Test when custom width is less than max width
        ("under_max", 1200, 1600, 800, 1200),
        # Test when custom width is None (should use window width)
        ("no_custom", None, 1600, 800, 800),
        # Test when custom width equals max width
        ("equals_max", 1600, 1600, 800, 1600),
    ],
)
def test_screenshot_width_calculation(
    app: AxBIApp,
    mocker: MockerFixture,
    test_id: str,
    custom_width: int | None,
    max_width: int,
    window_width: int,
    expected_width: int,
) -> None:
    """
    Test that screenshot width is correctly calculated.

    The width should be:
    - Limited by max_width when custom_width exceeds it
    - Equal to custom_width when it's less than max_width
    - Equal to window_width when custom_width is None
    """
    from axbi.commands.report.execute import BaseReportState

    # Mock configuration
    app.config.update(
        {
            "ALERT_REPORTS_MAX_CUSTOM_SCREENSHOT_WIDTH": max_width,
            "WEBDRIVER_WINDOW": {
                "slice": (window_width, 600),
                "dashboard": (window_width, 600),
            },
            "ALERT_REPORTS_EXECUTORS": {},
        }
    )

    # Create report schedule with specified custom width
    report_schedule = create_report_schedule(mocker, custom_width=custom_width)

    # Initialize BaseReportState
    report_state = BaseReportState(
        report_schedule=report_schedule,
        scheduled_dttm=datetime.now(),
        execution_id=UUID("084e7ee6-5557-4ecd-9632-b7f39c9ec524"),
    )

    # Mock security manager and screenshot
    with (
        patch("axbi.commands.report.execute.security_manager") as mock_security_manager,
        patch(
            "axbi.utils.screenshots.ChartScreenshot.get_screenshot"
        ) as mock_get_screenshot,
    ):
        # Mock user
        mock_user = mocker.MagicMock()
        mock_security_manager.find_user.return_value = mock_user
        mock_get_screenshot.return_value = b"screenshot bytes"

        # Mock get_executor to avoid database lookups
        with patch("axbi.commands.report.execute.get_executor") as mock_get_executor:
            mock_get_executor.return_value = ("executor", "username")

            # Capture the ChartScreenshot instantiation
            with patch(
                "axbi.commands.report.execute.ChartScreenshot",
                wraps=ChartScreenshot,
            ) as mock_chart_screenshot:
                # Call the method that triggers screenshot creation
                report_state._get_screenshots()

                # Verify ChartScreenshot was created with correct window_size
                mock_chart_screenshot.assert_called_once()
                _, kwargs = mock_chart_screenshot.call_args
                assert kwargs["window_size"][0] == expected_width, (
                    f"Test {test_id}: Expected width {expected_width}, "
                    f"but got {kwargs['window_size'][0]}"
                )


def test_update_recipient_to_slack_v2(mocker: MockerFixture):
    """
    Test converting a Slack recipient to Slack v2 format.
    """
    mocker.patch(
        "axbi.commands.report.execute.get_channels_with_search",
        return_value=[
            {
                "id": "abc124f",
                "name": "channel-1",
                "is_member": True,
                "is_private": False,
            },
            {
                "id": "blah_!channel_2",
                "name": "Channel_2",
                "is_member": True,
                "is_private": False,
            },
        ],
    )
    mock_report_schedule = ReportSchedule(
        recipients=[
            ReportRecipients(
                type=ReportRecipientType.SLACK,
                recipient_config_json=json.dumps({"target": "Channel-1, Channel_2"}),
            ),
        ],
    )

    mock_cmmd: BaseReportState = BaseReportState(
        mock_report_schedule, "January 1, 2021", "execution_id_example"
    )
    mock_cmmd.update_report_schedule_slack_v2()

    assert (
        mock_cmmd._report_schedule.recipients[0].recipient_config_json
        == '{"target": "abc124f,blah_!channel_2"}'
    )
    assert mock_cmmd._report_schedule.recipients[0].type == ReportRecipientType.SLACKV2


def test_update_recipient_to_slack_v2_missing_channels(mocker: MockerFixture):
    """
    Test converting a Slack recipient to Slack v2 format raises an error
    in case it can't find all channels.
    """
    mocker.patch(
        "axbi.commands.report.execute.get_channels_with_search",
        return_value=[
            {
                "id": "blah_!channel_2",
                "name": "Channel 2",
                "is_member": True,
                "is_private": False,
            },
        ],
    )
    mock_report_schedule = ReportSchedule(
        name="Test Report",
        recipients=[
            ReportRecipients(
                type=ReportRecipientType.SLACK,
                recipient_config_json=json.dumps({"target": "Channel 1, Channel 2"}),
            ),
        ],
    )

    mock_cmmd: BaseReportState = BaseReportState(
        mock_report_schedule, "January 1, 2021", "execution_id_example"
    )
    with pytest.raises(UpdateFailedError):
        mock_cmmd.update_report_schedule_slack_v2()


def test_update_recipient_to_slack_v2_restores_all_recipients_on_failure(
    mocker: MockerFixture,
) -> None:
    """
    Test Slack v2 conversion restores earlier recipient mutations on failure.
    """
    mocker.patch(
        "axbi.commands.report.execute.get_channels_with_search",
        side_effect=[
            [
                {
                    "id": "channel_1_id",
                    "name": "Channel 1",
                    "is_member": True,
                    "is_private": False,
                },
            ],
            [],
        ],
    )
    first_config = json.dumps({"target": "Channel 1"})
    second_config = json.dumps({"target": "Missing Channel"})
    mock_report_schedule = ReportSchedule(
        recipients=[
            ReportRecipients(
                type=ReportRecipientType.SLACK,
                recipient_config_json=first_config,
            ),
            ReportRecipients(
                type=ReportRecipientType.SLACK,
                recipient_config_json=second_config,
            ),
        ],
    )

    mock_cmmd: BaseReportState = BaseReportState(
        mock_report_schedule, "January 1, 2021", "execution_id_example"
    )

    with pytest.raises(UpdateFailedError, match="Could not find"):
        mock_cmmd.update_report_schedule_slack_v2()

    first_recipient, second_recipient = mock_cmmd._report_schedule.recipients
    assert first_recipient.type == ReportRecipientType.SLACK
    assert first_recipient.recipient_config_json == first_config
    assert second_recipient.type == ReportRecipientType.SLACK
    assert second_recipient.recipient_config_json == second_config


def test_update_recipient_to_slack_v2_skips_malformed_channels(
    mocker: MockerFixture,
) -> None:
    """
    Test converting Slack recipients treats malformed channel lookup results
    as missing channels instead of raising a raw lookup error.
    """
    mocker.patch(
        "axbi.commands.report.execute.get_channels_with_search",
        return_value=[
            {
                "id": "abc124f",
                "name": "Channel 1",
                "is_member": True,
                "is_private": False,
            },
            {
                "name": "Channel 2",
                "is_member": True,
                "is_private": False,
            },
        ],
    )
    mock_report_schedule = ReportSchedule(
        recipients=[
            ReportRecipients(
                type=ReportRecipientType.SLACK,
                recipient_config_json=json.dumps({"target": "Channel 1, Channel 2"}),
            ),
        ],
    )

    mock_cmmd: BaseReportState = BaseReportState(
        mock_report_schedule, "January 1, 2021", "execution_id_example"
    )

    with pytest.raises(UpdateFailedError, match="Could not find"):
        mock_cmmd.update_report_schedule_slack_v2()

    assert mock_cmmd._report_schedule.recipients[0].type == ReportRecipientType.SLACK
    assert mock_cmmd._report_schedule.recipients[0].recipient_config_json == json.dumps(
        {"target": "Channel 1, Channel 2"}
    )


# ---------------------------------------------------------------------------
# Tier 1: _update_query_context + create_log
# ---------------------------------------------------------------------------


def test_update_query_context_wraps_screenshot_failure(mocker: MockerFixture) -> None:
    """_update_query_context wraps ScreenshotFailedError as CsvFailedError."""
    schedule = mocker.Mock(spec=ReportSchedule)
    state = BaseReportState(schedule, datetime.utcnow(), uuid4())
    state._report_schedule = schedule
    mocker.patch.object(
        state,
        "_get_screenshots",
        side_effect=ReportScheduleScreenshotFailedError("boom"),
    )
    with pytest.raises(ReportScheduleCsvFailedError, match="query context"):
        state._update_query_context()


def test_update_query_context_wraps_screenshot_timeout(mocker: MockerFixture) -> None:
    """_update_query_context wraps ScreenshotTimeout as CsvFailedError."""
    schedule = mocker.Mock(spec=ReportSchedule)
    state = BaseReportState(schedule, datetime.utcnow(), uuid4())
    state._report_schedule = schedule
    mocker.patch.object(
        state,
        "_get_screenshots",
        side_effect=ReportScheduleScreenshotTimeout(),
    )
    with pytest.raises(ReportScheduleCsvFailedError, match="query context"):
        state._update_query_context()


def test_create_log_stale_data_raises_unexpected_error(mocker: MockerFixture) -> None:
    """StaleDataError during create_log should rollback and raise UnexpectedError."""
    from sqlalchemy.orm.exc import StaleDataError

    schedule = mocker.Mock(spec=ReportSchedule)
    schedule.last_value = None
    schedule.last_value_row_json = None
    schedule.last_state = ReportState.WORKING

    state = BaseReportState(schedule, datetime.utcnow(), uuid4())
    state._report_schedule = schedule

    mock_db = mocker.patch("axbi.commands.report.execute.db")
    mock_db.session.commit.side_effect = StaleDataError("stale")
    mocker.patch(
        "axbi.commands.report.execute.ReportExecutionLogDAO.create_for_schedule",
        return_value=mocker.Mock(),
    )

    with pytest.raises(ReportScheduleUnexpectedError):
        state.create_log()
    # commit_session rolls back on commit failure; create_log also rolls back
    # if StaleDataError originated earlier. At least one cleanup is required.
    assert mock_db.session.rollback.call_count >= 1


# ---------------------------------------------------------------------------
# Tier 2: _get_notification_content branches
# ---------------------------------------------------------------------------


def _make_notification_state(
    mocker: MockerFixture,
    *,
    report_format: ReportDataFormat = ReportDataFormat.PNG,
    schedule_type: ReportScheduleType = ReportScheduleType.REPORT,
    has_chart: bool = True,
    email_subject: str | None = None,
    chart_name: str = "My Chart",
    dashboard_title: str = "My Dashboard",
) -> BaseReportState:
    """Build a BaseReportState with a mock schedule for notification tests."""
    schedule = mocker.Mock(spec=ReportSchedule)
    schedule.type = schedule_type
    schedule.report_format = report_format
    schedule.name = "Test Schedule"
    schedule.description = "desc"
    schedule.email_subject = email_subject
    schedule.force_screenshot = False
    schedule.recipients = []
    schedule.owners = []

    if has_chart:
        schedule.chart = mocker.Mock()
        schedule.chart.slice_name = chart_name
        schedule.dashboard = None
    else:
        schedule.chart = None
        schedule.dashboard = mocker.Mock()
        schedule.dashboard.dashboard_title = dashboard_title
        schedule.dashboard.uuid = "dash-uuid"
        schedule.dashboard.id = 1

    schedule.extra = {}

    state = BaseReportState(schedule, datetime.utcnow(), uuid4())
    state._report_schedule = schedule

    # Stub helpers that _get_notification_content calls
    mocker.patch.object(state, "_get_log_data", return_value={})
    mocker.patch.object(state, "_get_url", return_value="http://example.com")

    return state


@patch("axbi.commands.report.execute.feature_flag_manager")
def test_get_notification_content_png_screenshot(
    mock_ff, mocker: MockerFixture
) -> None:
    mock_ff.is_feature_enabled.return_value = False
    state = _make_notification_state(mocker, report_format=ReportDataFormat.PNG)
    mocker.patch.object(state, "_get_screenshots", return_value=[b"img1", b"img2"])

    content = state._get_notification_content()
    assert content.screenshots == [b"img1", b"img2"]
    assert content.text is None


@patch("axbi.commands.report.execute.feature_flag_manager")
def test_get_notification_content_png_empty_returns_error(
    mock_ff, mocker: MockerFixture
) -> None:
    mock_ff.is_feature_enabled.return_value = False
    state = _make_notification_state(mocker, report_format=ReportDataFormat.PNG)
    mocker.patch.object(state, "_get_screenshots", return_value=[])

    content = state._get_notification_content()
    assert content.text == "Unexpected missing screenshot"


@patch("axbi.commands.report.execute.feature_flag_manager")
def test_get_notification_content_csv_format(mock_ff, mocker: MockerFixture) -> None:
    mock_ff.is_feature_enabled.return_value = False
    state = _make_notification_state(
        mocker, report_format=ReportDataFormat.CSV, has_chart=True
    )
    mocker.patch.object(state, "_get_csv_data", return_value=b"col1,col2\n1,2")

    content = state._get_notification_content()
    assert content.csv == b"col1,col2\n1,2"


@patch("axbi.commands.report.execute.feature_flag_manager")
def test_get_notification_content_text_format(mock_ff, mocker: MockerFixture) -> None:
    import pandas as pd

    mock_ff.is_feature_enabled.return_value = False
    state = _make_notification_state(
        mocker, report_format=ReportDataFormat.TEXT, has_chart=True
    )
    df = pd.DataFrame({"a": [1]})
    mocker.patch.object(state, "_get_embedded_data", return_value=df)

    content = state._get_notification_content()
    assert content.embedded_data is not None
    assert list(content.embedded_data.columns) == ["a"]


@pytest.mark.parametrize(
    "email_subject,has_chart,expected_name",
    [
        ("Custom Subject", True, "Custom Subject"),
        (None, True, "Test Schedule: My Chart"),
        (None, False, "Test Schedule: My Dashboard"),
    ],
    ids=["email_subject", "chart_name", "dashboard_name"],
)
@patch("axbi.commands.report.execute.feature_flag_manager")
def test_get_notification_content_name(
    mock_ff,
    mocker: MockerFixture,
    email_subject: str | None,
    has_chart: bool,
    expected_name: str,
) -> None:
    """Notification name comes from email_subject, chart, or dashboard."""
    mock_ff.is_feature_enabled.return_value = False
    state = _make_notification_state(
        mocker,
        report_format=ReportDataFormat.PNG,
        email_subject=email_subject,
        has_chart=has_chart,
    )
    mocker.patch.object(state, "_get_screenshots", return_value=[b"img"])

    content = state._get_notification_content()
    assert content.name == expected_name


# ---------------------------------------------------------------------------
# Tier 3: State machine top-level branches
# ---------------------------------------------------------------------------


def _make_state_instance(
    mocker: MockerFixture,
    cls: type,
    *,
    schedule_type: ReportScheduleType = ReportScheduleType.ALERT,
    last_state: ReportState = ReportState.NOOP,
    grace_period: int = 3600,
    working_timeout: int = 3600,
) -> BaseReportState:
    """Create a state-machine state instance with a mocked schedule."""
    schedule = mocker.Mock(spec=ReportSchedule)
    schedule.type = schedule_type
    schedule.last_state = last_state
    schedule.grace_period = grace_period
    schedule.working_timeout = working_timeout
    schedule.last_eval_dttm = datetime.utcnow()
    schedule.name = "Test"
    schedule.owners = []
    schedule.recipients = []
    schedule.force_screenshot = False
    schedule.extra = {}

    instance = cls(schedule, datetime.utcnow(), uuid4())
    instance._report_schedule = schedule
    return instance


def test_working_state_timeout_raises_timeout_error(mocker: MockerFixture) -> None:
    """Working state past timeout should raise WorkingTimeoutError and log ERROR."""
    state = _make_state_instance(mocker, ReportWorkingState)
    mocker.patch.object(state, "is_on_working_timeout", return_value=True)

    mock_log = mocker.Mock()
    mock_log.end_dttm = datetime.utcnow() - timedelta(hours=2)
    mocker.patch(
        "axbi.commands.report.execute.ReportScheduleDAO.find_last_entered_working_log",
        return_value=mock_log,
    )
    mocker.patch.object(state, "update_report_schedule_and_log")

    with pytest.raises(ReportScheduleWorkingTimeoutError):
        state.next()

    state.update_report_schedule_and_log.assert_called_once_with(  # type: ignore[attr-defined]
        ReportState.ERROR,
        error_message=str(ReportScheduleWorkingTimeoutError()),
    )


def test_working_state_still_working_raises_previous_working(
    mocker: MockerFixture,
) -> None:
    """Working state not yet timed out should raise PreviousWorkingError."""
    state = _make_state_instance(mocker, ReportWorkingState)
    mocker.patch.object(state, "is_on_working_timeout", return_value=False)
    mocker.patch.object(state, "update_report_schedule_and_log")

    with pytest.raises(ReportSchedulePreviousWorkingError):
        state.next()

    state.update_report_schedule_and_log.assert_called_once_with(  # type: ignore[attr-defined]
        ReportState.WORKING,
        error_message=str(ReportSchedulePreviousWorkingError()),
    )


def test_success_state_grace_period_returns_without_sending(
    mocker: MockerFixture,
) -> None:
    """Alert in grace period should set GRACE state and not send."""
    state = _make_state_instance(
        mocker,
        ReportSuccessState,
        schedule_type=ReportScheduleType.ALERT,
    )
    mocker.patch.object(state, "is_in_grace_period", return_value=True)
    mocker.patch.object(state, "update_report_schedule_and_log")
    mock_send = mocker.patch.object(state, "send")

    state.next()

    mock_send.assert_not_called()
    state.update_report_schedule_and_log.assert_called_once_with(  # type: ignore[attr-defined]
        ReportState.GRACE,
        error_message=str(ReportScheduleAlertGracePeriodError()),
    )


def test_not_triggered_error_state_send_failure_logs_error_and_reraises(
    mocker: MockerFixture,
) -> None:
    """When send() fails in NOOP/ERROR state, error should be logged and re-raised."""
    state = _make_state_instance(
        mocker,
        ReportNotTriggeredErrorState,
        schedule_type=ReportScheduleType.REPORT,
    )
    send_error = RuntimeError("send failed")
    mocker.patch.object(state, "send", side_effect=send_error)
    mocker.patch.object(state, "update_report_schedule_and_log")
    mocker.patch.object(state, "is_in_error_grace_period", return_value=True)

    with pytest.raises(RuntimeError, match="send failed"):
        state.next()

    # Should have logged WORKING, then ERROR
    calls = state.update_report_schedule_and_log.call_args_list  # type: ignore[attr-defined]
    assert calls[0].args[0] == ReportState.WORKING
    assert calls[1].args[0] == ReportState.ERROR
    error_msg = calls[1].kwargs.get("error_message") or (
        calls[1].args[1] if len(calls[1].args) > 1 else ""
    )
    assert "send failed" in error_msg


# ---------------------------------------------------------------------------
# Phase 1 remaining gaps
# ---------------------------------------------------------------------------


def test_get_dashboard_urls_no_state_fallback(
    mocker: MockerFixture, app: AxBIApp
) -> None:
    """No dashboard state in extra -> standard dashboard URL, not permalink."""
    mock_report_schedule = mocker.Mock(spec=ReportSchedule)
    mock_report_schedule.chart = False
    mock_report_schedule.force_screenshot = False
    mock_report_schedule.extra = {}  # no dashboard state
    mock_report_schedule.dashboard = mocker.Mock()
    mock_report_schedule.dashboard.uuid = "dash-uuid-123"
    mock_report_schedule.dashboard.id = 42
    mock_report_schedule.recipients = []
    mock_report_schedule.get_native_filters_params.return_value = ("", [])

    state = BaseReportState(mock_report_schedule, "Jan 1", "exec_id")
    state._report_schedule = mock_report_schedule

    result = state.get_dashboard_urls()

    assert len(result) == 1
    assert "ax-bi/dashboard/" in result[0]
    assert "dashboard/p/" not in result[0]  # not a permalink


def test_success_state_alert_command_error_sends_error_and_reraises(
    mocker: MockerFixture,
) -> None:
    """AlertCommand exception -> send_error + ERROR state with marker."""
    state = _make_state_instance(
        mocker, ReportSuccessState, schedule_type=ReportScheduleType.ALERT
    )
    mocker.patch.object(state, "is_in_grace_period", return_value=False)
    mocker.patch.object(state, "update_report_schedule_and_log")
    mocker.patch.object(state, "send_error")
    mocker.patch(
        "axbi.commands.report.execute.AlertCommand"
    ).return_value.run.side_effect = RuntimeError("alert boom")

    with pytest.raises(RuntimeError, match="alert boom"):
        state.next()

    state.send_error.assert_called_once()  # type: ignore[attr-defined]
    calls = state.update_report_schedule_and_log.call_args_list  # type: ignore[attr-defined]
    # First call: WORKING, second call: ERROR with marker
    assert calls[0].args[0] == ReportState.WORKING
    assert calls[1].args[0] == ReportState.ERROR
    assert (
        calls[1].kwargs.get("error_message")
        == REPORT_SCHEDULE_ERROR_NOTIFICATION_MARKER
    )


def test_success_state_send_error_logs_and_reraises(
    mocker: MockerFixture,
) -> None:
    """send() exception for REPORT type -> ERROR state + re-raise."""
    state = _make_state_instance(
        mocker, ReportSuccessState, schedule_type=ReportScheduleType.REPORT
    )
    mocker.patch.object(state, "send", side_effect=RuntimeError("send boom"))
    mocker.patch.object(state, "update_report_schedule_and_log")

    with pytest.raises(RuntimeError, match="send boom"):
        state.next()

    calls = state.update_report_schedule_and_log.call_args_list  # type: ignore[attr-defined]
    assert calls[-1].args[0] == ReportState.ERROR


@patch("axbi.commands.report.execute.feature_flag_manager")
def test_get_notification_content_pdf_format(mock_ff, mocker: MockerFixture) -> None:
    """PDF report format branch produces pdf content."""
    mock_ff.is_feature_enabled.return_value = False
    state = _make_notification_state(mocker, report_format=ReportDataFormat.PDF)
    mocker.patch.object(state, "_get_pdf", return_value=b"%PDF-fake")

    content = state._get_notification_content()
    assert content.pdf == b"%PDF-fake"
    assert content.text is None


# ---------------------------------------------------------------------------
# Phase 1 gap closure: state machine, feature flag, create_log, success path
# ---------------------------------------------------------------------------


def test_state_machine_unknown_state_raises_not_found(
    mocker: MockerFixture,
) -> None:
    """State machine raises StateNotFoundError when last_state matches no class."""
    schedule = mocker.Mock(spec=ReportSchedule)
    # Use a string that isn't in any state class's current_states
    schedule.last_state = "NONEXISTENT_STATE"

    sm = ReportScheduleStateMachine(uuid4(), schedule, datetime.utcnow())
    with pytest.raises(ReportScheduleStateNotFoundError):
        sm.run()


@patch("axbi.commands.report.execute.feature_flag_manager")
def test_get_notification_content_alert_no_flag_skips_attachment(
    mock_ff, mocker: MockerFixture
) -> None:
    """Alert with ALERTS_ATTACH_REPORTS=False skips screenshot/pdf/csv attachment."""
    mock_ff.is_feature_enabled.return_value = False
    state = _make_notification_state(
        mocker,
        report_format=ReportDataFormat.PNG,
        schedule_type=ReportScheduleType.ALERT,
        has_chart=True,
    )
    mock_screenshots = mocker.patch.object(state, "_get_screenshots")

    content = state._get_notification_content()

    # _get_screenshots should NOT be called — the attachment block is skipped
    mock_screenshots.assert_not_called()
    assert content.screenshots == []
    assert content.text is None


def test_create_log_success_commits(mocker: MockerFixture) -> None:
    """Successful create_log creates a log entry and commits."""
    schedule = mocker.Mock(spec=ReportSchedule)
    schedule.last_value = "42"
    schedule.last_value_row_json = '{"col": 42}'
    schedule.last_state = ReportState.SUCCESS

    state = BaseReportState(schedule, datetime.utcnow(), uuid4())
    state._report_schedule = schedule

    mock_db = mocker.patch("axbi.commands.report.execute.db")
    mock_log_create = mocker.patch(
        "axbi.commands.report.execute.ReportExecutionLogDAO.create_for_schedule",
        return_value=mocker.Mock(),
    )

    state.create_log(error_message=None)

    mock_log_create.assert_called_once_with(
        report_schedule=schedule,
        scheduled_dttm=state._scheduled_dttm,
        start_dttm=state._start_dttm,
        end_dttm=ANY,
        error_message=None,
        execution_id=state._execution_id,
    )
    mock_db.session.commit.assert_called_once()
    mock_db.session.rollback.assert_not_called()


def test_async_execute_validate_uses_unfiltered_schedule_dao(
    mocker: MockerFixture,
) -> None:
    """Background execution resolves schedules through the explicit DAO boundary."""
    schedule = mocker.Mock(spec=ReportSchedule)
    find_schedule = mocker.patch(
        "axbi.commands.report.execute.ReportScheduleDAO.find_one_or_none",
        return_value=schedule,
    )
    command = AsyncExecuteReportScheduleCommand(str(uuid4()), 42, datetime.utcnow())

    command.validate()

    find_schedule.assert_called_once_with(skip_base_filter=True, id=42)
    assert command._model is schedule


def test_async_execute_validate_raises_when_schedule_is_missing(
    mocker: MockerFixture,
) -> None:
    """A missing DAO result retains the command's not-found contract."""
    mocker.patch(
        "axbi.commands.report.execute.ReportScheduleDAO.find_one_or_none",
        return_value=None,
    )
    command = AsyncExecuteReportScheduleCommand(str(uuid4()), 42, datetime.utcnow())

    with pytest.raises(ReportScheduleNotFoundError):
        command.validate()


def test_success_state_report_sends_and_logs_success(
    mocker: MockerFixture,
) -> None:
    """REPORT type success path: send() + update state to SUCCESS."""
    state = _make_state_instance(
        mocker,
        ReportSuccessState,
        schedule_type=ReportScheduleType.REPORT,
    )
    mock_send = mocker.patch.object(state, "send")
    mock_update = mocker.patch.object(state, "update_report_schedule_and_log")

    state.next()

    mock_send.assert_called_once()
    # WORKING is set before send() (concurrency guard against duplicate sends),
    # then SUCCESS after.
    assert mock_update.call_args_list == [
        mocker.call(ReportState.WORKING),
        mocker.call(ReportState.SUCCESS, error_message=None),
    ]


def test_success_state_error_logged_when_send_error_raises(
    mocker: MockerFixture,
) -> None:
    """If send_error() itself raises, the schedule must still transition to
    ERROR (not stay stuck in WORKING)."""
    state = _make_state_instance(
        mocker, ReportSuccessState, schedule_type=ReportScheduleType.ALERT
    )
    mocker.patch.object(state, "is_in_grace_period", return_value=False)
    mock_update = mocker.patch.object(state, "update_report_schedule_and_log")
    mocker.patch.object(
        state, "send_error", side_effect=RuntimeError("notification boom")
    )
    mocker.patch(
        "axbi.commands.report.execute.AlertCommand"
    ).return_value.run.side_effect = RuntimeError("alert boom")

    # The original alert error propagates...
    with pytest.raises(RuntimeError, match="alert boom"):
        state.next()

    # ...but ERROR was still logged despite send_error() failing.
    states = [call.args[0] for call in mock_update.call_args_list]
    assert ReportState.ERROR in states


def test_get_url_for_csv_uses_post_processed_type(
    app: AxBIApp,
    mocker: MockerFixture,
) -> None:
    """Regression for #25538: when an alert/report generates a CSV for a
    chart, the URL must request type=POST_PROCESSED so the chart's saved
    filters (including time-range filters) are applied. The original report
    described a chart with a "last 30 days" filter that returned only 14
    rows in the UI, but the alert CSV came back with 219 rows (the entire
    unfiltered table).

    POST_PROCESSED is the marker that propagates the chart's query_context
    -- including its time filter -- through to the CSV renderer. A
    regression that switched to FULL or RAW would replicate the original
    bug.
    """
    from datetime import datetime
    from uuid import UUID

    from axbi.commands.report.execute import BaseReportState
    from axbi.common.chart_data import ChartDataResultFormat

    app.config.update({"ALERT_REPORTS_EXECUTORS": {}})

    report_schedule = create_report_schedule(mocker)
    report_schedule.force_screenshot = False
    report_schedule.chart_id = report_schedule.chart.id

    state = BaseReportState(
        report_schedule=report_schedule,
        scheduled_dttm=datetime.now(),
        execution_id=UUID("084e7ee6-5557-4ecd-9632-b7f39c9ec524"),
    )

    url = state._get_url(result_format=ChartDataResultFormat.CSV)

    assert "format=csv" in url.lower(), f"expected csv format in URL: {url}"
    assert "type=post_processed" in url.lower(), (
        f"CSV report URL must use type=post_processed so chart filters "
        f"(incl. time filters) are applied; got: {url}; see issue #25538"
    )

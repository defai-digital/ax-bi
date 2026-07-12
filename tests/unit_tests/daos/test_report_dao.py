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
from __future__ import annotations

from datetime import datetime
from uuid import uuid4

import pytest
from sqlalchemy.orm.session import Session

from axbi.daos.report import ReportExecutionLogDAO, ReportScheduleDAO
from axbi.reports.models import ReportSchedule, ReportScheduleType, ReportState
from axbi.utils import json


@pytest.fixture(autouse=True)
def _create_tables(session: Session) -> None:
    ReportSchedule.metadata.create_all(session.get_bind())  # pylint: disable=no-member


def _create_report(
    session: Session,
    name: str,
    extra_json: str = "{}",
) -> ReportSchedule:
    report = ReportSchedule(
        name=name,
        type=ReportScheduleType.REPORT,
        crontab="0 9 * * *",
        extra_json=extra_json,
    )
    session.add(report)
    session.flush()
    return report


def test_find_by_extra_metadata_returns_matching_reports(
    session: Session,
) -> None:
    extra = json.dumps({"dashboard_tab_ids": ["TAB-abc123"]})
    _create_report(session, "match", extra_json=extra)
    _create_report(session, "no-match", extra_json="{}")

    results = ReportScheduleDAO.find_by_extra_metadata("TAB-abc123")

    assert len(results) == 1
    assert results[0].name == "match"


def test_find_by_extra_metadata_returns_empty_when_no_match(
    session: Session,
) -> None:
    _create_report(session, "report1", extra_json='{"key": "value"}')

    results = ReportScheduleDAO.find_by_extra_metadata("nonexistent")

    assert results == []


def test_find_by_extra_metadata_escapes_percent_wildcard(
    session: Session,
) -> None:
    _create_report(session, "with-percent", extra_json='{"slug": "100%done"}')
    _create_report(session, "other", extra_json='{"slug": "100xdone"}')

    results = ReportScheduleDAO.find_by_extra_metadata("100%done")

    assert len(results) == 1
    assert results[0].name == "with-percent"


def test_find_by_extra_metadata_escapes_underscore_wildcard(
    session: Session,
) -> None:
    _create_report(session, "with-underscore", extra_json='{"slug": "a_b"}')
    _create_report(session, "other", extra_json='{"slug": "axb"}')

    results = ReportScheduleDAO.find_by_extra_metadata("a_b")

    assert len(results) == 1
    assert results[0].name == "with-underscore"


def test_find_by_native_filter_id_returns_matching_reports(
    session: Session,
) -> None:
    extra = json.dumps({"dashboard": {"nativeFilters": "NATIVE_FILTER-abc123"}})
    _create_report(session, "match", extra_json=extra)
    _create_report(session, "no-match", extra_json="{}")

    results = ReportScheduleDAO.find_by_native_filter_id("NATIVE_FILTER-abc123")

    assert len(results) == 1
    assert results[0].name == "match"


def test_find_by_native_filter_id_escapes_percent_wildcard(
    session: Session,
) -> None:
    _create_report(session, "with-percent", extra_json='{"id": "FILTER-100%x"}')
    _create_report(session, "other", extra_json='{"id": "FILTER-100yx"}')

    results = ReportScheduleDAO.find_by_native_filter_id("FILTER-100%x")

    assert len(results) == 1
    assert results[0].name == "with-percent"


def test_find_by_native_filter_id_escapes_underscore_wildcard(
    session: Session,
) -> None:
    _create_report(session, "with-underscore", extra_json='{"id": "FILTER-a_b"}')
    _create_report(session, "other", extra_json='{"id": "FILTER-axb"}')

    results = ReportScheduleDAO.find_by_native_filter_id("FILTER-a_b")

    assert len(results) == 1
    assert results[0].name == "with-underscore"


def test_set_execution_state_clears_stale_alert_values_for_working(
    session: Session,
) -> None:
    """Entering WORKING clears values that must not leak into its execution log."""
    report = _create_report(session, "working")
    report.last_value = 42
    report.last_value_row_json = '{"value": 42}'
    evaluated_at = datetime(2026, 7, 12, 12, 0, 0)

    result = ReportScheduleDAO.set_execution_state(
        report,
        ReportState.WORKING,
        evaluated_at,
    )

    assert result is report
    assert report.last_state == ReportState.WORKING
    assert report.last_eval_dttm == evaluated_at
    assert report.last_value is None
    assert report.last_value_row_json is None


def test_set_execution_state_preserves_values_for_terminal_state(
    session: Session,
) -> None:
    """Terminal transitions preserve the alert result captured for logging."""
    report = _create_report(session, "success")
    report.last_value = 42
    report.last_value_row_json = '{"value": 42}'
    evaluated_at = datetime(2026, 7, 12, 12, 0, 0)

    ReportScheduleDAO.set_execution_state(
        report,
        ReportState.SUCCESS,
        evaluated_at,
    )

    assert report.last_state == ReportState.SUCCESS
    assert report.last_value == 42
    assert report.last_value_row_json == '{"value": 42}'


def test_create_execution_log_copies_schedule_result_state(session: Session) -> None:
    """The log DAO owns ORM construction and copies the schedule result atomically."""
    report = _create_report(session, "execution log")
    report.last_state = ReportState.SUCCESS
    report.last_value = 42
    report.last_value_row_json = '{"value": 42}'
    scheduled_at = datetime(2026, 7, 12, 12, 0, 0)
    started_at = datetime(2026, 7, 12, 12, 0, 1)
    ended_at = datetime(2026, 7, 12, 12, 0, 2)
    execution_id = uuid4()

    log = ReportExecutionLogDAO.create_for_schedule(
        report_schedule=report,
        scheduled_dttm=scheduled_at,
        start_dttm=started_at,
        end_dttm=ended_at,
        execution_id=execution_id,
        error_message=None,
    )
    session.flush()

    assert log.report_schedule is report
    assert log.scheduled_dttm == scheduled_at
    assert log.start_dttm == started_at
    assert log.end_dttm == ended_at
    assert log.uuid == execution_id
    assert log.state == ReportState.SUCCESS
    assert log.value == 42
    assert log.value_row_json == '{"value": 42}'

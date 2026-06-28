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

from unittest.mock import call, MagicMock, patch

import pytest

from superset.commands.dashboard.exceptions import DashboardInvalidError
from superset.commands.dashboard.update import (
    _get_native_filter_ids,
    UpdateDashboardCommand,
)
from superset.utils import json


def test_get_native_filter_ids_ignores_malformed_metadata() -> None:
    """Malformed dashboard metadata should not break native-filter diffing."""
    assert _get_native_filter_ids("{malformed") == set()


def test_get_native_filter_ids_ignores_malformed_entries() -> None:
    """Malformed native-filter entries should be skipped."""
    metadata = json.dumps(
        {
            "native_filter_configuration": [
                "not-a-filter",
                {"name": "missing id"},
                {"id": 42},
                {"id": "filter-1"},
            ],
        }
    )

    assert _get_native_filter_ids(metadata) == {"filter-1"}


def test_process_native_filter_diff_ignores_malformed_current_metadata() -> None:
    """Updating a dashboard should tolerate malformed persisted metadata."""
    command = UpdateDashboardCommand(
        1,
        {"json_metadata": json.dumps({"native_filter_configuration": []})},
    )
    command._model = MagicMock(id=1, json_metadata="{malformed")

    with patch(
        "superset.commands.dashboard.update.ReportScheduleDAO"
    ) as mock_report_dao:
        command.process_native_filter_diff()

    mock_report_dao.find_by_native_filter_id.assert_not_called()


def test_process_tab_diff_deduplicates_reports_matching_multiple_tabs() -> None:
    """A report matching multiple deleted tabs should only be deactivated once."""
    command = UpdateDashboardCommand(1, {"position_json": json.dumps({})})
    command._model = MagicMock(
        id=1,
        tabs={"all_tabs": ["TAB-A", "TAB-B"]},
    )
    report = MagicMock(id=7)

    with (
        patch(
            "superset.commands.dashboard.update.ReportScheduleDAO"
        ) as mock_report_dao,
        patch.object(command, "_send_deactivated_report_email") as mock_send_email,
    ):
        mock_report_dao.find_by_extra_metadata.side_effect = [[report], [report]]

        command.process_tab_diff()

    mock_report_dao.find_by_extra_metadata.assert_has_calls(
        [call("TAB-A"), call("TAB-B")]
    )
    assert mock_report_dao.find_by_extra_metadata.call_count == 2
    mock_report_dao.update.assert_called_once_with(report, {"active": False})
    mock_send_email.assert_called_once()


def test_validate_rejects_non_object_json_metadata() -> None:
    command = UpdateDashboardCommand(1, {"json_metadata": "[]"})

    with (
        patch("superset.commands.dashboard.update.DashboardDAO") as mock_dao,
        patch(
            "superset.commands.dashboard.update.security_manager.raise_for_ownership"
        ),
    ):
        mock_dao.find_by_id.return_value = MagicMock(id=1)

        with pytest.raises(DashboardInvalidError):
            command.validate()

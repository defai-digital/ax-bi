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
import pytest
from pytest_mock import MockerFixture

from superset.commands.dashboard.delete import DeleteDashboardCommand
from superset.commands.dashboard.exceptions import DashboardForbiddenError
from superset.errors import ErrorLevel, SupersetError, SupersetErrorType
from superset.exceptions import SupersetSecurityException


def _ownership_exc() -> SupersetSecurityException:
    return SupersetSecurityException(
        SupersetError(
            error_type=SupersetErrorType.MISSING_OWNERSHIP_ERROR,
            message="User does not own this dashboard",
            level=ErrorLevel.ERROR,
        )
    )


def test_delete_dashboard_checks_ownership_before_reports(
    mocker: MockerFixture,
) -> None:
    """Unauthorized deletes should not expose associated report details."""
    dashboard = mocker.MagicMock(id=1)
    find_by_ids = mocker.patch(
        "superset.commands.dashboard.delete.DashboardDAO.find_by_ids",
        return_value=[dashboard],
    )
    find_reports = mocker.patch(
        "superset.commands.dashboard.delete.ReportScheduleDAO.find_by_dashboard_ids"
    )
    raise_for_ownership = mocker.patch(
        "superset.commands.dashboard.delete.security_manager.raise_for_ownership",
        side_effect=_ownership_exc(),
    )

    with pytest.raises(DashboardForbiddenError):
        DeleteDashboardCommand([1]).validate()

    find_by_ids.assert_called_once_with([1])
    raise_for_ownership.assert_called_once_with(dashboard)
    find_reports.assert_not_called()

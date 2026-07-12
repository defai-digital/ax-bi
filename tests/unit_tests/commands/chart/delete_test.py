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

from axbi.commands.chart.delete import DeleteChartCommand
from axbi.commands.chart.exceptions import ChartForbiddenError
from axbi.errors import AxBIError, AxBIErrorType, ErrorLevel
from axbi.exceptions import AxBISecurityException


def _ownership_exc() -> AxBISecurityException:
    return AxBISecurityException(
        AxBIError(
            error_type=AxBIErrorType.MISSING_OWNERSHIP_ERROR,
            message="User does not own this chart",
            level=ErrorLevel.ERROR,
        )
    )


def test_delete_chart_checks_ownership_before_reports(
    mocker: MockerFixture,
) -> None:
    """Unauthorized deletes should not expose associated report details."""
    chart = mocker.MagicMock(id=1)
    find_by_ids = mocker.patch(
        "axbi.commands.chart.delete.ChartDAO.find_by_ids",
        return_value=[chart],
    )
    find_reports = mocker.patch(
        "axbi.commands.chart.delete.ReportScheduleDAO.find_by_chart_ids"
    )
    raise_for_ownership = mocker.patch(
        "axbi.commands.chart.delete.security_manager.raise_for_ownership",
        side_effect=_ownership_exc(),
    )

    with pytest.raises(ChartForbiddenError):
        DeleteChartCommand([1]).validate()

    find_by_ids.assert_called_once_with([1])
    raise_for_ownership.assert_called_once_with(chart)
    find_reports.assert_not_called()

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
"""Unit tests for per-object datasource access checks in chart create/update."""

from unittest.mock import MagicMock, patch

import pytest

from axbi.commands.chart.exceptions import ChartForbiddenError
from axbi.errors import AxBIError, AxBIErrorType, ErrorLevel
from axbi.exceptions import AxBISecurityException


def _security_exception() -> AxBISecurityException:
    return AxBISecurityException(
        AxBIError(
            error_type=AxBIErrorType.DATASOURCE_SECURITY_ACCESS_ERROR,
            message="Access denied",
            level=ErrorLevel.ERROR,
        )
    )


# ---------------------------------------------------------------------------
# CreateChartCommand
# ---------------------------------------------------------------------------


def test_create_chart_command_forbidden_when_no_datasource_access() -> None:
    """CreateChartCommand.validate() must raise ChartForbiddenError when the
    caller lacks access to the chart's datasource."""
    from axbi.commands.chart.create import CreateChartCommand

    with patch(
        "axbi.commands.chart.create.get_datasource_by_id",
        return_value=MagicMock(name="datasource"),
    ):
        with patch(
            "axbi.commands.chart.create.security_manager.raise_for_access",
            side_effect=_security_exception(),
        ):
            with patch(
                "axbi.commands.chart.create.CreateChartCommand.populate_owners",
                return_value=[],
            ):
                command = CreateChartCommand(
                    {
                        "slice_name": "test",
                        "viz_type": "echarts_timeseries_bar",
                        "datasource_id": 1,
                        "datasource_type": "table",
                    }
                )
                with pytest.raises(ChartForbiddenError):
                    command.validate()


def test_create_chart_command_allowed_when_access_passes() -> None:
    """CreateChartCommand.validate() must not raise when the caller has access."""
    from axbi.commands.chart.create import CreateChartCommand

    mock_datasource = MagicMock()
    mock_datasource.name = "test_table"

    with patch(
        "axbi.commands.chart.create.get_datasource_by_id",
        return_value=mock_datasource,
    ):
        with patch("axbi.commands.chart.create.security_manager.raise_for_access"):
            with patch(
                "axbi.commands.chart.create.CreateChartCommand.populate_owners",
                return_value=[],
            ):
                with patch(
                    "axbi.commands.chart.create.DashboardDAO.find_by_ids",
                    return_value=[],
                ):
                    command = CreateChartCommand(
                        {
                            "slice_name": "test",
                            "viz_type": "echarts_timeseries_bar",
                            "datasource_id": 1,
                            "datasource_type": "table",
                        }
                    )
                    command.validate()  # should not raise


def test_create_chart_command_ignores_malformed_params_for_viz_type() -> None:
    """Malformed params should not break command construction."""
    from axbi.commands.chart.create import CreateChartCommand

    command = CreateChartCommand(
        {
            "slice_name": "test",
            "params": "{",
            "datasource_id": 1,
            "datasource_type": "table",
        }
    )

    assert "viz_type" not in command._properties


def test_create_chart_command_uses_object_params_for_viz_type() -> None:
    """Object params can provide the fallback viz_type."""
    from axbi.commands.chart.create import CreateChartCommand

    command = CreateChartCommand(
        {
            "slice_name": "test",
            "params": '{"viz_type": "table"}',
            "datasource_id": 1,
            "datasource_type": "table",
        }
    )

    assert command._properties["viz_type"] == "table"


# ---------------------------------------------------------------------------
# UpdateChartCommand
# ---------------------------------------------------------------------------


def test_update_chart_command_forbidden_when_no_datasource_access() -> None:
    """UpdateChartCommand.validate() must raise ChartForbiddenError when the
    caller lacks access to the new datasource."""
    from axbi.commands.chart.update import UpdateChartCommand

    mock_chart = MagicMock()
    mock_chart.id = 1
    mock_chart.owners = []
    mock_chart.dashboards = []
    mock_chart.tags = []

    with patch(
        "axbi.commands.chart.update.ChartDAO.find_by_id",
        return_value=mock_chart,
    ):
        with patch("axbi.commands.chart.update.security_manager.raise_for_ownership"):
            with patch(
                "axbi.commands.chart.update.UpdateChartCommand.compute_owners",
                return_value=[],
            ):
                with patch("axbi.commands.chart.update.validate_tags"):
                    with patch(
                        "axbi.commands.chart.update.get_datasource_by_id",
                        return_value=MagicMock(name="datasource"),
                    ):
                        with patch(
                            "axbi.commands.chart.update.security_manager.raise_for_access",
                            side_effect=_security_exception(),
                        ):
                            command = UpdateChartCommand(
                                1,
                                {
                                    "datasource_id": 2,
                                    "datasource_type": "table",
                                },
                            )
                            with pytest.raises(ChartForbiddenError):
                                command.validate()

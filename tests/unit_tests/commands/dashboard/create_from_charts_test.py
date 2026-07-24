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

from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture
from sqlalchemy.exc import SQLAlchemyError

from axbi.commands.dashboard.create_from_charts import (
    CreateDashboardFromChartsCommand,
)
from axbi.commands.dashboard.exceptions import (
    DashboardChartsAccessDeniedError,
    DashboardChartsNotFoundError,
    DashboardCreateFailedError,
)


def _chart(chart_id: int) -> MagicMock:
    """Create a chart-shaped mock with a stable ID."""
    chart = MagicMock()
    chart.id = chart_id
    return chart


def _properties() -> dict[str, object]:
    """Return valid generated-dashboard properties."""
    return {
        "dashboard_title": "Generated dashboard",
        "json_metadata": "{}",
        "position_json": "{}",
        "published": False,
    }


@pytest.fixture(autouse=True)
def allow_chart_access(mocker: MockerFixture) -> None:
    """Allow charts unless a test exercises authorization explicitly."""
    mocker.patch(
        "axbi.commands.dashboard.create_from_charts.security_manager.can_access_chart",
        return_value=True,
    )


def test_create_dashboard_from_charts_requeries_and_attaches_same_session_models(
    mocker: MockerFixture,
) -> None:
    """The command owns chart ordering, owner lookup, and relationship binding."""
    first = _chart(1)
    second = _chart(2)
    find_charts = mocker.patch(
        "axbi.commands.dashboard.create_from_charts.ChartDAO.find_by_ids",
        return_value=[second, first],
    )
    owner = MagicMock()
    mocker.patch(
        "axbi.commands.dashboard.create_from_charts.get_user_id",
        return_value=17,
    )
    find_owner = mocker.patch(
        "axbi.commands.dashboard.create_from_charts.UserDAO.get_by_id_or_none",
        return_value=owner,
    )
    dashboard = MagicMock()
    create = mocker.patch(
        "axbi.commands.dashboard.create_from_charts.DashboardDAO.create",
        return_value=dashboard,
    )
    properties = _properties()

    command = CreateDashboardFromChartsCommand(properties, [2, 1])
    result = command.run()

    assert result is dashboard
    assert properties == _properties()
    find_charts.assert_called_once_with(
        [2, 1],
        skip_base_filter=True,
    )
    create.assert_called_once_with(attributes=properties)
    find_owner.assert_called_once_with(17)
    # Chart order follows chart_ids ([2, 1]), not primary-key sort.
    assert dashboard.slices == [second, first]
    assert dashboard.owners == [owner]
    assert command.charts == [second, first]


def test_create_dashboard_from_charts_rejects_missing_chart_ids(
    mocker: MockerFixture,
) -> None:
    """A chart removed between tool validation and commit fails atomically."""
    mocker.patch(
        "axbi.commands.dashboard.create_from_charts.ChartDAO.find_by_ids",
        return_value=[_chart(1)],
    )
    create = mocker.patch(
        "axbi.commands.dashboard.create_from_charts.DashboardDAO.create"
    )

    with pytest.raises(DashboardChartsNotFoundError) as exc_info:
        CreateDashboardFromChartsCommand(_properties(), [1, 2]).run()

    assert exc_info.value.missing_ids == {2}
    create.assert_not_called()


def test_create_dashboard_from_charts_rejects_inaccessible_charts(
    mocker: MockerFixture,
) -> None:
    """Authorization is rechecked after charts enter the command session."""
    first = _chart(1)
    second = _chart(2)
    mocker.patch(
        "axbi.commands.dashboard.create_from_charts.ChartDAO.find_by_ids",
        return_value=[first, second],
    )
    mocker.patch(
        "axbi.commands.dashboard.create_from_charts.security_manager.can_access_chart",
        side_effect=[True, False],
    )
    create = mocker.patch(
        "axbi.commands.dashboard.create_from_charts.DashboardDAO.create"
    )

    with pytest.raises(DashboardChartsAccessDeniedError) as exc_info:
        CreateDashboardFromChartsCommand(_properties(), [1, 2]).run()

    assert exc_info.value.chart_ids == {2}
    create.assert_not_called()


def test_create_dashboard_from_charts_runs_asset_hook_after_relationships(
    mocker: MockerFixture,
) -> None:
    """Generated dashboards participate in the standard asset lifecycle hook."""
    chart = _chart(1)
    owner = MagicMock()
    mocker.patch(
        "axbi.commands.dashboard.create_from_charts.ChartDAO.find_by_ids",
        return_value=[chart],
    )
    mocker.patch(
        "axbi.commands.dashboard.create_from_charts.get_user_id",
        return_value=17,
    )
    mocker.patch(
        "axbi.commands.dashboard.create_from_charts.UserDAO.get_by_id_or_none",
        return_value=owner,
    )
    dashboard = MagicMock()
    mocker.patch(
        "axbi.commands.dashboard.create_from_charts.DashboardDAO.create",
        return_value=dashboard,
    )
    after_create = MagicMock()
    current_app = mocker.patch("axbi.commands.dashboard.create_from_charts.current_app")
    current_app.config = {"AFTER_ASSET_CREATE": after_create}

    CreateDashboardFromChartsCommand(_properties(), [1]).run()

    assert dashboard.slices == [chart]
    assert dashboard.owners == [owner]
    after_create.assert_called_once_with(dashboard, "dashboard")


@pytest.mark.parametrize("user_id", [None, 17])
def test_create_dashboard_from_charts_allows_missing_runtime_owner(
    mocker: MockerFixture,
    user_id: int | None,
) -> None:
    """The command preserves the prior owner-optional persistence behavior."""
    mocker.patch(
        "axbi.commands.dashboard.create_from_charts.ChartDAO.find_by_ids",
        return_value=[_chart(1)],
    )
    mocker.patch(
        "axbi.commands.dashboard.create_from_charts.get_user_id",
        return_value=user_id,
    )
    find_owner = mocker.patch(
        "axbi.commands.dashboard.create_from_charts.UserDAO.get_by_id_or_none",
        return_value=None,
    )
    dashboard = MagicMock()
    dashboard.owners = []
    mocker.patch(
        "axbi.commands.dashboard.create_from_charts.DashboardDAO.create",
        return_value=dashboard,
    )

    CreateDashboardFromChartsCommand(_properties(), [1]).run()

    if user_id is None:
        find_owner.assert_not_called()
    else:
        find_owner.assert_called_once_with(user_id)
    assert dashboard.owners == []


def test_create_dashboard_from_charts_maps_sqlalchemy_failures(
    mocker: MockerFixture,
) -> None:
    """Persistence failures roll back through the dashboard command contract."""
    mocker.patch(
        "axbi.commands.dashboard.create_from_charts.ChartDAO.find_by_ids",
        return_value=[_chart(1)],
    )
    mocker.patch(
        "axbi.commands.dashboard.create_from_charts.DashboardDAO.create",
        side_effect=SQLAlchemyError("write failed"),
    )

    with pytest.raises(DashboardCreateFailedError) as exc_info:
        CreateDashboardFromChartsCommand(_properties(), [1]).run()

    assert isinstance(exc_info.value.__cause__, SQLAlchemyError)

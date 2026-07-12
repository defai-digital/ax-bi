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

from collections.abc import Iterator
from typing import Any
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from flask import g
from pytest_mock import MockerFixture
from sqlalchemy.orm.session import Session

from axbi.utils import json


@pytest.fixture
def session_with_data(session: Session) -> Iterator[Session]:
    from axbi.models.dashboard import Dashboard

    engine = session.get_bind()
    Dashboard.metadata.create_all(engine)  # pylint: disable=no-member

    dashboard_obj = Dashboard(
        id=100,
        dashboard_title="test_dashboard",
        slug="test_slug",
        slices=[],
        published=True,
    )

    session.add(dashboard_obj)
    session.commit()
    yield session
    session.rollback()


def test_add_favorite(session: Session) -> None:
    from axbi.daos.dashboard import DashboardDAO

    dashboard = DashboardDAO.find_by_id(100, skip_base_filter=True)
    if not dashboard:
        return
    assert len(DashboardDAO.favorited_ids([dashboard])) == 0

    DashboardDAO.add_favorite(dashboard)
    assert len(DashboardDAO.favorited_ids([dashboard])) == 1

    DashboardDAO.add_favorite(dashboard)
    assert len(DashboardDAO.favorited_ids([dashboard])) == 1


def test_remove_favorite(session: Session) -> None:
    from axbi.daos.dashboard import DashboardDAO

    dashboard = DashboardDAO.find_by_id(100, skip_base_filter=True)
    if not dashboard:
        return
    assert len(DashboardDAO.favorited_ids([dashboard])) == 0

    DashboardDAO.add_favorite(dashboard)
    assert len(DashboardDAO.favorited_ids([dashboard])) == 1

    DashboardDAO.remove_favorite(dashboard)
    assert len(DashboardDAO.favorited_ids([dashboard])) == 0

    DashboardDAO.remove_favorite(dashboard)
    assert len(DashboardDAO.favorited_ids([dashboard])) == 0


def test_set_dash_metadata_ignores_non_object_filter_metadata(
    mocker: MockerFixture,
) -> None:
    from axbi.daos.dashboard import DashboardDAO
    from axbi.models.dashboard import Dashboard

    chart_uuid = uuid4()
    mock_slice = MagicMock(id=10, uuid=chart_uuid)
    query = mocker.patch("axbi.daos.dashboard.db").session.query.return_value
    query.filter.return_value.all.return_value = [mock_slice]

    dashboard = Dashboard(json_metadata="{}", position_json="{}")
    DashboardDAO.set_dash_metadata(
        dashboard,
        {
            "positions": {
                "ROOT_ID": {"type": "ROOT", "children": ["CHART-10"]},
                "CHART-10": {"type": "CHART", "meta": {"chartId": 10}},
                "BROKEN": {"type": "CHART"},
            },
            "filter_scopes": "[]",
            "default_filters": "[]",
        },
    )

    metadata = json.loads(dashboard.json_metadata)
    position = json.loads(dashboard.position_json)

    assert json.loads(metadata["default_filters"]) == {}
    assert "filter_scopes" not in metadata
    assert position["CHART-10"]["meta"]["uuid"] == str(chart_uuid)


def test_set_dash_metadata_ignores_non_object_positions(
    mocker: MockerFixture,
) -> None:
    from axbi.daos.dashboard import DashboardDAO
    from axbi.models.dashboard import Dashboard

    query = mocker.patch("axbi.daos.dashboard.db").session.query.return_value
    query.filter.return_value.all.return_value = []

    dashboard = Dashboard(json_metadata="{}", position_json='{"stale": true}')
    DashboardDAO.set_dash_metadata(
        dashboard,
        {
            "positions": "[]",
            "default_filters": {"10": "value"},
        },
    )

    metadata = json.loads(dashboard.json_metadata)

    assert json.loads(dashboard.position_json) == {}
    assert json.loads(metadata["default_filters"]) == {}


def test_copy_dashboard_ignores_non_object_metadata_positions(
    app: Any,
    mocker: MockerFixture,
) -> None:
    from axbi.daos.dashboard import DashboardDAO

    mocker.patch("axbi.daos.dashboard.is_feature_enabled", return_value=False)
    mock_db = mocker.patch("axbi.daos.dashboard.db")
    mock_slice = MagicMock(id=10)
    mock_slice.clone.return_value = MagicMock(id=100, dashboards=[])
    original_dash = MagicMock(slices=[mock_slice], params="{}")

    with app.test_request_context():
        g.user = None
        copied_dash = DashboardDAO.copy_dashboard(
            original_dash,
            {
                "dashboard_title": "copied dash",
                "json_metadata": "[]",
                "duplicate_slices": True,
            },
        )

    assert copied_dash.dashboard_title == "copied dash"
    mock_db.session.add.assert_any_call(copied_dash)


def test_copy_dashboard_skips_malformed_position_meta(
    app: Any,
    mocker: MockerFixture,
) -> None:
    from axbi.daos.dashboard import DashboardDAO

    chart_uuid = uuid4()
    mocker.patch("axbi.daos.dashboard.is_feature_enabled", return_value=False)
    mock_db = mocker.patch("axbi.daos.dashboard.db")
    mock_db.session.query.return_value.filter.return_value.all.return_value = [
        MagicMock(id=100, uuid=chart_uuid)
    ]

    mock_slice = MagicMock(id=10)
    mock_slice.clone.return_value = MagicMock(id=100, dashboards=[])
    original_dash = MagicMock(slices=[mock_slice], params="{}")

    with app.test_request_context():
        g.user = None
        copied_dash = DashboardDAO.copy_dashboard(
            original_dash,
            {
                "dashboard_title": "copied dash",
                "json_metadata": {
                    "positions": {
                        "BROKEN": {"type": "CHART", "meta": "not-an-object"},
                        "CHART-10": {"type": "CHART", "meta": {"chartId": 10}},
                    }
                },
                "duplicate_slices": True,
            },
        )

    position = json.loads(copied_dash.position_json)

    assert position["BROKEN"]["meta"] == "not-an-object"
    assert position["CHART-10"]["meta"]["chartId"] == 100
    assert position["CHART-10"]["meta"]["uuid"] == str(chart_uuid)

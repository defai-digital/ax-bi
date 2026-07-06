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

import inspect
from unittest.mock import MagicMock

import pytest
from flask import Flask
from pytest_mock import MockerFixture

from superset.dashboards.api import DashboardRestApi
from superset.dashboards.schemas import DashboardGetResponseSchema


@pytest.fixture
def mock_dashboard() -> MagicMock:
    dash = MagicMock()
    # Real Dashboard objects are not subscriptable. Without this, marshmallow's
    # get_value reads ``dash["changed_on"]`` (which a MagicMock happily returns
    # as another mock) instead of the attribute, and marshmallow 4's DateTime
    # field then fails serializing the mock via datetime.isoformat().
    dash.__getitem__.side_effect = TypeError
    dash.id = 1
    dash.slug = "test-slug"
    dash.url = "/ax-bi/dashboard/test-slug/"
    dash.dashboard_title = "Test Dashboard"
    dash.thumbnail_url = "http://example.com/thumb.png"
    dash.published = True
    dash.css = ""
    dash.theme = None
    dash.json_metadata = "{}"
    dash.position_json = "{}"
    dash.certified_by = None
    dash.certification_details = None
    dash.changed_by_name = "admin"
    dash.changed_by = MagicMock(id=1, first_name="admin", last_name="user")
    dash.changed_on = None
    dash.changed_on_humanized = "2 days ago"
    dash.created_by = MagicMock(id=1, first_name="admin", last_name="user")
    dash.created_on_humanized = "5 days ago"
    dash.charts = []
    dash.owners = []
    dash.roles = []
    dash.tags = []
    dash.custom_tags = []
    dash.is_managed_externally = False
    dash.uuid = None
    return dash


def test_schema_column_selection_excludes_thumbnail(
    mock_dashboard: MagicMock,
) -> None:
    schema = DashboardGetResponseSchema(only=["id", "dashboard_title"])
    result = schema.dump(mock_dashboard)
    assert "id" in result
    assert "dashboard_title" in result
    assert "thumbnail_url" not in result
    assert "slug" not in result


def test_schema_column_selection_with_data_key(
    mock_dashboard: MagicMock,
) -> None:
    """Fields with data_key should work when using the internal field name."""
    schema = DashboardGetResponseSchema(only=["id", "changed_on_humanized"])
    result = schema.dump(mock_dashboard)
    assert "id" in result
    assert "changed_on_delta_humanized" in result
    assert "dashboard_title" not in result


def test_schema_full_response_includes_thumbnail(
    mock_dashboard: MagicMock,
) -> None:
    schema = DashboardGetResponseSchema()
    result = schema.dump(mock_dashboard)
    assert "thumbnail_url" in result
    assert "id" in result
    assert "dashboard_title" in result


def test_data_key_mapping_logic() -> None:
    """The key_to_name mapping used in the API correctly maps data_key to field name."""
    schema = DashboardGetResponseSchema()
    key_to_name = {
        field.data_key or name: name for name, field in schema.fields.items()
    }
    # changed_on_delta_humanized is the data_key for changed_on_humanized
    assert key_to_name["changed_on_delta_humanized"] == "changed_on_humanized"
    assert key_to_name["created_on_delta_humanized"] == "created_on_humanized"
    # fields without data_key map to themselves
    assert key_to_name["id"] == "id"
    assert key_to_name["thumbnail_url"] == "thumbnail_url"


@pytest.mark.parametrize(
    ("method_name", "args", "kwargs"),
    [
        ("post", (), {}),
        ("put", (1,), {}),
        ("put_filters", (1,), {}),
        ("put_chart_customizations", (1,), {}),
        ("put_colors", (1,), {}),
        ("cache_dashboard_screenshot", (1,), {"rison": {}}),
        ("set_embedded", (MagicMock(),), {}),
        ("copy_dash", (MagicMock(),), {}),
    ],
)
def test_json_body_handlers_reject_malformed_json_body(
    mocker: MockerFixture,
    method_name: str,
    args: tuple[object, ...],
    kwargs: dict[str, object],
) -> None:
    """Dashboard JSON handlers should reject parser failures as validation errors."""
    mocker.patch("superset.dashboards.api.is_feature_enabled", return_value=False)
    mocker.patch("superset.dashboards.api.db.session.rollback")
    app = Flask(__name__)
    api = DashboardRestApi.__new__(DashboardRestApi)
    api.response_400 = MagicMock(return_value="bad request")
    method = inspect.unwrap(getattr(DashboardRestApi, method_name))

    with app.test_request_context(
        method="POST",
        data="{malformed",
        content_type="application/json",
    ):
        response = method(api, *args, **kwargs)

    assert response == "bad request"
    api.response_400.assert_called_once_with(
        message={"_schema": ["Invalid input type."]}
    )

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

from datetime import datetime
from unittest.mock import MagicMock, patch

from axbi.models.dashboard import _get_native_filter_datasource_ids, Dashboard
from axbi.utils import json


def test_dashboard_link_escapes_slug() -> None:
    """dashboard_link must HTML-escape the user-controlled slug in the href.

    The slug can carry markup via the import path (which does not run the REST
    API's slug sanitization), so the rendered FAB list-view link must escape it.
    """
    dash = Dashboard()
    dash.id = 1
    dash.dashboard_title = "My Dashboard"
    dash.slug = '"><script>alert(1)</script>'

    link = str(dash.dashboard_link())

    # The injected script tag / attribute breakout must be escaped away.
    assert "<script>" not in link
    assert '"><script' not in link
    # The legitimate anchor markup is still present.
    assert link.startswith("<a href=")
    assert "My Dashboard" in link


def test_dashboard_link_renders_plain_slug() -> None:
    """A normal slug renders a working link."""
    dash = Dashboard()
    dash.id = 7
    dash.dashboard_title = "Sales"
    dash.slug = "sales"

    link = str(dash.dashboard_link())

    assert "/ax-bi/dashboard/sales/" in link
    assert "Sales" in link


def test_dashboard_position_ignores_malformed_layout_json() -> None:
    """Malformed position_json should not break dashboard model access."""
    dash = Dashboard(position_json="{malformed")

    assert dash.position == {}


def test_dashboard_position_ignores_non_object_layout_json() -> None:
    """Non-object position_json should not be treated as layout data."""
    dash = Dashboard(position_json="[]")

    assert dash.position == {}


def test_dashboard_data_ignores_malformed_layout_json() -> None:
    """Dashboard serialization should tolerate malformed position_json."""
    dash = Dashboard(
        id=1,
        dashboard_title="Sales",
        json_metadata="{}",
        position_json="{malformed",
        changed_on=datetime(2024, 1, 1),
    )
    dash.slices = []

    assert dash.data["position_json"] == {}


def test_native_filter_datasource_ids_ignore_malformed_metadata() -> None:
    """Malformed metadata should not break export datasource discovery."""
    with patch("axbi.models.dashboard.DatasourceDAO") as mock_dao:
        assert _get_native_filter_datasource_ids("{malformed") == set()
        mock_dao.get_datasource.assert_not_called()


def test_native_filter_datasource_ids_ignore_malformed_entries() -> None:
    """Malformed native filter entries should not break export discovery."""
    metadata = json.dumps(
        {
            "native_filter_configuration": [
                "not-a-filter",
                {"targets": "not-a-list"},
                {"targets": ["not-a-target", {}]},
            ]
        }
    )

    with patch("axbi.models.dashboard.DatasourceDAO") as mock_dao:
        assert _get_native_filter_datasource_ids(metadata) == set()
        mock_dao.get_datasource.assert_not_called()


def test_native_filter_datasource_ids_include_valid_targets() -> None:
    """Valid native filter targets are included in export datasource discovery."""
    metadata = json.dumps(
        {
            "native_filter_configuration": [
                {"targets": [{"datasetId": 42}]},
            ]
        }
    )
    datasource = MagicMock(id=7, type="table")

    with patch("axbi.models.dashboard.DatasourceDAO") as mock_dao:
        mock_dao.get_datasource.return_value = datasource

        assert _get_native_filter_datasource_ids(metadata) == {(7, "table")}

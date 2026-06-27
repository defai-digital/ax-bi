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
"""Tests for superset.views.utils module"""

from unittest.mock import MagicMock, patch

from flask import current_app

from superset.models.dashboard import Dashboard
from superset.models.slice import Slice
from superset.utils import json
from superset.views.utils import (
    get_dashboard_extra_filters,
    get_form_data,
    JS_CONTROL_FORM_DATA_KEYS,
    REJECTED_FORM_DATA_KEYS,
)


def test_rejected_form_data_keys_cover_all_js_control_keys() -> None:
    """
    With ENABLE_JAVASCRIPT_CONTROLS disabled (the default), every form_data key
    that is later executed as JavaScript by the deck.gl charts must be rejected.

    This guards against a new ``sandboxedEval(fd.<key>)`` call site being added
    without also adding its key to the strip list.
    """
    # The test app keeps ENABLE_JAVASCRIPT_CONTROLS at its default (off).
    assert set(JS_CONTROL_FORM_DATA_KEYS) <= set(REJECTED_FORM_DATA_KEYS)


def test_get_form_data_strips_js_control_keys() -> None:
    """get_form_data drops all JS-executed keys when the flag is disabled."""
    initial_form_data = dict.fromkeys(JS_CONTROL_FORM_DATA_KEYS, "data => data")
    initial_form_data["viz_type"] = "deck_geojson"

    form_data, _ = get_form_data(initial_form_data=initial_form_data)

    for key in JS_CONTROL_FORM_DATA_KEYS:
        assert key not in form_data
    # Non-JS keys are preserved.
    assert form_data["viz_type"] == "deck_geojson"


def test_get_form_data_ignores_non_object_request_form_data() -> None:
    """Non-object request form data should not crash form parsing."""
    with current_app.test_request_context(
        data={"form_data": "[]"},
        query_string={"form_data": "[]"},
    ):
        form_data, slc = get_form_data()

    assert form_data == {}
    assert slc is None


def test_get_form_data_ignores_non_object_json_body() -> None:
    """Non-object JSON request bodies should not crash form parsing."""
    with current_app.test_request_context(json=["queries"]):
        form_data, slc = get_form_data()

    assert form_data == {}
    assert slc is None


def test_get_form_data_ignores_non_object_query_entries() -> None:
    """Query arrays without object entries should not crash form parsing."""
    with current_app.test_request_context(
        data={"form_data": json.dumps({"queries": ["not an object"]})},
    ):
        form_data, slc = get_form_data()

    assert form_data == {"queries": ["not an object"]}
    assert slc is None


def _mock_dashboard_extra_filter_queries(
    mock_db: MagicMock,
    dashboard: Dashboard,
    filter_slice: Slice | None = None,
) -> None:
    dashboard_query = MagicMock()
    dashboard_query.filter_by.return_value.one_or_none.return_value = dashboard
    filter_query = MagicMock()
    filter_query.filter_by.return_value.one_or_none.return_value = filter_slice
    mock_db.session.query.side_effect = (
        lambda model: dashboard_query if model is Dashboard else filter_query
    )


def test_get_dashboard_extra_filters_ignores_non_object_metadata() -> None:
    """Non-object dashboard metadata should not break default filter lookup."""
    dashboard = Dashboard(id=1, json_metadata="[]", position_json="{}")
    dashboard.slices = [Slice(id=10)]

    with patch("superset.views.utils.db") as mock_db:
        _mock_dashboard_extra_filter_queries(mock_db, dashboard)

        assert get_dashboard_extra_filters(slice_id=10, dashboard_id=1) == []


def test_get_dashboard_extra_filters_ignores_non_object_filter_params() -> None:
    """Non-object filter chart params should not break extra filter creation."""
    dashboard = Dashboard(
        id=1,
        json_metadata=json.dumps(
            {
                "default_filters": json.dumps({"10": {"country": ["US"]}}),
                "filter_scopes": {"10": {"country": {"scope": ["ROOT_ID"]}}},
            }
        ),
        position_json="{}",
    )
    dashboard.slices = [Slice(id=20)]
    filter_slice = Slice(id=10, params="[]")

    with patch("superset.views.utils.db") as mock_db:
        _mock_dashboard_extra_filter_queries(mock_db, dashboard, filter_slice)

        assert get_dashboard_extra_filters(slice_id=20, dashboard_id=1) == [
            {"col": "country", "op": "in", "val": ["US"]}
        ]


def test_get_dashboard_extra_filters_ignores_stale_scope_layout_node() -> None:
    """Stale filter scopes should not crash when a layout node is missing."""
    dashboard = Dashboard(
        id=1,
        json_metadata=json.dumps(
            {
                "default_filters": json.dumps({"10": {"country": ["US"]}}),
                "filter_scopes": {"10": {"country": {"scope": ["MISSING_ID"]}}},
            }
        ),
        position_json="{}",
    )
    dashboard.slices = [Slice(id=20)]

    with patch("superset.views.utils.db") as mock_db:
        _mock_dashboard_extra_filter_queries(mock_db, dashboard)

        assert get_dashboard_extra_filters(slice_id=20, dashboard_id=1) == []

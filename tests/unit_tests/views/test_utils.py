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
"""Tests for axbi.views.utils module"""

from typing import Any
from unittest.mock import MagicMock, patch

import msgpack
import pytest
from flask import current_app, g

from axbi.common.db_query_status import QueryStatus
from axbi.exceptions import AxBIException, SerializationError
from axbi.models.dashboard import Dashboard
from axbi.models.slice import Slice
from axbi.utils import json
from axbi.utils.core import merge_extra_filters
from axbi.views.utils import (
    _deserialize_results_payload,
    add_sqllab_custom_filters,
    apply_display_max_row_limit,
    bootstrap_user_data,
    get_dashboard_extra_filters,
    get_datasource_info,
    get_form_data,
    is_slice_in_container,
    JS_CONTROL_FORM_DATA_KEYS,
    loads_request_json,
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


def test_get_form_data_reads_form_encoded_extra_filters() -> None:
    """SQL Lab filter parsing must not consume form-encoded chart form_data."""
    with current_app.test_request_context(
        data={
            "form_data": json.dumps(
                {"extra_filters": [{"col": "name", "op": "in", "val": "foo"}]}
            )
        }
    ):
        form_data, slc = get_form_data()

    assert form_data == {
        "extra_filters": [{"col": "name", "op": "in", "val": "foo"}],
    }
    assert slc is None


def test_merge_extra_filters_normalizes_legacy_in_operator() -> None:
    """Legacy lowercase extra filter operators should become adhoc operators."""
    form_data = {
        "extra_filters": [{"col": "name", "op": "in", "val": "foo"}],
    }

    merge_extra_filters(form_data)

    assert len(form_data["adhoc_filters"]) == 1
    adhoc_filter = form_data["adhoc_filters"][0]
    assert adhoc_filter["clause"] == "WHERE"
    assert adhoc_filter["comparator"] == "foo"
    assert adhoc_filter["expressionType"] == "SIMPLE"
    assert adhoc_filter["isExtra"] is True
    assert adhoc_filter["operator"] == "IN"
    assert adhoc_filter["subject"] == "name"
    assert "extra_filters" not in form_data


def test_loads_request_json_requires_object() -> None:
    """Request JSON helpers should return only decoded JSON objects."""
    assert loads_request_json('{"slice_id": 1}') == {"slice_id": 1}
    assert loads_request_json("[]") == {}
    assert loads_request_json("null") == {}
    assert loads_request_json('"scalar"') == {}
    assert loads_request_json("not json") == {}


@pytest.mark.parametrize(
    "payload",
    [
        [],
        {"selected_columns": []},
        {"data": b"not-arrow", "selected_columns": []},
        {"data": b"", "selected_columns": "not-columns"},
        {"data": b"", "selected_columns": ["not-a-column"]},
    ],
)
def test_deserialize_results_payload_rejects_malformed_msgpack_payloads(
    payload: object,
) -> None:
    """Malformed msgpack result payloads should raise SerializationError."""
    serialized_payload = msgpack.packb(payload)
    query = MagicMock()

    with pytest.raises(SerializationError):
        _deserialize_results_payload(serialized_payload, query, use_msgpack=True)


@pytest.mark.parametrize("payload", ["[]", "null", '"scalar"', "{"])
def test_deserialize_results_payload_rejects_malformed_json_payloads(
    payload: str,
) -> None:
    """Malformed JSON result payloads should raise SerializationError."""
    query = MagicMock()

    with pytest.raises(SerializationError):
        _deserialize_results_payload(payload, query, use_msgpack=False)


def test_bootstrap_user_data_allows_missing_created_on() -> None:
    """Partially populated users should still serialize for bootstrap data."""
    user = MagicMock()
    user.is_anonymous = False
    user.username = "admin"
    user.first_name = "Admin"
    user.last_name = "User"
    user.id = 1
    user.is_active = True
    user.created_on = None
    user.email = "admin@example.com"
    user.login_count = 5

    with patch("axbi.views.utils.security_manager.is_guest_user", return_value=False):
        payload = bootstrap_user_data(user)

    assert payload["createdOn"] is None
    assert payload["username"] == "admin"


def test_apply_display_max_row_limit_truncates_success_payload() -> None:
    sql_results = {
        "status": QueryStatus.SUCCESS,
        "query": {"rows": 3},
        "data": [{"id": 1}, {"id": 2}, {"id": 3}],
    }

    result = apply_display_max_row_limit(sql_results, rows=2)

    assert result["data"] == [{"id": 1}, {"id": 2}]
    assert result["displayLimitReached"] is True


@pytest.mark.parametrize(
    "sql_results",
    [
        {},
        {"status": QueryStatus.SUCCESS},
        {"status": QueryStatus.SUCCESS, "query": None, "data": []},
        {"status": QueryStatus.SUCCESS, "query": {"rows": "3"}, "data": []},
        {"status": QueryStatus.SUCCESS, "query": {"rows": 3}, "data": None},
    ],
)
def test_apply_display_max_row_limit_ignores_malformed_payloads(
    sql_results: dict[str, object],
) -> None:
    original = dict(sql_results)

    result = apply_display_max_row_limit(sql_results, rows=2)

    assert result == original


def test_is_slice_in_container_handles_malformed_chart_meta() -> None:
    """Malformed chart metadata should not crash container checks."""
    layout: dict[str, dict[str, Any]] = {
        "CHART-1": {
            "type": "CHART",
            "meta": "bad",
        },
    }

    assert not is_slice_in_container(layout, "CHART-1", 1)


def test_is_slice_in_container_handles_malformed_children() -> None:
    """Malformed container children should not be traversed."""
    layout: dict[str, dict[str, Any]] = {
        "TABS-1": {
            "type": "TABS",
            "children": "CHART-1",
        },
        "CHART-1": {
            "type": "CHART",
            "meta": {"chartId": 1},
        },
    }

    assert not is_slice_in_container(layout, "TABS-1", 1)


def test_is_slice_in_container_finds_nested_chart() -> None:
    layout: dict[str, dict[str, Any]] = {
        "TABS-1": {
            "type": "TABS",
            "children": ["CHART-1"],
        },
        "CHART-1": {
            "type": "CHART",
            "meta": {"chartId": 1},
        },
    }

    assert is_slice_in_container(layout, "TABS-1", 1)


def test_get_datasource_info_parses_combined_datasource_key() -> None:
    """Combined datasource keys override the explicit URL values."""
    assert get_datasource_info(None, None, {"datasource": "12__table"}) == (
        12,
        "table",
    )


def test_get_datasource_info_uses_explicit_values_without_combined_key() -> None:
    """Explicit datasource route values still work without form datasource."""
    assert get_datasource_info(7, "table", {}) == (7, "table")


def test_get_datasource_info_rejects_malformed_datasource_keys() -> None:
    """Malformed datasource keys should raise the normal missing-dataset error."""
    malformed_datasources: tuple[str | list[str], ...] = (
        "bad__table",
        "1__table__extra",
        "None__table",
        [],
    )
    for datasource in malformed_datasources:
        with pytest.raises(AxBIException) as excinfo:
            get_datasource_info(None, None, {"datasource": datasource})
        assert str(excinfo.value) == (
            "The dataset associated with this chart no longer exists"
        )


def test_get_form_data_ignores_non_object_json_body() -> None:
    """Non-object JSON request bodies should not crash form parsing."""
    with current_app.test_request_context(json=["queries"]):
        form_data, slc = get_form_data()

    assert form_data == {}
    assert slc is None


def test_get_form_data_ignores_malformed_json_body() -> None:
    """Malformed JSON request bodies should not crash form parsing."""
    with current_app.test_request_context(
        data="{malformed",
        content_type="application/json",
    ):
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


@pytest.mark.parametrize(
    ("global_form_data", "expected_form_data"),
    [
        ({"queries": []}, {"queries": []}),
        ({"queries": ["not an object"]}, {"queries": ["not an object"]}),
        ({"queries": "not a list"}, {"queries": "not a list"}),
        (["not an object"], {}),
    ],
)
def test_get_form_data_ignores_malformed_global_query_entries(
    global_form_data: Any,
    expected_form_data: dict[str, Any],
) -> None:
    """Malformed global query payloads should not crash form parsing."""
    with current_app.test_request_context():
        g.form_data = global_form_data
        try:
            form_data, slc = get_form_data()
        finally:
            delattr(g, "form_data")

    assert form_data == expected_form_data
    assert slc is None


def test_add_sqllab_custom_filters_adds_valid_filters() -> None:
    form_data: dict[str, Any] = {}
    filters = [{"col": "country", "op": "==", "val": "US"}]

    with current_app.test_request_context(
        data=json.dumps({"templateParams": json.dumps({"_filters": filters})}),
    ):
        add_sqllab_custom_filters(form_data)

    assert form_data["filters"] == filters


@pytest.mark.parametrize("filters_value", ["bad", {"col": "country"}, 1, None])
def test_add_sqllab_custom_filters_ignores_malformed_filters(
    filters_value: Any,
) -> None:
    form_data: dict[str, Any] = {}

    with current_app.test_request_context(
        data=json.dumps({"templateParams": json.dumps({"_filters": filters_value})}),
    ):
        add_sqllab_custom_filters(form_data)

    assert form_data == {}


def test_add_sqllab_custom_filters_drops_malformed_filter_entries() -> None:
    form_data: dict[str, Any] = {}
    valid_filter = {"col": "country", "op": "==", "val": "US"}

    with current_app.test_request_context(
        data=json.dumps(
            {"templateParams": json.dumps({"_filters": ["bad", valid_filter]})}
        ),
    ):
        add_sqllab_custom_filters(form_data)

    assert form_data["filters"] == [valid_filter]


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

    with patch("axbi.utils.form_data.db") as mock_db:
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

    with patch("axbi.utils.form_data.db") as mock_db:
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

    with patch("axbi.utils.form_data.db") as mock_db:
        _mock_dashboard_extra_filter_queries(mock_db, dashboard)

        assert get_dashboard_extra_filters(slice_id=20, dashboard_id=1) == []


def test_get_dashboard_extra_filters_ignores_non_object_default_filter_columns() -> (
    None
):
    """Malformed default filter values should not abort dashboard loads."""
    dashboard = Dashboard(
        id=1,
        json_metadata=json.dumps(
            {
                "default_filters": json.dumps({"10": ["US"]}),
                "filter_scopes": {"10": {"country": {"scope": ["ROOT_ID"]}}},
            }
        ),
        position_json="{}",
    )
    dashboard.slices = [Slice(id=20)]

    with patch("axbi.utils.form_data.db") as mock_db:
        _mock_dashboard_extra_filter_queries(mock_db, dashboard)

        assert get_dashboard_extra_filters(slice_id=20, dashboard_id=1) == []


def test_get_dashboard_extra_filters_ignores_malformed_explicit_scope() -> None:
    """Malformed explicit scopes should not apply filters broadly."""
    dashboard = Dashboard(
        id=1,
        json_metadata=json.dumps(
            {
                "default_filters": json.dumps({"10": {"country": ["US"]}}),
                "filter_scopes": {"10": {"country": {"scope": "ROOT_ID"}}},
            }
        ),
        position_json="{}",
    )
    dashboard.slices = [Slice(id=20)]

    with patch("axbi.utils.form_data.db") as mock_db:
        _mock_dashboard_extra_filter_queries(mock_db, dashboard)

        assert get_dashboard_extra_filters(slice_id=20, dashboard_id=1) == []

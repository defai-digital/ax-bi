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
"""Form-data and dashboard-filter helpers for non-views layers.

Hoisted from ``axbi.views.utils`` so Command/Task/Model layers do not depend on
the views package (API → Command → DAO → Model boundary).
"""

from __future__ import annotations

from typing import Any

from flask import g, has_request_context, request

from axbi import db
from axbi.extensions import feature_flag_manager, security_manager
from axbi.legacy import update_time_range
from axbi.models.dashboard import Dashboard
from axbi.models.helpers import json_to_dict
from axbi.models.slice import Slice
from axbi.utils import json

# Form-data keys whose values are executed as JavaScript at render time by the
# deck.gl charts (via the frontend ``sandboxedEval`` helper). These are stripped
# from incoming form_data unless the ``ENABLE_JAVASCRIPT_CONTROLS`` feature flag
# is enabled. Keep this list in sync with every ``sandboxedEval(fd.<key>)`` call
# site in the deck.gl plugins.
JS_CONTROL_FORM_DATA_KEYS: list[str] = [
    "js_tooltip",
    "js_onclick_href",
    "js_data_mutator",
    "label_javascript_config_generator",
    "icon_javascript_config_generator",
]

REJECTED_FORM_DATA_KEYS: list[str] = []
if not feature_flag_manager.is_feature_enabled("ENABLE_JAVASCRIPT_CONTROLS"):
    REJECTED_FORM_DATA_KEYS = list(JS_CONTROL_FORM_DATA_KEYS)

# see all dashboard components type in
# /ax-bi-frontend/src/dashboard/util/componentTypes.js
CONTAINER_TYPES = ["COLUMN", "GRID", "TABS", "TAB", "ROW"]


def loads_request_json(request_json_data: str) -> dict[Any, Any]:
    try:
        data = json.loads(request_json_data)
    except (TypeError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _normalize_global_form_data(global_form_data: Any) -> dict[str, Any]:
    if not isinstance(global_form_data, dict):
        return {}

    queries = global_form_data.get("queries")
    if isinstance(queries, list) and queries and isinstance(queries[0], dict):
        global_form_data.update(queries[0])

    return global_form_data


def add_sqllab_custom_filters(form_data: dict[Any, Any]) -> Any:
    """
    SQLLab can include a "filters" attribute in the templateParams.
    The filters attribute is a list of filters to include in the
    request. Useful for testing templates in SQLLab.
    """
    try:
        data = json.loads(request.data)
        if isinstance(data, dict):
            params_str = data.get("templateParams")
            if isinstance(params_str, str):
                params = json.loads(params_str)
                if isinstance(params, dict):
                    filters = params.get("_filters")
                    if isinstance(filters, list):
                        valid_filters = [
                            filter_ for filter_ in filters if isinstance(filter_, dict)
                        ]
                        if valid_filters:
                            form_data.update({"filters": valid_filters})
    except (TypeError, json.JSONDecodeError):
        data = {}


def get_form_data(
    slice_id: int | None = None,
    use_slice_data: bool = False,
    initial_form_data: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], Slice | None]:
    form_data: dict[str, Any] = initial_form_data or {}

    if has_request_context():
        json_data = request.get_json(cache=True, silent=True) if request.is_json else {}
        if not isinstance(json_data, dict):
            json_data = {}

        # chart data API requests are JSON
        first_query = (
            json_data["queries"][0]
            if isinstance(json_data.get("queries"), list)
            and json_data["queries"]
            and isinstance(json_data["queries"][0], dict)
            else None
        )

        request_form_data = request.form.get("form_data")
        request_args_data = request.args.get("form_data")
        if first_query:
            form_data.update(first_query)
        if request_form_data:
            parsed_form_data = loads_request_json(request_form_data)
            # some chart data api requests are form_data
            queries = parsed_form_data.get("queries")
            if isinstance(queries, list) and queries and isinstance(queries[0], dict):
                form_data.update(queries[0])
            else:
                form_data.update(parsed_form_data)
        # request params can overwrite the body
        if request_args_data:
            form_data.update(loads_request_json(request_args_data))
        add_sqllab_custom_filters(form_data)

    # Fallback to using the Flask globals (used for cache warmup and async queries)
    if not form_data and hasattr(g, "form_data"):
        form_data = _normalize_global_form_data(g.form_data)

    form_data = {k: v for k, v in form_data.items() if k not in REJECTED_FORM_DATA_KEYS}

    # When a slice_id is present, load from DB and override
    # the form_data from the DB with the other form_data provided
    slice_id = form_data.get("slice_id") or slice_id
    slc = None

    # Check if form data only contains slice_id, additional filters and viz type
    valid_keys = ["slice_id", "extra_filters", "adhoc_filters", "viz_type"]
    valid_slice_id = all(key in valid_keys for key in form_data)

    # Include the slice_form_data if request from explore or slice calls
    # or if form_data only contains slice_id and additional filters
    if slice_id and (use_slice_data or valid_slice_id):
        slc = db.session.query(Slice).filter_by(id=slice_id).one_or_none()
        if slc and security_manager.can_access_chart(slc):
            slice_form_data = slc.form_data.copy()
            slice_form_data.update(form_data)
            form_data = slice_form_data
        else:
            slc = None

    update_time_range(form_data)
    return form_data, slc


def get_dashboard_extra_filters(
    slice_id: int, dashboard_id: int
) -> list[dict[str, Any]]:
    dashboard = db.session.query(Dashboard).filter_by(id=dashboard_id).one_or_none()

    # is chart in this dashboard?
    if (
        dashboard is None
        or not dashboard.json_metadata
        or not dashboard.slices
        or not any(slc for slc in dashboard.slices if slc.id == slice_id)
    ):
        return []

    # does this dashboard have default filters?
    json_metadata = json_to_dict(dashboard.json_metadata)
    raw_default_filters = json_metadata.get("default_filters")
    if isinstance(raw_default_filters, str):
        default_filters = json_to_dict(raw_default_filters)
    elif isinstance(raw_default_filters, dict):
        default_filters = raw_default_filters
    else:
        default_filters = {}
    if not default_filters:
        return []

    # are default filters applicable to the given slice?
    filter_scopes = json_metadata.get("filter_scopes", {})
    if isinstance(filter_scopes, dict):
        return build_extra_filters(
            dashboard.position, filter_scopes, default_filters, slice_id
        )
    return []


def build_extra_filters(  # noqa: C901
    layout: dict[str, dict[str, Any]],
    filter_scopes: dict[str, dict[str, Any]],
    default_filters: dict[str, dict[str, list[Any]]],
    slice_id: int,
) -> list[dict[str, Any]]:
    extra_filters = []

    # do not apply filters if chart is not in filter's scope or chart is immune to the
    # filter.
    for filter_id, columns in default_filters.items():
        if not isinstance(columns, dict):
            continue

        filter_slice = db.session.query(Slice).filter_by(id=filter_id).one_or_none()

        filter_configs: list[dict[str, Any]] = []
        if filter_slice:
            raw_filter_configs = filter_slice.params_dict.get("filter_configs") or []
            filter_configs = (
                raw_filter_configs if isinstance(raw_filter_configs, list) else []
            )

        scopes_by_filter_field = filter_scopes.get(filter_id, {})
        if not isinstance(scopes_by_filter_field, dict):
            scopes_by_filter_field = {}
        for col, val in columns.items():
            if not val:
                continue

            current_field_scopes = scopes_by_filter_field.get(col, {})
            if not isinstance(current_field_scopes, dict):
                current_field_scopes = {}
            if "scope" in current_field_scopes:
                scoped_container_ids = current_field_scopes["scope"]
                if not isinstance(scoped_container_ids, list):
                    scoped_container_ids = []
            else:
                scoped_container_ids = ["ROOT_ID"]
            immune_slice_ids = current_field_scopes.get("immune", [])
            if not isinstance(immune_slice_ids, list):
                immune_slice_ids = []

            for container_id in scoped_container_ids:
                if slice_id not in immune_slice_ids and is_slice_in_container(
                    layout, container_id, slice_id
                ):
                    # Ensure that the filter value encoding adheres to the filter select
                    # type.
                    for filter_config in filter_configs:
                        if not isinstance(filter_config, dict):
                            continue
                        if filter_config.get("column") == col:
                            is_multiple = filter_config.get("multiple")

                            if not is_multiple and isinstance(val, list):
                                val = val[0]
                            elif is_multiple and not isinstance(val, list):
                                val = [val]
                            break

                    extra_filters.append(
                        {
                            "col": col,
                            "op": "in" if isinstance(val, list) else "==",
                            "val": val,
                        }
                    )

    return extra_filters


def is_slice_in_container(
    layout: dict[str, dict[str, Any]], container_id: str, slice_id: int
) -> bool:
    if container_id == "ROOT_ID":
        return True

    node = layout.get(container_id)
    if not isinstance(node, dict):
        return False
    node_type = node.get("type")
    meta = node.get("meta")
    if (
        node_type == "CHART"
        and isinstance(meta, dict)
        and meta.get("chartId") == slice_id
    ):
        return True

    if node_type in CONTAINER_TYPES:
        children = node.get("children", [])
        if not isinstance(children, list):
            return False
        return any(
            is_slice_in_container(layout, child_id, slice_id) for child_id in children
        )

    return False

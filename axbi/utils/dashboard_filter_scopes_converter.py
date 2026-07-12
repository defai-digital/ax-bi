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
import logging
from collections import defaultdict
from typing import Any

from axbi.models.slice import Slice
from axbi.utils import json

logger = logging.getLogger(__name__)


def _load_json_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    try:
        parsed = json.loads(value or "{}")
    except (TypeError, ValueError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _as_int_list(values: Any) -> list[int]:
    int_values = []
    for value in _as_list(values):
        try:
            int_values.append(int(value))
        except (TypeError, ValueError):
            continue
    return int_values


def convert_filter_scopes(  # noqa: C901
    json_metadata: dict[Any, Any], filter_boxes: list[Slice]
) -> dict[int, dict[str, dict[str, Any]]]:
    filter_scopes = {}
    immuned_by_id = _as_int_list(json_metadata.get("filter_immune_slices"))
    immuned_by_column: dict[str, list[int]] = defaultdict(list)
    immune_slice_fields = json_metadata.get("filter_immune_slice_fields") or {}
    if not isinstance(immune_slice_fields, dict):
        immune_slice_fields = {}
    for slice_id, columns in immune_slice_fields.items():
        try:
            slice_id_int = int(slice_id)
        except (TypeError, ValueError):
            continue
        for column in _as_list(columns):
            immuned_by_column[column].append(slice_id_int)

    def add_filter_scope(
        filter_fields: dict[str, dict[str, Any]], filter_field: Any, filter_id: int
    ) -> None:
        # in case filter field is invalid
        if isinstance(filter_field, str):
            current_filter_immune = list(
                set(immuned_by_id + immuned_by_column.get(filter_field, []))
            )
            filter_fields[filter_field] = {
                "scope": ["ROOT_ID"],
                "immune": current_filter_immune,
            }
        else:
            logging.info("slice [%i] has invalid field: %s", filter_id, filter_field)

    for filter_box in filter_boxes:
        filter_fields: dict[str, dict[str, Any]] = {}
        filter_id = filter_box.id
        slice_params = _load_json_dict(filter_box.params)
        configs = _as_list(slice_params.get("filter_configs"))

        if slice_params.get("date_filter"):
            add_filter_scope(filter_fields, "__time_range", filter_id)
        if slice_params.get("show_sqla_time_column"):
            add_filter_scope(filter_fields, "__time_col", filter_id)
        if slice_params.get("show_sqla_time_granularity"):
            add_filter_scope(filter_fields, "__time_grain", filter_id)
        for config in configs:
            if not isinstance(config, dict):
                continue
            add_filter_scope(filter_fields, config.get("column"), filter_id)

        if filter_fields:
            filter_scopes[filter_id] = filter_fields

    return filter_scopes


def copy_filter_scopes(
    old_to_new_slc_id_dict: dict[int, int],
    old_filter_scopes: dict[int, dict[str, dict[str, Any]]],
) -> dict[str, dict[Any, Any]]:
    new_filter_scopes: dict[str, dict[Any, Any]] = {}
    for filter_id, scopes in old_filter_scopes.items():
        try:
            filter_id_int = int(filter_id)
        except (TypeError, ValueError):
            continue
        new_filter_key = old_to_new_slc_id_dict.get(filter_id_int)
        if new_filter_key and isinstance(scopes, dict):
            new_filter_scopes[str(new_filter_key)] = scopes
            for scope in scopes.values():
                if not isinstance(scope, dict):
                    continue
                scope["immune"] = [
                    old_to_new_slc_id_dict[slice_id]
                    for slice_id in _as_int_list(scope.get("immune"))
                    if slice_id in old_to_new_slc_id_dict
                ]
    return new_filter_scopes

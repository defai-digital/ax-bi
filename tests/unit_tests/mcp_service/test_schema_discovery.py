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

"""Tests for MCP schema discovery helpers."""

from superset.mcp_service.common.schema_discovery import (
    build_schema_resource,
    CHART_EXTRA_COLUMNS,
    ColumnMetadata,
    get_columns_from_model,
)
from superset.models.slice import Slice


def test_get_columns_from_model_excludes_matching_extra_columns():
    columns = get_columns_from_model(
        Slice,
        default_columns=["id"],
        extra_columns={
            "owners": ColumnMetadata(**CHART_EXTRA_COLUMNS["owners"].model_dump()),
            "url": ColumnMetadata(**CHART_EXTRA_COLUMNS["url"].model_dump()),
        },
        exclude_columns={"owners"},
    )

    column_names = {column.name for column in columns}

    assert "id" in column_names
    assert "url" in column_names
    assert "owners" not in column_names


def test_build_schema_resource_uses_common_schema_metadata():
    resource = build_schema_resource("chart")

    assert resource["model_type"] == "chart"
    assert "slice_name" in resource["all_column_names"]
    assert "slice_name" in resource["default_columns"]
    assert "changed_on" in resource["sortable_columns"]
    assert resource["search_columns"] == ["slice_name", "description"]
    assert resource["default_sort"] == "changed_on"
    assert resource["default_sort_direction"] == "desc"
    assert all(
        {"name", "description", "type"} <= set(column)
        for column in resource["select_columns"]
    )


def test_build_schema_resource_returns_empty_for_unsupported_model():
    assert build_schema_resource("unsupported") == {}

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

from unittest.mock import patch

from superset.daos.dashboard import DashboardDAO
from superset.models.dashboard import Dashboard
from superset.utils import json


def test_get_native_filter_configuration_ignores_malformed_metadata() -> None:
    dashboard = Dashboard(id=1, json_metadata="{malformed")

    with patch.object(DashboardDAO, "get_by_id_or_slug", return_value=dashboard):
        result = DashboardDAO.get_native_filter_configuration("1")

    assert dict(result) == {}


def test_update_native_filters_config_ignores_malformed_metadata() -> None:
    dashboard = Dashboard(id=1, json_metadata="{malformed")
    attributes = {
        "modified": [{"id": "filter-1", "name": "Region"}],
        "deleted": [],
        "reordered": ["filter-1"],
    }

    result = DashboardDAO.update_native_filters_config(dashboard, attributes)

    assert result == [{"id": "filter-1", "name": "Region"}]
    assert json.loads(dashboard.json_metadata) == {
        "native_filter_configuration": [{"id": "filter-1", "name": "Region"}]
    }


def test_update_native_filters_config_empty_attributes_returns_empty_list() -> None:
    dashboard = Dashboard(id=1, json_metadata="{}")

    assert DashboardDAO.update_native_filters_config(dashboard, {}) == []


def test_get_native_filter_configuration_ignores_non_object_items() -> None:
    dashboard = Dashboard(
        id=1,
        json_metadata=json.dumps(
            {
                "native_filter_configuration": [
                    "bad-filter",
                    {"id": "filter-1", "tabsInScope": ["TAB-1"]},
                    {"id": "filter-2", "tabsInScope": "TAB-2"},
                ]
            }
        ),
    )

    with patch.object(DashboardDAO, "get_by_id_or_slug", return_value=dashboard):
        result = DashboardDAO.get_native_filter_configuration("1")

    assert dict(result) == {
        "TAB-1": [{"id": "filter-1", "tabsInScope": ["TAB-1"]}],
        "all": [
            {"id": "filter-1", "tabsInScope": ["TAB-1"]},
            {"id": "filter-2", "tabsInScope": "TAB-2"},
        ],
    }


def test_update_native_filters_config_ignores_non_object_items() -> None:
    dashboard = Dashboard(
        id=1,
        json_metadata=json.dumps(
            {
                "native_filter_configuration": [
                    "bad-filter",
                    {"name": "No ID"},
                ]
            }
        ),
    )
    attributes = {
        "modified": ["bad-update", {"id": "filter-1", "name": "Region"}],
        "deleted": [],
        "reordered": ["filter-1"],
    }

    result = DashboardDAO.update_native_filters_config(dashboard, attributes)

    assert result == [{"id": "filter-1", "name": "Region"}]
    assert json.loads(dashboard.json_metadata) == {
        "native_filter_configuration": [{"id": "filter-1", "name": "Region"}]
    }


def test_update_native_filters_config_ignores_scalar_update_containers() -> None:
    dashboard = Dashboard(
        id=1,
        json_metadata=json.dumps(
            {"native_filter_configuration": [{"id": "filter-1", "name": "Region"}]}
        ),
    )
    attributes = {
        "modified": "bad-update",
        "deleted": "filter-1",
        "reordered": "filter-1",
    }

    result = DashboardDAO.update_native_filters_config(dashboard, attributes)

    assert result == [{"id": "filter-1", "name": "Region"}]
    assert json.loads(dashboard.json_metadata) == {
        "native_filter_configuration": [{"id": "filter-1", "name": "Region"}]
    }


def test_update_chart_customizations_config_ignores_malformed_metadata() -> None:
    dashboard = Dashboard(id=1, json_metadata="{malformed")
    attributes = {
        "modified": [{"id": "customization-1", "name": "Compact title"}],
        "deleted": [],
        "reordered": ["customization-1"],
    }

    result = DashboardDAO.update_chart_customizations_config(dashboard, attributes)

    assert result == [{"id": "customization-1", "name": "Compact title"}]
    assert json.loads(dashboard.json_metadata) == {
        "chart_customization_config": [
            {"id": "customization-1", "name": "Compact title"}
        ]
    }


def test_update_chart_customizations_config_ignores_non_object_items() -> None:
    dashboard = Dashboard(
        id=1,
        json_metadata=json.dumps(
            {
                "chart_customization_config": [
                    "bad-customization",
                    {"name": "No ID"},
                ]
            }
        ),
    )
    attributes = {
        "modified": [
            "bad-update",
            {"id": "customization-1", "name": "Compact title"},
        ],
        "deleted": [],
        "reordered": ["customization-1"],
    }

    result = DashboardDAO.update_chart_customizations_config(dashboard, attributes)

    assert result == [{"id": "customization-1", "name": "Compact title"}]
    assert json.loads(dashboard.json_metadata) == {
        "chart_customization_config": [
            {"id": "customization-1", "name": "Compact title"}
        ]
    }


def test_update_chart_customizations_config_ignores_scalar_update_containers() -> None:
    dashboard = Dashboard(
        id=1,
        json_metadata=json.dumps(
            {
                "chart_customization_config": [
                    {"id": "customization-1", "name": "Compact title"}
                ]
            }
        ),
    )
    attributes = {
        "modified": "bad-update",
        "deleted": "customization-1",
        "reordered": "customization-1",
    }

    result = DashboardDAO.update_chart_customizations_config(dashboard, attributes)

    assert result == [{"id": "customization-1", "name": "Compact title"}]
    assert json.loads(dashboard.json_metadata) == {
        "chart_customization_config": [
            {"id": "customization-1", "name": "Compact title"}
        ]
    }


def test_update_colors_config_ignores_non_object_metadata() -> None:
    dashboard = Dashboard(id=1, json_metadata="[]")

    DashboardDAO.update_colors_config(dashboard, {"label_colors": {"APAC": "#00ff00"}})

    assert json.loads(dashboard.json_metadata) == {"label_colors": {"APAC": "#00ff00"}}

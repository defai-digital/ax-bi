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
from axbi.models.dashboard import Dashboard
from axbi.utils import json


def test_dashboard_tabs_skips_malformed_layout_references() -> None:
    """Malformed layout references should not crash tab extraction."""
    dashboard = Dashboard(
        position_json=json.dumps(
            {
                "ROOT_ID": {
                    "id": "ROOT_ID",
                    "type": "ROOT",
                    "children": ["TABS-1", "MISSING"],
                },
                "TABS-1": {
                    "id": "TABS-1",
                    "type": "TABS",
                    "children": ["TAB-1", "MISSING-TAB", "BROKEN-NODE"],
                },
                "BROKEN-NODE": {"id": "BROKEN-NODE", "children": []},
                "TAB-1": {
                    "id": "TAB-1",
                    "type": "TAB",
                    "meta": {"text": "Overview"},
                    "children": "not-a-list",
                },
            }
        )
    )

    assert dashboard.tabs == {
        "all_tabs": {"TAB-1": "Overview"},
        "tab_tree": [
            {
                "id": "TAB-1",
                "type": "TAB",
                "meta": {"text": "Overview"},
                "children": [],
                "title": "Overview",
                "value": "TAB-1",
            }
        ],
    }


def test_dashboard_tabs_falls_back_for_malformed_tab_meta() -> None:
    """Tabs with malformed metadata should still be returned."""
    dashboard = Dashboard(
        position_json=json.dumps(
            {
                "ROOT_ID": {"id": "ROOT_ID", "type": "ROOT", "children": ["TABS-1"]},
                "TABS-1": {"id": "TABS-1", "type": "TABS", "children": ["TAB-1"]},
                "TAB-1": {
                    "id": "TAB-1",
                    "type": "TAB",
                    "meta": "not-an-object",
                    "children": [],
                },
            }
        )
    )

    assert dashboard.tabs["all_tabs"] == {"TAB-1": "TAB-1"}
    assert dashboard.tabs["tab_tree"][0]["title"] == "TAB-1"

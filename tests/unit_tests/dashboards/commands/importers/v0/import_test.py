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
import pytest

from superset.commands.dashboard.importers.v0 import (
    _validate_dashboard_bundle_shape,
    import_dashboards,
    ImportDashboardsCommand,
)
from superset.connectors.sqla.models import SqlaTable
from superset.exceptions import DashboardImportException
from superset.models.dashboard import Dashboard
from superset.utils import json


@pytest.mark.parametrize(
    "content",
    [
        json.dumps([]),
        json.dumps({"datasources": []}),
        json.dumps({"dashboards": []}),
        json.dumps({"datasources": {}, "dashboards": []}),
        json.dumps({"datasources": [], "dashboards": {}}),
        json.dumps({"datasources": [{}], "dashboards": []}),
        json.dumps({"datasources": [], "dashboards": [{}]}),
    ],
)
def test_import_dashboards_rejects_invalid_bundle_shape(content: str) -> None:
    """V0 dashboard imports must contain datasource and dashboard lists."""
    with pytest.raises(DashboardImportException):
        import_dashboards(content)


def test_import_dashboards_command_validate_rejects_invalid_bundle_shape() -> None:
    """Validation should reject malformed bundles before run-time DB work."""
    command = ImportDashboardsCommand({"dashboard.json": json.dumps([])})

    with pytest.raises(DashboardImportException):
        command.validate()


@pytest.mark.parametrize(
    "params",
    [
        "{",
        "[]",
        "{}",
    ],
)
def test_validate_dashboard_bundle_shape_rejects_invalid_datasource_params(
    params: str,
) -> None:
    """V0 dashboard datasource params must be objects with a remote id."""
    data = {
        "datasources": [SqlaTable(params=params)],
        "dashboards": [],
    }

    with pytest.raises(DashboardImportException):
        _validate_dashboard_bundle_shape(data)


def test_validate_dashboard_bundle_shape_accepts_valid_entries() -> None:
    """V0 dashboard bundles must contain SqlaTable and Dashboard entries."""
    data = {
        "datasources": [SqlaTable(params=json.dumps({"remote_id": 42}))],
        "dashboards": [Dashboard(dashboard_title="My dashboard")],
    }

    assert _validate_dashboard_bundle_shape(data) is data

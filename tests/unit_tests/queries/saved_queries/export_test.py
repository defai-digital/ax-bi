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

from unittest.mock import MagicMock

import yaml

from superset.commands.query.export import ExportSavedQueriesCommand


def test_export_related_database_replaces_non_object_extra() -> None:
    database = MagicMock()
    database.database_name = "my_database"
    database.export_to_dict.return_value = {
        "database_name": "my_database",
        "extra": "[]",
    }

    query = MagicMock()
    query.database = database
    query.label = "my query"
    query.schema = None
    query.uuid = "00000000-0000-0000-0000-000000000001"

    export = dict(
        ExportSavedQueriesCommand._export(query)  # pylint: disable=protected-access
    )
    database_payload = yaml.safe_load(export["databases/my_database.yaml"]())

    assert database_payload["extra"] == {}

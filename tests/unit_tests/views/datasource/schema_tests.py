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
from superset.views.datasource.schemas import ExternalMetadataSchema


def test_external_metadata_schema_defaults_optional_flags() -> None:
    """External metadata params should not require optional boolean flags."""
    payload = ExternalMetadataSchema().load(
        {
            "datasource_type": "table",
            "database_name": "examples",
            "schema_name": "public",
            "table_name": "birth_names",
        }
    )

    assert payload["normalize_columns"] is False
    assert payload["always_filter_main_dttm"] is False

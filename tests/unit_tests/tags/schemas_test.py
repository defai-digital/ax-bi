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
from marshmallow import ValidationError

from axbi.tags.schemas import TagPostBulkSchema


def test_tag_post_bulk_schema_requires_tags() -> None:
    """Bulk tag requests without tags should fail validation."""
    with pytest.raises(ValidationError) as exc_info:
        TagPostBulkSchema().load({})

    assert exc_info.value.messages == {"tags": ["Missing data for required field."]}


def test_tag_post_bulk_schema_loads_valid_tags() -> None:
    """Bulk tag requests with tags should load successfully."""
    payload = {
        "tags": [
            {
                "name": "tag1",
                "description": "description",
                "objects_to_tag": [["dashboard", 1]],
            }
        ]
    }

    assert TagPostBulkSchema().load(payload) == {
        "tags": [
            {
                "name": "tag1",
                "description": "description",
                "objects_to_tag": [("dashboard", 1)],
            }
        ]
    }

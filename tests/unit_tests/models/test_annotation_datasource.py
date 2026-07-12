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
from typing import Any, cast

import pytest

from axbi.common.db_query_status import QueryStatus
from axbi.common.query_object import QueryObjectDict
from axbi.connectors.sqla.models import AnnotationDatasource


@pytest.mark.parametrize(
    "query_obj",
    [
        {},
        {"filter": []},
        {"filter": [{}]},
        {"filter": "not-a-list"},
    ],
)
def test_annotation_datasource_query_returns_failure_for_malformed_filters(
    query_obj: dict[str, Any],
) -> None:
    """Malformed annotation filters should return a failed query result."""
    datasource = AnnotationDatasource()

    result = datasource.query(cast(QueryObjectDict, query_obj))

    assert result.status == QueryStatus.FAILED
    assert result.df.empty
    assert result.error_message

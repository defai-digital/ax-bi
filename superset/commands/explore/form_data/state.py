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
from typing import Any, TypedDict, TypeGuard

from superset.utils.core import DatasourceType


class TemporaryExploreState(TypedDict):
    owner: int | None
    datasource_id: int
    datasource_type: DatasourceType
    chart_id: int | None
    form_data: str


def is_temporary_explore_state(value: Any) -> TypeGuard[TemporaryExploreState]:
    """Return true when a cached Explore form-data state is usable."""
    if not isinstance(value, dict):
        return False

    owner = value.get("owner")
    chart_id = value.get("chart_id")
    datasource_type = value.get("datasource_type")
    if not isinstance(datasource_type, str):
        return False
    try:
        DatasourceType(datasource_type)
    except ValueError:
        return False

    return (
        (owner is None or isinstance(owner, int))
        and not isinstance(owner, bool)
        and isinstance(value.get("datasource_id"), int)
        and not isinstance(value.get("datasource_id"), bool)
        and (chart_id is None or isinstance(chart_id, int))
        and not isinstance(chart_id, bool)
        and isinstance(value.get("form_data"), str)
    )

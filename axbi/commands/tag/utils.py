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

from typing import Any

from axbi.daos.chart import ChartDAO
from axbi.daos.dashboard import DashboardDAO
from axbi.daos.query import SavedQueryDAO
from axbi.models.dashboard import Dashboard
from axbi.models.slice import Slice
from axbi.models.sql_lab import SavedQuery
from axbi.tags.models import ObjectType


def to_object_type(object_type: ObjectType | int | str) -> ObjectType | None:
    if isinstance(object_type, ObjectType):
        return object_type
    for type_ in ObjectType:
        if object_type in [type_.value, type_.name]:
            return type_
    return None


def to_object_model(
    object_type: ObjectType, object_id: int, skip_base_filter: bool = False
) -> Dashboard | SavedQuery | Slice | Any | None:
    if ObjectType.dashboard == object_type:
        return DashboardDAO.find_by_id(object_id, skip_base_filter=skip_base_filter)
    if ObjectType.query == object_type:
        return SavedQueryDAO.find_by_id(object_id, skip_base_filter=skip_base_filter)
    if ObjectType.chart == object_type:
        return ChartDAO.find_by_id(object_id, skip_base_filter=skip_base_filter)
    if ObjectType.dataset == object_type:
        # Imported lazily to avoid a circular import via axbi.views.base
        from axbi.daos.dataset import DatasetDAO

        return DatasetDAO.find_by_id(object_id, skip_base_filter=skip_base_filter)
    return None

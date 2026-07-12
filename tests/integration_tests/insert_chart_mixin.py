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

from axbi import db, security_manager
from axbi.connectors.sqla.models import SqlaTable
from axbi.models.slice import Slice


class InsertChartMixin:
    """
    Implements shared logic for tests to insert charts (slices) in the DB
    """

    def insert_chart(
        self,
        slice_name: str,
        owners: list[int],
        datasource_id: int,
        created_by=None,
        datasource_type: str = "table",
        description: str | None = None,
        viz_type: str | None = None,
        params: str | None = None,
        cache_timeout: int | None = None,
        certified_by: str | None = None,
        certification_details: str | None = None,
    ) -> Slice:
        obj_owners = list()  # noqa: C408
        for owner in owners:
            user = db.session.query(security_manager.user_model).get(owner)
            obj_owners.append(user)
        datasource = (
            db.session.query(SqlaTable).filter_by(id=datasource_id).one_or_none()
        )
        slice = Slice(
            cache_timeout=cache_timeout,
            certified_by=certified_by,
            certification_details=certification_details,
            created_by=created_by,
            datasource_id=datasource.id,
            datasource_name=datasource.name,
            datasource_type=datasource.type,
            description=description,
            owners=obj_owners,
            params=params,
            slice_name=slice_name,
            viz_type=viz_type,
        )
        db.session.add(slice)
        db.session.commit()
        return slice

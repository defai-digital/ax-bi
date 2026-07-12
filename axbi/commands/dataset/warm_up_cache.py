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

from axbi.commands.base import BaseCommand
from axbi.commands.chart.warm_up_cache import ChartWarmUpCacheCommand
from axbi.commands.dataset.exceptions import (
    DatasetAccessDeniedError,
    WarmUpCacheTableNotFoundError,
)
from axbi.connectors.sqla.models import SqlaTable
from axbi.exceptions import AxBISecurityException
from axbi.extensions import db, security_manager
from axbi.models.core import Database
from axbi.models.slice import Slice
from axbi.utils.core import error_msg_from_exception


class DatasetWarmUpCacheCommand(BaseCommand):
    def __init__(
        self,
        db_name: str,
        table_name: str,
        dashboard_id: int | None,
        extra_filters: str | None,
    ):
        self._db_name = db_name
        self._table_name = table_name
        self._dashboard_id = dashboard_id
        self._extra_filters = extra_filters
        self._charts: list[Slice] = []

    def run(self) -> list[dict[str, Any]]:
        self.validate()
        chart_ids = [chart.id for chart in self._charts]
        results = []
        for chart_id in chart_ids:
            try:
                results.append(
                    ChartWarmUpCacheCommand(
                        chart_id,
                        self._dashboard_id,
                        self._extra_filters,
                    ).run()
                )
            except Exception as ex:  # pylint: disable=broad-except
                results.append(
                    {
                        "chart_id": chart_id,
                        "viz_error": error_msg_from_exception(ex),
                        "viz_status": None,
                    }
                )
        return results

    def validate(self) -> None:
        table = (
            db.session.query(SqlaTable)
            .join(Database)
            .filter(
                Database.database_name == self._db_name,
                SqlaTable.table_name == self._table_name,
            )
        ).one_or_none()
        if not table:
            raise WarmUpCacheTableNotFoundError()
        try:
            security_manager.raise_for_access(datasource=table)
        except AxBISecurityException as ex:
            raise DatasetAccessDeniedError() from ex
        self._charts = (
            db.session.query(Slice)
            .filter_by(datasource_id=table.id, datasource_type=table.type)
            .all()
        )

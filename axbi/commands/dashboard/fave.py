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
import logging
from functools import partial

from axbi.commands.base import BaseCommand
from axbi.commands.dashboard.exceptions import (
    DashboardFaveError,
)
from axbi.daos.dashboard import DashboardDAO
from axbi.models.dashboard import Dashboard
from axbi.utils.decorators import on_error, transaction

logger = logging.getLogger(__name__)


class AddFavoriteDashboardCommand(BaseCommand):
    def __init__(self, dashboard_id: int) -> None:
        self._dashboard_id = dashboard_id
        self._dashboard: Dashboard | None = None

    @transaction(on_error=partial(on_error, reraise=DashboardFaveError))
    def run(self) -> None:
        self.validate()
        if self._dashboard:
            DashboardDAO.add_favorite(self._dashboard)

    def validate(self) -> None:
        # Raises DashboardNotFoundError or DashboardAccessDeniedError
        dashboard = DashboardDAO.get_by_id_or_slug(self._dashboard_id)
        self._dashboard = dashboard

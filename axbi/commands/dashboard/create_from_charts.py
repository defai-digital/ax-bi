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
from __future__ import annotations

from functools import partial
from typing import Any

from flask import current_app

from axbi import security_manager
from axbi.commands.base import BaseCommand
from axbi.commands.dashboard.exceptions import (
    DashboardChartsAccessDeniedError,
    DashboardChartsNotFoundError,
    DashboardCreateFailedError,
)
from axbi.daos.chart import ChartDAO
from axbi.daos.dashboard import DashboardDAO
from axbi.daos.user import UserDAO
from axbi.models.dashboard import Dashboard
from axbi.models.slice import Slice
from axbi.utils.core import get_user_id
from axbi.utils.decorators import on_error, transaction


class CreateDashboardFromChartsCommand(BaseCommand):
    """Create a dashboard with chart and owner objects from one scoped session."""

    def __init__(self, data: dict[str, Any], chart_ids: list[int]) -> None:
        self._properties = data.copy()
        self._chart_ids = list(chart_ids)
        self._charts: list[Slice] = []

    @property
    def charts(self) -> list[Slice]:
        """Return the same-session chart objects attached during creation."""
        return list(self._charts)

    @transaction(on_error=partial(on_error, reraise=DashboardCreateFailedError))
    def run(self) -> Dashboard:
        """Persist the dashboard and its relationships atomically."""
        self.validate()
        dashboard = DashboardDAO.create(attributes=self._properties)
        dashboard.slices = self._charts

        if (user_id := get_user_id()) is not None:
            owner = UserDAO.get_by_id_or_none(user_id)
            if owner is not None:
                dashboard.owners = [owner]

        if after_create := current_app.config.get("AFTER_ASSET_CREATE"):
            after_create(dashboard, "dashboard")

        return dashboard

    def validate(self) -> None:
        """Resolve every chart again inside the command's scoped session."""
        charts = ChartDAO.find_by_ids(
            self._chart_ids,
            skip_base_filter=True,
        )
        # Preserve caller chart_ids order (layout treats first chart as KPI header).
        charts_by_id = {chart.id: chart for chart in charts}
        if missing_ids := set(self._chart_ids) - charts_by_id.keys():
            raise DashboardChartsNotFoundError(missing_ids)
        self._charts = [charts_by_id[chart_id] for chart_id in self._chart_ids]

        denied_ids = {
            chart.id
            for chart in self._charts
            if not security_manager.can_access_chart(chart)
        }
        if denied_ids:
            raise DashboardChartsAccessDeniedError(denied_ids)

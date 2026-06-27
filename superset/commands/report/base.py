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
from collections.abc import Mapping
from typing import Any, Optional

from croniter import croniter
from flask import current_app as app
from flask_babel import gettext as _
from marshmallow import ValidationError

from superset import security_manager
from superset.commands.base import BaseCommand
from superset.commands.report.exceptions import (
    ChartNotFoundValidationError,
    ChartNotSavedValidationError,
    DashboardNotFoundValidationError,
    DashboardNotSavedValidationError,
    ReportScheduleEitherChartOrDashboardError,
    ReportScheduleForbiddenError,
    ReportScheduleFrequencyNotAllowed,
    ReportScheduleOnlyChartOrDashboardError,
)
from superset.daos.base import BaseDAO
from superset.daos.chart import ChartDAO
from superset.daos.dashboard import DashboardDAO
from superset.exceptions import SupersetSecurityException
from superset.reports.models import (
    ReportCreationMethod,
    ReportScheduleType,
)
from superset.reports.types import ReportScheduleExtra
from superset.utils import json

logger = logging.getLogger(__name__)


def _load_json_object(value: str | None) -> dict[str, Any] | None:
    try:
        parsed = json.loads(value or "{}")
    except (TypeError, ValueError):
        return None

    if not isinstance(parsed, dict):
        return None

    return parsed


def _get_dashboard_state_invalid_tab_ids(
    dashboard_state: Mapping[str, Any],
    position_data: dict[str, Any],
) -> set[str]:
    active_tabs = dashboard_state.get("activeTabs") or []
    invalid_tab_ids = set(active_tabs) - set(position_data.keys())

    if anchor := dashboard_state.get("anchor"):
        try:
            anchor_list: list[str] = json.loads(anchor)
            if _invalid_tab_ids := set(anchor_list) - set(position_data.keys()):
                invalid_tab_ids.update(_invalid_tab_ids)
        except json.JSONDecodeError:
            if anchor not in position_data:
                invalid_tab_ids.add(anchor)

    return invalid_tab_ids


def _get_native_filter_id(
    native_filter: Any,
    idx: int,
    exceptions: list[ValidationError],
) -> str | None:
    if not isinstance(native_filter, dict):
        exceptions.append(
            ValidationError(
                _("nativeFilters[%(idx)s] must be an object", idx=idx),
                "extra",
            )
        )
        return None

    required_keys = {"nativeFilterId", "filterType", "columnName", "filterValues"}
    if missing_keys := required_keys - set(native_filter.keys()):
        exceptions.append(
            ValidationError(
                _(
                    "nativeFilters[%(idx)s] missing required keys: %(keys)s",
                    idx=idx,
                    keys=", ".join(sorted(missing_keys)),
                ),
                "extra",
            )
        )
        return None

    if not isinstance(native_filter["filterValues"], list):
        exceptions.append(
            ValidationError(
                _(
                    "nativeFilters[%(idx)s].filterValues must be a list",
                    idx=idx,
                ),
                "extra",
            )
        )
        return None

    filter_id = native_filter["nativeFilterId"]
    if not isinstance(filter_id, str) or not filter_id:
        exceptions.append(
            ValidationError(
                _(
                    "nativeFilters[%(idx)s].nativeFilterId must be a non-empty string",
                    idx=idx,
                ),
                "extra",
            )
        )
        return None

    return filter_id


def _get_dashboard_native_filter_ids(
    dashboard: Any,
    exceptions: list[ValidationError],
) -> set[str] | None:
    json_metadata = _load_json_object(dashboard.json_metadata)
    if json_metadata is None:
        exceptions.append(
            ValidationError(
                _("Dashboard native filter metadata is invalid"),
                "extra",
            )
        )
        return None

    return {
        f["id"]
        for f in json_metadata.get("native_filter_configuration", [])
        if "id" in f
    }


class BaseReportScheduleCommand(BaseCommand):
    _properties: dict[str, Any]

    def run(self) -> Any:
        pass

    def validate(self) -> None:
        pass

    def _check_object_access(
        self,
        object_id: int,
        *,
        kind: str,
        dao: type[BaseDAO[Any]],
        not_found_exc: type[ValidationError],
        exceptions: list[ValidationError],
    ) -> None:
        """Validate the object exists and the current user can access it."""
        obj = dao.find_by_id(object_id)
        if not obj:
            exceptions.append(not_found_exc())
        else:
            try:
                security_manager.raise_for_access(**{kind: obj})
            except SupersetSecurityException as ex:
                raise ReportScheduleForbiddenError() from ex
        self._properties[kind] = obj

    def validate_chart_dashboard(
        self, exceptions: list[ValidationError], update: bool = False
    ) -> None:
        """Validate chart or dashboard relation"""
        chart_id = self._properties.get("chart")
        dashboard_id = self._properties.get("dashboard")
        creation_method = self._properties.get("creation_method")

        if creation_method == ReportCreationMethod.CHARTS and not chart_id:
            # User has not saved chart yet in Explore view
            exceptions.append(ChartNotSavedValidationError())
            return

        if creation_method == ReportCreationMethod.DASHBOARDS and not dashboard_id:
            exceptions.append(DashboardNotSavedValidationError())
            return

        if chart_id and dashboard_id:
            exceptions.append(ReportScheduleOnlyChartOrDashboardError())

        if chart_id:
            self._check_object_access(
                chart_id,
                kind="chart",
                dao=ChartDAO,
                not_found_exc=ChartNotFoundValidationError,
                exceptions=exceptions,
            )
        elif dashboard_id:
            self._check_object_access(
                dashboard_id,
                kind="dashboard",
                dao=DashboardDAO,
                not_found_exc=DashboardNotFoundValidationError,
                exceptions=exceptions,
            )
        elif not update:
            exceptions.append(ReportScheduleEitherChartOrDashboardError())

    def _validate_report_extra(self, exceptions: list[ValidationError]) -> None:
        extra: Optional[ReportScheduleExtra] = self._properties.get("extra")
        dashboard = self._properties.get("dashboard")

        # On PUT requests, dashboard may not be in the payload — fall back to the model
        if dashboard is None:
            model = getattr(self, "_model", None)
            dashboard = getattr(model, "dashboard", None)

        if extra is None or dashboard is None:
            return

        dashboard_state = extra.get("dashboard")
        if not dashboard_state:
            return

        if not isinstance(dashboard_state, dict):
            exceptions.append(
                ValidationError(
                    _("extra.dashboard must be an object"),
                    "extra",
                )
            )
            return

        position_data = _load_json_object(dashboard.position_json)
        if position_data is None:
            exceptions.append(
                ValidationError(
                    _("Dashboard layout metadata is invalid"),
                    "extra",
                )
            )
            return

        invalid_tab_ids = _get_dashboard_state_invalid_tab_ids(
            dashboard_state,
            position_data,
        )

        if invalid_tab_ids:
            exceptions.append(
                ValidationError(
                    _("Invalid tab ids: %(tab_ids)s", tab_ids=str(invalid_tab_ids)),
                    "extra",
                )
            )

        self._validate_native_filters(dashboard, dashboard_state, exceptions)

    def _validate_native_filters(
        self,
        dashboard: Any,
        dashboard_state: Any,
        exceptions: list[ValidationError],
    ) -> None:
        native_filters = dashboard_state.get("nativeFilters")
        if not native_filters:
            return

        if not isinstance(native_filters, list):
            exceptions.append(
                ValidationError(
                    _("nativeFilters must be a list"),
                    "extra",
                )
            )
            return

        valid_filter_ids: set[str] | None = None

        for idx, native_filter in enumerate(native_filters):
            filter_id = _get_native_filter_id(native_filter, idx, exceptions)
            if filter_id is None:
                continue

            if valid_filter_ids is None:
                valid_filter_ids = _get_dashboard_native_filter_ids(
                    dashboard,
                    exceptions,
                )
                if valid_filter_ids is None:
                    return
            if filter_id not in valid_filter_ids:
                exceptions.append(
                    ValidationError(
                        _(
                            "nativeFilters[%(idx)s].nativeFilterId '%(filter_id)s' "
                            "does not exist on the dashboard",
                            idx=idx,
                            filter_id=filter_id,
                        ),
                        "extra",
                    )
                )

    def validate_report_frequency(
        self,
        cron_schedule: str,
        report_type: str,
    ) -> None:
        """
        Validates if the report scheduled frequency doesn't exceed a limit
        configured in `config.py`.

        :param cron_schedule: The cron schedule configured.
        :param report_type: The report type (Alert/Report).
        """
        config_key = (
            "ALERT_MINIMUM_INTERVAL"
            if report_type == ReportScheduleType.ALERT
            else "REPORT_MINIMUM_INTERVAL"
        )
        minimum_interval = app.config.get(config_key, 0)
        if callable(minimum_interval):
            minimum_interval = minimum_interval()

        if not isinstance(minimum_interval, int):
            logger.error(
                "Invalid value for %s: %s", config_key, minimum_interval, exc_info=True
            )
            return

        # Since configuration is in minutes, we only need to validate
        # in case `minimum_interval` is <= 120 (2min)
        if minimum_interval < 120:
            return

        iterations = 60 if minimum_interval <= 3660 else 24
        schedule = croniter(cron_schedule)
        current_exec = next(schedule)

        for _i in range(iterations):
            next_exec = next(schedule)
            diff, current_exec = next_exec - current_exec, next_exec
            if int(diff) < minimum_interval:
                raise ReportScheduleFrequencyNotAllowed(
                    report_type=report_type, minimum_interval=minimum_interval
                )

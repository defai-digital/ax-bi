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

from flask_babel import lazy_gettext as _
from marshmallow.validate import ValidationError

from axbi.commands.exceptions import (
    CommandInvalidError,
    CreateFailedError,
    DeleteFailedError,
    ForbiddenError,
    ImportFailedError,
    ObjectNotFoundError,
    UpdateFailedError,
)


class DashboardSlugExistsValidationError(ValidationError):
    """
    Marshmallow validation error for dashboard slug already exists
    """

    def __init__(self) -> None:
        super().__init__([_("Must be unique")], field_name="slug")


class DashboardInvalidError(CommandInvalidError):
    message = _("Dashboard parameters are invalid.")


class DashboardChartsNotFoundError(CommandInvalidError):
    """Raised when dashboard creation references missing chart IDs."""

    def __init__(self, missing_ids: set[int]) -> None:
        self.missing_ids = set(missing_ids)
        super().__init__(
            _(
                "Charts not found: %(chart_ids)s",
                chart_ids=sorted(self.missing_ids),
            )
        )


class DashboardChartsAccessDeniedError(ForbiddenError):
    """Raised when dashboard creation references inaccessible charts."""

    def __init__(self, chart_ids: set[int]) -> None:
        self.chart_ids = set(chart_ids)
        super().__init__(
            _(
                "Access denied to charts: %(chart_ids)s",
                chart_ids=sorted(self.chart_ids),
            )
        )


class DashboardNotFoundError(ObjectNotFoundError):
    def __init__(
        self, dashboard_id: str | None = None, exception: Exception | None = None
    ) -> None:
        super().__init__("Dashboard", dashboard_id, exception)


class DashboardCreateFailedError(CreateFailedError):
    message = _("Dashboards could not be created.")


class DashboardUpdateFailedError(UpdateFailedError):
    message = _("Dashboard could not be updated.")


class DashboardNativeFiltersUpdateFailedError(UpdateFailedError):
    message = _("Dashboard native filters could not be patched.")


class DashboardChartCustomizationsUpdateFailedError(UpdateFailedError):
    message = _("Dashboard chart customizations could not be updated.")


class DashboardColorsConfigUpdateFailedError(UpdateFailedError):
    message = _("Dashboard color configuration could not be updated.")


class DashboardDeleteFailedError(DeleteFailedError):
    message = _("Dashboard could not be deleted.")


class DashboardDeleteEmbeddedFailedError(DeleteFailedError):
    message = _("Embedded dashboard could not be deleted.")


class DashboardDeleteFailedReportsExistError(DashboardDeleteFailedError):
    message = _("There are associated alerts or reports")


class DashboardForbiddenError(ForbiddenError):
    message = _("Changing this Dashboard is forbidden")


class DashboardImportError(ImportFailedError):
    message = _("Import dashboard failed for an unknown reason")


class DashboardAccessDeniedError(ForbiddenError):
    message = _("You don't have access to this dashboard.")


class DashboardCopyError(CommandInvalidError):
    message = _("Dashboard cannot be copied due to invalid parameters.")


class DashboardFaveError(CommandInvalidError):
    message = _("Dashboard cannot be favorited.")


class DashboardUnfaveError(CommandInvalidError):
    message = _("Dashboard cannot be unfavorited.")

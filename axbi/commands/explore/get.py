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
import contextlib
import logging
from abc import ABC
from typing import Any, cast

from flask import current_app, request
from flask_babel import lazy_gettext as _
from sqlalchemy.exc import SQLAlchemyError

from axbi.axbi_typing import ExplorableData
from axbi.commands.base import BaseCommand
from axbi.commands.explore.form_data.get import GetFormDataCommand
from axbi.commands.explore.form_data.parameters import (
    CommandParameters as FormDataCommandParameters,
)
from axbi.commands.explore.parameters import CommandParameters
from axbi.commands.explore.permalink.get import GetExplorePermalinkCommand
from axbi.connectors.sqla.models import BaseDatasource, SqlaTable
from axbi.daos.datasource import DatasourceDAO
from axbi.daos.exceptions import DatasourceNotFound
from axbi.exceptions import AxBIException
from axbi.explore.exceptions import WrongEndpointError
from axbi.explore.permalink.exceptions import ExplorePermalinkGetFailedError
from axbi.extensions import security_manager
from axbi.utils import core as utils
from axbi.utils.form_data import get_form_data, loads_request_json
from axbi.utils.viz_helpers import get_datasource_info
from axbi.views.utils import sanitize_datasource_data

logger = logging.getLogger(__name__)


def _get_slice_metadata(slc: Any) -> dict[str, Any]:
    extra_owners = []
    if resolver := current_app.config.get("EXTRA_OWNERS_RESOLVER"):
        extra_owners = resolver(slc)

    metadata = {
        "created_on_humanized": (slc.created_on_humanized if slc.created_on else None),
        "changed_on_humanized": (slc.changed_on_humanized if slc.changed_on else None),
        "owners": [owner.get_full_name() for owner in slc.owners],
        "extra_owners": extra_owners,
        "dashboards": [
            {"id": dashboard.id, "dashboard_title": dashboard.dashboard_title}
            for dashboard in slc.dashboards
        ],
    }
    if slc.created_by:
        metadata["created_by"] = slc.created_by.get_full_name()
    if slc.changed_by:
        metadata["changed_by"] = slc.changed_by.get_full_name()
    return metadata


class GetExploreCommand(BaseCommand, ABC):
    def __init__(
        self,
        params: CommandParameters,
    ) -> None:
        self._permalink_key = params.permalink_key
        self._form_data_key = params.form_data_key
        self._datasource_id = params.datasource_id
        self._datasource_type = params.datasource_type
        self._slice_id = params.slice_id

    # pylint: disable=too-many-locals,too-many-branches,too-many-statements
    def run(self) -> dict[str, Any] | None:  # noqa: C901
        initial_form_data = {}
        permalink_chart_state = None
        if self._permalink_key is not None:
            command = GetExplorePermalinkCommand(self._permalink_key)
            permalink_value = command.run()
            if not permalink_value:
                raise ExplorePermalinkGetFailedError()
            state = permalink_value.get("state")
            if not isinstance(state, dict):
                raise ExplorePermalinkGetFailedError()
            form_data = state.get("formData")
            if not isinstance(form_data, dict):
                raise ExplorePermalinkGetFailedError()
            initial_form_data = form_data
            url_params = state.get("urlParams")
            if url_params:
                try:
                    initial_form_data["url_params"] = dict(url_params)
                except (TypeError, ValueError) as ex:
                    raise ExplorePermalinkGetFailedError() from ex
            permalink_chart_state = state.get("chartState")
        elif self._form_data_key:
            parameters = FormDataCommandParameters(key=self._form_data_key)
            value = GetFormDataCommand(parameters).run()
            initial_form_data = loads_request_json(value) if value else {}

        message = None

        if not initial_form_data:
            if self._slice_id:
                initial_form_data["slice_id"] = self._slice_id
                if self._form_data_key:
                    message = _(
                        "Form data not found in cache, reverting to chart metadata."
                    )
            elif self._datasource_id:
                initial_form_data["datasource"] = (
                    f"{self._datasource_id}__{self._datasource_type}"
                )
                if self._form_data_key:
                    message = _(
                        "Form data not found in cache, reverting to dataset metadata."
                    )

        form_data, slc = get_form_data(
            slice_id=self._slice_id,
            use_slice_data=True,
            initial_form_data=initial_form_data,
        )
        try:
            self._datasource_id, self._datasource_type = get_datasource_info(
                self._datasource_id, self._datasource_type, form_data
            )
        except AxBIException:
            self._datasource_id = None
            # fallback unknown datasource to table type
            self._datasource_type = SqlaTable.type

        datasource: BaseDatasource | None = None

        if self._datasource_id is not None:
            with contextlib.suppress(DatasourceNotFound):
                datasource = DatasourceDAO.get_datasource(
                    cast(str, self._datasource_type), self._datasource_id
                )

        datasource_name = _("[Missing Dataset]")

        if datasource:
            datasource_name = datasource.name
            security_manager.raise_for_access(datasource=datasource)

        viz_type = form_data.get("viz_type")
        if (
            not viz_type
            and datasource
            and getattr(datasource, "default_endpoint", None)
        ):
            raise WrongEndpointError(redirect=datasource.default_endpoint)

        form_data["datasource"] = (
            str(self._datasource_id) + "__" + cast(str, self._datasource_type)
        )

        # On explore, merge legacy/extra filters and URL params into the form data
        utils.convert_legacy_filters_into_adhoc(form_data)
        utils.merge_extra_filters(form_data)
        utils.merge_request_params(form_data, request.args)

        datasource_data: ExplorableData = {
            "type": self._datasource_type or "unknown",
            "name": datasource_name,
            "columns": [],
            "metrics": [],
            "database": {"id": 0, "backend": ""},
        }
        try:
            if datasource:
                datasource_data = datasource.data
        except AxBIException as ex:
            message = ex.message
        except SQLAlchemyError:
            message = "SQLAlchemy error"

        metadata = None

        if slc:
            metadata = _get_slice_metadata(slc)

        result: dict[str, Any] = {
            "dataset": sanitize_datasource_data(datasource_data),
            "form_data": form_data,
            "slice": slc.data if slc else None,
            "message": message,
            "metadata": metadata,
        }
        if permalink_chart_state:
            result["chartState"] = permalink_chart_state
        return result

    def validate(self) -> None:
        pass

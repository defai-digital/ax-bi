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
"""Shared viz/datasource helpers for non-views layers (commands, tasks).

Hoisted out of ``axbi.views.utils`` so Command/DAO/Task layers do not depend on
the views package (API → Command → DAO → Model boundary).
"""

from __future__ import annotations

from typing import Any

from flask_babel import _

from axbi import viz
from axbi.axbi_typing import FormData
from axbi.daos.datasource import DatasourceDAO
from axbi.exceptions import AxBIException
from axbi.utils.core import DatasourceType
from axbi.viz import BaseViz


def get_viz(
    form_data: FormData,
    datasource_type: str,
    datasource_id: int,
    force: bool = False,
    force_cached: bool = False,
) -> BaseViz:
    """Build a visualization object for the given form data and datasource."""
    viz_type = form_data.get("viz_type", "table")
    datasource = DatasourceDAO.get_datasource(
        DatasourceType(datasource_type),
        datasource_id,
    )
    viz_obj = viz.viz_types[viz_type](
        datasource, form_data=form_data, force=force, force_cached=force_cached
    )
    return viz_obj


def get_datasource_info(
    datasource_id: int | None, datasource_type: str | None, form_data: FormData
) -> tuple[int, str | None]:
    """
    Compatibility layer for handling of datasource info.

    datasource_id & datasource_type used to be passed in the URL
    directory; now they should come as part of the form_data.
    """
    raw_datasource_id: Any = datasource_id
    if isinstance(datasource := form_data.get("datasource"), str):
        parts = datasource.split("__")
        if len(parts) == 2:
            raw_datasource_id, datasource_type = parts
        # The case where the datasource has been deleted
        if raw_datasource_id == "None":
            raw_datasource_id = None

    if not raw_datasource_id:
        raise AxBIException(
            _("The dataset associated with this chart no longer exists")
        )

    try:
        datasource_id = int(raw_datasource_id)
    except (TypeError, ValueError) as ex:
        raise AxBIException(
            _("The dataset associated with this chart no longer exists")
        ) from ex
    return datasource_id, datasource_type

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

"""
MCP tool: add_dashboard_filter

Add a native filter (dropdown, time range, or numeric range) to an
existing dashboard and scope it to specific charts.
"""

import logging
import uuid
from typing import Any, Literal

from fastmcp import Context
from pydantic import BaseModel, Field
from sqlalchemy.exc import SQLAlchemyError
from superset_core.mcp.decorators import tool, ToolAnnotations

from superset.mcp_service.utils.logging_utils import mcp_event_log_context
from superset.mcp_service.utils.url_utils import get_superset_base_url
from superset.utils import json

logger = logging.getLogger(__name__)


class FilterTarget(BaseModel):
    """A single filter target (column scope)."""

    dataset_id: int = Field(description="Dataset ID the chart uses")
    column_name: str = Field(description="Column name to filter on")


class AddDashboardFilterRequest(BaseModel):
    """Request schema for add_dashboard_filter."""

    dashboard_id: int = Field(
        ...,
        description="ID of the dashboard to add the filter to",
    )
    filter_type: Literal[
        "filter_select",
        "filter_time",
        "filter_range",
        "filter_timecolumn",
    ] = Field(
        ...,
        description=(
            "Type of filter: 'filter_select' for dropdown, 'filter_time' for "
            "time range, 'filter_range' for numeric range, "
            "'filter_timecolumn' for time column filter"
        ),
    )
    name: str = Field(
        ...,
        description="Display name for the filter (shown in the filter bar)",
    )
    targets: list[FilterTarget] = Field(
        default_factory=list,
        description=(
            "List of dataset/column pairs this filter applies to. "
            "When empty, the filter applies to all charts on the dashboard."
        ),
    )
    default_value: str | list[str] | None = Field(
        default=None,
        description="Default filter value (string for single select, list for multi)",
    )
    multi_select: bool = Field(
        default=False,
        description="Allow multiple selections (only for filter_select type)",
    )
    search_all_filters: bool = Field(
        default=False,
        description="Enable search within the filter dropdown (only for filter_select)",
    )


class AddDashboardFilterResponse(BaseModel):
    """Response schema for add_dashboard_filter."""

    dashboard_id: int | None = Field(default=None)
    filter_name: str | None = Field(default=None)
    dashboard_url: str | None = Field(default=None)
    error: str | None = Field(default=None)


def _build_filter_config(
    request: AddDashboardFilterRequest,
    existing_filters: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Build the native filter config entry and append to existing filters."""

    filter_id = str(uuid.uuid4())

    # Build targets
    targets: list[dict[str, Any]] = []
    for t in request.targets:
        targets.append(
            {
                "datasetId": t.dataset_id,
                "column": {"name": t.column_name},
            }
        )

    filter_config: dict[str, Any] = {
        "id": filter_id,
        "name": request.name,
        "filterType": request.filter_type,
        "targets": targets if targets else None,
        "defaultDataMask": {},
        "cascadeParentIds": [],
        "scope": {
            "rootPath": ["ROOT_ID"],
            "excluded": [],
        },
        "isInstant": True,
    }

    # Type-specific configuration
    if request.filter_type == "filter_select":
        filter_config["controlValues"] = {
            "enableEmptyFilter": False,
            "multiSelect": request.multi_select,
            "searchAllFilters": request.search_all_filters,
        }
        if request.default_value is not None:
            filter_config["defaultDataMask"] = {
                "filterState": {"value": request.default_value},
            }
    elif request.filter_type == "filter_time":
        filter_config["controlValues"] = {
            "enableEmptyFilter": False,
        }
        if request.default_value:
            filter_config["defaultDataMask"] = {
                "filterState": {"value": request.default_value},
            }
    elif request.filter_type == "filter_range":
        filter_config["controlValues"] = {
            "enableEmptyFilter": False,
        }

    existing_filters.append(filter_config)
    return existing_filters


@tool(
    tags=["mutate"],
    class_permission_name="Dashboard",
    annotations=ToolAnnotations(
        title="Add dashboard filter",
        readOnlyHint=False,
        destructiveHint=False,
    ),
)
def add_dashboard_filter(
    request: AddDashboardFilterRequest,
    ctx: Context,
) -> AddDashboardFilterResponse:
    """Add a native filter to an existing dashboard.

    Supports dropdown (filter_select), time range (filter_time),
    numeric range (filter_range), and time column (filter_timecolumn) filters.
    Filters can be scoped to specific charts via the targets parameter.

    Example: Add a region dropdown filter:
    ```json
    {
        "dashboard_id": 123,
        "filter_type": "filter_select",
        "name": "Region",
        "targets": [{"dataset_id": 1, "column_name": "region"}],
        "multi_select": true
    }
    ```

    Example: Add a time range filter:
    ```json
    {
        "dashboard_id": 123,
        "filter_type": "filter_time",
        "name": "Date Range"
    }
    ```
    """
    try:
        from superset import security_manager
        from superset.commands.dashboard.update import UpdateDashboardCommand
        from superset.daos.dashboard import DashboardDAO
        from superset.exceptions import SupersetSecurityException

        # Validate dashboard exists and user has ownership
        with mcp_event_log_context(action="mcp.add_dashboard_filter.validation"):
            dashboard = DashboardDAO.find_by_id(request.dashboard_id)
            if not dashboard:
                return AddDashboardFilterResponse(
                    error=(
                        f"Dashboard with ID {request.dashboard_id} not found. "
                        "Use list_dashboards to get valid dashboard IDs."
                    )
                )

            try:
                security_manager.raise_for_ownership(dashboard)
            except SupersetSecurityException:
                return AddDashboardFilterResponse(
                    error=(
                        f"You don't have permission to edit dashboard "
                        f"'{dashboard.dashboard_title}' (ID: {request.dashboard_id})."
                    )
                )

        # Parse existing json_metadata
        with mcp_event_log_context(action="mcp.add_dashboard_filter.build_config"):
            try:
                json_metadata = json.loads(dashboard.json_metadata or "{}")
            except (json.JSONDecodeError, TypeError):
                json_metadata = {}

            # Get or initialize native filter configuration
            existing_filters = json_metadata.get("native_filter_configuration", [])

            # Build and append the new filter
            updated_filters = _build_filter_config(request, list(existing_filters))
            json_metadata["native_filter_configuration"] = updated_filters

        # Apply update
        with mcp_event_log_context(action="mcp.add_dashboard_filter.db_write"):
            update_data = {"json_metadata": json.dumps(json_metadata)}
            command = UpdateDashboardCommand(request.dashboard_id, update_data)
            updated = command.run()

        dashboard_url = f"{get_superset_base_url()}/superset/dashboard/{updated.id}/"

        logger.info(
            "Added filter '%s' (%s) to dashboard %s",
            request.name,
            request.filter_type,
            updated.id,
        )

        return AddDashboardFilterResponse(
            dashboard_id=updated.id,
            filter_name=request.name,
            dashboard_url=dashboard_url,
            error=None,
        )

    except (SQLAlchemyError, ValueError) as e:
        from superset import db

        try:
            db.session.rollback()  # pylint: disable=consider-using-transaction
        except SQLAlchemyError:
            logger.warning(
                "Database rollback failed during error handling", exc_info=True
            )
        logger.error("Error adding dashboard filter: %s", e)
        return AddDashboardFilterResponse(
            error=f"Failed to add dashboard filter: {str(e)}"
        )

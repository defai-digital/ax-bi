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
MCP tool: update_dashboard

Update an existing dashboard's title, description, published status,
owners, or layout configuration.
"""

import logging
from typing import Any

from fastmcp import Context
from pydantic import BaseModel, Field
from sqlalchemy.exc import SQLAlchemyError
from superset_core.mcp.decorators import tool, ToolAnnotations

from superset.mcp_service.utils.logging_utils import mcp_event_log_context
from superset.mcp_service.utils.url_utils import get_superset_base_url

logger = logging.getLogger(__name__)


class UpdateDashboardRequest(BaseModel):
    """Request schema for update_dashboard."""

    dashboard_id: int = Field(
        ...,
        description="ID of the dashboard to update",
    )
    title: str | None = Field(
        default=None,
        description="New dashboard title. Omit to keep current.",
    )
    description: str | None = Field(
        default=None,
        description="New dashboard description. Omit to keep current.",
    )
    published: bool | None = Field(
        default=None,
        description="Set to True to publish, False to unpublish. Omit to keep current.",
    )
    slug: str | None = Field(
        default=None,
        description="New slug. Omit to keep current.",
    )
    css: str | None = Field(
        default=None,
        description="Custom CSS for the dashboard. Omit to keep current.",
    )
    json_metadata: str | None = Field(
        default=None,
        description=(
            "JSON metadata string (e.g. native filter config). Omit to keep current."
        ),
    )


class UpdateDashboardResponse(BaseModel):
    """Response schema for update_dashboard."""

    dashboard: dict[str, Any] | None = Field(
        default=None,
        description="Updated dashboard metadata",
    )
    dashboard_url: str | None = Field(default=None)
    changes_applied: list[str] = Field(
        default_factory=list,
        description="List of fields that were changed",
    )
    error: str | None = Field(default=None)


@tool(
    tags=["mutate"],
    class_permission_name="Dashboard",
    annotations=ToolAnnotations(
        title="Update dashboard",
        readOnlyHint=False,
        destructiveHint=False,
    ),
)
def update_dashboard(  # noqa: C901
    request: UpdateDashboardRequest,
    ctx: Context,
) -> UpdateDashboardResponse:
    """Update an existing dashboard's metadata.

    Modify dashboard title, description, published status, slug, CSS, or JSON
    metadata without recreating the dashboard. Use this tool to rename dashboards,
    add descriptions, publish/unpublish, or update filter configurations.

    Example usage:
    ```json
    {
        "dashboard_id": 123,
        "title": "Updated Sales Dashboard",
        "description": "Q4 2024 executive summary",
        "published": true
    }
    ```
    """
    try:
        from superset import security_manager
        from superset.commands.dashboard.update import UpdateDashboardCommand
        from superset.daos.dashboard import DashboardDAO
        from superset.exceptions import SupersetSecurityException

        # Validate dashboard exists and user has ownership
        with mcp_event_log_context(action="mcp.update_dashboard.validation"):
            dashboard = DashboardDAO.find_by_id(request.dashboard_id)
            if not dashboard:
                return UpdateDashboardResponse(
                    error=(
                        f"Dashboard with ID {request.dashboard_id} not found. "
                        "Use list_dashboards to get valid dashboard IDs."
                    )
                )

            try:
                security_manager.raise_for_ownership(dashboard)
            except SupersetSecurityException:
                return UpdateDashboardResponse(
                    error=(
                        f"You don't have permission to edit dashboard "
                        f"'{dashboard.dashboard_title}' (ID: {request.dashboard_id})."
                    )
                )

        # Build update payload from non-None fields
        update_data: dict[str, Any] = {}
        changes: list[str] = []

        if request.title is not None:
            update_data["dashboard_title"] = request.title
            changes.append("title")
        if request.description is not None:
            update_data["description"] = request.description
            changes.append("description")
        if request.published is not None:
            update_data["published"] = request.published
            changes.append("published")
        if request.slug is not None:
            update_data["slug"] = request.slug
            changes.append("slug")
        if request.css is not None:
            update_data["css"] = request.css
            changes.append("css")
        if request.json_metadata is not None:
            update_data["json_metadata"] = request.json_metadata
            changes.append("json_metadata")

        if not changes:
            return UpdateDashboardResponse(
                dashboard={
                    "id": dashboard.id,
                    "title": dashboard.dashboard_title,
                    "published": dashboard.published,
                },
                dashboard_url=(
                    f"{get_superset_base_url()}/ax-office/dashboard/{dashboard.id}/"
                ),
                changes_applied=[],
                error="No fields specified for update.",
            )

        # Apply update
        with mcp_event_log_context(action="mcp.update_dashboard.db_write"):
            command = UpdateDashboardCommand(request.dashboard_id, update_data)
            updated = command.run()

        dashboard_url = f"{get_superset_base_url()}/ax-office/dashboard/{updated.id}/"

        logger.info("Updated dashboard %s: %s", updated.id, ", ".join(changes))

        return UpdateDashboardResponse(
            dashboard={
                "id": updated.id,
                "title": updated.dashboard_title,
                "description": updated.description,
                "published": updated.published,
                "slug": updated.slug,
            },
            dashboard_url=dashboard_url,
            changes_applied=changes,
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
        logger.error("Error updating dashboard: %s", e)
        return UpdateDashboardResponse(error=f"Failed to update dashboard: {str(e)}")

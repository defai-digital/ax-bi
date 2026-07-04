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
Pydantic schemas for report (alerts & reports) related responses.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_serializer,
    model_validator,
    PositiveInt,
)

from superset.daos.base import ColumnOperator, ColumnOperatorEnum
from superset.mcp_service.common.cache_schemas import (
    CreatedByMeMixin,
    MetadataCacheControl,
    OwnedByMeMixin,
)
from superset.mcp_service.common.error_schemas import MCPResourceError
from superset.mcp_service.constants import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from superset.mcp_service.system.schemas import PaginationInfo
from superset.mcp_service.utils import sanitize_for_llm_context
from superset.mcp_service.utils.response_utils import (
    filter_serialized_response_fields,
    humanize_timestamp,
)
from superset.mcp_service.utils.schema_utils import (
    ensure_search_and_filters_not_combined,
    parse_filters,
    parse_select_columns,
)


class ReportFilter(ColumnOperator):
    """
    Filter object for report listing.
    col: The column to filter on. Must be one of the allowed filter fields.
    opr: The operator to use. Must be one of the supported operators.
    value: The value to filter by (type depends on col and opr).
    """

    col: Literal[
        "name",
        "type",
        "active",
        "dashboard_id",
        "chart_id",
        "last_state",
        "creation_method",
    ] = Field(
        ...,
        description="Column to filter on. Use get_schema(model_type='report') for "
        "available filter columns.",
    )
    opr: ColumnOperatorEnum = Field(
        ...,
        description="Operator to use. Use get_schema(model_type='report') for "
        "available operators.",
    )
    value: str | int | float | bool | list[str | int | float | bool] = Field(
        ..., description="Value to filter by (type depends on col and opr)"
    )


class ReportInfo(BaseModel):
    id: int | None = Field(None, description="Report/Alert ID")
    name: str | None = Field(None, description="Report/Alert name")
    description: str | None = Field(None, description="Report/Alert description")
    type: str | None = Field(None, description="Schedule type: 'Alert' or 'Report'")
    active: bool | None = Field(None, description="Whether the schedule is active")
    crontab: str | None = Field(None, description="Cron expression for scheduling")
    dashboard_id: int | None = Field(
        None, description="Associated dashboard ID, if any"
    )
    chart_id: int | None = Field(None, description="Associated chart ID, if any")
    last_eval_dttm: str | datetime | None = Field(
        None, description="Last report/alert evaluation timestamp"
    )
    last_eval_dttm_humanized: str | None = Field(
        None, description="Humanized last evaluation time"
    )
    last_state: str | None = Field(
        None, description="Last report/alert execution state"
    )
    creation_method: str | None = Field(
        None, description="How the report/alert was created"
    )
    owners: list[dict[str, Any]] | None = Field(
        None, description="List of owners (always empty; excluded by privacy policy)"
    )
    changed_on: str | datetime | None = Field(
        None, description="Last modification timestamp"
    )
    changed_on_humanized: str | None = Field(
        None, description="Humanized modification time"
    )
    created_on: str | datetime | None = Field(None, description="Creation timestamp")
    created_on_humanized: str | None = Field(
        None, description="Humanized creation time"
    )
    model_config = ConfigDict(
        from_attributes=True,
        ser_json_timedelta="iso8601",
        populate_by_name=True,
    )

    @model_serializer(mode="wrap")
    def _filter_fields_by_context(self, serializer: Any, info: Any) -> dict[str, Any]:
        return filter_serialized_response_fields(serializer(self), info)


class ReportList(BaseModel):
    reports: list[ReportInfo]
    count: int
    total_count: int
    page: int
    page_size: int
    total_pages: int
    has_previous: bool
    has_next: bool
    columns_requested: list[str] = Field(
        default_factory=list,
        description="Requested columns for the response",
    )
    columns_loaded: list[str] = Field(
        default_factory=list,
        description="Columns that were actually loaded for each report",
    )
    columns_available: list[str] = Field(
        default_factory=list,
        description="All columns available for selection via select_columns parameter",
    )
    sortable_columns: list[str] = Field(
        default_factory=list,
        description="Columns that can be used with order_column parameter",
    )
    filters_applied: list[ReportFilter] = Field(
        default_factory=list,
        description="List of advanced filter dicts applied to the query.",
    )
    pagination: PaginationInfo | None = None
    timestamp: datetime | None = None
    model_config = ConfigDict(ser_json_timedelta="iso8601")


class ListReportsRequest(OwnedByMeMixin, CreatedByMeMixin, MetadataCacheControl):
    """Request schema for list_reports."""

    filters: Annotated[
        list[ReportFilter],
        Field(
            default_factory=list,
            description="List of filter objects (column, operator, value). Each "
            "filter is an object with 'col', 'opr', and 'value' "
            "properties. Cannot be used together with 'search'.",
        ),
    ]
    select_columns: Annotated[
        list[str],
        Field(
            default_factory=list,
            description="List of columns to select. Defaults to common columns if not "
            "specified.",
        ),
    ]
    search: Annotated[
        str | None,
        Field(
            default=None,
            description="Text search string to match against report fields. Cannot "
            "be used together with 'filters'.",
        ),
    ]
    order_column: Annotated[
        str | None, Field(default=None, description="Column to order results by")
    ]
    order_direction: Annotated[
        Literal["asc", "desc"],
        Field(
            default="desc", description="Direction to order results ('asc' or 'desc')"
        ),
    ]
    page: Annotated[
        PositiveInt,
        Field(default=1, description="Page number for pagination (1-based)"),
    ]
    page_size: Annotated[
        int,
        Field(
            default=DEFAULT_PAGE_SIZE,
            gt=0,
            le=MAX_PAGE_SIZE,
            description=f"Number of items per page (max {MAX_PAGE_SIZE})",
        ),
    ]

    @field_validator("filters", mode="before")
    @classmethod
    def parse_filters(cls, v: Any) -> list[ReportFilter]:
        """Accept both JSON string and list of objects."""
        return parse_filters(v, ReportFilter)

    @field_validator("select_columns", mode="before")
    @classmethod
    def parse_columns(cls, v: Any) -> list[str]:
        """Accept JSON array, list, or comma-separated string."""
        return parse_select_columns(v)

    @model_validator(mode="after")
    def validate_search_and_filters(self) -> ListReportsRequest:
        """Prevent using both search and filters simultaneously."""
        ensure_search_and_filters_not_combined(
            self.search,
            self.filters,
            "Cannot use both 'search' and 'filters' parameters simultaneously. "
            "Use either 'search' for text-based searching across multiple fields, "
            "or 'filters' for precise column-based filtering, but not both.",
        )
        return self


class ReportError(MCPResourceError):
    pass


class GetReportInfoRequest(MetadataCacheControl):
    """Request schema for get_report_info — identifier is a numeric ID only."""

    identifier: Annotated[
        int,
        Field(description="Report/Alert numeric ID"),
    ]


def serialize_report_object(report: Any) -> ReportInfo | None:
    if not report:
        return None

    return ReportInfo(
        id=getattr(report, "id", None),
        name=sanitize_for_llm_context(
            getattr(report, "name", None),
            field_path=("name",),
        ),
        description=sanitize_for_llm_context(
            getattr(report, "description", None),
            field_path=("description",),
        ),
        type=getattr(report, "type", None),
        active=getattr(report, "active", None),
        crontab=getattr(report, "crontab", None),
        dashboard_id=getattr(report, "dashboard_id", None),
        chart_id=getattr(report, "chart_id", None),
        last_eval_dttm=getattr(report, "last_eval_dttm", None),
        last_eval_dttm_humanized=humanize_timestamp(
            getattr(report, "last_eval_dttm", None)
        ),
        last_state=getattr(report, "last_state", None),
        creation_method=getattr(report, "creation_method", None),
        owners=None,
        changed_on=getattr(report, "changed_on", None),
        changed_on_humanized=humanize_timestamp(getattr(report, "changed_on", None)),
        created_on=getattr(report, "created_on", None),
        created_on_humanized=humanize_timestamp(getattr(report, "created_on", None)),
    )

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
Pydantic schemas for row level security filter responses.
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

from axbi.daos.base import ColumnOperator, ColumnOperatorEnum
from axbi.mcp_service.common.error_schemas import MCPResourceError
from axbi.mcp_service.constants import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from axbi.mcp_service.system.schemas import PaginationInfo
from axbi.mcp_service.utils.response_utils import select_serialized_response_fields
from axbi.mcp_service.utils.schema_utils import (
    ensure_search_and_filters_not_combined,
    parse_filters,
    parse_select_columns,
)

DEFAULT_RLS_COLUMNS = ["id", "name", "filter_type", "clause"]

ALL_RLS_COLUMNS = [
    "id",
    "name",
    "filter_type",
    "tables",
    "roles",
    "clause",
    "group_key",
    "changed_on",
]

SORTABLE_RLS_COLUMNS = ["id", "name", "filter_type", "changed_on"]


class RlsColumnFilter(ColumnOperator):
    """Filter object for RLS filter listing."""

    col: Literal["name", "filter_type"] = Field(
        ...,
        description="Column to filter on.",
    )
    opr: ColumnOperatorEnum = Field(..., description="Operator to use.")
    value: str | int | float | bool | list[str | int | float | bool] = Field(
        ..., description="Value to filter by"
    )


class RlsTableRef(BaseModel):
    id: int | None = Field(None, description="Table ID")
    table_name: str | None = Field(None, description="Table name")
    model_config = ConfigDict(from_attributes=True)


class RlsRoleRef(BaseModel):
    id: int | None = Field(None, description="Role ID")
    name: str | None = Field(None, description="Role name")
    model_config = ConfigDict(from_attributes=True)


class RlsFilterInfo(BaseModel):
    id: int | None = Field(None, description="RLS filter ID")
    name: str | None = Field(None, description="RLS filter name")
    filter_type: str | None = Field(None, description="Filter type: Regular or Base")
    tables: list[RlsTableRef] | None = Field(
        None, description="Tables this filter applies to"
    )
    roles: list[RlsRoleRef] | None = Field(
        None, description="Roles this filter applies to"
    )
    clause: str | None = Field(None, description="SQL WHERE clause")
    group_key: str | None = Field(
        None, description="Group key for Base filter grouping"
    )
    changed_on: str | datetime | None = Field(
        None, description="Last modification timestamp"
    )
    model_config = ConfigDict(
        from_attributes=True,
        ser_json_timedelta="iso8601",
        populate_by_name=True,
    )

    @model_serializer(mode="wrap")
    def _filter_fields_by_context(self, serializer: Any, info: Any) -> dict[str, Any]:
        return select_serialized_response_fields(serializer(self), info)


class RlsFilterList(BaseModel):
    rls_filters: list[RlsFilterInfo]
    count: int
    total_count: int
    page: int
    page_size: int
    total_pages: int
    has_previous: bool
    has_next: bool
    columns_requested: list[str] = Field(default_factory=list)
    columns_loaded: list[str] = Field(default_factory=list)
    columns_available: list[str] = Field(default_factory=list)
    sortable_columns: list[str] = Field(default_factory=list)
    filters_applied: list[RlsColumnFilter] = Field(default_factory=list)
    pagination: PaginationInfo | None = None
    timestamp: datetime | None = None
    model_config = ConfigDict(ser_json_timedelta="iso8601")


class ListRlsFiltersRequest(BaseModel):
    """Request schema for list_rls_filters."""

    filters: Annotated[
        list[RlsColumnFilter],
        Field(
            default_factory=list,
            description="List of filter objects (col, opr, value). "
            "Cannot be used with search.",
        ),
    ]
    select_columns: Annotated[
        list[str],
        Field(
            default_factory=list,
            description="Columns to include in response. Defaults to common columns.",
        ),
    ]
    search: Annotated[
        str | None,
        Field(
            default=None,
            description="Text search on filter name. Cannot be used with filters.",
        ),
    ]
    order_column: Annotated[
        str | None, Field(default=None, description="Column to order results by")
    ]
    order_direction: Annotated[
        Literal["asc", "desc"],
        Field(default="desc", description="Sort direction"),
    ]
    page: Annotated[
        PositiveInt,
        Field(default=1, description="Page number (1-based)"),
    ]
    page_size: Annotated[
        int,
        Field(
            default=DEFAULT_PAGE_SIZE,
            gt=0,
            le=MAX_PAGE_SIZE,
            description=f"Items per page (max {MAX_PAGE_SIZE})",
        ),
    ]

    @field_validator("filters", mode="before")
    @classmethod
    def parse_filters(cls, v: Any) -> list[RlsColumnFilter]:
        return parse_filters(v, RlsColumnFilter)

    @field_validator("select_columns", mode="before")
    @classmethod
    def parse_columns(cls, v: Any) -> list[str]:
        return parse_select_columns(v)

    @model_validator(mode="after")
    def validate_search_and_filters(self) -> ListRlsFiltersRequest:
        ensure_search_and_filters_not_combined(self.search, self.filters)
        return self


class RlsFilterError(MCPResourceError):
    pass


class GetRlsFilterInfoRequest(BaseModel):
    """Request schema for get_rls_filter_info."""

    identifier: Annotated[
        int,
        Field(description="RLS filter ID"),
    ]


def serialize_rls_filter_object(rls_filter: Any) -> RlsFilterInfo | None:
    if not rls_filter:
        return None

    tables = [
        RlsTableRef(
            id=getattr(t, "id", None),
            table_name=getattr(t, "table_name", None),
        )
        for t in (getattr(rls_filter, "tables", None) or [])
    ]

    roles = [
        RlsRoleRef(
            id=getattr(r, "id", None),
            name=getattr(r, "name", None),
        )
        for r in (getattr(rls_filter, "roles", None) or [])
    ]

    return RlsFilterInfo(
        id=getattr(rls_filter, "id", None),
        name=getattr(rls_filter, "name", None),
        filter_type=getattr(rls_filter, "filter_type", None),
        tables=tables,
        roles=roles,
        clause=getattr(rls_filter, "clause", None),
        group_key=getattr(rls_filter, "group_key", None),
        changed_on=getattr(rls_filter, "changed_on", None),
    )

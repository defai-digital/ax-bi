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

"""Pydantic schemas for user-related MCP tool responses."""

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
from sqlalchemy.orm.exc import DetachedInstanceError

from axbi.daos.base import ColumnOperator, ColumnOperatorEnum
from axbi.mcp_service.common.error_schemas import MCPResourceError
from axbi.mcp_service.constants import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from axbi.mcp_service.system.schemas import PaginationInfo
from axbi.mcp_service.utils import (
    escape_llm_context_delimiters,
    sanitize_for_llm_context,
)
from axbi.mcp_service.utils.response_utils import select_serialized_response_fields
from axbi.mcp_service.utils.schema_utils import (
    ensure_search_and_filters_not_combined,
    parse_filters,
    parse_select_columns,
)

DEFAULT_USER_COLUMNS = ["id", "username", "first_name", "last_name", "active"]

USER_ALL_COLUMNS = [
    "id",
    "username",
    "first_name",
    "last_name",
    "active",
    "email",
    "changed_on",
]

USER_SORTABLE_COLUMNS = [
    "id",
    "username",
    "first_name",
    "last_name",
    "active",
    "changed_on",
]


class UserFilter(ColumnOperator):
    """Filter object for user listing.

    col: The column to filter on. Must be one of the allowed filter fields.
    opr: The operator to use. Must be one of the supported operators.
    value: The value to filter by (type depends on col and opr).
    """

    col: Literal["username", "first_name", "last_name", "active"] = Field(
        ...,
        description="Column to filter on.",
    )
    opr: ColumnOperatorEnum = Field(
        ...,
        description="Operator to use.",
    )
    value: str | int | float | bool | list[str | int | float | bool] = Field(
        ..., description="Value to filter by (type depends on col and opr)"
    )


class UserInfo(BaseModel):
    id: int | None = Field(None, description="User ID")
    username: str | None = Field(None, description="Username")
    first_name: str | None = Field(None, description="First name")
    last_name: str | None = Field(None, description="Last name")
    active: bool | None = Field(None, description="Whether the user account is active")
    email: str | None = Field(
        None,
        description="Email address (only returned with data model metadata access)",
    )
    roles: list[str] | None = Field(
        None,
        description="Assigned role names (only returned with data model metadata "
        "access via get_user_info; not available in list_users because roles "
        "is a relationship, not a selectable column)",
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


class UserList(BaseModel):
    users: list[UserInfo]
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
        description="Columns that were actually loaded for each user",
    )
    columns_available: list[str] = Field(
        default_factory=list,
        description="All columns available for selection via select_columns parameter",
    )
    sortable_columns: list[str] = Field(
        default_factory=list,
        description="Columns that can be used with order_column parameter",
    )
    filters_applied: list[UserFilter] = Field(
        default_factory=list,
        description="List of advanced filter dicts applied to the query.",
    )
    pagination: PaginationInfo | None = None
    timestamp: datetime | None = None
    model_config = ConfigDict(ser_json_timedelta="iso8601")


class ListUsersRequest(BaseModel):
    """Request schema for list_users."""

    filters: Annotated[
        list[UserFilter],
        Field(
            default_factory=list,
            description="List of filter objects (column, operator, value). Each "
            "filter is an object with 'col', 'opr', and 'value' properties. "
            "Cannot be used together with 'search'.",
        ),
    ]
    select_columns: Annotated[
        list[str],
        Field(
            default_factory=list,
            description="List of columns to select. Defaults to common columns if "
            "not specified.",
        ),
    ]
    search: Annotated[
        str | None,
        Field(
            default=None,
            description="Text search string to match against user fields. Cannot be "
            "used together with 'filters'.",
        ),
    ]
    order_column: Annotated[
        str | None, Field(default=None, description="Column to order results by")
    ]
    order_direction: Annotated[
        Literal["asc", "desc"],
        Field(
            default="asc", description="Direction to order results ('asc' or 'desc')"
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
    def parse_filters(cls, v: Any) -> list[UserFilter]:
        """Accept both JSON string and list of objects."""
        return parse_filters(v, UserFilter)

    @field_validator("select_columns", mode="before")
    @classmethod
    def parse_columns(cls, v: Any) -> list[str]:
        """Accept JSON array, list, or comma-separated string."""
        return parse_select_columns(v)

    @model_validator(mode="after")
    def validate_search_and_filters(self) -> ListUsersRequest:
        ensure_search_and_filters_not_combined(
            self.search,
            self.filters,
            "Cannot use both 'search' and 'filters' parameters simultaneously. "
            "Use either 'search' for text-based searching or 'filters' for "
            "precise column-based filtering, but not both.",
        )
        return self


class UserError(MCPResourceError):
    pass


class GetUserInfoRequest(BaseModel):
    """Request schema for get_user_info."""

    identifier: Annotated[
        int,
        Field(description="User ID (integer)"),
    ]


def serialize_user_object(
    user: Any, include_sensitive: bool = False, include_roles: bool = True
) -> UserInfo | None:
    """Serialize a FAB User object into a UserInfo schema.

    Sensitive fields (email, roles) are only included when include_sensitive=True,
    which should reflect whether the caller has data model metadata access.
    Set include_roles=False to skip the roles relationship traversal (avoids N+1
    queries in list context where roles are never returned).
    """
    if not user:
        return None

    roles: list[str] | None = None
    if include_sensitive and include_roles:
        user_roles = getattr(user, "roles", None)
        if user_roles is not None:
            try:
                roles = [r.name for r in user_roles if hasattr(r, "name")]
            except (AttributeError, DetachedInstanceError):
                roles = None

    return UserInfo(
        id=getattr(user, "id", None),
        username=escape_llm_context_delimiters(getattr(user, "username", None)),
        first_name=sanitize_for_llm_context(
            getattr(user, "first_name", None), field_path=("first_name",)
        ),
        last_name=sanitize_for_llm_context(
            getattr(user, "last_name", None), field_path=("last_name",)
        ),
        active=getattr(user, "active", None),
        email=escape_llm_context_delimiters(getattr(user, "email", None))
        if include_sensitive
        else None,
        roles=[sanitize_for_llm_context(r, field_path=("roles",)) for r in roles]
        if roles is not None
        else None,
        changed_on=getattr(user, "changed_on", None),
    )

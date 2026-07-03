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
Pydantic schemas for dataset-related responses
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, cast, Literal

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
from superset.mcp_service.chart.schemas import DataColumn, PerformanceMetadata
from superset.mcp_service.common.cache_schemas import (
    CacheStatus,
    CreatedByMeMixin,
    MetadataCacheControl,
    OwnedByMeMixin,
    QueryCacheControl,
)
from superset.mcp_service.common.error_schemas import MCPResourceError
from superset.mcp_service.constants import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from superset.mcp_service.privacy import filter_user_directory_fields
from superset.mcp_service.system.schemas import (
    PaginationInfo,
    TagInfo,
)
from superset.mcp_service.utils import (
    escape_llm_context_delimiters,
    sanitize_for_llm_context,
)
from superset.mcp_service.utils.response_utils import (
    humanize_timestamp,
    select_serialized_response_fields,
)
from superset.utils import json


class DatasetFilter(ColumnOperator):
    """
    Filter object for dataset listing.
    col: The column to filter on. Must be one of the allowed filter fields.
    opr: The operator to use. Must be one of the supported operators.
    value: The value to filter by (type depends on col and opr).
    """

    col: Literal[  # pyright: ignore[reportIncompatibleVariableOverride]
        "table_name",
        "schema",
        "database_name",
        "created_by_fk",
        "changed_by_fk",
    ] = Field(
        ...,
        description="Column to filter on. Use get_schema(model_type='dataset') for "
        "available filter columns. To filter by a person, first call find_users "
        "to resolve a name to a user ID, then filter by created_by_fk or "
        "changed_by_fk with that integer ID.",
    )
    opr: ColumnOperatorEnum = Field(
        ...,
        description="Operator to use. Use get_schema(model_type='dataset') for "
        "available operators.",
    )
    value: str | int | float | bool | list[str | int | float | bool] = Field(
        ..., description="Value to filter by (type depends on col and opr)"
    )


class TableColumnInfo(BaseModel):
    column_name: str = Field(..., description="Column name")
    verbose_name: str | None = Field(None, description="Verbose name")
    type: str | None = Field(None, description="Column type")
    is_dttm: bool | None = Field(None, description="Is datetime column")
    groupby: bool | None = Field(None, description="Is groupable")
    filterable: bool | None = Field(None, description="Is filterable")
    description: str | None = Field(None, description="Column description")

    @model_serializer(mode="wrap")
    def _filter_column_fields_by_context(
        self, serializer: Any, info: Any
    ) -> dict[str, Any]:
        """Filter column fields based on serialization context.

        If context contains 'column_fields', only include those fields plus
        column_name (always required). Keeps wide datasets small when the
        caller only needs column_name + type.
        """
        data = serializer(self)
        if info.context and isinstance(info.context, dict):
            column_fields = info.context.get("column_fields")
            if column_fields is not None:
                requested = set(column_fields)
                requested.add("column_name")
                return {k: v for k, v in data.items() if k in requested}
        return data


class SqlMetricInfo(BaseModel):
    metric_name: str = Field(
        ...,
        description=(
            "Saved metric name. In chart configs, reference as "
            '{"name": "<metric_name>", "saved_metric": true}.'
        ),
    )
    verbose_name: str | None = Field(None, description="Verbose name")
    expression: str | None = Field(None, description="SQL expression")
    description: str | None = Field(None, description="Metric description")
    d3format: str | None = Field(None, description="D3 format string")


class DatasetInfo(BaseModel):
    id: int | None = Field(None, description="Dataset ID")
    table_name: str | None = Field(None, description="Table name")
    schema_name: str | None = Field(None, description="Schema name", alias="schema")
    database_name: str | None = Field(None, description="Database name")
    description: str | None = Field(None, description="Dataset description")
    certified_by: str | None = Field(
        None, description="Name of the person or team who certified this dataset"
    )
    certification_details: str | None = Field(
        None, description="Certification details or reason"
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
    tags: list[TagInfo] = Field(default_factory=list, description="Dataset tags")
    is_virtual: bool | None = Field(
        None, description="Whether the dataset is virtual (uses SQL)"
    )
    database_id: int | None = Field(None, description="Database ID")
    uuid: str | None = Field(None, description="Dataset UUID")
    schema_perm: str | None = Field(None, description="Schema permission string")
    url: str | None = Field(None, description="Explore view URL for this dataset")
    sql: str | None = Field(None, description="SQL for virtual datasets")
    main_dttm_col: str | None = Field(None, description="Main datetime column")
    offset: int | None = Field(None, description="Offset")
    cache_timeout: int | None = Field(None, description="Cache timeout")
    params: dict[str, Any | None] | None = Field(None, description="Extra params")
    template_params: dict[str, Any | None] | None = Field(
        None, description="Template params"
    )
    extra: dict[str, Any | None] | None = Field(None, description="Extra metadata")
    columns: list[TableColumnInfo] = Field(
        default_factory=list, description="Columns in the dataset"
    )
    metrics: list[SqlMetricInfo] = Field(
        default_factory=list,
        description="Saved metrics (pre-defined aggregations). "
        "NOT columns — use saved_metric=true in chart configs.",
    )
    is_favorite: bool | None = Field(
        None, description="Whether this dataset is favorited by the current user"
    )
    model_config = ConfigDict(
        from_attributes=True,
        ser_json_timedelta="iso8601",
        populate_by_name=True,  # Allow both 'schema' (alias) and 'schema_name' (field)
    )

    @model_serializer(mode="wrap")
    def _filter_fields_by_context(self, serializer: Any, info: Any) -> dict[str, Any]:
        """Filter fields based on serialization context.

        If context contains 'select_columns', only include those fields.
        Otherwise, include all fields (default behavior).
        """
        # Get full serialization
        data = filter_user_directory_fields(serializer(self))

        # Normalize alias: Pydantic serializes as 'schema_name' (field name)
        # but the DAO column and API convention is 'schema'
        if "schema_name" in data:
            data["schema"] = data.pop("schema_name")

        return select_serialized_response_fields(data, info)


class DatasetList(BaseModel):
    datasets: list[DatasetInfo]
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
        description="Columns that were actually loaded for each dataset",
    )
    columns_available: list[str] = Field(
        default_factory=list,
        description="All columns available for selection via select_columns parameter",
    )
    sortable_columns: list[str] = Field(
        default_factory=list,
        description="Columns that can be used with order_column parameter",
    )
    filters_applied: list[DatasetFilter] = Field(
        default_factory=list,
        description="List of advanced filter dicts applied to the query.",
    )
    pagination: PaginationInfo | None = None
    timestamp: datetime | None = None
    model_config = ConfigDict(ser_json_timedelta="iso8601")


class ListDatasetsRequest(OwnedByMeMixin, CreatedByMeMixin, MetadataCacheControl):
    """Request schema for list_datasets with clear, unambiguous types."""

    filters: Annotated[
        list[DatasetFilter],
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
            description="Text search string to match against dataset fields. Cannot "
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

    @model_validator(mode="after")
    def validate_search_and_filters(self) -> ListDatasetsRequest:
        """Prevent using both search and filters simultaneously."""
        from superset.mcp_service.utils.schema_utils import (
            ensure_search_and_filters_not_combined,
        )

        ensure_search_and_filters_not_combined(
            self.search,
            self.filters,
            "Cannot use both 'search' and 'filters' parameters simultaneously. "
            "Use either 'search' for text-based searching across multiple fields, "
            "or 'filters' for precise column-based filtering, but not both.",
        )
        return self


class DatasetError(MCPResourceError):
    pass


DEFAULT_GET_DATASET_INFO_COLUMNS: list[str] = [
    "id",
    "table_name",
    "schema",
    "database_name",
    "database_id",
    "uuid",
    "is_virtual",
    "description",
    "main_dttm_col",
    "sql",
    "url",
    "columns",
    "metrics",
]

DEFAULT_GET_DATASET_INFO_COLUMN_FIELDS: list[str] = [
    "column_name",
    "type",
    "is_dttm",
]


class GetDatasetInfoRequest(MetadataCacheControl):
    """Request schema for get_dataset_info with support for ID or UUID."""

    identifier: Annotated[
        int | str,
        Field(description="Dataset identifier - can be numeric ID or UUID string"),
    ]
    select_columns: Annotated[
        list[str],
        Field(
            default_factory=lambda: list(DEFAULT_GET_DATASET_INFO_COLUMNS),
            description=(
                "Top-level fields to include in the response. Defaults to a lean "
                "set that excludes verbose fields like params, template_params, "
                "extra, tags, certification_details. Pass an explicit list to "
                "override (e.g. ['id','table_name','columns'] for minimal output)."
            ),
        ),
    ]
    column_fields: Annotated[
        list[str],
        Field(
            default_factory=lambda: list(DEFAULT_GET_DATASET_INFO_COLUMN_FIELDS),
            description=(
                "Per-column fields to include for entries in 'columns'. Defaults "
                "to ['column_name','type','is_dttm']. Pass a wider list to "
                "include 'verbose_name','groupby','filterable','description' "
                "when needed."
            ),
        ),
    ]

    @field_validator("select_columns", mode="before")
    @classmethod
    def _parse_select_columns(cls, value: Any) -> Any:
        from superset.mcp_service.utils.schema_utils import (
            parse_select_columns_or_default,
        )

        return parse_select_columns_or_default(value, DEFAULT_GET_DATASET_INFO_COLUMNS)

    @field_validator("column_fields", mode="before")
    @classmethod
    def _parse_column_fields(cls, value: Any) -> Any:
        from superset.mcp_service.utils.schema_utils import parse_json_or_list

        if value is None or value == "":
            return list(DEFAULT_GET_DATASET_INFO_COLUMN_FIELDS)
        parsed = parse_json_or_list(value, "column_fields")
        return parsed


class CreateDatasetMetric(BaseModel):
    """Metric definition for dataset creation."""

    metric_name: str = Field(..., description="Name of the metric")
    expression: str = Field(..., description="SQL expression for the metric")
    verbose_name: str | None = None
    description: str | None = None
    metric_type: str | None = None
    d3format: str | None = None
    warning_text: str | None = None


class CreateDatasetCalculatedColumn(BaseModel):
    """Calculated column definition for dataset creation."""

    column_name: str = Field(..., description="Name of the calculated column")
    expression: str = Field(..., description="SQL expression for the column")
    verbose_name: str | None = None
    description: str | None = None
    type: str | None = None
    advanced_data_type: str | None = None
    is_dttm: bool | None = None


class CreateDatasetRequest(BaseModel):
    """Request schema for create_dataset to register a physical table as a dataset."""

    model_config = ConfigDict(populate_by_name=True)

    database_id: Annotated[
        int,
        Field(
            description="ID of the database connection to register the table against"
        ),
    ]
    schema_: Annotated[
        str | None,
        Field(
            default=None,
            alias="schema",
            serialization_alias="schema",
            max_length=250,
            description="Schema (namespace) where the table lives, e.g. 'public'. "
            "Omit or pass None for databases without schema namespaces (e.g. SQLite).",
        ),
    ]
    catalog: Annotated[
        str | None,
        Field(
            default=None,
            max_length=250,
            description="Catalog where the table lives. Omit for databases without "
            "catalog support.",
        ),
    ]
    table_name: Annotated[
        str,
        Field(
            min_length=1,
            max_length=250,
            description="Name of the physical table to register as a dataset",
        ),
    ]
    owners: Annotated[
        list[int] | None,
        Field(
            default=None,
            description="Optional list of owner user IDs. "
            "Defaults to the calling user.",
        ),
    ]

    @field_validator("schema_", "catalog", mode="before")
    @classmethod
    def _normalize_optional_str(cls, v: object) -> object:
        """Strip whitespace and convert blank strings to None.

        Non-string values pass through unchanged so Pydantic's type validation
        rejects them, rather than silently treating a malformed value (e.g. an
        int or dict) as an omitted namespace.
        """
        if isinstance(v, str):
            return v.strip() or None
        return v

    @field_validator("table_name", mode="before")
    @classmethod
    def _strip_table_name(cls, v: object) -> object:
        """Strip leading/trailing whitespace from table_name."""
        if isinstance(v, str):
            return v.strip()
        return v


class UploadFileRequest(BaseModel):
    """Request schema for upload_file to upload a CSV/Excel/Parquet file
    and create a dataset from it with zero-config (auto-provisions DuckDB)."""

    model_config = ConfigDict(populate_by_name=True)

    file_content: str = Field(
        ...,
        description="Base64-encoded file content. The AI agent should encode "
        "the file bytes as base64 before sending.",
    )
    filename: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Original filename including extension (e.g. 'sales.csv', "
        "'report.xlsx', 'data.parquet'). Used to detect file type and derive "
        "the table name.",
    )
    table_name: str | None = Field(
        default=None,
        max_length=250,
        description="Optional custom table name. If omitted, a name is derived "
        "from the filename with a random suffix to avoid collisions.",
    )


class FileItem(BaseModel):
    """A single file within a batch upload request."""

    model_config = ConfigDict(populate_by_name=True)

    file_content: str = Field(
        ...,
        description="Base64-encoded file content.",
    )
    filename: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Original filename including extension.",
    )
    table_name: str | None = Field(
        default=None,
        max_length=250,
        description="Optional custom table name for this file.",
    )


class UploadFilesRequest(BaseModel):
    """Request schema for upload_files to upload multiple CSV/Excel/Parquet files
    and create datasets from them with zero-config (auto-provisions DuckDB)."""

    model_config = ConfigDict(populate_by_name=True)

    files: list[FileItem] = Field(
        ...,
        min_length=1,
        description="List of files to upload. Each file is processed independently "
        "and gets its own dataset. Maximum 10 files per batch.",
    )

    @field_validator("files", mode="after")
    @classmethod
    def _limit_batch_size(cls, v: list[FileItem]) -> list[FileItem]:
        """Enforce a maximum batch size of 10 files."""
        if len(v) > 10:
            raise ValueError("Maximum 10 files per batch upload")
        return v


class FileUploadResult(BaseModel):
    """Result for a single file in a batch upload."""

    filename: str = Field(..., description="Original filename")
    success: bool = Field(
        ..., description="Whether this file was uploaded successfully"
    )
    dataset: DatasetInfo | None = Field(
        None, description="Dataset info if upload succeeded"
    )
    error: str | None = Field(None, description="Error message if upload failed")

    @field_validator("filename")
    @classmethod
    def sanitize_filename(cls, v: str) -> str:
        """Escape delimiter tokens in echoed filenames before LLM exposure."""
        return escape_llm_context_delimiters(v)

    @field_validator("error")
    @classmethod
    def sanitize_error(cls, v: str | None) -> str | None:
        """Wrap per-file upload error text before LLM exposure."""
        if v is None:
            return None
        return sanitize_for_llm_context(v, field_path=("error",))


class UploadFilesResponse(BaseModel):
    """Response schema for upload_files batch upload."""

    results: list[FileUploadResult] = Field(..., description="Per-file upload results")
    total: int = Field(..., description="Total number of files processed")
    succeeded: int = Field(..., description="Number of files uploaded successfully")
    failed: int = Field(..., description="Number of files that failed to upload")


class CreateVirtualDatasetRequest(BaseModel):
    """Request schema for create_virtual_dataset."""

    model_config = ConfigDict(populate_by_name=True)

    database_id: int = Field(
        ...,
        description="ID of the database connection to use. "
        "Use list_databases to find valid IDs.",
    )
    sql: str = Field(
        ...,
        description="SQL query to save as a virtual dataset. "
        "Can be a JOIN, CTE, aggregation, or any valid SELECT.",
    )
    dataset_name: str = Field(
        ...,
        min_length=1,
        max_length=250,
        description="Name for the new virtual dataset.",
    )
    schema_name: str | None = Field(
        None,
        alias="schema",
        description="Schema to associate with the dataset (optional).",
    )
    catalog: str | None = Field(
        None,
        description="Catalog to associate with the dataset (optional).",
    )
    description: str | None = Field(
        None,
        description="Human-readable description of the dataset (optional).",
    )
    metrics: list[CreateDatasetMetric] | None = Field(
        None,
        description="Optional list of saved metrics to create. Each metric "
        "must have 'metric_name' and 'expression'.",
    )
    calculated_columns: list[CreateDatasetCalculatedColumn] | None = Field(
        None,
        description="Optional list of calculated columns to create. Each column "
        "must have 'column_name' and 'expression'.",
    )

    @field_validator("sql")
    @classmethod
    def sql_must_not_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("sql must not be empty")
        return v.strip()

    @field_validator("dataset_name")
    @classmethod
    def dataset_name_must_not_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("dataset_name must not be empty")
        return v.strip()


class CreateVirtualDatasetResponse(BaseModel):
    """Response schema for create_virtual_dataset."""

    id: int | None = Field(
        None,
        description="Dataset ID. Pass this as dataset_id to generate_chart "
        "or generate_explore_link. None if creation failed.",
    )
    dataset_name: str = Field(..., description="Name of the created dataset.")
    sql: str = Field(..., description="SQL query stored in the dataset.")
    database_id: int = Field(..., description="Database ID used.")
    columns: list[str] = Field(
        default_factory=list,
        description="Column names available for charting. "
        "Use these when building chart configs.",
    )
    url: str | None = Field(
        None,
        description="URL to view/edit the dataset in Superset. None if failed.",
    )
    error: str | None = Field(
        None,
        description="Error message if creation failed, otherwise null.",
    )

    @field_validator("dataset_name")
    @classmethod
    def sanitize_dataset_name(cls, v: str) -> str:
        """Escape delimiter tokens in dataset names before LLM exposure."""
        return escape_llm_context_delimiters(v)

    @field_validator("sql")
    @classmethod
    def sanitize_sql(cls, v: str) -> str:
        """Wrap stored SQL text before LLM exposure."""
        return sanitize_for_llm_context(v, field_path=("sql",))

    @field_validator("columns")
    @classmethod
    def sanitize_columns(cls, v: list[str]) -> list[str]:
        """Escape delimiter tokens in returned column names."""
        return [escape_llm_context_delimiters(column) for column in v]

    @field_validator("error")
    @classmethod
    def sanitize_error(cls, v: str | None) -> str | None:
        """Wrap creation error text before LLM exposure."""
        if v is None:
            return None
        return sanitize_for_llm_context(v, field_path=("error",))


VALID_FILTER_OPS = Literal[
    "==",
    "!=",
    ">",
    "<",
    ">=",
    "<=",
    "LIKE",
    "NOT LIKE",
    "ILIKE",
    "NOT ILIKE",
    "IN",
    "NOT IN",
    "IS NULL",
    "IS NOT NULL",
    "IS TRUE",
    "IS FALSE",
    "TEMPORAL_RANGE",
]


class QueryDatasetFilter(BaseModel):
    """A single filter condition for dataset queries."""

    col: str = Field(..., description="Column name to filter on")
    op: VALID_FILTER_OPS = Field(
        ...,
        description=(
            'Filter operator. Use "==" for equals, "!=" for not equals, '
            '"IN" / "NOT IN" for membership, "IS NULL" / "IS NOT NULL", '
            '"LIKE" for pattern matching, "TEMPORAL_RANGE" for time filters.'
        ),
    )
    val: Any = Field(
        default=None,
        description="Filter value (omit for IS NULL/IS NOT NULL)",
    )


class QueryDatasetRequest(QueryCacheControl):
    """Request schema for query_dataset tool."""

    dataset_id: int | str = Field(
        ...,
        description="Dataset identifier — numeric ID or UUID string.",
    )
    metrics: list[str] = Field(
        default_factory=list,
        description=(
            "Saved metric names to compute (e.g. ['count', 'avg_revenue']). "
            "Use get_dataset_info to discover available metrics."
        ),
    )
    columns: list[str] = Field(
        default_factory=list,
        description=(
            "Column/dimension names for GROUP BY or SELECT "
            "(e.g. ['category', 'region']). "
            "Use get_dataset_info to discover available columns."
        ),
    )
    filters: list[QueryDatasetFilter] = Field(
        default_factory=list,
        description=(
            'Filter conditions (e.g. [{"col": "status", "op": "==", "val": "active"}]).'
        ),
    )
    time_range: str | None = Field(
        default=None,
        description=(
            "Time range filter (e.g. 'Last 7 days', 'Last month', "
            "'2024-01-01 : 2024-12-31'). Requires a temporal column "
            "on the dataset."
        ),
    )
    time_column: str | None = Field(
        default=None,
        description=(
            "Temporal column to apply time_range to. "
            "Defaults to the dataset's main datetime column."
        ),
    )
    order_by: list[str] | None = Field(
        default=None,
        description="Column or metric names to sort results by.",
    )
    order_desc: bool = Field(
        default=True,
        description="Sort descending (True) or ascending (False).",
    )
    row_limit: int = Field(
        default=1000,
        ge=1,
        le=50000,
        description="Maximum number of rows to return (default 1000, max 50000).",
    )

    @model_validator(mode="after")
    def validate_metrics_or_columns(self) -> QueryDatasetRequest:
        """At least one of metrics or columns must be provided."""
        if not self.metrics and not self.columns:
            raise ValueError(
                "At least one of 'metrics' or 'columns' must be provided. "
                "Use get_dataset_info to discover available metrics and columns."
            )
        return self


class QueryDatasetResponse(BaseModel):
    """Response schema for query_dataset tool."""

    model_config = ConfigDict(ser_json_timedelta="iso8601")

    dataset_id: int = Field(..., description="Dataset ID")
    dataset_name: str = Field(..., description="Dataset name")
    columns: list[DataColumn] = Field(
        default_factory=list, description="Column metadata for returned data"
    )
    data: list[dict[str, Any]] = Field(
        default_factory=list, description="Query result rows"
    )
    row_count: int = Field(0, description="Number of rows returned")
    total_rows: int | None = Field(
        None, description="Total row count from the query engine"
    )
    summary: str = Field("", description="Human-readable summary of the results")
    performance: PerformanceMetadata | None = Field(
        None, description="Query performance metadata"
    )
    cache_status: CacheStatus | None = Field(
        None, description="Cache hit/miss information"
    )
    applied_filters: list[QueryDatasetFilter] = Field(
        default_factory=list, description="Filters that were applied to the query"
    )
    warnings: list[str] = Field(
        default_factory=list, description="Any warnings encountered during execution"
    )

    @field_validator("dataset_name")
    @classmethod
    def sanitize_dataset_name(cls, v: str) -> str:
        """Escape delimiter tokens in dataset names before LLM exposure."""
        return escape_llm_context_delimiters(v)

    @field_validator("columns")
    @classmethod
    def sanitize_columns(cls, v: list[DataColumn]) -> list[DataColumn]:
        """Escape column names and wrap sample values in query responses."""
        sanitized_columns: list[DataColumn] = []
        for index, column in enumerate(v):
            payload = column.model_dump(mode="python")
            payload["name"] = escape_llm_context_delimiters(payload.get("name"))
            payload["display_name"] = escape_llm_context_delimiters(
                payload.get("display_name")
            )
            payload["sample_values"] = sanitize_for_llm_context(
                payload.get("sample_values", []),
                field_path=("columns", str(index), "sample_values"),
                excluded_field_names=frozenset(),
            )
            payload["statistics"] = sanitize_for_llm_context(
                payload.get("statistics"),
                field_path=("columns", str(index), "statistics"),
                excluded_field_names=frozenset(),
            )
            sanitized_columns.append(DataColumn.model_validate(payload))
        return sanitized_columns

    @field_validator("data")
    @classmethod
    def sanitize_data(cls, v: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Wrap query result row strings and escape delimiter tokens in row keys."""
        return cast(
            list[dict[str, Any]],
            sanitize_for_llm_context(
                v,
                field_path=("data",),
                excluded_field_names=frozenset(),
            ),
        )

    @field_validator("summary")
    @classmethod
    def sanitize_summary(cls, v: str) -> str:
        """Wrap query summaries before LLM exposure."""
        return sanitize_for_llm_context(v, field_path=("summary",))

    @field_validator("applied_filters")
    @classmethod
    def sanitize_applied_filters(
        cls,
        v: list[QueryDatasetFilter],
    ) -> list[QueryDatasetFilter]:
        """Wrap echoed filter values without changing query execution inputs."""
        sanitized_filters: list[QueryDatasetFilter] = []
        for index, filter_ in enumerate(v):
            payload = filter_.model_dump(mode="python")
            payload["col"] = escape_llm_context_delimiters(payload.get("col"))
            payload["val"] = sanitize_for_llm_context(
                payload.get("val"),
                field_path=("applied_filters", str(index), "val"),
                excluded_field_names=frozenset(),
            )
            sanitized_filters.append(QueryDatasetFilter.model_validate(payload))
        return sanitized_filters

    @field_validator("warnings")
    @classmethod
    def sanitize_warnings(cls, v: list[str]) -> list[str]:
        """Wrap warning strings before LLM exposure."""
        return cast(
            list[str],
            sanitize_for_llm_context(
                v,
                field_path=("warnings",),
                excluded_field_names=frozenset(),
            ),
        )


def _parse_json_field(obj: Any, field_name: str) -> dict[str, Any] | None:
    """Parse a field that may be stored as a JSON string into a dict."""
    value = getattr(obj, field_name, None)
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, dict):
                return parsed
        except (ValueError, TypeError):
            pass
        return None
    return value if isinstance(value, dict) else None


def _sanitize_dataset_info_for_llm_context(dataset_info: DatasetInfo) -> DatasetInfo:
    """Wrap dataset read-path descriptive fields before LLM exposure."""
    payload = dataset_info.model_dump(mode="python")

    for field_name in ("description", "certified_by", "certification_details", "sql"):
        payload[field_name] = sanitize_for_llm_context(
            payload.get(field_name),
            field_path=(field_name,),
        )

    for field_name in ("table_name", "schema_name", "database_name", "schema_perm"):
        payload[field_name] = escape_llm_context_delimiters(payload.get(field_name))

    payload["extra"] = sanitize_for_llm_context(
        payload.get("extra"),
        field_path=("extra",),
        excluded_field_names=frozenset(),
    )

    for field_name in ("params", "template_params"):
        payload[field_name] = sanitize_for_llm_context(
            payload.get(field_name),
            field_path=(field_name,),
            excluded_field_names=frozenset(),
        )

    payload["columns"] = [
        {
            **column,
            "column_name": escape_llm_context_delimiters(
                column.get("column_name"),
            ),
            "description": sanitize_for_llm_context(
                column.get("description"),
                field_path=("columns", str(index), "description"),
            ),
            "verbose_name": sanitize_for_llm_context(
                column.get("verbose_name"),
                field_path=("columns", str(index), "verbose_name"),
            ),
        }
        for index, column in enumerate(payload.get("columns", []))
    ]

    payload["metrics"] = [
        {
            **metric,
            "metric_name": escape_llm_context_delimiters(
                metric.get("metric_name"),
            ),
            "expression": sanitize_for_llm_context(
                metric.get("expression"),
                field_path=("metrics", str(index), "expression"),
            ),
            "description": sanitize_for_llm_context(
                metric.get("description"),
                field_path=("metrics", str(index), "description"),
            ),
            "verbose_name": sanitize_for_llm_context(
                metric.get("verbose_name"),
                field_path=("metrics", str(index), "verbose_name"),
            ),
        }
        for index, metric in enumerate(payload.get("metrics", []))
    ]

    payload["tags"] = [
        {
            **tag,
            "name": sanitize_for_llm_context(
                tag.get("name"),
                field_path=("tags", str(index), "name"),
            ),
            "description": sanitize_for_llm_context(
                tag.get("description"),
                field_path=("tags", str(index), "description"),
            ),
        }
        for index, tag in enumerate(payload.get("tags", []))
    ]

    return DatasetInfo.model_validate(payload)


def serialize_dataset_object(dataset: Any) -> DatasetInfo | None:
    if not dataset:
        return None

    from superset.mcp_service.utils.url_utils import get_superset_base_url

    params = getattr(dataset, "params", None)
    if isinstance(params, str):
        try:
            params = json.loads(params)
        except (json.JSONDecodeError, TypeError):
            params = None
    if not isinstance(params, dict):
        params = None
    columns = [
        TableColumnInfo(
            column_name=getattr(col, "column_name", None) or "",
            verbose_name=getattr(col, "verbose_name", None),
            type=getattr(col, "type", None),
            is_dttm=getattr(col, "is_dttm", None),
            groupby=getattr(col, "groupby", None),
            filterable=getattr(col, "filterable", None),
            description=getattr(col, "description", None),
        )
        for col in getattr(dataset, "columns", [])
    ]
    metrics = [
        SqlMetricInfo(
            metric_name=getattr(metric, "metric_name", None) or "",
            verbose_name=getattr(metric, "verbose_name", None),
            expression=getattr(metric, "expression", None),
            description=getattr(metric, "description", None),
            d3format=getattr(metric, "d3format", None),
        )
        for metric in getattr(dataset, "metrics", [])
    ]
    return _sanitize_dataset_info_for_llm_context(
        DatasetInfo(
            id=getattr(dataset, "id", None),
            table_name=getattr(dataset, "table_name", None),
            schema_name=getattr(dataset, "schema", None),
            database_name=getattr(dataset.database, "database_name", None)
            if getattr(dataset, "database", None)
            else None,
            description=getattr(dataset, "description", None),
            certified_by=getattr(dataset, "certified_by", None),
            certification_details=getattr(dataset, "certification_details", None),
            changed_on=getattr(dataset, "changed_on", None),
            changed_on_humanized=humanize_timestamp(
                getattr(dataset, "changed_on", None)
            ),
            created_on=getattr(dataset, "created_on", None),
            created_on_humanized=humanize_timestamp(
                getattr(dataset, "created_on", None)
            ),
            tags=[
                TagInfo.model_validate(tag, from_attributes=True)
                for tag in getattr(dataset, "tags", [])
            ]
            if getattr(dataset, "tags", None)
            else [],
            is_virtual=getattr(dataset, "is_virtual", None),
            database_id=getattr(dataset, "database_id", None),
            uuid=str(getattr(dataset, "uuid", ""))
            if getattr(dataset, "uuid", None)
            else None,
            schema_perm=getattr(dataset, "schema_perm", None),
            url=(
                f"{get_superset_base_url()}/explore/"
                f"?datasource_type=table&datasource_id={getattr(dataset, 'id', None)}"
                if getattr(dataset, "id", None)
                else None
            ),
            sql=getattr(dataset, "sql", None),
            main_dttm_col=getattr(dataset, "main_dttm_col", None),
            offset=getattr(dataset, "offset", None),
            cache_timeout=getattr(dataset, "cache_timeout", None),
            params=params,
            template_params=_parse_json_field(dataset, "template_params"),
            extra=_parse_json_field(dataset, "extra"),
            columns=columns,
            metrics=metrics,
            is_favorite=getattr(dataset, "is_favorite", None),
        )
    )

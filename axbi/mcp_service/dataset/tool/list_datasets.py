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
List datasets FastMCP tool (Advanced with metadata cache control)

This module contains the FastMCP tool for listing datasets using
advanced filtering with clear, unambiguous request schema and metadata cache control.
"""

import logging
from typing import Any, TYPE_CHECKING

from axbi_core.mcp.decorators import tool, ToolAnnotations
from fastmcp import Context
from flask import current_app

if TYPE_CHECKING:
    from axbi.connectors.sqla.models import SqlaTable

from axbi import is_feature_enabled
from axbi.mcp_service.dataset.schemas import (
    DatasetError,
    DatasetFilter,
    DatasetInfo,
    DatasetList,
    ListDatasetsRequest,
    serialize_dataset_object,
)
from axbi.mcp_service.mcp_core import (
    ModelListCore,
    request_or_default,
    to_zero_based_page,
)
from axbi.mcp_service.privacy import (
    DATA_MODEL_METADATA_ERROR_TYPE,
    requires_data_model_metadata_access,
    user_can_view_data_model_metadata,
)
from axbi.mcp_service.system.schemas import PaginationInfo
from axbi.mcp_service.utils import sanitize_for_llm_context
from axbi.mcp_service.utils.logging_utils import mcp_event_log_context
from axbi.mcp_service.utils.response_utils import (
    dump_model_with_select_columns,
    finalize_list_response,
)
from axbi.runtime_modernization.ax_services import (
    AxServicesClient,
    AxServicesConfig,
    AxServicesResponse,
)
from axbi.runtime_modernization.measurement import measure_runtime_candidate
from axbi.runtime_modernization.shadow import (
    execute_with_shadow,
    ShadowMismatchReport,
)

logger = logging.getLogger(__name__)

# Minimal defaults for reduced token usage - users can request more via select_columns
# NOTE: "database" (relationship) is included so the DAO eagerly loads it
# via joinedload, which avoids N+1 lazy-load queries when the serializer
# accesses dataset.database.name (via the database_name @property).
DEFAULT_DATASET_COLUMNS = [
    "id",
    "table_name",
    "schema",
    "database_name",
    "database",
    "description",
    "certified_by",
    "certification_details",
    "changed_on",
    "changed_on_humanized",
]

SORTABLE_DATASET_COLUMNS = [
    "id",
    "table_name",
    "schema",
    "changed_on",
    "created_on",
]

_DEFAULT_LIST_DATASETS_REQUEST = ListDatasetsRequest()
_DATASET_LIST_CONTRACT_VERSION = "dataset-list.v1"


def _dataset_list_request_payload(request: ListDatasetsRequest) -> dict[str, Any]:
    """Build an ax-services dataset list request payload."""

    return {
        "contractVersion": _DATASET_LIST_CONTRACT_VERSION,
        "filters": [filter_.model_dump(mode="json") for filter_ in request.filters],
        "selectColumns": list(request.select_columns),
        "search": request.search,
        "orderColumn": request.order_column,
        "orderDirection": request.order_direction,
        "page": request.page,
        "pageSize": request.page_size,
        "createdByMe": request.created_by_me,
        "ownedByMe": request.owned_by_me,
    }


def _ax_services_dataset_list_candidate(
    request: ListDatasetsRequest,
) -> AxServicesResponse:
    """Run the TypeScript sidecar dataset list candidate."""

    client = AxServicesClient(AxServicesConfig.from_mapping(current_app.config))
    return client.list_datasets(_dataset_list_request_payload(request))


def _optional_string(value: Any) -> str | None:
    """Return a string value or None."""

    return value if isinstance(value, str) else None


def _dataset_info_from_ax_services(payload: dict[str, Any]) -> DatasetInfo | None:
    """Convert one valid ax-services dataset item to the MCP dataset schema."""

    dataset_id = payload.get("id")
    if not isinstance(dataset_id, int):
        return None

    dataset = DatasetInfo(
        id=dataset_id,
        table_name=_optional_string(payload.get("tableName")),
        schema=_optional_string(payload.get("schema")),
        database_name=_optional_string(payload.get("databaseName")),
        description=_optional_string(payload.get("description")),
        certified_by=_optional_string(payload.get("certifiedBy")),
        certification_details=_optional_string(payload.get("certificationDetails")),
        changed_on=_optional_string(payload.get("changedOn")),
        changed_on_humanized=_optional_string(payload.get("changedOnHumanized")),
        is_virtual=payload.get("isVirtual")
        if isinstance(payload.get("isVirtual"), bool)
        else None,
        database_id=payload.get("databaseId")
        if isinstance(payload.get("databaseId"), int)
        else None,
        uuid=_optional_string(payload.get("uuid")),
        url=_optional_string(payload.get("url")),
    )
    return _sanitize_ax_services_dataset_info(dataset)


def _sanitize_ax_services_dataset_info(dataset: DatasetInfo) -> DatasetInfo:
    """Apply MCP LLM-context sanitization to sidecar dataset fields."""

    payload = dataset.model_dump(mode="python", by_alias=True)
    for field_name in (
        "table_name",
        "schema",
        "database_name",
        "description",
        "certified_by",
        "certification_details",
    ):
        payload[field_name] = sanitize_for_llm_context(
            payload.get(field_name),
            field_path=(field_name,),
        )
    return DatasetInfo(**payload)


def _is_string_list(value: Any) -> bool:
    """Return whether a value is a list of strings."""

    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def _dataset_list_from_ax_services_response(
    response: AxServicesResponse,
) -> dict[str, Any] | None:
    """Convert a valid ax-services dataset list response to the MCP schema."""

    payload = response.payload or {}
    if (
        not response.ok
        or payload.get("contractVersion") != _DATASET_LIST_CONTRACT_VERSION
    ):
        return None

    raw_datasets = payload.get("datasets")
    if not isinstance(raw_datasets, list):
        return None

    datasets = []
    for raw_dataset in raw_datasets:
        if not isinstance(raw_dataset, dict):
            return None
        dataset = _dataset_info_from_ax_services(raw_dataset)
        if dataset is None:
            return None
        datasets.append(dataset)

    count = payload.get("count")
    total_count = payload.get("totalCount")
    page = payload.get("page")
    page_size = payload.get("pageSize")
    total_pages = payload.get("totalPages")
    has_next = payload.get("hasNext")
    has_previous = payload.get("hasPrevious")
    columns_requested = payload.get("columnsRequested")
    columns_loaded = payload.get("columnsLoaded")
    if (
        not isinstance(count, int)
        or not isinstance(total_count, int)
        or not isinstance(page, int)
        or not isinstance(page_size, int)
        or not isinstance(total_pages, int)
        or not isinstance(has_next, bool)
        or not isinstance(has_previous, bool)
        or not _is_string_list(columns_requested)
        or not _is_string_list(columns_loaded)
    ):
        return None

    dataset_list = DatasetList(
        datasets=datasets,
        count=count,
        total_count=total_count,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        has_next=has_next,
        has_previous=has_previous,
        columns_requested=columns_requested,
        columns_loaded=columns_loaded,
        columns_available=[],
        sortable_columns=SORTABLE_DATASET_COLUMNS,
        filters_applied=[],
        pagination=PaginationInfo(
            page=page,
            page_size=page_size,
            total_count=total_count,
            total_pages=total_pages,
            has_next=has_next,
            has_previous=has_previous,
        ),
    )
    return dump_model_with_select_columns(dataset_list, columns_requested)


def _dataset_keys_from_mcp_response(response: dict[str, Any]) -> list[int]:
    """Return dataset IDs from an MCP dataset list response."""

    datasets = response.get("datasets")
    if not isinstance(datasets, list):
        return []
    return [
        dataset["id"]
        for dataset in datasets
        if isinstance(dataset, dict) and isinstance(dataset.get("id"), int)
    ]


def _dataset_keys_from_ax_services_response(response: AxServicesResponse) -> list[int]:
    """Return dataset IDs from an ax-services dataset list response."""

    payload = response.payload or {}
    datasets = payload.get("datasets") if isinstance(payload, dict) else None
    if not isinstance(datasets, list):
        return []
    return [
        dataset["id"]
        for dataset in datasets
        if isinstance(dataset, dict) and isinstance(dataset.get("id"), int)
    ]


def _dataset_list_shadow_matches(
    authoritative: dict[str, Any],
    candidate: AxServicesResponse,
) -> bool:
    """Compare Python and TypeScript dataset list outputs by ID order."""

    return candidate.ok and _dataset_keys_from_mcp_response(
        authoritative
    ) == _dataset_keys_from_ax_services_response(candidate)


def _summarize_dataset_list_response(response: dict[str, Any]) -> dict[str, object]:
    """Summarize Python dataset list results for shadow mismatch reports."""

    return {
        "count": len(_dataset_keys_from_mcp_response(response)),
        "ids": _dataset_keys_from_mcp_response(response),
    }


def _summarize_ax_services_dataset_list_response(
    response: AxServicesResponse,
) -> dict[str, object]:
    """Summarize ax-services dataset list results for shadow mismatch reports."""

    payload = response.payload or {}
    return {
        "ok": response.ok,
        "status_code": response.status_code,
        "contract_version": payload.get("contractVersion")
        if isinstance(payload, dict)
        else None,
        "count": len(_dataset_keys_from_ax_services_response(response)),
        "ids": _dataset_keys_from_ax_services_response(response),
        "error": response.error,
    }


def _report_dataset_list_shadow_mismatch(report: ShadowMismatchReport) -> None:
    """Log a compact dataset list shadow mismatch report."""

    logger.warning(
        "Runtime modernization dataset list shadow mismatch: %s",
        report.to_dict(),
    )


def _dataset_list_shadow_enabled() -> bool:
    """Return whether dataset listing should shadow through ax-services."""

    return is_feature_enabled("RUNTIME_SHADOW_EXECUTION") and is_feature_enabled(
        "TS_MCP_ORCHESTRATION"
    )


def _dataset_list_serving_enabled() -> bool:
    """Return whether dataset listing should be served through ax-services."""

    return is_feature_enabled("TS_MCP_ORCHESTRATION") and is_feature_enabled(
        "TS_DATASET_LIST_SERVING"
    )


def _record_dataset_list_metric(metric: str) -> None:
    """Record a dataset-list migration metric."""

    current_app.config["STATS_LOGGER"].incr(
        f"runtime_modernization.mcp_orchestration.list_datasets.{metric}"
    )


@tool(
    tags=["core"],
    class_permission_name="Dataset",
    annotations=ToolAnnotations(
        title="List datasets",
        readOnlyHint=True,
        destructiveHint=False,
    ),
)
@requires_data_model_metadata_access
async def list_datasets(
    request: ListDatasetsRequest | None = None,
    ctx: Context | None = None,
) -> DatasetList | DatasetError | dict[str, Any]:
    """List datasets with filtering and search.

    Returns dataset metadata including table name, schema, and last modified
    time.

    **IMPORTANT**: All parameters must be wrapped in a ``request`` object.
    Do NOT pass ``search``, ``page``, ``page_size``, etc. as top-level
    keyword arguments — they will be rejected. Use the ``request`` wrapper::

        # Correct usage
        list_datasets(request={"search": "sales", "page": 1, "page_size": 10})
        list_datasets(request={"filters": [{"col": "table_name", "opr": "sw", "value": "orders"}]})
        list_datasets()  # no arguments returns first page with defaults

        # Wrong — causes pydantic validation errors
        list_datasets(search="sales", page=1)  # DO NOT DO THIS

    Valid filter columns for ``filters[].col``:
        ``table_name``, ``schema``, ``database_name``,
        ``created_by_fk``, ``changed_by_fk``

    Sortable columns for ``order_column``:
        ``id``, ``table_name``, ``schema``, ``changed_on``, ``created_on``

    To filter by a person, call find_users to resolve the name to a user ID,
    then pass it as a filter: filters=[{"col": "created_by_fk", "opr": "eq",
    "value": <id>}] (or "changed_by_fk"). Do not pass the name as search.
    """
    if ctx is None:
        raise RuntimeError("FastMCP context is required for list_datasets")

    request = request_or_default(request, _DEFAULT_LIST_DATASETS_REQUEST)

    await ctx.info(
        f"Listing datasets: page={request.page}, "
        f"page_size={request.page_size}, search={request.search}"
    )
    await ctx.debug(
        f"Dataset listing parameters: filters={request.filters}, "
        f"order_column={request.order_column}, "
        f"order_direction={request.order_direction}, "
        f"select_columns={request.select_columns}"
    )
    await ctx.debug(
        f"Metadata cache settings: use_cache={request.use_cache}, "
        f"refresh_metadata={request.refresh_metadata}, "
        f"force_refresh={request.force_refresh}"
    )

    if not user_can_view_data_model_metadata():
        await ctx.warning("Dataset listing blocked by data-model privacy controls")
        return DatasetError.create(
            error="You don't have permission to access dataset details for your role.",
            error_type=DATA_MODEL_METADATA_ERROR_TYPE,
        )

    with measure_runtime_candidate(
        "mcp_orchestration",
        "list_datasets",
        current_app.config["STATS_LOGGER"],
    ):
        if _dataset_list_serving_enabled():
            candidate_response = _ax_services_dataset_list_candidate(request)
            candidate_datasets = _dataset_list_from_ax_services_response(
                candidate_response,
            )
            if candidate_datasets is not None:
                _record_dataset_list_metric("served_candidate")
                return candidate_datasets

            _record_dataset_list_metric("fallback")
            return await _list_datasets_python(request, ctx)

        python_response = await _list_datasets_python(request, ctx)
        return execute_with_shadow(
            area="mcp_orchestration",
            operation="list_datasets",
            authoritative=lambda: python_response,
            candidate=lambda: _ax_services_dataset_list_candidate(request),
            compare=_dataset_list_shadow_matches,
            stats_logger=current_app.config["STATS_LOGGER"],
            shadow_enabled=_dataset_list_shadow_enabled(),
            report_mismatch=_report_dataset_list_shadow_mismatch,
            summarize_authoritative=_summarize_dataset_list_response,
            summarize_candidate=_summarize_ax_services_dataset_list_response,
        )


async def _list_datasets_python(
    request: ListDatasetsRequest,
    ctx: Context,
) -> dict[str, Any]:
    """Run the authoritative Python dataset list path."""

    try:
        from axbi.daos.dataset import DatasetDAO
        from axbi.mcp_service.common.schema_discovery import (
            DATASET_SORTABLE_COLUMNS,
            get_all_column_names,
            get_dataset_columns,
        )

        # Get all column names dynamically from the model
        all_columns = get_all_column_names(get_dataset_columns())

        def _serialize_dataset(
            obj: "SqlaTable | None", cols: list[str] | None
        ) -> DatasetInfo | None:
            """Serialize dataset (filtering via model_serializer)."""
            return serialize_dataset_object(obj)

        # Create tool with standard serialization
        tool = ModelListCore(
            dao_class=DatasetDAO,
            output_schema=DatasetInfo,
            item_serializer=_serialize_dataset,
            filter_type=DatasetFilter,
            default_columns=DEFAULT_DATASET_COLUMNS,
            search_columns=["schema", "sql", "table_name", "uuid"],
            list_field_name="datasets",
            output_list_schema=DatasetList,
            all_columns=all_columns,
            sortable_columns=DATASET_SORTABLE_COLUMNS,
            logger=logger,
        )

        with mcp_event_log_context(action="mcp.list_datasets.query"):
            result = tool.run_tool(
                filters=request.filters,
                search=request.search,
                select_columns=request.select_columns,
                order_column=request.order_column,
                order_direction=request.order_direction,
                page=to_zero_based_page(request.page),
                page_size=request.page_size,
                created_by_me=request.created_by_me,
                owned_by_me=request.owned_by_me,
            )

        return await finalize_list_response(result, "datasets", "Datasets", ctx)

    except Exception as e:
        await ctx.error(
            f"Dataset listing failed: page={request.page}, "
            f"page_size={request.page_size}, error={str(e)}, "
            f"error_type={type(e).__name__}"
        )
        raise

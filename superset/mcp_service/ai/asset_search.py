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
"""Business asset search service for GenAI BI.

Provides cross-asset text search over datasets, charts, and dashboards
using existing DAOs with RBAC-aware base filters. Results are ranked
by a simple relevance score based on name/description match quality
and certification status.
"""

from __future__ import annotations

import logging
from typing import Any, cast

from flask import current_app, has_app_context
from sqlalchemy import or_

from superset import is_feature_enabled
from superset.extensions import db
from superset.mcp_service.ai.schemas import AssetResult
from superset.runtime_modernization.ax_services import (
    AxServicesClient,
    AxServicesConfig,
    AxServicesResponse,
)
from superset.runtime_modernization.measurement import runtime_metric_key
from superset.runtime_modernization.rust_genai import (
    rank_assets as rank_assets_with_rust,
    rust_asset_ranking_kernel_available,
)
from superset.runtime_modernization.shadow import (
    execute_with_shadow,
    ShadowMismatchReport,
)

logger = logging.getLogger(__name__)

# Scoring weights
_NAME_MATCH_SCORE = 1.0
_DESCRIPTION_MATCH_SCORE = 0.5
_CERTIFIED_BONUS = 0.2

_VALID_ASSET_TYPES = frozenset({"dataset", "chart", "dashboard", "metric"})
_ASSET_SEARCH_CONTRACT_VERSION = "asset-search.v1"


def _escape_like_pattern(value: str) -> str:
    """Escape LIKE wildcard characters in a search value.

    SQLAlchemy's ``ilike`` parameterises the value (preventing SQL injection)
    but ``%`` and ``_`` inside the value are still interpreted as LIKE
    wildcards.  Escape them so searches for literal ``100%`` or ``_admin``
    return correct results.
    """
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _score_result(name: str | None, description: str | None, query: str) -> float:
    """Compute a simple relevance score for a search result."""
    score = 0.0
    query_lower = query.lower()
    if name and query_lower in name.lower():
        score += _NAME_MATCH_SCORE
    if description and query_lower in description.lower():
        score += _DESCRIPTION_MATCH_SCORE
    return score


def _is_certified(obj: Any) -> bool:
    """Check if an object is certified (has a non-empty certified_by field)."""
    return bool(getattr(obj, "certified_by", None))


def _get_owners(obj: Any) -> list[str]:
    """Extract owner names from an object's owners relationship."""
    owners_rel = getattr(obj, "owners", None)
    if not owners_rel:
        return []
    return [
        getattr(o, "username", "") or getattr(o, "first_name", "")
        for o in owners_rel
        if o
    ]


def _get_tags(obj: Any) -> list[str]:
    """Extract tag names from an object's tags relationship."""
    tags_rel = getattr(obj, "tags", None)
    if not tags_rel:
        return []
    return [getattr(t, "name", "") for t in tags_rel if t and getattr(t, "name", None)]


def _search_datasets(
    query: str,
    include_certified_only: bool,
    limit: int,
) -> list[AssetResult]:
    """Search datasets by name/description."""
    from superset.connectors.sqla.models import SqlaTable
    from superset.daos.dataset import DatasetDAO

    escaped_query = _escape_like_pattern(query)
    search_filter = or_(
        SqlaTable.table_name.ilike(f"%{escaped_query}%", escape="\\"),
        cast(Any, SqlaTable.description).ilike(
            f"%{escaped_query}%",
            escape="\\",
        ),
    )

    session = db.session
    model_query = session.query(SqlaTable)

    # Apply DAO base filters for RBAC
    model_query = DatasetDAO._apply_base_filter(model_query)  # noqa: SLF001

    if include_certified_only:
        model_query = model_query.filter(SqlaTable.certified_by.isnot(None))

    results = model_query.filter(search_filter).limit(limit).all()

    assets = []
    for ds in results:
        score = _score_result(ds.table_name, ds.description, query)
        if _is_certified(ds):
            score += _CERTIFIED_BONUS
        assets.append(
            AssetResult(
                asset_type="dataset",
                id=ds.id,
                uuid=str(getattr(ds, "uuid", "")),
                name=ds.table_name or "",
                description=ds.description or "",
                certified=_is_certified(ds),
                relevance_score=round(score, 4),
                relevance_reason=_build_reason(ds.table_name, ds.description, query),
                owners=_get_owners(ds),
                tags=_get_tags(ds),
            )
        )
    return assets


def _search_charts(
    query: str,
    include_certified_only: bool,
    limit: int,
) -> list[AssetResult]:
    """Search charts by name/description."""
    from superset.daos.chart import ChartDAO
    from superset.models.slice import Slice

    escaped_query = _escape_like_pattern(query)
    search_filter = or_(
        Slice.slice_name.ilike(f"%{escaped_query}%", escape="\\"),
        Slice.description.ilike(f"%{escaped_query}%", escape="\\"),
    )

    session = db.session
    model_query = session.query(Slice)

    # Apply DAO base filters for RBAC
    model_query = ChartDAO._apply_base_filter(model_query)  # noqa: SLF001

    if include_certified_only:
        model_query = model_query.filter(Slice.certified_by.isnot(None))

    results = model_query.filter(search_filter).limit(limit).all()

    assets = []
    for chart in results:
        score = _score_result(chart.slice_name, chart.description, query)
        if _is_certified(chart):
            score += _CERTIFIED_BONUS
        assets.append(
            AssetResult(
                asset_type="chart",
                id=chart.id,
                uuid=str(getattr(chart, "uuid", "")),
                name=chart.slice_name or "",
                description=chart.description or "",
                certified=_is_certified(chart),
                relevance_score=round(score, 4),
                relevance_reason=_build_reason(
                    chart.slice_name, chart.description, query
                ),
                owners=_get_owners(chart),
                tags=_get_tags(chart),
            )
        )
    return assets


def _search_dashboards(
    query: str,
    include_certified_only: bool,
    limit: int,
) -> list[AssetResult]:
    """Search dashboards by title/description."""
    from superset.daos.dashboard import DashboardDAO
    from superset.models.dashboard import Dashboard

    escaped_query = _escape_like_pattern(query)
    search_filter = or_(
        Dashboard.dashboard_title.ilike(f"%{escaped_query}%", escape="\\"),
        Dashboard.description.ilike(f"%{escaped_query}%", escape="\\"),
    )

    session = db.session
    model_query = session.query(Dashboard)

    # Apply DAO base filters for RBAC
    model_query = DashboardDAO._apply_base_filter(model_query)  # noqa: SLF001

    if include_certified_only:
        model_query = model_query.filter(Dashboard.certified_by.isnot(None))

    results = model_query.filter(search_filter).limit(limit).all()

    assets = []
    for dash in results:
        score = _score_result(dash.dashboard_title, dash.description, query)
        if _is_certified(dash):
            score += _CERTIFIED_BONUS
        assets.append(
            AssetResult(
                asset_type="dashboard",
                id=dash.id,
                uuid=str(getattr(dash, "uuid", "")),
                name=dash.dashboard_title or "",
                description=dash.description or "",
                certified=_is_certified(dash),
                relevance_score=round(score, 4),
                relevance_reason=_build_reason(
                    dash.dashboard_title, dash.description, query
                ),
                owners=_get_owners(dash),
                tags=_get_tags(dash),
            )
        )
    return assets


def _build_reason(name: str | None, description: str | None, query: str) -> str:
    """Build a human-readable relevance reason string."""
    parts: list[str] = []
    query_lower = query.lower()
    if name and query_lower in name.lower():
        parts.append(f"name matches '{query}'")
    if description and query_lower in description.lower():
        parts.append(f"description matches '{query}'")
    return ", ".join(parts) if parts else "tag/owner match"


def _search_assets_python(
    query: str,
    asset_types: list[str] | None = None,
    include_certified_only: bool = False,
    limit: int = 10,
) -> list[AssetResult]:
    """Search business assets across datasets, charts, and dashboards.

    :param query: Natural language search query.
    :param asset_types: Asset types to include. Defaults to all types.
    :param include_certified_only: Only return certified assets.
    :param limit: Maximum number of results to return.
    :returns: List of AssetResult sorted by relevance_score descending.
    """
    if not query or not query.strip() or limit <= 0:
        return []

    types_to_search = set(asset_types) if asset_types else _VALID_ASSET_TYPES
    # Validate types
    types_to_search = types_to_search & _VALID_ASSET_TYPES
    if not types_to_search:
        return []

    all_results: list[AssetResult] = []
    semantic_results = _search_assets_semantic(
        query,
        asset_types=asset_types,
        include_certified_only=include_certified_only,
        limit=limit,
    )

    # Allocate limit per type to ensure diversity
    per_type_limit = max(limit, 1)

    if "dataset" in types_to_search:
        all_results.extend(
            _search_datasets(query, include_certified_only, per_type_limit)
        )

    if "chart" in types_to_search:
        all_results.extend(
            _search_charts(query, include_certified_only, per_type_limit)
        )

    if "dashboard" in types_to_search:
        all_results.extend(
            _search_dashboards(query, include_certified_only, per_type_limit)
        )

    # "metric" type searches would require querying SqlMetric directly
    # For now, metrics are surfaced via describe_dataset_for_ai

    all_results = _merge_asset_results(semantic_results, all_results)

    # Sort by relevance score descending and apply final limit
    return _rank_asset_results(query, all_results, limit)


def _merge_asset_results(
    primary_results: list[AssetResult],
    fallback_results: list[AssetResult],
) -> list[AssetResult]:
    """Merge asset results while keeping one result per concrete asset."""

    merged: list[AssetResult] = []
    seen: set[tuple[str, int]] = set()
    for result in [*primary_results, *fallback_results]:
        key = (result.asset_type, result.id)
        if key in seen:
            continue
        seen.add(key)
        merged.append(result)
    return merged


def _semantic_asset_search_enabled() -> bool:
    """Return whether pgvector semantic asset search should be attempted."""

    return (
        has_app_context()
        and is_feature_enabled("GENAI_SEMANTIC_INDEX")
        and is_feature_enabled("GENAI_SEMANTIC_INDEX_PGVECTOR")
    )


def _semantic_score(distance: float | None) -> float:
    """Convert cosine distance into a compact relevance score."""

    if distance is None:
        return 0.0
    return round(max(0.0, 2.0 - distance), 4)


def _search_assets_semantic(  # noqa: C901
    query: str,
    asset_types: list[str] | None,
    include_certified_only: bool,
    limit: int,
) -> list[AssetResult]:
    """Search indexed semantic documents and return authorized datasets."""

    if limit <= 0:
        return []

    if not _semantic_asset_search_enabled():
        return []

    types_to_search = set(asset_types) if asset_types else _VALID_ASSET_TYPES
    if "dataset" not in types_to_search:
        return []

    try:
        from superset.connectors.sqla.models import SqlaTable
        from superset.daos.dataset import DatasetDAO
        from superset.semantic_index.service import SemanticIndexService

        semantic_results = SemanticIndexService().search(
            query,
            limit=limit * 4,
            object_types=["dataset", "column", "metric"],
        )
    except Exception:
        logger.warning(
            "Semantic asset search failed; falling back to lexical search",
            exc_info=True,
        )
        return []

    dataset_ids: list[int] = []
    seen_dataset_ids: set[int] = set()
    best_by_dataset: dict[int, tuple[float, str]] = {}
    for result in semantic_results:
        if result.dataset_id is None or result.dataset_id in seen_dataset_ids:
            continue
        seen_dataset_ids.add(result.dataset_id)
        dataset_ids.append(result.dataset_id)
        best_by_dataset[result.dataset_id] = (
            _semantic_score(result.distance),
            f"semantic match via {result.document_kind}: {result.object_name}",
        )
        if len(dataset_ids) >= limit:
            break

    if not dataset_ids:
        return []

    model_query = db.session.query(SqlaTable)
    model_query = DatasetDAO._apply_base_filter(model_query)  # noqa: SLF001
    model_query = model_query.filter(SqlaTable.id.in_(dataset_ids))
    if include_certified_only:
        model_query = model_query.filter(SqlaTable.certified_by.isnot(None))

    datasets = {dataset.id: dataset for dataset in model_query.all()}
    assets: list[AssetResult] = []
    for dataset_id in dataset_ids:
        dataset = datasets.get(dataset_id)
        if dataset is None:
            continue
        score, reason = best_by_dataset.get(dataset_id, (0.0, "semantic match"))
        assets.append(
            AssetResult(
                asset_type="dataset",
                id=dataset.id,
                uuid=str(getattr(dataset, "uuid", "")),
                name=dataset.table_name or "",
                description=dataset.description or "",
                certified=_is_certified(dataset),
                relevance_score=score,
                relevance_reason=reason,
                owners=_get_owners(dataset),
                tags=_get_tags(dataset),
            )
        )

    return assets[:limit]


def _rust_asset_ranking_enabled() -> bool:
    """Return whether asset results should be ranked through Rust."""

    return (
        has_app_context()
        and is_feature_enabled("RUST_ASSET_RANKING_KERNEL")
        and rust_asset_ranking_kernel_available()
    )


def _rank_asset_results_python(
    _query: str,
    results: list[AssetResult],
    limit: int,
) -> list[AssetResult]:
    """Rank asset results through the Python compatibility path."""

    results.sort(key=lambda result: result.relevance_score or 0.0, reverse=True)
    return results[:limit]


def _rank_asset_results_with_rust(
    query: str,
    results: list[AssetResult],
    limit: int,
) -> list[AssetResult] | None:
    """Rank asset results through the optional Rust kernel."""

    try:
        ranked_payload = rank_assets_with_rust(
            query,
            [result.model_dump() for result in results],
            limit,
        )
    except Exception:
        logger.warning(
            "Rust asset ranking failed; falling back to Python ranking",
            exc_info=True,
        )
        return None

    ranked_results: list[AssetResult] = []
    for item in ranked_payload:
        if not isinstance(item, dict):
            return None
        try:
            ranked_results.append(AssetResult(**item))
        except (TypeError, ValueError):
            logger.warning(
                "Rust asset ranking returned an invalid result; falling back",
                exc_info=True,
            )
            return None

    return ranked_results


def _rank_asset_results(
    query: str,
    results: list[AssetResult],
    limit: int,
) -> list[AssetResult]:
    """Rank authorized asset results with an optional Rust kernel."""

    if _rust_asset_ranking_enabled():
        ranked_results = _rank_asset_results_with_rust(query, results, limit)
        if ranked_results is not None:
            return ranked_results

    return _rank_asset_results_python(query, results, limit)


def _asset_search_shadow_enabled() -> bool:
    """Return whether asset search should shadow through ax-services."""

    return (
        has_app_context()
        and is_feature_enabled("RUNTIME_SHADOW_EXECUTION")
        and is_feature_enabled("TS_MCP_ORCHESTRATION")
    )


def _asset_search_serving_enabled() -> bool:
    """Return whether asset search should serve from ax-services."""

    return (
        has_app_context()
        and is_feature_enabled("TS_MCP_ORCHESTRATION")
        and is_feature_enabled("TS_ASSET_SEARCH_SERVING")
    )


def _ax_services_asset_search_candidate(
    query: str,
    asset_types: list[str] | None,
    include_certified_only: bool,
    limit: int,
) -> AxServicesResponse:
    """Run the TypeScript sidecar asset search candidate."""

    client = AxServicesClient(AxServicesConfig.from_mapping(current_app.config))
    return client.asset_search(
        {
            "contractVersion": _ASSET_SEARCH_CONTRACT_VERSION,
            "query": query,
            "assetTypes": asset_types or [],
            "includeCertifiedOnly": include_certified_only,
            "limit": limit,
        }
    )


def _is_string_list(value: object) -> bool:
    """Return whether value is a list of strings."""

    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def _asset_results_from_ax_services_response(
    response: AxServicesResponse,
) -> list[AssetResult] | None:
    """Convert a TypeScript sidecar asset-search response into Python schemas."""

    if not response.ok or not response.payload:
        return None

    assets = response.payload.get("assets")
    if not isinstance(assets, list):
        return None

    results: list[AssetResult] = []
    for asset in assets:
        if not isinstance(asset, dict):
            return None

        asset_type = asset.get("assetType")
        asset_id = asset.get("id")
        name = asset.get("name")
        if not isinstance(asset_type, str) or not isinstance(asset_id, int):
            return None
        if not isinstance(name, str):
            return None

        owners = asset.get("owners", [])
        tags = asset.get("tags", [])
        if not _is_string_list(owners) or not _is_string_list(tags):
            return None

        relevance_score = asset.get("relevanceScore")
        results.append(
            AssetResult(
                asset_type=asset_type,
                id=asset_id,
                uuid=asset.get("uuid") if isinstance(asset.get("uuid"), str) else "",
                name=name,
                description=asset.get("description")
                if isinstance(asset.get("description"), str)
                else "",
                certified=asset.get("certified") is True,
                relevance_score=relevance_score
                if isinstance(relevance_score, (int, float))
                and not isinstance(relevance_score, bool)
                else None,
                relevance_reason=asset.get("relevanceReason")
                if isinstance(asset.get("relevanceReason"), str)
                else None,
                owners=owners,
                tags=tags,
            )
        )

    return results


def _asset_search_shadow_matches(
    authoritative: list[AssetResult],
    candidate: AxServicesResponse,
) -> bool:
    """Compare Python and TypeScript asset search outputs by type and ID."""

    if not candidate.ok or not candidate.payload:
        return False

    candidate_assets = candidate.payload.get("assets")
    if not isinstance(candidate_assets, list):
        return False

    authoritative_keys = [(asset.asset_type, asset.id) for asset in authoritative]
    candidate_keys: list[tuple[str, int]] = []
    for asset in candidate_assets:
        if not isinstance(asset, dict):
            return False
        asset_type = asset.get("assetType")
        asset_id = asset.get("id")
        if not isinstance(asset_type, str) or not isinstance(asset_id, int):
            return False
        candidate_keys.append((asset_type, asset_id))

    return authoritative_keys == candidate_keys


def _asset_keys_from_results(results: list[AssetResult]) -> list[tuple[str, int]]:
    """Return stable asset keys without exposing names or descriptions."""

    return [(asset.asset_type, asset.id) for asset in results]


def _asset_keys_from_ax_services_payload(payload: Any) -> list[tuple[str, int]]:
    """Return stable asset keys from an ax-services payload."""

    if not isinstance(payload, dict):
        return []

    assets = payload.get("assets")
    if not isinstance(assets, list):
        return []

    keys = []
    for asset in assets:
        if not isinstance(asset, dict):
            continue

        asset_type = asset.get("assetType")
        asset_id = asset.get("id")
        if isinstance(asset_type, str) and isinstance(asset_id, int):
            keys.append((asset_type, asset_id))

    return keys


def _summarize_asset_search_results(results: list[AssetResult]) -> dict[str, object]:
    """Summarize Python asset search results for shadow mismatch reports."""

    return {
        "count": len(results),
        "keys": _asset_keys_from_results(results),
    }


def _summarize_ax_services_asset_search_response(
    response: AxServicesResponse,
) -> dict[str, object]:
    """Summarize ax-services asset search results for shadow mismatch reports."""

    payload = response.payload or {}
    return {
        "ok": response.ok,
        "status_code": response.status_code,
        "contract_version": payload.get("contractVersion")
        if isinstance(payload, dict)
        else None,
        "count": len(_asset_keys_from_ax_services_payload(payload)),
        "keys": _asset_keys_from_ax_services_payload(payload),
        "error": response.error,
    }


def _report_asset_search_shadow_mismatch(report: ShadowMismatchReport) -> None:
    """Log a compact asset search shadow mismatch report."""

    logger.warning(
        "Runtime modernization asset search shadow mismatch: %s",
        report.to_dict(),
    )


def _record_asset_search_metric(metric: str) -> None:
    """Record an asset-search migration metric when Flask context is available."""

    if has_app_context():
        current_app.config["STATS_LOGGER"].incr(
            runtime_metric_key("mcp_orchestration", "search_assets", metric)
        )


def search_assets(
    query: str,
    asset_types: list[str] | None = None,
    include_certified_only: bool = False,
    limit: int = 10,
) -> list[AssetResult]:
    """Search business assets with optional TypeScript shadow execution."""

    if not has_app_context():
        return _search_assets_python(
            query,
            asset_types=asset_types,
            include_certified_only=include_certified_only,
            limit=limit,
        )

    if _asset_search_serving_enabled():
        candidate_response = _ax_services_asset_search_candidate(
            query,
            asset_types,
            include_certified_only,
            limit,
        )
        candidate_assets = _asset_results_from_ax_services_response(candidate_response)
        if candidate_assets is not None:
            _record_asset_search_metric("served_candidate")
            return candidate_assets

        _record_asset_search_metric("fallback")
        return _search_assets_python(
            query,
            asset_types=asset_types,
            include_certified_only=include_certified_only,
            limit=limit,
        )

    return execute_with_shadow(
        area="mcp_orchestration",
        operation="search_assets",
        authoritative=lambda: _search_assets_python(
            query,
            asset_types=asset_types,
            include_certified_only=include_certified_only,
            limit=limit,
        ),
        candidate=lambda: _ax_services_asset_search_candidate(
            query,
            asset_types,
            include_certified_only,
            limit,
        ),
        compare=_asset_search_shadow_matches,
        stats_logger=current_app.config["STATS_LOGGER"],
        shadow_enabled=_asset_search_shadow_enabled(),
        report_mismatch=_report_asset_search_shadow_mismatch,
        summarize_authoritative=_summarize_asset_search_results,
        summarize_candidate=_summarize_ax_services_asset_search_response,
    )

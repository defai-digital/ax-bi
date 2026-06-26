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
from typing import Any

from sqlalchemy import or_

from superset.extensions import db
from superset.mcp_service.ai.schemas import AssetResult

logger = logging.getLogger(__name__)

# Scoring weights
_NAME_MATCH_SCORE = 1.0
_DESCRIPTION_MATCH_SCORE = 0.5
_CERTIFIED_BONUS = 0.2

_VALID_ASSET_TYPES = frozenset({"dataset", "chart", "dashboard", "metric"})


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

    search_filter = or_(
        SqlaTable.table_name.ilike(f"%{query}%"),
        SqlaTable.description.ilike(f"%{query}%"),
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

    search_filter = or_(
        Slice.slice_name.ilike(f"%{query}%"),
        Slice.description.ilike(f"%{query}%"),
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

    search_filter = or_(
        Dashboard.dashboard_title.ilike(f"%{query}%"),
        Dashboard.description.ilike(f"%{query}%"),
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


def search_assets(
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
    if not query or not query.strip():
        return []

    types_to_search = set(asset_types) if asset_types else _VALID_ASSET_TYPES
    # Validate types
    types_to_search = types_to_search & _VALID_ASSET_TYPES
    if not types_to_search:
        return []

    all_results: list[AssetResult] = []

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

    # Sort by relevance score descending and apply final limit
    all_results.sort(key=lambda r: r.relevance_score or 0.0, reverse=True)
    return all_results[:limit]

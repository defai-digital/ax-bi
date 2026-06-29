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
"""Registry of removed legacy ``viz_type`` values and their replacements.

These are the legacy chart types that have a modern (ECharts/``_v2``)
equivalent and an automatic migration in
``superset.migrations.shared.migrate_viz``. They are no longer creatable:
the API and MCP command layers reject any chart written with one of these
``viz_type`` values, and ``test_legacy.py`` asserts this mapping stays in
sync with the migration processors so the two cannot drift apart.
"""

from __future__ import annotations

from typing import TypeGuard

# Maps each removed legacy ``viz_type`` to the modern ``viz_type`` that
# replaces it. Mirrors the ``source_viz_type``/``target_viz_type`` pairs in
# ``superset.migrations.shared.migrate_viz.processors``.
LEGACY_VIZ_TYPE_REPLACEMENTS: dict[str, str] = {
    "area": "echarts_area",
    "bar": "echarts_timeseries_bar",
    "bubble": "bubble_v2",
    "dist_bar": "echarts_timeseries_bar",
    "dual_line": "mixed_timeseries",
    "heatmap": "heatmap_v2",
    "histogram": "histogram_v2",
    "line": "echarts_timeseries_line",
    "mapbox": "point_cluster_map",
    "pivot_table": "pivot_table_v2",
    "sankey": "sankey_v2",
    "sunburst": "sunburst_v2",
    "treemap": "treemap_v2",
}

# The set of legacy ``viz_type`` values that are no longer accepted.
LEGACY_VIZ_TYPES: frozenset[str] = frozenset(LEGACY_VIZ_TYPE_REPLACEMENTS)


def is_legacy_viz_type(viz_type: str | None) -> TypeGuard[str]:
    """Return ``True`` if ``viz_type`` is a removed legacy chart type."""
    return viz_type in LEGACY_VIZ_TYPES


def legacy_viz_type_message(viz_type: str) -> str:
    """Build a user-facing message pointing at the modern replacement."""
    replacement = LEGACY_VIZ_TYPE_REPLACEMENTS.get(viz_type)
    base = f"The chart type '{viz_type}' has been removed"
    if replacement:
        return f"{base}. Use '{replacement}' instead."
    return f"{base}."

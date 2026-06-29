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
"""Unit tests for legacy ``viz_type`` rejection in chart create/update."""

from unittest.mock import MagicMock, patch

import pytest

from superset.commands.chart.exceptions import ChartInvalidError
from superset.commands.chart.legacy import (
    is_legacy_viz_type,
    legacy_viz_type_message,
    LEGACY_VIZ_TYPE_REPLACEMENTS,
    LEGACY_VIZ_TYPES,
)


def test_legacy_registry_matches_migration_processors() -> None:
    """The removed-legacy registry must stay in sync with the migration
    processors so the API/MCP ban and the data migration never drift apart."""
    from superset.migrations.shared.migrate_viz.base import MigrateViz

    def _leaf_processors(cls: type) -> list[type]:
        subclasses = cls.__subclasses__()
        if not subclasses:
            return [cls]
        leaves: list[type] = []
        for sub in subclasses:
            leaves.extend(_leaf_processors(sub))
        return leaves

    # Import processors so every subclass is registered.
    import superset.migrations.shared.migrate_viz.processors  # noqa: F401

    migration_map = {
        proc.source_viz_type: proc.target_viz_type
        for proc in _leaf_processors(MigrateViz)
        if getattr(proc, "source_viz_type", "")
    }

    # Every loaded migration (legacy -> modern) must be reflected in the ban
    # list with the same replacement. Version-file processors load lazily, so
    # the registry may legitimately list more than are loaded here; the
    # invariant we enforce is that none drift out or disagree.
    for source_viz_type, target_viz_type in migration_map.items():
        assert LEGACY_VIZ_TYPE_REPLACEMENTS.get(source_viz_type) == target_viz_type, (
            f"Migration {source_viz_type!r} -> {target_viz_type!r} is not "
            "reflected in LEGACY_VIZ_TYPE_REPLACEMENTS"
        )


def test_is_legacy_viz_type() -> None:
    assert is_legacy_viz_type("bubble") is True
    assert is_legacy_viz_type("line") is True
    assert is_legacy_viz_type("bubble_v2") is False
    assert is_legacy_viz_type("echarts_timeseries_line") is False
    assert is_legacy_viz_type(None) is False


def test_legacy_viz_type_message_names_replacement() -> None:
    message = legacy_viz_type_message("bubble")
    assert "bubble" in message
    assert "bubble_v2" in message


@pytest.mark.parametrize("viz_type", sorted(LEGACY_VIZ_TYPES))
def test_create_chart_command_rejects_legacy_viz_type(viz_type: str) -> None:
    """CreateChartCommand.validate() must reject every removed legacy type."""
    from superset.commands.chart.create import CreateChartCommand

    mock_datasource = MagicMock()
    mock_datasource.name = "test_table"

    with (
        patch(
            "superset.commands.chart.create.get_datasource_by_id",
            return_value=mock_datasource,
        ),
        patch("superset.commands.chart.create.security_manager.raise_for_access"),
        patch(
            "superset.commands.chart.create.CreateChartCommand.populate_owners",
            return_value=[],
        ),
        patch(
            "superset.commands.chart.create.DashboardDAO.find_by_ids",
            return_value=[],
        ),
    ):
        command = CreateChartCommand(
            {
                "slice_name": "test",
                "viz_type": viz_type,
                "datasource_id": 1,
                "datasource_type": "table",
            }
        )
        with pytest.raises(ChartInvalidError) as exc_info:
            command.validate()

    messages = exc_info.value.normalized_messages()
    assert "viz_type" in messages


def test_create_chart_command_allows_modern_viz_type() -> None:
    """CreateChartCommand.validate() must not flag a modern replacement type."""
    from superset.commands.chart.create import CreateChartCommand

    mock_datasource = MagicMock()
    mock_datasource.name = "test_table"

    with (
        patch(
            "superset.commands.chart.create.get_datasource_by_id",
            return_value=mock_datasource,
        ),
        patch("superset.commands.chart.create.security_manager.raise_for_access"),
        patch(
            "superset.commands.chart.create.CreateChartCommand.populate_owners",
            return_value=[],
        ),
        patch(
            "superset.commands.chart.create.DashboardDAO.find_by_ids",
            return_value=[],
        ),
    ):
        command = CreateChartCommand(
            {
                "slice_name": "test",
                "viz_type": "bubble_v2",
                "datasource_id": 1,
                "datasource_type": "table",
            }
        )
        # Should not raise.
        command.validate()


def test_update_chart_command_rejects_legacy_viz_type() -> None:
    """UpdateChartCommand.validate() must reject setting a legacy type."""
    from superset.commands.chart.update import UpdateChartCommand

    mock_chart = MagicMock()
    mock_chart.owners = []

    with (
        patch(
            "superset.commands.chart.update.ChartDAO.find_by_id",
            return_value=mock_chart,
        ),
        patch(
            "superset.commands.chart.update.security_manager.raise_for_ownership"
        ),
        patch(
            "superset.commands.chart.update.UpdateChartCommand.compute_owners",
            return_value=[],
        ),
    ):
        command = UpdateChartCommand(1, {"viz_type": "bubble"})
        with pytest.raises(ChartInvalidError) as exc_info:
            command.validate()

    assert "viz_type" in exc_info.value.normalized_messages()

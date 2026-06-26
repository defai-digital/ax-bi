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
# under the license.
"""Unit tests for the asset search service."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from superset.mcp_service.ai.asset_search import (
    _build_reason,
    _is_certified,
    _score_result,
    search_assets,
)


def test_score_result_name_match() -> None:
    score = _score_result("Sales Dashboard", "Some description", "sales")
    assert score == 1.0


def test_score_result_description_match() -> None:
    score = _score_result("Other Name", "Contains sales data", "sales")
    assert score == 0.5


def test_score_result_both_match() -> None:
    score = _score_result("Sales Data", "Contains sales metrics", "sales")
    assert score == 1.5


def test_score_result_no_match() -> None:
    score = _score_result("Other", "No match here", "sales")
    assert score == 0.0


def test_score_result_case_insensitive() -> None:
    score = _score_result("SALES DASHBOARD", "description", "sales")
    assert score == 1.0


def test_is_certified_true() -> None:
    obj = MagicMock()
    obj.certified_by = "Analytics Team"
    assert _is_certified(obj) is True


def test_is_certified_false() -> None:
    obj = MagicMock()
    obj.certified_by = None
    assert _is_certified(obj) is False


def test_is_certified_empty_string() -> None:
    obj = MagicMock()
    obj.certified_by = ""
    assert _is_certified(obj) is False


def test_build_reason_name_match() -> None:
    reason = _build_reason("Sales Dashboard", "description", "sales")
    assert "name matches" in reason


def test_build_reason_description_match() -> None:
    reason = _build_reason("Other", "Contains sales data", "sales")
    assert "description matches" in reason


def test_build_reason_no_match() -> None:
    reason = _build_reason("Other", "No match", "sales")
    assert reason == "tag/owner match"


def test_search_assets_empty_query() -> None:
    results = search_assets("")
    assert results == []


def test_search_assets_whitespace_query() -> None:
    results = search_assets("   ")
    assert results == []


def test_search_assets_invalid_types() -> None:
    results = search_assets("test", asset_types=["invalid_type"])
    assert results == []


@patch("superset.mcp_service.ai.asset_search._search_datasets")
@patch("superset.mcp_service.ai.asset_search._search_charts")
@patch("superset.mcp_service.ai.asset_search._search_dashboards")
def test_search_assets_calls_correct_types(
    mock_dashboards: MagicMock,
    mock_charts: MagicMock,
    mock_datasets: MagicMock,
) -> None:
    mock_datasets.return_value = []
    mock_charts.return_value = []
    mock_dashboards.return_value = []

    search_assets("test", asset_types=["dataset"])

    mock_datasets.assert_called_once()
    mock_charts.assert_not_called()
    mock_dashboards.assert_not_called()


@patch("superset.mcp_service.ai.asset_search._search_datasets")
@patch("superset.mcp_service.ai.asset_search._search_charts")
@patch("superset.mcp_service.ai.asset_search._search_dashboards")
def test_search_assets_respects_limit(
    mock_dashboards: MagicMock,
    mock_charts: MagicMock,
    mock_datasets: MagicMock,
) -> None:
    from superset.mcp_service.ai.schemas import AssetResult

    # Create more results than the limit
    mock_datasets.return_value = [
        AssetResult(
            asset_type="dataset",
            id=i,
            uuid=f"uuid-{i}",
            name=f"dataset_{i}",
            description="",
            certified=False,
            relevance_score=1.0 - i * 0.1,
            owners=[],
            tags=[],
        )
        for i in range(5)
    ]
    mock_charts.return_value = []
    mock_dashboards.return_value = []

    results = search_assets("test", limit=3)
    assert len(results) == 3


@patch("superset.mcp_service.ai.asset_search._search_datasets")
@patch("superset.mcp_service.ai.asset_search._search_charts")
@patch("superset.mcp_service.ai.asset_search._search_dashboards")
def test_search_assets_sorts_by_relevance(
    mock_dashboards: MagicMock,
    mock_charts: MagicMock,
    mock_datasets: MagicMock,
) -> None:
    from superset.mcp_service.ai.schemas import AssetResult

    mock_datasets.return_value = [
        AssetResult(
            asset_type="dataset",
            id=1,
            uuid="uuid-1",
            name="low_relevance",
            description="",
            certified=False,
            relevance_score=0.5,
            owners=[],
            tags=[],
        ),
        AssetResult(
            asset_type="dataset",
            id=2,
            uuid="uuid-2",
            name="high_relevance",
            description="",
            certified=False,
            relevance_score=1.0,
            owners=[],
            tags=[],
        ),
    ]
    mock_charts.return_value = []
    mock_dashboards.return_value = []

    results = search_assets("test", limit=10)
    assert results[0].relevance_score >= results[1].relevance_score

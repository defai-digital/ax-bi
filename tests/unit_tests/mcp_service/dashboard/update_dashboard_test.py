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
"""Unit tests for the update_dashboard MCP tool schemas."""

from __future__ import annotations

import sys
import types
from collections.abc import Callable
from typing import Any
from unittest.mock import MagicMock

import pytest


# ---------------------------------------------------------------------------
# Decorator passthrough
# ---------------------------------------------------------------------------


def _force_passthrough_decorators() -> dict[str, types.ModuleType]:
    def _passthrough_tool(
        func: Callable[..., Any] | None = None,
        **kwargs: Any,
    ) -> Callable[..., Any]:
        del kwargs
        if func is not None:
            return func
        return lambda f: f

    mock_decorators = MagicMock()
    mock_decorators.tool = _passthrough_tool
    mock_decorators.ToolAnnotations = dict

    saved_modules: dict[str, types.ModuleType] = {}
    for key in ("superset_core.mcp", "superset_core.mcp.decorators"):
        if key in sys.modules:
            saved_modules[key] = sys.modules[key]

    sys.modules["superset_core.mcp"] = MagicMock()
    sys.modules["superset_core.mcp.decorators"] = mock_decorators
    return saved_modules


def _restore_modules(saved_modules: dict[str, types.ModuleType]) -> None:
    for key in list(sys.modules.keys()):
        if key.startswith("superset_core.mcp"):
            del sys.modules[key]
    sys.modules.update(saved_modules)


_saved = _force_passthrough_decorators()
try:
    from superset.mcp_service.dashboard.tool.update_dashboard import (
        UpdateDashboardRequest,
        UpdateDashboardResponse,
    )
finally:
    _restore_modules(_saved)


# ---------------------------------------------------------------------------
# UpdateDashboardRequest schema validation
# ---------------------------------------------------------------------------


class TestUpdateDashboardRequest:
    def test_required_dashboard_id(self) -> None:
        with pytest.raises(Exception):
            UpdateDashboardRequest()  # type: ignore[call-arg]

    def test_valid_minimal_request(self) -> None:
        req = UpdateDashboardRequest(dashboard_id=42)
        assert req.dashboard_id == 42
        assert req.title is None
        assert req.description is None
        assert req.published is None
        assert req.slug is None
        assert req.css is None
        assert req.json_metadata is None

    def test_valid_request_with_title(self) -> None:
        req = UpdateDashboardRequest(dashboard_id=42, title="New Title")
        assert req.dashboard_id == 42
        assert req.title == "New Title"

    def test_all_fields(self) -> None:
        req = UpdateDashboardRequest(
            dashboard_id=1,
            title="T",
            description="D",
            published=True,
            slug="my-dash",
            css=".header { color: red; }",
            json_metadata='{"key": "value"}',
        )
        assert req.dashboard_id == 1
        assert req.title == "T"
        assert req.description == "D"
        assert req.published is True
        assert req.slug == "my-dash"
        assert req.css == ".header { color: red; }"
        assert req.json_metadata == '{"key": "value"}'

    def test_published_false(self) -> None:
        req = UpdateDashboardRequest(dashboard_id=1, published=False)
        assert req.published is False

    def test_serialization(self) -> None:
        req = UpdateDashboardRequest(dashboard_id=1, title="T")
        data = req.model_dump()
        assert data["dashboard_id"] == 1
        assert data["title"] == "T"
        assert data["description"] is None


# ---------------------------------------------------------------------------
# UpdateDashboardResponse schema validation
# ---------------------------------------------------------------------------


class TestUpdateDashboardResponse:
    def test_defaults(self) -> None:
        resp = UpdateDashboardResponse()
        assert resp.dashboard is None
        assert resp.dashboard_url is None
        assert resp.changes_applied == []
        assert resp.error is None

    def test_with_error(self) -> None:
        resp = UpdateDashboardResponse(error="Dashboard not found")
        assert resp.error == "Dashboard not found"
        assert resp.dashboard is None

    def test_with_success(self) -> None:
        resp = UpdateDashboardResponse(
            dashboard={"id": 1, "title": "Updated", "published": True},
            dashboard_url="http://localhost:8088/superset/dashboard/1/",
            changes_applied=["title", "published"],
        )
        assert resp.dashboard is not None
        assert resp.dashboard["title"] == "Updated"
        assert resp.dashboard_url is not None
        assert len(resp.changes_applied) == 2
        assert resp.error is None

    def test_serialization(self) -> None:
        resp = UpdateDashboardResponse(
            dashboard={"id": 42},
            changes_applied=["title"],
        )
        data = resp.model_dump()
        assert data["dashboard"]["id"] == 42
        assert data["changes_applied"] == ["title"]
        assert data["error"] is None

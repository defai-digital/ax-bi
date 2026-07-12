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

"""Unit tests for Excel upload and prompt-to-dashboard MCP helpers."""

import base64
import importlib
import logging
from io import BytesIO
from unittest.mock import MagicMock, Mock, patch

import pytest
from fastmcp import Client
from openpyxl import Workbook

from axbi.mcp_service.app import mcp

upload_file_module = importlib.import_module(
    "axbi.mcp_service.dataset.tool.upload_file"
)

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------


def _make_mock_local_db(db_id: int = 1, name: str = "Local Files") -> MagicMock:
    local_db = MagicMock()
    local_db.id = db_id
    local_db.database_name = name
    return local_db


def _make_mock_dataset(
    dataset_id: int = 99,
    table_name: str = "upload_revenue_abc123",
    database_id: int = 1,
) -> MagicMock:
    dataset = MagicMock()
    dataset.id = dataset_id
    dataset.table_name = table_name
    dataset.schema = None
    dataset.description = None
    dataset.certified_by = None
    dataset.certification_details = None
    dataset.changed_by_name = "admin"
    dataset.changed_on = None
    dataset.changed_on_humanized = None
    dataset.created_by_name = "admin"
    dataset.created_on = None
    dataset.created_on_humanized = None
    dataset.tags = []
    dataset.owners = []
    dataset.is_virtual = False
    dataset.is_favorite = None
    dataset.database_id = database_id
    dataset.schema_perm = "[Local Files]"
    dataset.url = f"/tablemodelview/edit/{dataset_id}"
    dataset.database = MagicMock()
    dataset.database.database_name = "Local Files"
    dataset.sql = None
    dataset.main_dttm_col = None
    dataset.offset = 0
    dataset.cache_timeout = 0
    dataset.params = {}
    dataset.template_params = {}
    dataset.extra = {}
    dataset.uuid = f"dataset-uuid-{dataset_id}"
    col_names = [
        "Type of Service",
        "Cost Center",
        "Service Line Group",
        "Client Profile",
        "Client",
        "Client Code",
        "Revenue Jan.25",
        "Revenue Feb.25",
        "Revenue Mar.25",
        "Revenue Apr.25",
        "Revenue May.25",
        "Revenue Jun.25",
    ]
    dataset.columns = []
    for cn in col_names:
        col = MagicMock()
        col.column_name = cn
        col.verbose_name = cn
        col.type = "VARCHAR" if "Client" in cn or "Service" in cn else "FLOAT"
        col.is_dttm = False
        col.groupby = True
        col.filterable = True
        col.description = None
        dataset.columns.append(col)
    dataset.metrics = []
    return dataset


def _make_minimal_xlsx() -> str:
    """Create a minimal multi-sheet xlsx in memory."""
    wb = Workbook()
    sheets = ["SG", "MY", "HK", "CN", "AU"]
    for index, sheet_name in enumerate(sheets):
        ws = wb.active if index == 0 else wb.create_sheet(sheet_name)
        ws.title = sheet_name
        ws.append(["Client", "Revenue", "Month"])
        ws.append([f"{sheet_name}-CLIENT-01", 50000 + index * 1000, "Jan"])
        ws.append([f"{sheet_name}-CLIENT-02", 30000 + index * 1000, "Feb"])

    buf = BytesIO()
    wb.save(buf)
    return base64.b64encode(buf.getvalue()).decode()


@pytest.fixture(autouse=True)
def mock_auth():
    with patch("axbi.mcp_service.auth.get_user_from_request") as m:
        mock_user = Mock()
        mock_user.id = 1
        mock_user.username = "admin"
        m.return_value = mock_user
        yield m


# -----------------------------------------------------------------------
# Test 1: Excel file metadata discovery (multi-sheet)
# -----------------------------------------------------------------------


class TestExcelMetadataDiscovery:
    """Test that the MCP upload tool properly handles multi-sheet Excel files."""

    def test_excel_metadata_extracts_sheet_names(self) -> None:
        """file_metadata() returns all sheet names from an Excel workbook."""
        from werkzeug.datastructures import FileStorage

        from axbi.commands.database.uploaders.excel_reader import ExcelReader

        file_storage = FileStorage(
            stream=BytesIO(base64.b64decode(_make_minimal_xlsx())),
            filename="revenue.xlsx",
            content_type=(
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            ),
        )

        reader = ExcelReader({"already_exists": "replace"})
        metadata = reader.file_metadata(file_storage)

        logger.info("Excel metadata items: %d", len(metadata.get("items", [])))
        sheet_names = [item.get("sheet_name") for item in metadata["items"]]
        assert sheet_names == ["SG", "MY", "HK", "CN", "AU"]


# -----------------------------------------------------------------------
# Test 2: Upload flow with multi-sheet Excel
# -----------------------------------------------------------------------


class TestMultiSheetUpload:
    """Test upload behavior with multi-sheet Excel files."""

    @patch.object(upload_file_module, "serialize_dataset_object")
    @patch.object(upload_file_module.db, "session")
    @patch.object(upload_file_module, "UploadCommand")
    @patch.object(upload_file_module, "get_or_create_local_db")
    @pytest.mark.asyncio
    async def test_upload_uses_first_sheet_by_default(
        self, mock_local_db_fn, mock_upload_cmd, mock_session, mock_serialize
    ) -> None:
        """Verify that upload defaults to first sheet (index 0)."""
        local_db = _make_mock_local_db()
        mock_local_db_fn.return_value = local_db
        mock_cmd = MagicMock()
        mock_upload_cmd.return_value = mock_cmd
        mock_ds = _make_mock_dataset()
        mock_session.query.return_value.filter_by.return_value.one_or_none.return_value = mock_ds  # noqa: E501
        mock_serialize.return_value = {"id": 99, "table_name": "upload_revenue_abc"}

        excel_b64 = _make_minimal_xlsx()

        async with Client(mcp) as client:
            result = await client.call_tool(
                "upload_file",
                {
                    "request": {
                        "file_content": excel_b64,
                        "filename": "revenue.xlsx",
                    }
                },
            )

        mock_upload_cmd.assert_called_once()
        call_args = mock_upload_cmd.call_args
        reader = call_args[0][4]

        sheet = reader._options.get("sheet_name", 0)
        assert sheet == 0, f"Expected default sheet_name=0, got {sheet}"

        from axbi.utils import json as sj

        data = sj.loads(result.content[0].text)
        assert data.get("sheet_names") == ["SG", "MY", "HK", "CN", "AU"]


# -----------------------------------------------------------------------
# Test 3: prompt_to_dashboard with uploaded dataset
# -----------------------------------------------------------------------


class TestPromptToDashboardPipeline:
    """Test the full pipeline: upload -> plan -> chart -> compose."""

    @pytest.mark.asyncio
    async def test_prompt_to_dashboard_with_pinned_dataset(self) -> None:
        """Test that prompt_to_dashboard can use a pre-uploaded dataset."""
        from axbi.mcp_service.ai.schemas import PromptToDashboardRequest

        async def _mock_plan(*a, **kw):
            return {
                "plan": {
                    "plan_id": "test-plan-123",
                    "title": "Service Revenue Dashboard",
                    "description": "Revenue analysis by client",
                    "datasets": [{"id": 99, "name": "revenue_data"}],
                    "chart_intents": [
                        {
                            "purpose": "Revenue by client",
                            "chart_type": "xy",
                            "dataset_id": 99,
                            "metrics": ["Revenue"],
                            "dimensions": ["Client"],
                        },
                    ],
                    "global_filters": [],
                    "assumptions": [],
                    "clarifying_questions": [],
                    "confidence": 0.7,
                },
                "warnings": [],
            }

        async def _mock_chart(*a, **kw):
            return {
                "chart": {"id": 101, "slice_name": "Revenue by Client"},
                "chart_type_selected": "xy",
                "confidence": 0.8,
                "warnings": [],
            }

        async def _mock_compose(*a, **kw):
            return {
                "dashboard": {"id": 201, "dashboard_title": "Service Revenue"},
                "dashboard_url": "/ax-bi/dashboard/201/",
                "layout_summary": "1 chart",
                "lineage": {"dataset_ids": [99]},
            }

        req = PromptToDashboardRequest(
            prompt="Create a service revenue dashboard",
            dataset_ids=[99],
            max_charts=4,
            draft=True,
        )

        with (
            patch(
                "axbi.mcp_service.auth.tool_feature_flags_enabled",
                return_value=True,
            ),
            patch(
                "axbi.mcp_service.ai.tool.prompt_to_dashboard."
                "user_can_view_data_model_metadata",
                return_value=True,
            ),
            patch(
                "axbi.mcp_service.ai.tool.plan_dashboard.plan_dashboard",
                side_effect=_mock_plan,
            ),
            patch(
                "axbi.mcp_service.ai.tool.create_chart_from_intent."
                "create_chart_from_intent",
                side_effect=_mock_chart,
            ),
            patch(
                "axbi.mcp_service.ai.tool.compose_dashboard.compose_dashboard",
                side_effect=_mock_compose,
            ),
        ):
            async with Client(mcp) as client:
                result = await client.call_tool(
                    "prompt_to_dashboard",
                    {"request": req.model_dump()},
                )

        assert result is not None
        assert result.content is not None
        from axbi.utils import json as sj

        data = sj.loads(result.content[0].text)
        assert data.get("error") is None
        assert data.get("dashboard", {}).get("id") == 201
        assert data.get("charts", [])[0].get("chart_id") == 101

    @pytest.mark.asyncio
    async def test_prompt_to_dashboard_dry_run_returns_previews_without_composing(
        self,
    ) -> None:
        """Dry runs validate chart previews without persisting dashboard artifacts."""
        from axbi.mcp_service.ai.schemas import PromptToDashboardRequest

        async def _mock_plan(*a, **kw):
            return {
                "plan": {
                    "plan_id": "dry-run-plan",
                    "title": "Preview Dashboard",
                    "description": "Preview only",
                    "datasets": [{"id": 99, "name": "revenue_data"}],
                    "chart_intents": [
                        {
                            "purpose": "Revenue by client",
                            "chart_type": "xy",
                            "dataset_id": 99,
                            "metrics": ["Revenue"],
                            "dimensions": ["Client"],
                        },
                    ],
                    "global_filters": [],
                    "assumptions": [],
                    "clarifying_questions": [],
                    "confidence": 0.7,
                },
                "warnings": [],
            }

        async def _mock_preview(*a, **kw):
            return {
                "chart": None,
                "chart_name": "Revenue by Client",
                "chart_type_selected": "xy",
                "preview_url": "/explore/?form_data_key=preview",
                "confidence": 0.8,
                "success": True,
                "warnings": [],
            }

        compose = MagicMock()
        request = PromptToDashboardRequest(
            prompt="Preview a service revenue dashboard",
            dataset_ids=[99],
            dry_run=True,
            save_charts=False,
        )

        with (
            patch(
                "axbi.mcp_service.auth.tool_feature_flags_enabled",
                return_value=True,
            ),
            patch(
                "axbi.mcp_service.ai.tool.prompt_to_dashboard."
                "user_can_view_data_model_metadata",
                return_value=True,
            ),
            patch(
                "axbi.mcp_service.ai.tool.plan_dashboard.plan_dashboard",
                side_effect=_mock_plan,
            ),
            patch(
                "axbi.mcp_service.ai.tool.create_chart_from_intent."
                "create_chart_from_intent",
                side_effect=_mock_preview,
            ),
            patch(
                "axbi.mcp_service.ai.tool.compose_dashboard.compose_dashboard",
                compose,
            ),
        ):
            async with Client(mcp) as client:
                result = await client.call_tool(
                    "prompt_to_dashboard",
                    {"request": request.model_dump()},
                )

        from axbi.utils import json as sj

        data = sj.loads(result.content[0].text)
        assert data.get("error") is None
        assert data.get("dashboard") is None
        assert data.get("charts", [])[0].get("chart_id") is None
        assert "no charts or dashboard were created" in data.get("layout_summary", "")
        compose.assert_not_called()


# -----------------------------------------------------------------------
# Test 4: plan_dashboard sparse metadata
# -----------------------------------------------------------------------


class TestPlanDashboardSparseMetadata:
    """Test plan_dashboard behavior when dataset metadata is sparse."""

    @patch("axbi.mcp_service.ai.tool.plan_dashboard._discover_datasets")
    @pytest.mark.asyncio
    async def test_plan_handles_sparse_dataset_metadata(self, mock_discover) -> None:
        """plan_dashboard returns a bounded plan for sparse dataset metadata."""
        from axbi.mcp_service.ai.schemas import DashboardPlanRequest

        mock_discover.return_value = [
            {"id": 99, "name": "revenue_data", "description": "", "certified": False},
        ]

        req = DashboardPlanRequest(
            prompt="Create a revenue dashboard by client and service type",
            dataset_candidates=[99],
            constraints={"max_charts": 4},
        )

        with (
            patch(
                "axbi.mcp_service.auth.tool_feature_flags_enabled",
                return_value=True,
            ),
            patch(
                "axbi.mcp_service.ai.tool.plan_dashboard."
                "user_can_view_data_model_metadata",
                return_value=True,
            ),
        ):
            async with Client(mcp) as client:
                result = await client.call_tool(
                    "plan_dashboard",
                    {"request": req.model_dump()},
                )

        from axbi.utils import json as sj

        data = sj.loads(result.content[0].text)
        plan_data = data.get("plan", {})
        chart_intents = plan_data.get("chart_intents", [])

        assert data.get("error") is None
        assert plan_data.get("datasets")
        assert isinstance(chart_intents, list)
        assert len(chart_intents) <= 4


# -----------------------------------------------------------------------
# Test 5: Heuristic with real revenue columns
# -----------------------------------------------------------------------


class TestHeuristicWithRevenueColumns:
    """Verify the heuristic produces meaningful chart intents when
    given the actual revenue dataset columns (wide-format with many
    numeric columns like 'Revenue Jan.25', 'Revenue Feb.25', etc.)."""

    def _revenue_columns(self) -> list[dict[str, str | bool]]:
        """Simulate columns from the real Excel file."""
        from axbi.mcp_service.ai.tool.plan_dashboard import (
            _extract_columns,
        )

        mock_ds = MagicMock()
        mock_ds.columns = []
        col_defs = [
            ("Type of Service", "VARCHAR", False, False),
            ("Cost Center", "VARCHAR", False, False),
            ("Service Line Group", "VARCHAR", False, False),
            ("Client Profile", "VARCHAR", False, False),
            ("Client", "VARCHAR", False, False),
            ("Client Code", "VARCHAR", False, False),
            ("Revenue Jan.25", "FLOAT", True, False),
            ("Revenue Feb.25", "FLOAT", True, False),
            ("Revenue Mar.25", "FLOAT", True, False),
            ("Revenue Apr.25", "FLOAT", True, False),
            ("Revenue May.25", "FLOAT", True, False),
            ("Revenue Jun.25", "FLOAT", True, False),
        ]
        for name, ctype, _is_num, is_dttm in col_defs:
            col = MagicMock()
            col.column_name = name
            col.type = ctype
            col.is_dttm = is_dttm
            mock_ds.columns.append(col)
        return _extract_columns(mock_ds)

    def test_detect_by_dimension_maps_client_keyword(self) -> None:
        """'by client' in prompt should resolve to 'Client' column."""
        from axbi.mcp_service.ai.tool.plan_dashboard import (
            _detect_by_dimension,
        )

        category_cols = [
            "Type of Service",
            "Cost Center",
            "Service Line Group",
            "Client Profile",
            "Client",
            "Client Code",
        ]
        result = _detect_by_dimension("revenue by client", category_cols)
        assert result == "Client", f"Expected 'Client', got '{result}'"

    def test_detect_by_dimension_maps_service_type(self) -> None:
        """'by service type' should resolve to 'Type of Service'."""
        from axbi.mcp_service.ai.tool.plan_dashboard import (
            _detect_by_dimension,
        )

        category_cols = [
            "Type of Service",
            "Cost Center",
            "Service Line Group",
            "Client",
        ]
        result = _detect_by_dimension("revenue by service type", category_cols)
        assert result == "Type of Service", (
            f"Expected 'Type of Service', got '{result}'"
        )

    def test_heuristic_revenue_by_client(self) -> None:
        """'revenue by client' prompt should produce bar chart with
        Client dimension and revenue metrics."""
        from axbi.mcp_service.ai.tool.plan_dashboard import (
            _build_chart_intents_heuristic,
        )

        columns = self._revenue_columns()
        datasets = [
            {
                "id": 99,
                "name": "service_revenue_2025",
                "description": "Service revenue by client",
                "certified": False,
                "columns": columns,
            }
        ]
        intents = _build_chart_intents_heuristic(
            "Create a revenue dashboard by client and monthly trends "
            "with breakdown by service type",
            datasets,
            max_charts=6,
        )

        assert len(intents) >= 2, f"Expected at least 2 intents, got {len(intents)}"

        # Find the "by client" intent
        by_client = [i for i in intents if "Client" in (i.dimensions or [])]
        assert by_client, (
            "No intent has 'Client' as a dimension. "
            f"Got dimensions: {[i.dimensions for i in intents]}"
        )

        # All intents should have metrics (no empty metrics)
        for i in intents:
            assert i.metrics, (
                f"Intent '{i.purpose}' has empty metrics. "
                f"Type={i.chart_type}, dims={i.dimensions}"
            )

        logger.info(
            "Heuristic produced %d intents with revenue columns",
            len(intents),
        )
        for i in intents:
            logger.info(
                "  %s [%s]: metrics=%s, dims=%s",
                i.purpose,
                i.chart_type,
                i.metrics,
                i.dimensions,
            )

    def test_heuristic_wide_format_trend(self) -> None:
        """For wide-format data (many numeric cols, no datetime col),
        the 'monthly' pattern should use all numeric columns as
        separate series."""
        from axbi.mcp_service.ai.tool.plan_dashboard import (
            _build_chart_intents_heuristic,
        )

        columns = self._revenue_columns()
        datasets = [
            {
                "id": 99,
                "name": "service_revenue_2025",
                "description": "",
                "certified": False,
                "columns": columns,
            }
        ]
        intents = _build_chart_intents_heuristic(
            "Show monthly revenue trends",
            datasets,
            max_charts=4,
        )

        trend_intents = [i for i in intents if "trend" in i.purpose.lower()]
        assert trend_intents, "No trend intent found"
        trend = trend_intents[0]
        # Wide-format: should use all 6 revenue columns as metrics
        assert len(trend.metrics) >= 3, (
            f"Expected >= 3 metrics for wide-format, got {trend.metrics}"
        )
        logger.info(
            "Wide-format trend intent: metrics=%s, dims=%s",
            trend.metrics,
            trend.dimensions,
        )


# -----------------------------------------------------------------------
# Test 6: upload_and_plan convenience tool
# -----------------------------------------------------------------------


class TestUploadAndPlanTool:
    """Verify the upload_and_plan convenience tool chains upload + plan."""

    @pytest.mark.asyncio
    async def test_upload_and_plan_returns_plan(self) -> None:
        """upload_and_plan should upload a file and return a plan."""
        from axbi.mcp_service.ai.tool.upload_and_plan import (
            UploadAndPlanRequest,
        )

        excel_b64 = _make_minimal_xlsx()

        req = UploadAndPlanRequest(
            file_content=excel_b64,
            filename="revenue.xlsx",
            prompt="Create a revenue dashboard by client",
            max_charts=4,
        )

        with (
            patch(
                "axbi.mcp_service.auth.tool_feature_flags_enabled",
                return_value=True,
            ),
            patch(
                "axbi.mcp_service.ai.tool.upload_and_plan."
                "user_can_view_data_model_metadata",
                return_value=True,
            ),
            patch(
                "axbi.mcp_service.ai.tool.upload_and_plan.mcp_event_log_context",
            ),
            patch(
                "axbi.mcp_service.dataset.tool.upload_file.upload_single_file",
            ) as mock_upload,
            patch(
                "axbi.mcp_service.ai.tool.plan_dashboard._discover_datasets",
            ) as mock_discover,
            patch(
                "axbi.mcp_service.ai.tool.plan_dashboard._plan_with_llm",
            ) as mock_plan,
        ):
            # Mock upload success
            from axbi.mcp_service.dataset.schemas import (
                DatasetInfo,
                TableColumnInfo,
            )

            mock_upload.return_value = DatasetInfo(
                id=99,
                table_name="upload_revenue_abc",
                columns=[
                    TableColumnInfo(column_name="Client", type="VARCHAR"),
                    TableColumnInfo(column_name="Revenue", type="FLOAT"),
                    TableColumnInfo(column_name="Month", type="VARCHAR"),
                ],
                sheet_names=["SG", "MY", "HK"],
            )

            # Mock discover
            mock_discover.return_value = [
                {
                    "id": 99,
                    "name": "upload_revenue_abc",
                    "description": "",
                    "certified": False,
                    "columns": [
                        {
                            "name": "Client",
                            "type": "VARCHAR",
                            "is_numeric": False,
                            "is_dttm": False,
                        },
                        {
                            "name": "Revenue",
                            "type": "FLOAT",
                            "is_numeric": True,
                            "is_dttm": False,
                        },
                    ],
                }
            ]

            # Mock LLM failure -> heuristic fallback
            mock_plan.return_value = None

            async with Client(mcp) as client:
                result = await client.call_tool(
                    "upload_and_plan",
                    {"request": req.model_dump()},
                )

        from axbi.utils import json as sj

        data = sj.loads(result.content[0].text)
        assert "dataset" in data
        assert data["dataset"].get("id") == 99
        assert "plan" in data
        plan_data = data.get("plan", {})
        assert plan_data.get("chart_intents"), "Plan should have chart intents"
        logger.info("upload_and_plan response keys: %s", list(data.keys()))
        logger.info(
            "Plan: %d chart intents",
            len(plan_data.get("chart_intents", [])),
        )

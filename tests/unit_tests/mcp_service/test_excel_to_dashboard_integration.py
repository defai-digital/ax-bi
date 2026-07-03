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
Integration test: upload Excel file -> prompt_to_dashboard pipeline.

Exercises the full MCP AI pipeline with a real multi-sheet Excel file
(CODED_Service Revenue by Client) to identify gaps and improvement
opportunities in the MCP service.
"""

import base64
import importlib
import logging
from io import BytesIO
from unittest.mock import MagicMock, Mock, patch

import pytest
from fastmcp import Client
from openpyxl import Workbook

from superset.mcp_service.app import mcp

upload_file_module = importlib.import_module(
    "superset.mcp_service.dataset.tool.upload_file"
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

EXCEL_PATH = (
    "/Users/akiralam/Downloads/"
    "CODED_Service Revenue by Client (LCY)_2025_Top20.xlsx"
)


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
        "Type of Service", "Cost Center", "Service Line Group",
        "Client Profile", "Client", "Client Code",
        "Revenue Jan.25", "Revenue Feb.25", "Revenue Mar.25",
        "Revenue Apr.25", "Revenue May.25", "Revenue Jun.25",
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
    ws1 = wb.active
    ws1.title = "SG"
    ws1.append(["Client", "Revenue", "Month"])
    ws1.append(["SG-CLIENT-01", 50000, "Jan"])
    ws1.append(["SG-CLIENT-02", 30000, "Feb"])

    ws2 = wb.create_sheet("MY")
    ws2.append(["Client", "Revenue", "Month"])
    ws2.append(["MY-CLIENT-01", 40000, "Jan"])

    ws3 = wb.create_sheet("HK")
    ws3.append(["Client", "Revenue", "Month"])
    ws3.append(["HK-CLIENT-01", 60000, "Jan"])

    buf = BytesIO()
    wb.save(buf)
    return base64.b64encode(buf.getvalue()).decode()


@pytest.fixture(autouse=True)
def mock_auth():
    with patch("superset.mcp_service.auth.get_user_from_request") as m:
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
        """GAP TEST: file_metadata() returns sheet names, but the MCP
        upload_file tool does NOT expose them in its response."""
        from werkzeug.datastructures import FileStorage

        from superset.commands.database.uploaders.excel_reader import ExcelReader

        with open(EXCEL_PATH, "rb") as f:
            file_bytes = f.read()

        file_storage = FileStorage(
            stream=BytesIO(file_bytes),
            filename="revenue.xlsx",
            content_type=(
                "application/vnd.openxmlformats-officedocument"
                ".spreadsheetml.sheet"
            ),
        )

        reader = ExcelReader({"already_exists": "replace"})
        metadata = reader.file_metadata(file_storage)

        logger.info("Excel metadata items: %d", len(metadata.get("items", [])))
        for item in metadata.get("items", []):
            cols = [c.get("column_name", "") for c in item.get("columns", [])]
            logger.info("  Sheet: %s, columns: %s", item.get("name", ""), cols)

        assert len(metadata["items"]) == 5, (
            "Expected 5 sheets (SG, MY, HK, CN, AU)"
        )
        logger.warning(
            "GAP: upload_file does not return sheet_names metadata. "
            "MCP clients cannot discover what sheets are available."
        )

    def test_upload_request_missing_fields(self) -> None:
        """GAP TEST: Document fields missing from UploadFileRequest."""
        from superset.mcp_service.dataset.schemas import UploadFileRequest

        fields = UploadFileRequest.model_fields
        gaps = []

        if "sheet_name" not in fields:
            gaps.append("sheet_name: cannot select which sheet to upload")
        if "header_row" not in fields:
            gaps.append("header_row: cannot specify which row is the header")
        if "skip_rows" not in fields:
            gaps.append("skip_rows: cannot skip preamble rows")
        if "column_data_types" not in fields:
            gaps.append(
                "column_data_types: cannot specify column types"
            )

        logger.info("UploadFileRequest gaps found: %d", len(gaps))
        for g in gaps:
            logger.warning("  SCHEMA GAP: %s", g)

        assert len(gaps) >= 3, f"Expected 3+ schema gaps, found {len(gaps)}"


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
        mock_serialize.return_value = {
            "id": 99, "table_name": "upload_revenue_abc"
        }

        excel_b64 = _make_minimal_xlsx()

        async with Client(mcp) as client:
            await client.call_tool(
                "upload_file",
                {"request": {
                    "file_content": excel_b64,
                    "filename": "revenue.xlsx",
                }},
            )

        mock_upload_cmd.assert_called_once()
        call_args = mock_upload_cmd.call_args
        reader = call_args[0][4]

        sheet = reader._options.get("sheet_name", 0)
        assert sheet == 0, f"Expected default sheet_name=0, got {sheet}"

        logger.warning(
            "GAP: upload_file silently uploads only the first sheet. "
            "For a 5-sheet Excel (SG, MY, HK, CN, AU), only SG data "
            "is loaded. User has no control."
        )


# -----------------------------------------------------------------------
# Test 3: prompt_to_dashboard with uploaded dataset
# -----------------------------------------------------------------------


class TestPromptToDashboardPipeline:
    """Test the full pipeline: upload -> plan -> chart -> compose."""

    @pytest.mark.asyncio
    async def test_prompt_to_dashboard_with_pinned_dataset(self) -> None:
        """Test that prompt_to_dashboard can use a pre-uploaded dataset."""
        from superset.mcp_service.ai.schemas import PromptToDashboardRequest

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
                "dashboard_url": "/superset/dashboard/201/",
                "layout_summary": "1 chart",
                "lineage": {"dataset_ids": [99]},
            }

        req = PromptToDashboardRequest(
            prompt="Create a service revenue dashboard",
            dataset_ids=[99],
            max_charts=4,
            draft=True,
        )

        with patch(
            "superset.mcp_service.ai.tool.prompt_to_dashboard."
            "user_can_view_data_model_metadata",
            return_value=True,
        ), patch(
            "superset.mcp_service.ai.tool.plan_dashboard.plan_dashboard",
            side_effect=_mock_plan,
        ), patch(
            "superset.mcp_service.ai.tool.create_chart_from_intent."
            "create_chart_from_intent",
            side_effect=_mock_chart,
        ), patch(
            "superset.mcp_service.ai.tool.compose_dashboard."
            "compose_dashboard",
            side_effect=_mock_compose,
        ):
            async with Client(mcp) as client:
                result = await client.call_tool(
                    "prompt_to_dashboard",
                    {"request": req.model_dump()},
                )

        assert result is not None
        assert result.content is not None
        from superset.utils import json as sj
        data = sj.loads(result.content[0].text)
        logger.info("prompt_to_dashboard keys: %s", list(data.keys()))
        if data.get("error"):
            logger.warning("Pipeline error: %s", data["error"])
        for w in data.get("warnings", []):
            logger.warning("Pipeline warning: %s", w)


# -----------------------------------------------------------------------
# Test 4: plan_dashboard column-awareness
# -----------------------------------------------------------------------


class TestPlanDashboardColumnAwareness:
    """Test whether plan_dashboard uses column metadata."""

    @patch("superset.mcp_service.ai.tool.plan_dashboard._discover_datasets")
    @pytest.mark.asyncio
    async def test_plan_does_not_fetch_column_metadata(
        self, mock_discover
    ) -> None:
        """GAP TEST: plan_dashboard discovers datasets but does NOT
        fetch their column metadata."""
        from superset.mcp_service.ai.schemas import DashboardPlanRequest

        mock_discover.return_value = [
            {"id": 99, "name": "revenue_data", "description": "", "certified": False},
        ]

        req = DashboardPlanRequest(
            prompt="Create a revenue dashboard by client and service type",
            dataset_candidates=[99],
            constraints={"max_charts": 4},
        )

        with patch(
            "superset.mcp_service.ai.tool.plan_dashboard."
            "user_can_view_data_model_metadata",
            return_value=True,
        ):
            async with Client(mcp) as client:
                result = await client.call_tool(
                    "plan_dashboard",
                    {"request": req.model_dump()},
                )

        from superset.utils import json as sj
        data = sj.loads(result.content[0].text)
        plan_data = data.get("plan", {})
        chart_intents = plan_data.get("chart_intents", [])

        logger.info("Plan produced %d chart intents", len(chart_intents))
        for ci in chart_intents:
            m = ci.get("metrics", []) if isinstance(ci, dict) else ci.metrics
            d = ci.get("dimensions", []) if isinstance(ci, dict) else ci.dimensions
            p = ci.get("purpose", "") if isinstance(ci, dict) else ci.purpose
            logger.info("  Intent: %s, metrics=%s, dimensions=%s", p, m, d)

        has_empty_metrics = all(
            not (ci.get("metrics", []) if isinstance(ci, dict) else ci.metrics)
            for ci in chart_intents
        )
        if has_empty_metrics:
            logger.warning(
                "GAP: plan_dashboard produces chart intents with EMPTY "
                "metrics/dimensions. It should fetch column metadata."
            )


# -----------------------------------------------------------------------
# Test 5: Heuristic with real revenue columns
# -----------------------------------------------------------------------


class TestHeuristicWithRevenueColumns:
    """Verify the heuristic produces meaningful chart intents when
    given the actual revenue dataset columns (wide-format with many
    numeric columns like 'Revenue Jan.25', 'Revenue Feb.25', etc.)."""

    def _revenue_columns(self) -> list[dict[str, str | bool]]:
        """Simulate columns from the real Excel file."""
        from superset.mcp_service.ai.tool.plan_dashboard import (
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
        from superset.mcp_service.ai.tool.plan_dashboard import (
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
        result = _detect_by_dimension(
            "revenue by client", category_cols
        )
        assert result == "Client", (
            f"Expected 'Client', got '{result}'"
        )

    def test_detect_by_dimension_maps_service_type(self) -> None:
        """'by service type' should resolve to 'Type of Service'."""
        from superset.mcp_service.ai.tool.plan_dashboard import (
            _detect_by_dimension,
        )

        category_cols = [
            "Type of Service",
            "Cost Center",
            "Service Line Group",
            "Client",
        ]
        result = _detect_by_dimension(
            "revenue by service type", category_cols
        )
        assert result == "Type of Service", (
            f"Expected 'Type of Service', got '{result}'"
        )

    def test_heuristic_revenue_by_client(self) -> None:
        """'revenue by client' prompt should produce bar chart with
        Client dimension and revenue metrics."""
        from superset.mcp_service.ai.tool.plan_dashboard import (
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

        assert len(intents) >= 2, (
            f"Expected at least 2 intents, got {len(intents)}"
        )

        # Find the "by client" intent
        by_client = [
            i for i in intents
            if "Client" in (i.dimensions or [])
        ]
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
        from superset.mcp_service.ai.tool.plan_dashboard import (
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

        trend_intents = [
            i for i in intents if "trend" in i.purpose.lower()
        ]
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
        from superset.mcp_service.ai.tool.upload_and_plan import (
            UploadAndPlanRequest,
        )

        excel_b64 = _make_minimal_xlsx()

        req = UploadAndPlanRequest(
            file_content=excel_b64,
            filename="revenue.xlsx",
            prompt="Create a revenue dashboard by client",
            max_charts=4,
        )

        with patch(
            "superset.mcp_service.ai.tool.upload_and_plan."
            "user_can_view_data_model_metadata",
            return_value=True,
        ), patch(
            "superset.mcp_service.ai.tool.upload_and_plan."
            "mcp_event_log_context",
        ), patch(
            "superset.mcp_service.dataset.tool.upload_file."
            "upload_single_file",
        ) as mock_upload, patch(
            "superset.mcp_service.ai.tool.plan_dashboard."
            "_discover_datasets",
        ) as mock_discover, patch(
            "superset.mcp_service.ai.tool.plan_dashboard."
            "_plan_with_llm",
        ) as mock_plan:
            # Mock upload success
            from superset.mcp_service.dataset.schemas import (
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

        from superset.utils import json as sj

        data = sj.loads(result.content[0].text)
        assert "dataset" in data
        assert data["dataset"].get("id") == 99
        assert "plan" in data
        plan_data = data.get("plan", {})
        assert plan_data.get("chart_intents"), (
            "Plan should have chart intents"
        )
        logger.info("upload_and_plan response keys: %s", list(data.keys()))
        logger.info(
            "Plan: %d chart intents",
            len(plan_data.get("chart_intents", [])),
        )

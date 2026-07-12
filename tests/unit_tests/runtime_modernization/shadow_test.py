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
import pytest

from axbi.runtime_modernization.shadow import (
    execute_with_shadow,
    ShadowMismatchReport,
)
from tests.unit_tests.runtime_modernization.testing import RecordingStatsLogger


def test_execute_with_shadow_returns_authoritative_result_when_disabled() -> None:
    """Disabled shadow execution does not run the candidate path."""

    stats_logger = RecordingStatsLogger()
    candidate_called = False

    def candidate() -> str:
        nonlocal candidate_called
        candidate_called = True
        return "candidate"

    result = execute_with_shadow(
        area="mcp_orchestration",
        operation="plan_dashboard",
        authoritative=lambda: "authoritative",
        candidate=candidate,
        compare=lambda authoritative, candidate_result: authoritative
        == candidate_result,
        stats_logger=stats_logger,
        shadow_enabled=False,
    )

    assert result == "authoritative"
    assert candidate_called is False
    assert stats_logger.increments == [
        "runtime_modernization.mcp_orchestration.plan_dashboard.shadow_disabled"
    ]


def test_execute_with_shadow_records_match() -> None:
    """Matching candidate output records a shadow match."""

    stats_logger = RecordingStatsLogger()

    result = execute_with_shadow(
        area="mcp_orchestration",
        operation="plan_dashboard",
        authoritative=lambda: {"value": 1},
        candidate=lambda: {"value": 1},
        compare=lambda authoritative, candidate: authoritative == candidate,
        stats_logger=stats_logger,
        shadow_enabled=True,
    )

    assert result == {"value": 1}
    assert stats_logger.increments == [
        "runtime_modernization.mcp_orchestration.plan_dashboard.shadow_match"
    ]


def test_execute_with_shadow_records_mismatch() -> None:
    """Different candidate output records a shadow mismatch."""

    stats_logger = RecordingStatsLogger()
    reports: list[ShadowMismatchReport] = []

    result = execute_with_shadow(
        area="mcp_orchestration",
        operation="plan_dashboard",
        authoritative=lambda: {"value": 1},
        candidate=lambda: {"value": 2},
        compare=lambda authoritative, candidate: authoritative == candidate,
        stats_logger=stats_logger,
        shadow_enabled=True,
        report_mismatch=reports.append,
        summarize_authoritative=lambda value: {"value": value["value"]},
        summarize_candidate=lambda value: {"value": value["value"]},
    )

    assert result == {"value": 1}
    assert stats_logger.increments == [
        "runtime_modernization.mcp_orchestration.plan_dashboard.shadow_mismatch"
    ]
    assert [report.to_dict() for report in reports] == [
        {
            "area": "mcp_orchestration",
            "operation": "plan_dashboard",
            "reason": "comparison_failed",
            "authoritative": {"value": 1},
            "candidate": {"value": 2},
        }
    ]


def test_execute_with_shadow_mismatch_report_survives_summary_error() -> None:
    """Summary failures do not affect authoritative output."""

    stats_logger = RecordingStatsLogger()
    reports: list[ShadowMismatchReport] = []

    def summarize(value: dict[str, int]) -> dict[str, int]:
        raise RuntimeError("summary failed")

    result = execute_with_shadow(
        area="mcp_orchestration",
        operation="plan_dashboard",
        authoritative=lambda: {"value": 1},
        candidate=lambda: {"value": 2},
        compare=lambda authoritative, candidate: authoritative == candidate,
        stats_logger=stats_logger,
        shadow_enabled=True,
        report_mismatch=reports.append,
        summarize_authoritative=summarize,
        summarize_candidate=summarize,
    )

    assert result == {"value": 1}
    assert [report.to_dict() for report in reports] == [
        {
            "area": "mcp_orchestration",
            "operation": "plan_dashboard",
            "reason": "comparison_failed",
            "authoritative": {"summary_error": "RuntimeError"},
            "candidate": {"summary_error": "RuntimeError"},
        }
    ]


def test_execute_with_shadow_swallows_candidate_error() -> None:
    """Candidate failures do not affect authoritative output."""

    stats_logger = RecordingStatsLogger()

    def candidate() -> str:
        raise RuntimeError("candidate failed")

    result = execute_with_shadow(
        area="mcp_orchestration",
        operation="plan_dashboard",
        authoritative=lambda: "authoritative",
        candidate=candidate,
        compare=lambda authoritative, candidate_result: authoritative
        == candidate_result,
        stats_logger=stats_logger,
        shadow_enabled=True,
    )

    assert result == "authoritative"
    assert stats_logger.increments == [
        "runtime_modernization.mcp_orchestration.plan_dashboard.shadow_candidate_error"
    ]


def test_execute_with_shadow_swallows_compare_error() -> None:
    """Comparison failures do not affect authoritative output."""

    stats_logger = RecordingStatsLogger()

    def compare(authoritative: str, candidate: str) -> bool:
        raise RuntimeError("compare failed")

    result = execute_with_shadow(
        area="mcp_orchestration",
        operation="plan_dashboard",
        authoritative=lambda: "authoritative",
        candidate=lambda: "candidate",
        compare=compare,
        stats_logger=stats_logger,
        shadow_enabled=True,
    )

    assert result == "authoritative"
    assert stats_logger.increments == [
        "runtime_modernization.mcp_orchestration.plan_dashboard.shadow_compare_error"
    ]


def test_execute_with_shadow_propagates_authoritative_error() -> None:
    """Authoritative failures are not hidden by shadow execution."""

    stats_logger = RecordingStatsLogger()
    candidate_called = False

    def authoritative() -> str:
        raise RuntimeError("authoritative failed")

    def candidate() -> str:
        nonlocal candidate_called
        candidate_called = True
        return "candidate"

    with pytest.raises(RuntimeError, match="authoritative failed"):
        execute_with_shadow(
            area="mcp_orchestration",
            operation="plan_dashboard",
            authoritative=authoritative,
            candidate=candidate,
            compare=lambda authoritative_result, candidate_result: (
                authoritative_result == candidate_result
            ),
            stats_logger=stats_logger,
            shadow_enabled=True,
        )

    assert candidate_called is False
    assert stats_logger.increments == []

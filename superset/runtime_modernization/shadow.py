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
"""Shadow execution helpers for runtime modernization candidates."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any, TypeVar

from superset.runtime_modernization.measurement import runtime_metric_key
from superset.stats_logger import BaseStatsLogger

AuthoritativeResult = TypeVar("AuthoritativeResult")
CandidateResult = TypeVar("CandidateResult")
ShadowSummary = Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class ShadowMismatchReport:
    """Compact report for a shadow-execution mismatch."""

    area: str
    operation: str
    reason: str
    authoritative_summary: ShadowSummary
    candidate_summary: ShadowSummary

    def to_dict(self) -> dict[str, Any]:
        """Serialize the report for structured logs or artifacts."""

        return {
            "area": self.area,
            "operation": self.operation,
            "reason": self.reason,
            "authoritative": dict(self.authoritative_summary),
            "candidate": dict(self.candidate_summary),
        }


def _safe_summary(
    summarize: Callable[[Any], ShadowSummary] | None,
    value: Any,
) -> ShadowSummary:
    """Build a bounded shadow report summary without raising."""

    if summarize is None:
        return {"type": type(value).__name__}

    try:
        return summarize(value)
    except Exception as ex:  # pylint: disable=broad-except
        return {"summary_error": type(ex).__name__}


def execute_with_shadow(
    *,
    area: str,
    operation: str,
    authoritative: Callable[[], AuthoritativeResult],
    candidate: Callable[[], CandidateResult],
    compare: Callable[[AuthoritativeResult, CandidateResult], bool],
    stats_logger: BaseStatsLogger,
    shadow_enabled: bool,
    report_mismatch: Callable[[ShadowMismatchReport], None] | None = None,
    summarize_authoritative: Callable[[AuthoritativeResult], ShadowSummary]
    | None = None,
    summarize_candidate: Callable[[CandidateResult], ShadowSummary] | None = None,
) -> AuthoritativeResult:
    """Return authoritative output while optionally comparing a candidate path."""

    authoritative_result = authoritative()

    if not shadow_enabled:
        stats_logger.incr(runtime_metric_key(area, operation, "shadow_disabled"))
        return authoritative_result

    try:
        candidate_result = candidate()
    except Exception:  # pylint: disable=broad-except
        stats_logger.incr(runtime_metric_key(area, operation, "shadow_candidate_error"))
        return authoritative_result

    try:
        matched = compare(authoritative_result, candidate_result)
    except Exception:  # pylint: disable=broad-except
        stats_logger.incr(runtime_metric_key(area, operation, "shadow_compare_error"))
        return authoritative_result

    metric = "shadow_match" if matched else "shadow_mismatch"
    stats_logger.incr(runtime_metric_key(area, operation, metric))

    if not matched and report_mismatch is not None:
        report_mismatch(
            ShadowMismatchReport(
                area=area,
                operation=operation,
                reason="comparison_failed",
                authoritative_summary=_safe_summary(
                    summarize_authoritative,
                    authoritative_result,
                ),
                candidate_summary=_safe_summary(
                    summarize_candidate,
                    candidate_result,
                ),
            )
        )

    return authoritative_result

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
from __future__ import annotations

import pytest

from superset.runtime_modernization.measurement import (
    measure_runtime_candidate,
    runtime_metric_key,
)
from tests.unit_tests.runtime_modernization.testing import RecordingStatsLogger


def test_runtime_metric_key_uses_inventory_area() -> None:
    """Metric keys are scoped to a known runtime inventory area."""

    key = runtime_metric_key("mcp_orchestration", "plan_dashboard", "duration")

    assert key == "runtime_modernization.mcp_orchestration.plan_dashboard.duration"


def test_runtime_metric_key_rejects_unknown_area() -> None:
    """Unknown areas are rejected before metrics are emitted."""

    with pytest.raises(KeyError, match="Unknown runtime modernization area"):
        runtime_metric_key("missing", "operation", "duration")


def test_runtime_metric_key_rejects_unbounded_metric_parts() -> None:
    """Operation and metric names stay bounded for stats backends."""

    with pytest.raises(ValueError, match="operation must match"):
        runtime_metric_key("mcp_orchestration", "bad.value", "duration")


def test_measure_runtime_candidate_records_success_metrics() -> None:
    """Successful operations emit success, duration, and payload metrics."""

    stats_logger = RecordingStatsLogger()

    with measure_runtime_candidate(
        "mcp_orchestration",
        "plan_dashboard",
        stats_logger,
        payload_bytes=512,
    ):
        pass

    assert stats_logger.increments == [
        "runtime_modernization.mcp_orchestration.plan_dashboard.success"
    ]
    assert stats_logger.gauges == [
        (
            "runtime_modernization.mcp_orchestration.plan_dashboard.payload_bytes",
            512,
        )
    ]
    assert stats_logger.timings[0][0] == (
        "runtime_modernization.mcp_orchestration.plan_dashboard.duration"
    )
    assert stats_logger.timings[0][1] >= 0


def test_measure_runtime_candidate_records_error_metrics() -> None:
    """Failing operations emit error and duration metrics before reraising."""

    stats_logger = RecordingStatsLogger()

    with pytest.raises(RuntimeError, match="failed"):
        with measure_runtime_candidate(
            "mcp_orchestration",
            "plan_dashboard",
            stats_logger,
        ):
            raise RuntimeError("failed")

    assert stats_logger.increments == [
        "runtime_modernization.mcp_orchestration.plan_dashboard.error"
    ]
    assert stats_logger.timings[0][0] == (
        "runtime_modernization.mcp_orchestration.plan_dashboard.duration"
    )


def test_measure_runtime_candidate_rejects_negative_payload_size() -> None:
    """Payload gauges must be non-negative."""

    stats_logger = RecordingStatsLogger()

    with pytest.raises(ValueError, match="payload_bytes must be non-negative"):
        with measure_runtime_candidate(
            "mcp_orchestration",
            "plan_dashboard",
            stats_logger,
            payload_bytes=-1,
        ):
            pass

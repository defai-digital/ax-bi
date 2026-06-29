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
"""Measurement helpers for runtime modernization candidates."""

from __future__ import annotations

import re
from collections.abc import Iterator
from contextlib import contextmanager
from timeit import default_timer

from superset.runtime_modernization.inventory import get_inventory_item
from superset.stats_logger import BaseStatsLogger

METRIC_PREFIX = "runtime_modernization"
_METRIC_PART_RE = re.compile(r"^[a-z][a-z0-9_]*$")


def runtime_metric_key(area: str, operation: str, metric: str) -> str:
    """Build a bounded stats key for runtime modernization metrics."""

    get_inventory_item(area)
    for value, label in ((operation, "operation"), (metric, "metric")):
        if not _METRIC_PART_RE.fullmatch(value):
            raise ValueError(
                f"Runtime modernization {label} must match {_METRIC_PART_RE.pattern}"
            )

    return f"{METRIC_PREFIX}.{area}.{operation}.{metric}"


@contextmanager
def measure_runtime_candidate(
    area: str,
    operation: str,
    stats_logger: BaseStatsLogger,
    *,
    payload_bytes: int | None = None,
) -> Iterator[float]:
    """Measure a runtime modernization candidate operation.

    The Python path remains authoritative. This helper records baseline data
    that can later be compared with TypeScript or Rust candidate paths.
    """

    if payload_bytes is not None and payload_bytes < 0:
        raise ValueError("payload_bytes must be non-negative")

    duration_key = runtime_metric_key(area, operation, "duration")
    success_key = runtime_metric_key(area, operation, "success")
    error_key = runtime_metric_key(area, operation, "error")
    payload_key = runtime_metric_key(area, operation, "payload_bytes")
    start = default_timer()

    if payload_bytes is not None:
        stats_logger.gauge(payload_key, payload_bytes)

    try:
        yield start
    except Exception:
        stats_logger.incr(error_key)
        raise
    else:
        stats_logger.incr(success_key)
    finally:
        elapsed_ms = (default_timer() - start) * 1000
        stats_logger.timing(duration_key, elapsed_ms)

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
"""Test helpers for runtime modernization unit tests."""

from __future__ import annotations

from dataclasses import dataclass, field

from axbi.stats_logger import BaseStatsLogger


@dataclass
class RecordingStatsLogger(BaseStatsLogger):
    """Stats logger test double that records emitted metrics."""

    increments: list[str] = field(default_factory=list)
    decrements: list[str] = field(default_factory=list)
    timings: list[tuple[str, float]] = field(default_factory=list)
    gauges: list[tuple[str, float]] = field(default_factory=list)

    def incr(self, key: str) -> None:
        """Record incremented keys."""

        self.increments.append(key)

    def decr(self, key: str) -> None:
        """Record decremented keys."""

        self.decrements.append(key)

    def timing(self, key: str, value: float) -> None:
        """Record timing keys and values."""

        self.timings.append((key, value))

    def gauge(self, key: str, value: float) -> None:
        """Record gauge keys and values."""

        self.gauges.append((key, value))

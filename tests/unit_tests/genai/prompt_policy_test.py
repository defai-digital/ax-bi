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
"""Tests for GenAI prompt data-minimization policy."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from axbi.genai.prompt_policy import (
    fetch_bounded_column_samples,
    sanitize_sample_value,
    should_include_samples,
)


def test_samples_denied_by_default() -> None:
    with patch("axbi.genai.prompt_policy.bounded_samples_allowed", return_value=False):
        assert should_include_samples(True) is False
        assert should_include_samples(False) is False


def test_samples_require_policy_and_request() -> None:
    with patch("axbi.genai.prompt_policy.bounded_samples_allowed", return_value=True):
        assert should_include_samples(True) is True
        assert should_include_samples(False) is False


def test_sanitize_truncates_long_values() -> None:
    long = "x" * 500
    out = sanitize_sample_value(long)
    assert out is not None
    assert len(out) <= 100
    assert out.endswith("…")


def test_fetch_bounded_column_samples_respects_caps() -> None:
    col_a = SimpleNamespace(column_name="region")
    col_b = SimpleNamespace(column_name="amount")
    dataset = SimpleNamespace(
        columns=[col_a, col_b],
        values_for_column=lambda name, limit=5: [f"{name}-{i}" for i in range(20)],
    )
    with patch("axbi.genai.prompt_policy.bounded_samples_allowed", return_value=True):
        with patch(
            "axbi.genai.prompt_policy.sample_limits",
            return_value=(3, 1),
        ):
            samples = fetch_bounded_column_samples(dataset)
    assert list(samples.keys()) == ["region"]
    assert len(samples["region"]) == 3


def test_fetch_returns_empty_when_policy_off() -> None:
    dataset = SimpleNamespace(
        columns=[SimpleNamespace(column_name="x")],
        values_for_column=lambda *a, **k: ["1"],
    )
    with patch("axbi.genai.prompt_policy.bounded_samples_allowed", return_value=False):
        assert fetch_bounded_column_samples(dataset) == {}

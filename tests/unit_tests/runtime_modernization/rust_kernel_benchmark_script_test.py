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

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest

SCRIPT_PATH = (
    Path(__file__).parents[3] / "ax-bi-rust" / "python" / "benchmark_sql_kernel.py"
)


def load_benchmark_script() -> ModuleType:
    """Load the standalone Rust benchmark script as a test module."""

    spec = importlib.util.spec_from_file_location(
        "rust_kernel_benchmark_script",
        SCRIPT_PATH,
    )
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_rust_kernel_benchmark_script_reports_passing_evidence() -> None:
    """Benchmark report passes when Rust output matches the Python baseline."""

    module = load_benchmark_script()

    report = module.build_benchmark_report(
        rust_normalize=module.normalize_sql_whitespace_python,
        iterations=1,
        min_speedup=None,
    )

    assert report["schema_version"] == 1
    assert report["status"] == "passed"
    assert report["kernel"] == "sql_whitespace_kernel"
    assert report["iterations"] == 1
    assert report["output_matched"] is True
    assert report["output_bytes"] > 0
    assert report["target_checks"] == {"speedup_met": None}


def test_rust_kernel_benchmark_script_fails_output_mismatch() -> None:
    """Benchmark report fails when Rust output differs from the baseline."""

    module = load_benchmark_script()

    report = module.build_benchmark_report(
        rust_normalize=lambda _: "different",
        iterations=1,
        min_speedup=None,
    )

    assert report["status"] == "failed"
    assert report["output_matched"] is False


def test_rust_kernel_benchmark_script_fails_speedup_gate() -> None:
    """Benchmark report fails when an explicit speedup gate is not met."""

    module = load_benchmark_script()

    report = module.build_benchmark_report(
        rust_normalize=module.normalize_sql_whitespace_python,
        iterations=1,
        min_speedup=1_000_000.0,
    )

    assert report["status"] == "failed"
    assert report["output_matched"] is True
    assert report["target_checks"] == {"speedup_met": False}


def test_rust_kernel_benchmark_script_rejects_invalid_iterations() -> None:
    """Benchmark report requires positive iterations."""

    module = load_benchmark_script()

    with pytest.raises(ValueError, match="iterations must be positive"):
        module.build_benchmark_report(
            rust_normalize=module.normalize_sql_whitespace_python,
            iterations=0,
            min_speedup=None,
        )

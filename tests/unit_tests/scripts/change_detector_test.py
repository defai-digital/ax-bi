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

import importlib.util
import re
from collections.abc import Callable
from pathlib import Path
from types import ModuleType
from typing import Any, cast


def _load_change_detector() -> ModuleType:
    """Load the executable change detector script without package import aliases."""

    script_path = Path(__file__).parents[3] / "scripts" / "change_detector.py"
    spec = importlib.util.spec_from_file_location(
        "change_detector_under_test", script_path
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load change_detector.py")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_CHANGE_DETECTOR = _load_change_detector()
_PATTERNS = cast(dict[str, list[str]], _CHANGE_DETECTOR.PATTERNS)
_detect_changes = cast(
    Callable[[list[str], list[Any]], bool],
    _CHANGE_DETECTOR.detect_changes,
)


def _detects(group: str, *files: str) -> bool:
    """Return whether the change detector maps files to one check group."""

    return _detect_changes(
        list(files),
        [re.compile(pattern) for pattern in _PATTERNS[group]],
    )


def test_ax_services_changes_include_shared_change_detector() -> None:
    """Changing the shared detector re-runs ax-services checks."""

    assert _detects("ax-services", "scripts/change_detector.py")
    assert _detects("ax-services", ".github/actions/change-detector/action.yml")


def test_superset_rust_changes_include_sql_parser_integration() -> None:
    """Changing Rust SQL parser integration re-runs Rust checks."""

    assert _detects("superset-rust", "superset/sql/parse.py")
    assert _detects("superset-rust", "tests/unit_tests/sql/parse_tests.py")


def test_superset_rust_changes_include_shared_change_detector() -> None:
    """Changing the shared detector re-runs Rust checks."""

    assert _detects("superset-rust", "scripts/change_detector.py")
    assert _detects("superset-rust", ".github/actions/change-detector/action.yml")


def test_frontend_build_excludes_browser_test_harness() -> None:
    """Browser test harness changes should not run full frontend package builds."""

    assert not _detects(
        "frontend_build",
        "ax-bi-frontend/cypress-base/cypress/e2e/explore/utils.ts",
    )
    assert not _detects(
        "frontend_build",
        "ax-bi-frontend/playwright/components/core/Select.ts",
    )


def test_frontend_build_includes_app_source() -> None:
    """Frontend app source changes still run full frontend package builds."""

    assert _detects("frontend_build", "ax-bi-frontend/src/views/index.tsx")

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

"""Static guards that prevent high-risk Python stability regressions.

These tests are intentionally mechanical. They do not prove correctness of
business logic; they keep known-bad patterns from re-entering hot paths after
reviews flagged Superset-era Python stability debt.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CODE_ROOTS = (
    REPO_ROOT / "axbi",
    REPO_ROOT / "ax-bi-core" / "src" / "axbi_core",
)

# Paths where silent exception swallowing is accepted (best-effort UI assets,
# optional integrations). Prefer logging over bare ``pass`` even here.
ALLOWLIST_SILENT_PASS = frozenset(
    {
        # Empty exception class bodies / ABC stubs use ``pass`` legitimately.
    }
)


def _python_files() -> list[Path]:
    files: list[Path] = []
    for root in CODE_ROOTS:
        if not root.exists():
            continue
        files.extend(
            path
            for path in root.rglob("*.py")
            if "__pycache__" not in path.parts and "migrations" not in path.parts
        )
    return sorted(files)


def _relative(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT))


def test_no_bare_except_clauses() -> None:
    """Bare ``except:`` hides KeyboardInterrupt/SystemExit and is banned."""
    pattern = re.compile(r"^\s*except\s*:\s*(#.*)?$", re.MULTILINE)
    failures: list[str] = []
    for path in _python_files():
        contents = path.read_text(encoding="utf-8")
        for match in pattern.finditer(contents):
            line_no = contents.count("\n", 0, match.start()) + 1
            failures.append(f"{_relative(path)}:{line_no}: bare except")
    assert failures == []


def test_no_mutable_default_arguments_in_public_api() -> None:
    """Mutable default args leak state across calls; ban common cases."""
    failures: list[str] = []
    for path in _python_files():
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for default in node.args.defaults + node.args.kw_defaults:
                if default is None:
                    continue
                if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                    failures.append(
                        f"{_relative(path)}:{node.lineno}: "
                        f"mutable default in {node.name}()"
                    )
    assert failures == []


def test_session_lifecycle_module_is_the_shared_boundary() -> None:
    """MCP and app code must share one session recovery implementation."""
    lifecycle = (
        REPO_ROOT / "axbi" / "utils" / "session_lifecycle.py"
    ).read_text(encoding="utf-8")
    mcp_utils = (
        REPO_ROOT / "axbi" / "mcp_service" / "utils" / "session_utils.py"
    ).read_text(encoding="utf-8")

    assert "def rollback_session_safely" in lifecycle
    assert "def remove_session_with_connection_recovery" in lifecycle
    assert "from axbi.utils.session_lifecycle import" in mcp_utils


def test_transaction_decorator_uses_depth_and_safe_rollback() -> None:
    """Outer commit boundary and safe rollback must stay wired."""
    decorators = (REPO_ROOT / "axbi" / "utils" / "decorators.py").read_text(
        encoding="utf-8"
    )
    assert "transaction_depth" in decorators
    assert "rollback_session_safely" in decorators


def test_celery_task_postrun_uses_safe_session_removal() -> None:
    """Worker teardown must recover from stale DBAPI connections."""
    celery_app = (REPO_ROOT / "axbi" / "tasks" / "celery_app.py").read_text(
        encoding="utf-8"
    )
    assert "remove_session_safely" in celery_app
    assert "task_postrun" in celery_app

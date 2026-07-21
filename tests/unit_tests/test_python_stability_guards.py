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
reviews flagged legacy Python stability debt.
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
ALLOWLIST_SILENT_PASS: frozenset[str] = frozenset(
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
    lifecycle = (REPO_ROOT / "axbi" / "utils" / "session_lifecycle.py").read_text(
        encoding="utf-8"
    )
    mcp_utils = (
        REPO_ROOT / "axbi" / "mcp_service" / "utils" / "session_utils.py"
    ).read_text(encoding="utf-8")

    assert "def commit_session" in lifecycle
    assert "def rollback_session" in lifecycle
    assert "def rollback_session_safely" in lifecycle
    assert "def remove_session_with_connection_recovery" in lifecycle
    assert "from axbi.utils.session_lifecycle import" in mcp_utils


def test_sql_execution_and_report_hot_paths_use_commit_session() -> None:
    """High-churn persistence paths must go through commit_session."""
    hot_paths = (
        REPO_ROOT / "axbi" / "sql" / "execution" / "celery_task.py",
        REPO_ROOT / "axbi" / "sql" / "execution" / "executor.py",
        REPO_ROOT / "axbi" / "commands" / "report" / "execute.py",
        # Phase-1 leftover sweep (stability review 2026-07-21).
        REPO_ROOT / "axbi" / "extensions" / "metastore_cache.py",
        REPO_ROOT / "axbi" / "commands" / "sql_lab" / "execute.py",
        REPO_ROOT / "axbi" / "key_value" / "commands" / "prune.py",
        REPO_ROOT / "axbi" / "commands" / "prune.py",
        REPO_ROOT / "axbi" / "semantic_index" / "tasks.py",
    )
    for path in hot_paths:
        contents = path.read_text(encoding="utf-8")
        assert "commit_session" in contents, f"{_relative(path)} missing commit_session"
        # Raw commits on the Flask-SQLAlchemy session are banned on these paths.
        # User-database ``conn.commit()`` for SQL mutations remains allowed.
        for line_no, line in enumerate(contents.splitlines(), start=1):
            if "db.session.commit(" in line and "commit_session" not in line:
                raise AssertionError(
                    f"{_relative(path)}:{line_no}: raw db.session.commit()"
                )


def test_override_user_restores_on_exception() -> None:
    """override_user must use try/finally so g.user cannot stick after errors."""
    core_utils = (REPO_ROOT / "axbi" / "utils" / "core.py").read_text(encoding="utf-8")
    # Narrow to the override_user function body.
    start = core_utils.index("def override_user(")
    end = core_utils.index("\ndef ", start + 1)
    body = core_utils[start:end]
    assert "try:" in body
    assert "finally:" in body


def test_celery_sql_unhandled_error_resets_session() -> None:
    """Unhandled SQL celery failures must recover the metadata session first."""
    celery_task = (
        REPO_ROOT / "axbi" / "sql" / "execution" / "celery_task.py"
    ).read_text(encoding="utf-8")
    assert "reset_session_safely" in celery_task
    assert "error_sqllab_unhandled" in celery_task


def test_kv_distributed_lock_uses_independent_session() -> None:
    """KV lock acquire/release must not nest under the request unit of work."""
    acquire = (
        REPO_ROOT / "axbi" / "commands" / "distributed_lock" / "acquire.py"
    ).read_text(encoding="utf-8")
    release = (
        REPO_ROOT / "axbi" / "commands" / "distributed_lock" / "release.py"
    ).read_text(encoding="utf-8")
    assert "independent_kv_session" in acquire
    assert "independent_kv_session" in release
    # Nested @transaction would hide the lock until the outer boundary commits.
    # Match the decorator form, not docstring mentions of ``@transaction``.
    decorator = re.compile(r"^\s*@transaction\b", re.MULTILINE)
    assert decorator.search(acquire) is None
    assert decorator.search(release) is None


def test_gtf_abort_listener_recovers_instead_of_breaking() -> None:
    """Abort listeners must keep watching after transient metadata errors."""
    manager = (REPO_ROOT / "axbi" / "tasks" / "manager.py").read_text(encoding="utf-8")
    assert "_recover_abort_listener_session" in manager
    assert "reset_session_safely" in manager
    context = (REPO_ROOT / "axbi" / "tasks" / "context.py").read_text(encoding="utf-8")
    assert "_claim_abort_handlers" in context


def test_websocket_stream_reader_has_error_backoff() -> None:
    """Redis stream reader must back off on errors (no tight catch→continue)."""
    ws = (REPO_ROOT / "ax-bi-websocket" / "src" / "index.ts").read_text(
        encoding="utf-8"
    )
    assert "STREAM_ERROR_BACKOFF_MS" in ws
    assert "errorBackoffMs" in ws
    # CORS must not reflect any origin with credentials when lists are empty.
    assert "origin: corsOrigins.length > 0 ? corsOrigins : false" in ws


def test_chart_data_path_uses_single_flight_lock() -> None:
    """Chart-data cache miss path must single-flight warehouse recompute."""
    qcp = (REPO_ROOT / "axbi" / "common" / "query_context_processor.py").read_text(
        encoding="utf-8"
    )
    assert "DistributedLock" in qcp
    assert "chart_data_cache" in qcp
    # Waiters must poll until warm (or wait budget), not recompute after one sleep.
    assert "_CHART_DATA_WAIT_MAX_SECONDS" in qcp
    assert "wait budget exhausted" in qcp


def test_trino_execute_thread_is_joined() -> None:
    trino = (REPO_ROOT / "axbi" / "db_engine_specs" / "trino.py").read_text(
        encoding="utf-8"
    )
    assert "daemon=True" in trino
    assert "execute_thread.join" in trino


def test_playwright_browser_manager_has_launch_lock() -> None:
    webdriver = (REPO_ROOT / "axbi" / "utils" / "webdriver.py").read_text(
        encoding="utf-8"
    )
    assert "_launch_lock" in webdriver


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

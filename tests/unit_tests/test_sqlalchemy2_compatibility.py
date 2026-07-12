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

import re
from importlib.metadata import version
from pathlib import Path

from packaging.version import Version

REPO_ROOT = Path(__file__).resolve().parents[2]
SQLALCHEMY_CODE_ROOTS = (
    REPO_ROOT / "axbi",
    REPO_ROOT / "ax-bi-core" / "axbi_core",
)


def _python_files() -> list[Path]:
    files: list[Path] = []
    for root in SQLALCHEMY_CODE_ROOTS:
        files.extend(
            path for path in root.rglob("*.py") if "__pycache__" not in path.parts
        )
    return sorted(files)


def _relative(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT))


def test_sqlalchemy2_runtime_versions_are_installed() -> None:
    assert Version(version("sqlalchemy")) >= Version("2.0.51")
    assert Version(version("flask-sqlalchemy")) >= Version("3.1.1")


def test_removed_sqlalchemy2_apis_do_not_reappear() -> None:
    forbidden_patterns = {
        r"\bengine\.execute\(": "engine.execute() was removed in SQLAlchemy 2",
        r"\binspector\.bind\.execute\(": (
            "inspector.bind may be an Engine; use execute_inspector_statement()"
        ),
        r"\b(?:conn|connection)\.execute\(\s*['\"]": (
            "raw SQL strings passed to Connection.execute() must use text()"
        ),
        r"\bMetaData\(\s*bind\s*=": "MetaData(bind=...) was removed",
        r"\bautoload\s*=\s*True\b": "Table reflection must use autoload_with",
        r"\b(?:session|db\.session)\.query\([^)\n]+\)\.get\(": (
            "Query.get() must be replaced with Session.get()"
        ),
        r"\b[A-Z][A-Za-z0-9_]*\.query\.get\(": (
            "Flask-SQLAlchemy Model.query.get() must not be used"
        ),
        r"\bselect\(\s*\[": "select([columns]) must be select(columns)",
        r"\bcase\(\s*\[": "case([(condition, value)]) must use positional whens",
        r"\beagerload\(": "sqlalchemy.orm.eagerload was removed",
        r"\bload_only\(\s*['\"]": "load_only() must use mapped attributes",
    }

    failures: list[str] = []
    for path in _python_files():
        contents = path.read_text()
        for pattern, reason in forbidden_patterns.items():
            for match in re.finditer(pattern, contents):
                if (
                    pattern == r"\b(?:conn|connection)\.execute\(\s*['\"]"
                    and "sqlite3.Connection" in contents
                ):
                    continue
                line_no = contents.count("\n", 0, match.start()) + 1
                failures.append(f"{_relative(path)}:{line_no}: {reason}")

    assert failures == []

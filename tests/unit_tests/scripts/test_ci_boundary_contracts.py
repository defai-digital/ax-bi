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
"""Repository-level contracts for CI and generated workspace boundaries."""

from __future__ import annotations

import re
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
WORKFLOW_ROOT = REPOSITORY_ROOT / ".github" / "workflows"
DATABASE_ENDPOINT_PATTERN = re.compile(
    r"(?P<dialect>postgresql(?:\+psycopg2)?|mysql\+mysqldb)://"
    r"(?P<username>[^:]+):(?P<password>[^@]+)@127\.0\.0\.1:"
    r"(?P<port>15432|13306)/(?P<database>[^?\s\"']+)"
)


def test_ci_database_endpoints_match_canonical_service_identity() -> None:
    """CI clients use the account and database created by service containers."""
    workflow_files = sorted(WORKFLOW_ROOT.glob("*.yml"))
    boundary_files = [*workflow_files, WORKFLOW_ROOT / "bashlib.sh"]
    endpoints: list[tuple[Path, re.Match[str]]] = []
    postgres_service_users: list[tuple[Path, str]] = []

    for path in boundary_files:
        contents = path.read_text(encoding="utf-8")
        endpoints.extend(
            (path, match) for match in DATABASE_ENDPOINT_PATTERN.finditer(contents)
        )
        postgres_service_users.extend(
            (path, username)
            for username in re.findall(r"POSTGRES_USER:\s*([^\s#]+)", contents)
        )

    assert endpoints, "Expected CI database endpoints to be present"
    for path, endpoint in endpoints:
        assert endpoint.group("username") == "axbi", path
        assert endpoint.group("password") == "axbi", path
        assert endpoint.group("database") == "axbi", path

    assert postgres_service_users, "Expected Postgres service users to be present"
    for path, username in postgres_service_users:
        assert username == "axbi", path


def test_ax_office_generated_artifacts_are_ignored() -> None:
    """Generated AX Office compatibility artifacts cannot re-enter source control."""
    ignored_paths = {
        line.strip()
        for line in (REPOSITORY_ROOT / ".gitignore")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }

    assert {
        "ax-office-frontend/.swc/",
        "ax-office-frontend/playwright-report/",
        "ax-office-frontend/test-results/",
    } <= ignored_paths


def test_translation_baseline_targets_packaged_catalogs() -> None:
    """The comparison worktree reads catalogs from the Python package boundary."""
    catalog_path = REPOSITORY_ROOT / "axbi" / "translations"
    workflow = (WORKFLOW_ROOT / "axbi-translations.yml").read_text(encoding="utf-8")

    assert catalog_path.is_dir()
    assert "--translations-dir /tmp/base-worktree/axbi/translations" in workflow

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

"""Reject former-brand identifiers outside documentation and legal files."""

from __future__ import annotations

import sys
from pathlib import Path
from shutil import which
from subprocess import CalledProcessError, run

REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
FORMER_BRAND = "super" + "set"
EXCLUDED_DIRECTORIES = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "docs",
    "lib",
    "node_modules",
    "target",
    "venv",
}
DOCUMENTATION_SUFFIXES = {".md", ".mdx", ".rst"}
LEGAL_FILE_PREFIXES = ("license", "notice")


def is_excluded(path: Path) -> bool:
    """Return whether a repository path is outside the branding boundary."""
    relative = path.relative_to(REPOSITORY_ROOT)
    if any(part in EXCLUDED_DIRECTORIES for part in relative.parts[:-1]):
        return True
    if path.suffix.lower() in DOCUMENTATION_SUFFIXES:
        return True
    return path.name.lower().startswith(LEGAL_FILE_PREFIXES)


def iter_repository_files() -> list[Path]:
    """Return tracked and unignored repository files eligible for inspection."""
    git = which("git")
    if git is None:
        raise RuntimeError("Unable to enumerate repository files without git")

    try:
        result = run(  # noqa: S603 -- fixed executable and arguments
            [
                git,
                "ls-files",
                "--cached",
                "--others",
                "--exclude-standard",
                "-z",
            ],
            cwd=REPOSITORY_ROOT,
            check=True,
            capture_output=True,
        )
    except (CalledProcessError, FileNotFoundError) as error:
        raise RuntimeError("Unable to enumerate repository files with git") from error

    paths = (
        REPOSITORY_ROOT / name for name in result.stdout.decode().split("\0") if name
    )
    return sorted(path for path in paths if path.is_file() and not is_excluded(path))


def find_violations() -> list[str]:
    """Find former-brand tokens in eligible paths and UTF-8 text content."""
    violations: list[str] = []
    needle = FORMER_BRAND.casefold()

    for path in iter_repository_files():
        relative = path.relative_to(REPOSITORY_ROOT)
        if needle in relative.as_posix().casefold():
            violations.append(f"{relative}: former brand appears in path")

        try:
            raw_content = path.read_bytes()
        except OSError as error:
            violations.append(f"{relative}: unable to read ({error})")
            continue

        if b"\0" in raw_content:
            continue
        try:
            content = raw_content.decode("utf-8")
        except UnicodeDecodeError:
            continue

        for line_number, line in enumerate(content.splitlines(), start=1):
            if needle in line.casefold():
                violations.append(f"{relative}:{line_number}: {line.strip()}")

    return violations


def main() -> int:
    """Run the AX BI source-branding boundary check."""
    violations = find_violations()
    if not violations:
        print("AX BI branding check passed")
        return 0

    print(
        f"Former-brand references are only allowed in documentation and legal files; "
        f"found {len(violations)} violation(s):",
        file=sys.stderr,
    )
    for violation in violations:
        print(f"  {violation}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

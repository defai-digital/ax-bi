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

"""Reject source files hidden by broad Git ignore patterns."""

from __future__ import annotations

import sys
from pathlib import Path
from shutil import which
from subprocess import CalledProcessError, run

REPOSITORY_ROOT = Path(__file__).resolve().parent.parent

# These pathspecs deliberately point at authored source trees rather than whole
# projects so generated output such as node_modules, lib, target, and coverage
# remains eligible for normal ignore rules.
PROTECTED_SOURCE_PATHS = (
    ":(glob)axbi/**/*.py",
    ":(glob)axbi/**/*.pyi",
    ":(glob)axbi/templates/**",
    "axbi/static/.gitkeep",
    "axbi/static/uploads/.gitkeep",
    ":(glob)ax-bi-core/src/**",
    ":(glob)ax-bi-core/tests/**",
    ":(glob)ax-bi-frontend/src/**",
    ":(glob)ax-bi-frontend/packages/*/src/**",
    ":(glob)ax-bi-frontend/packages/*/test/**",
    ":(glob)ax-bi-frontend/plugins/*/src/**",
    ":(glob)ax-bi-frontend/plugins/*/test/**",
    ":(glob)ax-bi-extensions-cli/src/**",
    ":(glob)ax-bi-extensions-cli/tests/**",
    ":(glob)ax-bi-desktop/src/**",
    ":(glob)ax-bi-desktop/src-tauri/src/**",
    ":(glob)ax-bi-embedded-sdk/src/**",
    ":(glob)ax-bi-embedded-sdk/test/**",
    ":(glob)ax-bi-websocket/src/**",
    ":(glob)ax-services/src/**",
    ":(glob)ax-services/test/**",
    ":(glob)packages/ax-sdk/src/**",
    ":(glob)packages/ax-sdk/tests/**",
    ":(glob).github/actions/axbi-cached-dependencies/src/**",
    ":(glob).github/actions/axbi-cached-dependencies/dist/scripts/**",
)


def is_generated_path(path: str) -> bool:
    """Return whether an ignored path is generated inside a source tree."""
    parts = Path(path).parts
    return (
        "__pycache__" in parts
        or any(part.endswith(".egg-info") for part in parts)
        or Path(path).name == ".DS_Store"
    )


def find_ignored_source_files() -> list[str]:
    """Return protected source paths hidden by the active ignore rules."""
    git = which("git")
    if git is None:
        raise RuntimeError("Unable to inspect ignore rules without git")

    try:
        result = run(  # noqa: S603 -- fixed executable and arguments
            [
                git,
                "ls-files",
                "--others",
                "--ignored",
                "--exclude-standard",
                "-z",
                "--",
                *PROTECTED_SOURCE_PATHS,
            ],
            cwd=REPOSITORY_ROOT,
            check=True,
            capture_output=True,
        )
    except (CalledProcessError, FileNotFoundError) as error:
        raise RuntimeError("Unable to inspect ignored source files") from error

    return sorted(
        path
        for path in result.stdout.decode().split("\0")
        if path and not is_generated_path(path)
    )


def main() -> int:
    """Run the ignored-source boundary check."""
    ignored_files = find_ignored_source_files()
    if not ignored_files:
        print("Ignored source file check passed")
        return 0

    print(
        "Authored source files must not be hidden by .gitignore; "
        f"found {len(ignored_files)} violation(s):",
        file=sys.stderr,
    )
    for path in ignored_files:
        print(f"  {path}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

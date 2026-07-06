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

import argparse
import json
import os
import re
import subprocess
from urllib.request import Request, urlopen

# Define patterns for each group of files you're interested in
PATTERNS = {
    "python": [
        r"^\.github/workflows/.*python",
        r"^tests/",
        r"^superset/",
        r"^scripts/",
        r"^setup\.py",
        r"^pyproject\.toml$",
        r"^requirements/.+\.txt",
        r"^pyproject\.toml",
        r"^.pylintrc",
    ],
    "frontend": [
        r"^\.github/workflows/.*(bashlib|frontend|e2e)",
        r"^ax-bi-frontend/",
    ],
    "frontend_build": [
        r"^ax-bi-frontend/(?!(?:cypress-base|playwright)/)",
    ],
    "ax-services": [
        r"^\.github/workflows/ax-services\.yml",
        r"^\.github/actions/change-detector/",
        r"^ax-services/",
        r"^scripts/change_detector\.py",
    ],
    "ax-sdk": [
        r"^\.github/workflows/ax-sdk\.yml",
        r"^\.github/actions/change-detector/",
        r"^packages/ax-sdk/",
        r"^scripts/change_detector\.py",
    ],
    "superset-rust": [
        r"^\.github/workflows/superset-rust\.yml",
        r"^\.github/actions/change-detector/",
        r"^superset-rust/",
        r"^scripts/change_detector\.py",
        r"^superset/sql/parse\.py",
        r"^superset/runtime_modernization/rust_sql\.py",
        r"^tests/unit_tests/sql/parse_tests\.py",
        r"^tests/unit_tests/runtime_modernization/rust_sql_test\.py",
    ],
    "docker": [
        r"^\.github/workflows/(axbi-docker|docker)\.yml",
        r"^Dockerfile$",
        r"^docker.*",
        r"^pyproject\.toml$",
        r"^requirements/(base|development)\.(in|txt)$",
        r"^superset-core/",
        r"^superset/mcp_service/",
    ],
    "docs": [
        r"^docs/",
    ],
    "superset-extensions-cli": [
        r"^\.github/workflows/superset-extensions-cli\.yml",
        r"^superset-extensions-cli/",
        r"^superset-core/",
    ],
}
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")


def fetch_files_github_api(url: str):  # type: ignore
    """Fetches data using GitHub API."""
    req = Request(url)  # noqa: S310
    req.add_header("Authorization", f"Bearer {GITHUB_TOKEN}")
    req.add_header("Accept", "application/vnd.github.v3+json")

    print(f"Fetching from {url}")
    with urlopen(req) as response:  # noqa: S310
        body = response.read()
        return json.loads(body)


def fetch_changed_files_pr(repo: str, pr_number: str) -> list[str]:
    """Fetches files changed in a PR using the GitHub API."""

    # NOTE: limited to 100 files ideally should page-through but instead resorting
    # to assuming we should trigger when 100 files have been touched
    url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}/files?per_page=100"
    files = fetch_files_github_api(url)
    return [file_info["filename"] for file_info in files]


def fetch_changed_files_push(repo: str, sha: str) -> list[str]:
    """Fetches files changed in the last commit for push events using GitHub API."""
    # Fetch commit details to get the parent SHA
    commit_url = f"https://api.github.com/repos/{repo}/commits/{sha}"
    commit_data = fetch_files_github_api(commit_url)
    if "parents" not in commit_data or len(commit_data["parents"]) < 1:
        raise RuntimeError("No parent commit found for comparison.")
    parent_sha = commit_data["parents"][0]["sha"]
    # Compare the current commit against its parent
    compare_url = f"https://api.github.com/repos/{repo}/compare/{parent_sha}...{sha}"
    comparison_data = fetch_files_github_api(compare_url)
    return [file["filename"] for file in comparison_data["files"]]


def detect_changes(files: list[str], check_patterns: list[re.Pattern[str]]) -> bool:
    """Detects if any of the specified files match the provided patterns."""
    for file in files:
        for pattern in check_patterns:
            if re.match(pattern, file):
                return True
    return False


def print_files(files: list[str]) -> None:
    print("\n".join([f"- {s}" for s in files]))


def is_int(s: str) -> bool:
    return bool(re.match(r"^\d+$", s))


def main(event_type: str, sha: str, repo: str) -> None:
    """Main function to check for file changes based on event context."""
    print("SHA:", sha)
    print("EVENT_TYPE", event_type)
    files: list[str] | None = []
    if event_type == "pull_request":
        github_ref = os.getenv("GITHUB_REF", "")
        pr_number = github_ref.split("/")[-2] if "/" in github_ref else ""
        if not is_int(pr_number):
            raise ValueError(
                "GITHUB_REF must be a pull request ref like 'refs/pull/<number>/merge'"
            )
        files = fetch_changed_files_pr(repo, pr_number)
        print("PR files:")
        print_files(files)

    elif event_type == "push":
        files = fetch_changed_files_push(repo, sha)
        print("Files touched since previous commit:")
        print_files(files)

    elif event_type in ("workflow_dispatch", "schedule"):
        # Manual or cron-triggered runs aren't tied to a specific diff, so
        # treat every group as changed. `files = None` makes the loop below
        # short-circuit to True for every group via `files is None or ...`.
        print(f"{event_type} run, assuming all changed")
        files = None

    else:
        raise ValueError(f"Unsupported event type: {event_type}")

    changes_detected = {}
    for group, regex_patterns in PATTERNS.items():
        patterns_compiled = [re.compile(p) for p in regex_patterns]
        changes_detected[group] = files is None or detect_changes(
            files, patterns_compiled
        )

    # Output results
    output_path = os.getenv("GITHUB_OUTPUT") or "/tmp/GITHUB_OUTPUT.txt"  # noqa: S108
    with open(output_path, "a") as f:
        for check, changed in changes_detected.items():
            # NOTE: as noted above, we assume that if 100 files are touched, we should
            # trigger all checks. This is a workaround for the GitHub API limit of 100
            # files. Using >= 99 because off-by-one errors are not uncommon
            if changed or (files is not None and len(files) >= 99):
                print(f"{check}=true", file=f)
                print(f"Triggering group: {check}")


def get_git_sha() -> str:
    return os.getenv("GITHUB_SHA") or subprocess.check_output(  # noqa: S603
        ["git", "rev-parse", "HEAD"]  # noqa: S603, S607
    ).strip().decode("utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Detect file changes based on event context"
    )
    parser.add_argument(
        "--event-type",
        default=os.getenv("GITHUB_EVENT_NAME") or "push",
        help="The type of event that triggered the workflow",
    )
    parser.add_argument(
        "--sha",
        default=get_git_sha(),
        help="The commit SHA for push events or PR head SHA",
    )
    parser.add_argument(
        "--repo",
        default=os.getenv("GITHUB_REPOSITORY") or "apache/superset",
        help="GitHub repository in the format owner/repo",
    )
    args = parser.parse_args()

    try:
        main(args.event_type, args.sha, args.repo)
    except ValueError as ex:
        parser.error(str(ex))

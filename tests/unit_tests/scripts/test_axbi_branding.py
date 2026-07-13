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
"""Tests for the repository branding boundary."""

from pathlib import Path

import pytest

from scripts import check_axbi_branding


@pytest.mark.parametrize("legacy_root", check_axbi_branding.FORBIDDEN_LEGACY_ROOTS)
def test_legacy_top_level_paths_are_rejected(
    legacy_root: str,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Generated output cannot recreate a former-brand repository root."""
    monkeypatch.setattr(check_axbi_branding, "REPOSITORY_ROOT", tmp_path)
    monkeypatch.setattr(check_axbi_branding, "iter_repository_files", lambda: [])
    (tmp_path / legacy_root).mkdir()

    assert check_axbi_branding.find_violations() == [
        f"{legacy_root}: former-brand top-level path must not exist"
    ]


def test_ax_bi_top_level_paths_are_allowed(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Canonical Python and Rust roots remain valid."""
    monkeypatch.setattr(check_axbi_branding, "REPOSITORY_ROOT", tmp_path)
    monkeypatch.setattr(check_axbi_branding, "iter_repository_files", lambda: [])
    (tmp_path / "axbi").mkdir()
    (tmp_path / "ax-bi-rust").mkdir()

    assert check_axbi_branding.find_violations() == []

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

from superset.runtime_modernization import rust_sql
from superset.runtime_modernization.rust_sql import normalize_sql_whitespace


def test_normalize_sql_whitespace_python_fallback_collapses_outer_whitespace() -> None:
    """Python fallback matches the Rust kernel contract for basic SQL."""

    assert (
        normalize_sql_whitespace(
            " SELECT   *\nFROM   table\nWHERE id = 1 ",
            use_rust=False,
        )
        == "SELECT * FROM table WHERE id = 1"
    )


def test_normalize_sql_whitespace_preserves_literals_and_quoted_identifiers() -> None:
    """Whitespace inside SQL literals and quoted identifiers is preserved."""

    assert (
        normalize_sql_whitespace(
            "SELECT  'a   b',  'it''s ok', \"c   d\", `e   f`, [g   h]",
            use_rust=False,
        )
        == "SELECT 'a   b', 'it''s ok', \"c   d\", `e   f`, [g   h]"
    )


def test_normalize_sql_whitespace_preserves_comment_body() -> None:
    """Comment text is preserved while surrounding SQL whitespace is normalized."""

    assert (
        normalize_sql_whitespace("SELECT 1  -- keep   comment\n FROM t", use_rust=False)
        == "SELECT 1 -- keep   comment\n FROM t"
    )
    assert (
        normalize_sql_whitespace("SELECT  /* keep   block */ 1", use_rust=False)
        == "SELECT /* keep   block */ 1"
    )


def test_normalize_sql_whitespace_uses_rust_when_requested_and_available(
    monkeypatch,
) -> None:
    """The wrapper dispatches to the optional Rust extension when available."""

    calls: list[str] = []

    def rust_normalize(sql: str) -> str:
        calls.append(sql)
        return "rust-result"

    monkeypatch.setattr(rust_sql, "_rust_normalize_sql_whitespace", rust_normalize)

    assert normalize_sql_whitespace(" SELECT 1 ", use_rust=True) == "rust-result"
    assert calls == [" SELECT 1 "]


def test_normalize_sql_whitespace_falls_back_when_rust_requested_but_missing(
    monkeypatch,
) -> None:
    """Requesting Rust still returns correct output if the extension is absent."""

    monkeypatch.setattr(rust_sql, "_rust_normalize_sql_whitespace", None)

    assert normalize_sql_whitespace(" SELECT   1 ", use_rust=True) == "SELECT 1"

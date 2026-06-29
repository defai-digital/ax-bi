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
"""Optional Rust-backed SQL helpers for runtime modernization."""

from __future__ import annotations

from collections.abc import Callable
from enum import Enum

from flask import has_app_context

from superset import is_feature_enabled

try:
    from ax_sql import (
        normalize_sql_whitespace as _imported_rust_normalize_sql_whitespace,
    )
except ImportError:  # pragma: no cover - exercised by fallback behavior
    _imported_rust_normalize_sql_whitespace = None

_rust_normalize_sql_whitespace: Callable[[str], str] | None = (
    _imported_rust_normalize_sql_whitespace
)


class _ScanState(Enum):
    DEFAULT = "default"
    SINGLE_QUOTE = "single_quote"
    DOUBLE_QUOTE = "double_quote"
    BACKTICK = "backtick"
    BRACKET = "bracket"
    LINE_COMMENT = "line_comment"
    BLOCK_COMMENT = "block_comment"


def rust_sql_kernel_available() -> bool:
    """Return whether the optional Rust SQL extension is importable."""

    return _rust_normalize_sql_whitespace is not None


def normalize_sql_whitespace(sql: str, use_rust: bool | None = None) -> str:
    """Collapse whitespace outside SQL strings, quoted identifiers, and comments."""

    should_use_rust = (
        use_rust
        if use_rust is not None
        else has_app_context() and is_feature_enabled("RUST_SQL_KERNEL")
    )
    if should_use_rust and _rust_normalize_sql_whitespace is not None:
        return _rust_normalize_sql_whitespace(sql)

    return _normalize_sql_whitespace_python(sql)


def _normalize_sql_whitespace_python(sql: str) -> str:  # noqa: C901
    """Python compatibility implementation for the Rust SQL whitespace kernel."""

    output: list[str] = []
    index = 0
    state = _ScanState.DEFAULT
    pending_space = False

    def peek() -> str | None:
        return sql[index + 1] if index + 1 < len(sql) else None

    while index < len(sql):
        char = sql[index]
        next_char = peek()

        if state == _ScanState.DEFAULT:
            if char.isspace():
                pending_space = bool(output)
                index += 1
                continue

            if pending_space and (not output or output[-1] != " "):
                output.append(" ")
            pending_space = False

            if char == "'":
                output.append(char)
                state = _ScanState.SINGLE_QUOTE
            elif char == '"':
                output.append(char)
                state = _ScanState.DOUBLE_QUOTE
            elif char == "`":
                output.append(char)
                state = _ScanState.BACKTICK
            elif char == "[":
                output.append(char)
                state = _ScanState.BRACKET
            elif char == "-" and next_char == "-":
                output.extend((char, next_char))
                state = _ScanState.LINE_COMMENT
                index += 1
            elif char == "/" and next_char == "*":
                output.extend((char, next_char))
                state = _ScanState.BLOCK_COMMENT
                index += 1
            else:
                output.append(char)

        elif state == _ScanState.SINGLE_QUOTE:
            output.append(char)
            if char == "'":
                if next_char == "'":
                    output.append(next_char)
                    index += 1
                else:
                    state = _ScanState.DEFAULT

        elif state == _ScanState.DOUBLE_QUOTE:
            output.append(char)
            if char == '"':
                if next_char == '"':
                    output.append(next_char)
                    index += 1
                else:
                    state = _ScanState.DEFAULT

        elif state == _ScanState.BACKTICK:
            output.append(char)
            if char == "`":
                if next_char == "`":
                    output.append(next_char)
                    index += 1
                else:
                    state = _ScanState.DEFAULT

        elif state == _ScanState.BRACKET:
            output.append(char)
            if char == "]":
                state = _ScanState.DEFAULT

        elif state == _ScanState.LINE_COMMENT:
            output.append(char)
            if char == "\n":
                state = _ScanState.DEFAULT

        elif state == _ScanState.BLOCK_COMMENT:
            output.append(char)
            if char == "*" and next_char == "/":
                output.append(next_char)
                state = _ScanState.DEFAULT
                index += 1

        index += 1

    if output and output[-1] == " ":
        output.pop()

    return "".join(output)

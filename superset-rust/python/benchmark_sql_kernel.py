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
"""Generate benchmark evidence for the Rust SQL whitespace kernel."""

from __future__ import annotations

import argparse
import json  # noqa: TID251
from collections.abc import Callable
from enum import Enum
from pathlib import Path
from timeit import default_timer
from typing import Any

SAMPLE_SQL = """
WITH recent_orders AS (
  SELECT customer_id, SUM(total) AS total
  FROM public.orders
  WHERE created_at >= DATE '2024-01-01'
  GROUP BY customer_id
)
SELECT c.name, r.total, 'keep   literal   spaces' AS marker
FROM public.customers c
JOIN recent_orders r ON c.id = r.customer_id
WHERE r.total > 100
ORDER BY r.total DESC
LIMIT 100
"""


class ScanState(Enum):
    """State machine states for the Python compatibility baseline."""

    DEFAULT = "default"
    SINGLE_QUOTE = "single_quote"
    DOUBLE_QUOTE = "double_quote"
    BACKTICK = "backtick"
    BRACKET = "bracket"
    LINE_COMMENT = "line_comment"
    BLOCK_COMMENT = "block_comment"


def normalize_sql_whitespace_python(sql: str) -> str:  # noqa: C901
    """Collapse whitespace outside SQL strings, quoted identifiers, and comments."""

    output: list[str] = []
    index = 0
    state = ScanState.DEFAULT
    pending_space = False

    def peek() -> str | None:
        return sql[index + 1] if index + 1 < len(sql) else None

    while index < len(sql):
        char = sql[index]
        next_char = peek()

        if state == ScanState.DEFAULT:
            if char.isspace():
                pending_space = bool(output)
                index += 1
                continue

            if pending_space and (not output or output[-1] != " "):
                output.append(" ")
            pending_space = False

            if char == "'":
                output.append(char)
                state = ScanState.SINGLE_QUOTE
            elif char == '"':
                output.append(char)
                state = ScanState.DOUBLE_QUOTE
            elif char == "`":
                output.append(char)
                state = ScanState.BACKTICK
            elif char == "[":
                output.append(char)
                state = ScanState.BRACKET
            elif char == "-" and next_char == "-":
                output.extend((char, next_char))
                state = ScanState.LINE_COMMENT
                index += 1
            elif char == "/" and next_char == "*":
                output.extend((char, next_char))
                state = ScanState.BLOCK_COMMENT
                index += 1
            else:
                output.append(char)

        elif state == ScanState.SINGLE_QUOTE:
            output.append(char)
            if char == "'":
                if next_char == "'":
                    output.append(next_char)
                    index += 1
                else:
                    state = ScanState.DEFAULT

        elif state == ScanState.DOUBLE_QUOTE:
            output.append(char)
            if char == '"':
                if next_char == '"':
                    output.append(next_char)
                    index += 1
                else:
                    state = ScanState.DEFAULT

        elif state == ScanState.BACKTICK:
            output.append(char)
            if char == "`":
                if next_char == "`":
                    output.append(next_char)
                    index += 1
                else:
                    state = ScanState.DEFAULT

        elif state == ScanState.BRACKET:
            output.append(char)
            if char == "]":
                state = ScanState.DEFAULT

        elif state == ScanState.LINE_COMMENT:
            output.append(char)
            if char == "\n":
                state = ScanState.DEFAULT

        elif state == ScanState.BLOCK_COMMENT:
            output.append(char)
            if char == "*" and next_char == "/":
                output.append(next_char)
                state = ScanState.DEFAULT
                index += 1

        index += 1

    if output and output[-1] == " ":
        output.pop()

    return "".join(output)


def build_benchmark_report(
    *,
    rust_normalize: Callable[[str], str],
    iterations: int,
    min_speedup: float | None,
    sql: str = SAMPLE_SQL,
) -> dict[str, Any]:
    """Build benchmark evidence comparing the Rust kernel to the Python baseline."""

    if iterations <= 0:
        raise ValueError("iterations must be positive")

    python_output = ""
    start = default_timer()
    for _ in range(iterations):
        python_output = normalize_sql_whitespace_python(sql)
    python_duration_ms = (default_timer() - start) * 1000

    rust_output = ""
    start = default_timer()
    for _ in range(iterations):
        rust_output = rust_normalize(sql)
    rust_duration_ms = (default_timer() - start) * 1000

    speedup = (
        python_duration_ms / rust_duration_ms
        if rust_duration_ms and rust_duration_ms > 0
        else None
    )
    speedup_met = (
        None if min_speedup is None else speedup is not None and speedup >= min_speedup
    )
    output_matched = rust_output == python_output
    passed = output_matched and speedup_met is not False

    return {
        "schema_version": 1,
        "status": "passed" if passed else "failed",
        "kernel": "sql_whitespace_kernel",
        "iterations": iterations,
        "python_duration_ms": python_duration_ms,
        "python_operations_per_second": iterations / (python_duration_ms / 1000)
        if python_duration_ms > 0
        else 0,
        "rust_duration_ms": rust_duration_ms,
        "rust_operations_per_second": iterations / (rust_duration_ms / 1000)
        if rust_duration_ms > 0
        else 0,
        "speedup": speedup,
        "output_matched": output_matched,
        "output_bytes": len(python_output.encode("utf-8")),
        "targets": {
            "min_speedup": min_speedup,
        },
        "target_checks": {
            "speedup_met": speedup_met,
        },
    }


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--iterations",
        type=int,
        default=10_000,
        help="Number of benchmark iterations.",
    )
    parser.add_argument(
        "--min-speedup",
        type=float,
        help="Optional minimum Rust speedup target.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional path for the JSON report artifact.",
    )
    return parser.parse_args()


def main() -> int:
    """Run the benchmark and return a process exit code."""

    from ax_sql import normalize_sql_whitespace as rust_normalize

    args = parse_args()
    report = build_benchmark_report(
        rust_normalize=rust_normalize,
        iterations=args.iterations,
        min_speedup=args.min_speedup,
    )
    output = json.dumps(report, sort_keys=True, indent=2)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output + "\n", encoding="utf-8")

    print(output)
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())

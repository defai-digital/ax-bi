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
"""Benchmark helpers for runtime modernization candidates."""

from __future__ import annotations

from dataclasses import dataclass
from timeit import default_timer

from superset.runtime_modernization.rust_sql import (
    normalize_sql_whitespace,
    rust_sql_kernel_available,
)
from superset.sql.parse import SQLScript

SQL_PARSING_NORMALIZATION_SAMPLE = """
WITH recent_orders AS (
  SELECT customer_id, SUM(total) AS total
  FROM public.orders
  WHERE created_at >= DATE '2024-01-01'
  GROUP BY customer_id
)
SELECT c.name, r.total
FROM public.customers c
JOIN recent_orders r ON c.id = r.customer_id
WHERE r.total > 100
ORDER BY r.total DESC
LIMIT 100
"""


@dataclass(frozen=True, slots=True)
class RuntimeBenchmarkResult:
    """Result from a runtime modernization benchmark run."""

    area: str
    operation: str
    engine: str
    iterations: int
    duration_ms: float
    operations_per_second: float
    statement_count: int
    formatted_bytes: int
    table_check_matched: bool
    has_mutation: bool


@dataclass(frozen=True, slots=True)
class RuntimeKernelBenchmarkResult:
    """Result from a runtime modernization kernel benchmark run."""

    area: str
    operation: str
    iterations: int
    python_duration_ms: float
    python_operations_per_second: float
    rust_available: bool
    rust_duration_ms: float | None
    rust_operations_per_second: float | None
    speedup: float | None
    output_matched: bool | None
    output_bytes: int


def benchmark_sql_parsing_normalization(
    *,
    iterations: int = 50,
    engine: str = "postgresql",
    sql: str = SQL_PARSING_NORMALIZATION_SAMPLE,
) -> RuntimeBenchmarkResult:
    """Benchmark SQL parsing, table checks, mutation checks, and formatting."""

    if iterations <= 0:
        raise ValueError("iterations must be positive")

    statement_count = 0
    formatted_bytes = 0
    table_check_matched = False
    has_mutation = False
    start = default_timer()

    for _ in range(iterations):
        script = SQLScript(sql, engine)
        formatted = script.format(comments=False)
        statement_count = len(script.statements)
        formatted_bytes = len(formatted.encode("utf-8"))
        table_check_matched = script.check_tables_present({"orders", "customers"})
        has_mutation = script.has_mutation()

    duration_ms = (default_timer() - start) * 1000

    return RuntimeBenchmarkResult(
        area="sql_parsing_normalization",
        operation="parse_format_table_check",
        engine=engine,
        iterations=iterations,
        duration_ms=duration_ms,
        operations_per_second=iterations / (duration_ms / 1000)
        if duration_ms > 0
        else 0,
        statement_count=statement_count,
        formatted_bytes=formatted_bytes,
        table_check_matched=table_check_matched,
        has_mutation=has_mutation,
    )


def benchmark_sql_whitespace_kernel(
    *,
    iterations: int = 50,
    sql: str = SQL_PARSING_NORMALIZATION_SAMPLE,
) -> RuntimeKernelBenchmarkResult:
    """Benchmark Python and optional Rust SQL whitespace normalization kernels."""

    if iterations <= 0:
        raise ValueError("iterations must be positive")

    python_output = ""
    start = default_timer()
    for _ in range(iterations):
        python_output = normalize_sql_whitespace(sql, use_rust=False)
    python_duration_ms = (default_timer() - start) * 1000

    rust_available = rust_sql_kernel_available()
    rust_duration_ms = None
    rust_operations_per_second = None
    speedup = None
    output_matched = None

    if rust_available:
        rust_output = ""
        start = default_timer()
        for _ in range(iterations):
            rust_output = normalize_sql_whitespace(sql, use_rust=True)
        rust_duration_ms = (default_timer() - start) * 1000
        rust_operations_per_second = (
            iterations / (rust_duration_ms / 1000) if rust_duration_ms > 0 else 0
        )
        output_matched = rust_output == python_output
        speedup = (
            python_duration_ms / rust_duration_ms
            if rust_duration_ms and rust_duration_ms > 0
            else None
        )

    return RuntimeKernelBenchmarkResult(
        area="sql_whitespace_kernel",
        operation="normalize_whitespace",
        iterations=iterations,
        python_duration_ms=python_duration_ms,
        python_operations_per_second=iterations / (python_duration_ms / 1000)
        if python_duration_ms > 0
        else 0,
        rust_available=rust_available,
        rust_duration_ms=rust_duration_ms,
        rust_operations_per_second=rust_operations_per_second,
        speedup=speedup,
        output_matched=output_matched,
        output_bytes=len(python_output.encode("utf-8")),
    )

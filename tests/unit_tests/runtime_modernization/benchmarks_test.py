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

import pytest

from superset.runtime_modernization.benchmarks import (
    benchmark_sql_parsing_normalization,
)


def test_benchmark_sql_parsing_normalization_runs_superset_parser_path() -> None:
    """SQL benchmark exercises parse, format, table check, and mutation check."""

    result = benchmark_sql_parsing_normalization(iterations=1)

    assert result.area == "sql_parsing_normalization"
    assert result.operation == "parse_format_table_check"
    assert result.engine == "postgresql"
    assert result.iterations == 1
    assert result.duration_ms >= 0
    assert result.operations_per_second >= 0
    assert result.statement_count == 1
    assert result.formatted_bytes > 0
    assert result.table_check_matched is True
    assert result.has_mutation is False


def test_benchmark_sql_parsing_normalization_rejects_invalid_iterations() -> None:
    """Benchmark iterations must be positive."""

    with pytest.raises(ValueError, match="iterations must be positive"):
        benchmark_sql_parsing_normalization(iterations=0)

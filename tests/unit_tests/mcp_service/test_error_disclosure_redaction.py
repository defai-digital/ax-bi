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
"""MCP error schemas must redact SQL/schema details before LLM delivery."""

from __future__ import annotations

from axbi.mcp_service.common.error_schemas import MCPResourceError, sanitize_error_text
from axbi.mcp_service.utils.error_sanitization import _sanitize_validation_error


def test_sanitize_validation_error_redacts_sql_select() -> None:
    raw = "Failed: SELECT password FROM users WHERE id=1"
    out = _sanitize_validation_error(Exception(raw), log_original=False)
    assert "password" not in out.lower() or "REDACTED" in out
    assert "SELECT" in out.upper()


def test_sanitize_validation_error_redacts_table_name() -> None:
    raw = "relation table secret_payroll does not exist"
    out = _sanitize_validation_error(Exception(raw), log_original=False)
    assert "secret_payroll" not in out
    assert "REDACTED" in out or "Validation" in out


def test_sanitize_error_text_redacts_then_wraps() -> None:
    raw = "Failed to get dataset: table 'orders_secret' not found"
    out = sanitize_error_text(raw)
    assert out is not None
    assert "orders_secret" not in out
    # LLM context wrapper still applied
    assert "UNTRUSTED" in out or "REDACTED" in out


def test_mcp_resource_error_create_redacts_sql() -> None:
    err = MCPResourceError.create(
        error="query failed: SELECT ssn FROM employees WHERE ssn IS NOT NULL",
        error_type="InternalError",
    )
    assert "ssn" not in err.error.lower() or "REDACTED" in err.error
    assert "SELECT" in err.error.upper() or "REDACTED" in err.error

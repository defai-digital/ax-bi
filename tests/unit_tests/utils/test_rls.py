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

from unittest.mock import MagicMock, patch

import pytest

from axbi.utils.rls import collect_rls_predicates_for_sql


def test_collect_rls_predicates_fails_closed_on_parse_error() -> None:
    """An unparseable virtual query must not receive an RLS-free cache key."""
    database = MagicMock()
    database.db_engine_spec.engine = "postgresql"

    with (
        patch(
            "axbi.sql.parse.SQLScript",
            side_effect=RuntimeError("parser unavailable"),
        ),
        pytest.raises(RuntimeError, match="parser unavailable"),
    ):
        collect_rls_predicates_for_sql(
            "SELECT * FROM sensitive_table",
            database,
            catalog=None,
            schema="public",
        )


def test_collect_rls_predicates_fails_closed_on_lookup_error() -> None:
    """A failed RLS lookup must abort instead of collapsing user cache keys."""
    database = MagicMock()
    database.db_engine_spec.engine = "postgresql"
    database.get_default_catalog.return_value = None

    with (
        patch(
            "axbi.utils.rls.get_predicates_for_table",
            side_effect=RuntimeError("metadata database unavailable"),
        ),
        pytest.raises(RuntimeError, match="metadata database unavailable"),
    ):
        collect_rls_predicates_for_sql(
            "SELECT * FROM sensitive_table",
            database,
            catalog=None,
            schema="public",
        )

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
"""Unit tests for resource-level authorization in QueryEstimationCommand."""

from typing import cast
from unittest.mock import MagicMock, patch

import pytest

from axbi.commands.sql_lab.estimate import (
    EstimateQueryCostType,
    QueryEstimationCommand,
)
from axbi.errors import AxBIError, AxBIErrorType, ErrorLevel
from axbi.exceptions import AxBIErrorException, AxBISecurityException


def _make_params(**kwargs: object) -> EstimateQueryCostType:
    base: EstimateQueryCostType = {
        "database_id": 1,
        "sql": "SELECT 1",
        "template_params": {},
        "catalog": None,
        "schema": None,
    }
    base.update(kwargs)  # type: ignore[typeddict-item]
    return base


def _security_exception() -> AxBISecurityException:
    return AxBISecurityException(
        AxBIError(
            message="Access denied",
            error_type=AxBIErrorType.DATASOURCE_SECURITY_ACCESS_ERROR,
            level=ErrorLevel.WARNING,
        )
    )


# ---------------------------------------------------------------------------
# Existing behaviour: database not found
# ---------------------------------------------------------------------------


@patch("axbi.commands.sql_lab.estimate.security_manager", new_callable=MagicMock)
@patch("axbi.commands.sql_lab.estimate.db")
def test_validate_raises_when_database_not_found(
    mock_db: MagicMock,
    mock_security_manager: MagicMock,
) -> None:
    """404 is raised before the access check when the database does not exist."""
    mock_db.session.get.return_value = None

    command = QueryEstimationCommand(_make_params())
    with pytest.raises(AxBIErrorException) as exc_info:
        command.validate()

    assert exc_info.value.error.error_type == AxBIErrorType.RESULTS_BACKEND_ERROR
    mock_security_manager.raise_for_access.assert_not_called()


# ---------------------------------------------------------------------------
# New behaviour: database exists but caller has no access
# ---------------------------------------------------------------------------


@patch("axbi.commands.sql_lab.estimate.security_manager", new_callable=MagicMock)
@patch("axbi.commands.sql_lab.estimate.db")
def test_validate_raises_when_database_access_denied(
    mock_db: MagicMock,
    mock_security_manager: MagicMock,
) -> None:
    """AxBISecurityException propagates when raise_for_access denies access."""
    mock_database = MagicMock()
    mock_db.session.get.return_value = mock_database
    mock_security_manager.raise_for_access.side_effect = _security_exception()

    command = QueryEstimationCommand(_make_params())
    with pytest.raises(AxBISecurityException):
        command.validate()

    mock_security_manager.raise_for_access.assert_called_once_with(
        database=mock_database
    )


# ---------------------------------------------------------------------------
# New behaviour: authorised caller succeeds
# ---------------------------------------------------------------------------


@patch("axbi.commands.sql_lab.estimate.security_manager", new_callable=MagicMock)
@patch("axbi.commands.sql_lab.estimate.db")
def test_validate_succeeds_for_authorised_user(
    mock_db: MagicMock,
    mock_security_manager: MagicMock,
) -> None:
    """validate() completes without error when access is granted."""
    mock_database = MagicMock()
    mock_db.session.get.return_value = mock_database
    mock_security_manager.raise_for_access.return_value = None

    command = QueryEstimationCommand(_make_params())
    command.validate()  # must not raise

    mock_security_manager.raise_for_access.assert_called_once_with(
        database=mock_database
    )


# ---------------------------------------------------------------------------
# Kwarg correctness
# ---------------------------------------------------------------------------


@patch("axbi.commands.sql_lab.estimate.security_manager", new_callable=MagicMock)
@patch("axbi.commands.sql_lab.estimate.db")
def test_raise_for_access_called_with_correct_database(
    mock_db: MagicMock,
    mock_security_manager: MagicMock,
) -> None:
    """The database object fetched from the session is passed to raise_for_access."""
    mock_database = MagicMock()
    mock_database.id = 42
    mock_db.session.get.return_value = mock_database
    mock_security_manager.raise_for_access.return_value = None

    command = QueryEstimationCommand(_make_params(database_id=42))
    command.validate()

    call_kwargs = mock_security_manager.raise_for_access.call_args.kwargs
    assert call_kwargs["database"] is mock_database


# ---------------------------------------------------------------------------
# SQL security controls applied on the estimate path (parity with executor)
# ---------------------------------------------------------------------------


def _make_command_with_db(
    sql: str, *, allow_dml: bool = False, engine: str = "postgresql"
) -> QueryEstimationCommand:
    command = QueryEstimationCommand(_make_params(sql=sql))
    command._database = MagicMock()
    command._database.db_engine_spec.engine = engine
    command._database.allow_dml = allow_dml
    command._catalog = None
    command._schema = ""
    return command


@patch("axbi.commands.sql_lab.estimate.app")
def test_apply_sql_security_blocks_dml_when_not_allowed(mock_app: MagicMock) -> None:
    mock_app.config = {"DISALLOWED_SQL_FUNCTIONS": {}, "DISALLOWED_SQL_TABLES": {}}
    from axbi.exceptions import AxBIDMLNotAllowedException

    command = _make_command_with_db("INSERT INTO t VALUES (1)", allow_dml=False)
    with pytest.raises(AxBIDMLNotAllowedException):
        command._apply_sql_security("INSERT INTO t VALUES (1)")


@patch("axbi.commands.sql_lab.estimate.app")
def test_apply_sql_security_allows_dml_when_enabled(mock_app: MagicMock) -> None:
    mock_app.config = {"DISALLOWED_SQL_FUNCTIONS": {}, "DISALLOWED_SQL_TABLES": {}}
    command = _make_command_with_db("INSERT INTO t VALUES (1)", allow_dml=True)
    # No exception; SQL returned unchanged (RLS disabled by default).
    assert command._apply_sql_security("INSERT INTO t VALUES (1)")


@patch("axbi.commands.sql_lab.estimate.app")
def test_apply_sql_security_blocks_disallowed_table(mock_app: MagicMock) -> None:
    mock_app.config = {
        "DISALLOWED_SQL_FUNCTIONS": {},
        "DISALLOWED_SQL_TABLES": {"postgresql": {"secrets"}},
    }
    from axbi.exceptions import AxBIDisallowedSQLTableException

    command = _make_command_with_db("SELECT * FROM secrets", allow_dml=True)
    with pytest.raises(AxBIDisallowedSQLTableException):
        command._apply_sql_security("SELECT * FROM secrets")


@patch("axbi.commands.sql_lab.estimate.app")
def test_apply_sql_security_blocks_disallowed_function(mock_app: MagicMock) -> None:
    """A disallowed function cannot be probed via cost estimation either."""
    mock_app.config = {
        "DISALLOWED_SQL_FUNCTIONS": {"postgresql": {"PG_SLEEP"}},
        "DISALLOWED_SQL_TABLES": {},
    }
    from axbi.exceptions import AxBIDisallowedSQLFunctionException

    command = _make_command_with_db("SELECT pg_sleep(1)", allow_dml=True)
    with pytest.raises(AxBIDisallowedSQLFunctionException):
        command._apply_sql_security("SELECT pg_sleep(1)")


@patch("axbi.commands.sql_lab.estimate.app")
def test_apply_sql_security_allows_benign_select(mock_app: MagicMock) -> None:
    """A benign statement passes through unchanged (no false positives)."""
    mock_app.config = {"DISALLOWED_SQL_FUNCTIONS": {}, "DISALLOWED_SQL_TABLES": {}}
    command = _make_command_with_db("SELECT 1", allow_dml=False)
    # No disallowed content, no mutation, RLS disabled -> returned unchanged.
    assert command._apply_sql_security("SELECT 1") == "SELECT 1"


@patch("axbi.commands.sql_lab.estimate.apply_rls")
@patch("axbi.commands.sql_lab.estimate.Query")
@patch("axbi.commands.sql_lab.estimate.object_session")
@patch("axbi.commands.sql_lab.estimate.is_feature_enabled", return_value=True)
@patch("axbi.commands.sql_lab.estimate.app")
def test_apply_sql_security_injects_rls_when_enabled(
    mock_app: MagicMock,
    mock_is_feature_enabled: MagicMock,
    mock_object_session: MagicMock,
    mock_query: MagicMock,
    mock_apply_rls: MagicMock,
) -> None:
    """With RLS_IN_SQLLAB enabled, RLS predicates are applied per statement so
    the estimate reflects the constrained query the user could actually run."""
    mock_app.config = {"DISALLOWED_SQL_FUNCTIONS": {}, "DISALLOWED_SQL_TABLES": {}}
    command = _make_command_with_db("SELECT * FROM t", allow_dml=False)

    result = command._apply_sql_security("SELECT * FROM t")

    mock_is_feature_enabled.assert_called_with("RLS_IN_SQLLAB")
    mock_apply_rls.assert_called_once()
    # The probe Query is expunged from whichever session it is attached to, so
    # its (deliberately incomplete) row can't autoflush into the session when
    # apply_rls queries below.
    mock_object_session.assert_called_once_with(mock_query.return_value)
    mock_object_session.return_value.expunge.assert_called_once_with(
        mock_query.return_value
    )
    assert isinstance(result, str)


@patch("axbi.commands.sql_lab.estimate.Query")
@patch("axbi.commands.sql_lab.estimate.db")
@patch("axbi.commands.sql_lab.estimate.apply_rls")
@patch("axbi.commands.sql_lab.estimate.is_feature_enabled", return_value=True)
@patch("axbi.commands.sql_lab.estimate.app")
def test_apply_sql_security_resolves_default_schema_for_rls(
    mock_app: MagicMock,
    mock_is_feature_enabled: MagicMock,
    mock_apply_rls: MagicMock,
    mock_db: MagicMock,
    mock_query: MagicMock,
) -> None:
    """When no catalog/schema is supplied, RLS must be applied against the
    database's *resolved* default catalog/schema — mirroring the execution path
    (``SQLExecutor`` / ``sql_lab.execute_sql_statements``). Passing the raw
    ``""``/``None`` would let unqualified tables dodge RLS predicates that the
    real query enforces, defeating the security parity goal of this command.
    """
    mock_app.config = {"DISALLOWED_SQL_FUNCTIONS": {}, "DISALLOWED_SQL_TABLES": {}}
    command = _make_command_with_db("SELECT * FROM t", allow_dml=False)
    database = cast(MagicMock, command._database)
    # Caller passed nothing: schema is "" and catalog is None.
    command._schema = ""
    command._catalog = None
    database.get_default_catalog.return_value = "default_catalog"
    database.get_default_schema_for_query.return_value = "public"

    command._apply_sql_security("SELECT * FROM t")

    # Default catalog/schema are resolved before injection, in the same order
    # as the executor (catalog first, then schema derived per-query). The schema
    # goes through ``get_default_schema_for_query`` so engine-specific per-query
    # security gates (e.g. the Postgres ``search_path`` check) run as well.
    database.get_default_catalog.assert_called_once_with()
    database.get_default_schema_for_query.assert_called_once()

    # RLS is applied with the *resolved* values, never the raw ""/None.
    # apply_rls(database, catalog, schema, statement)
    call_args = mock_apply_rls.call_args.args
    assert call_args[1] == "default_catalog"
    assert call_args[2] == "public"


@patch("axbi.commands.sql_lab.estimate.Query")
@patch("axbi.commands.sql_lab.estimate.db")
@patch("axbi.commands.sql_lab.estimate.apply_rls")
@patch("axbi.commands.sql_lab.estimate.is_feature_enabled", return_value=True)
@patch("axbi.commands.sql_lab.estimate.app")
def test_apply_sql_security_respects_explicit_catalog_schema(
    mock_app: MagicMock,
    mock_is_feature_enabled: MagicMock,
    mock_apply_rls: MagicMock,
    mock_db: MagicMock,
    mock_query: MagicMock,
) -> None:
    """An explicitly supplied catalog short-circuits default-catalog resolution,
    and the explicit schema wins as the RLS target — but the schema resolver
    ``get_default_schema_for_query`` is still invoked so the engine's per-query
    security gate runs even when a schema is pinned (parity with the executor,
    which calls it unconditionally)."""
    mock_app.config = {"DISALLOWED_SQL_FUNCTIONS": {}, "DISALLOWED_SQL_TABLES": {}}
    command = _make_command_with_db("SELECT * FROM t", allow_dml=False)
    database = cast(MagicMock, command._database)
    command._catalog = "my_catalog"
    command._schema = "my_schema"

    command._apply_sql_security("SELECT * FROM t")

    # Explicit catalog wins, so the default-catalog lookup is skipped...
    database.get_default_catalog.assert_not_called()
    # ...but the schema gate must run even when a schema is pinned, otherwise an
    # explicit-schema estimate could smuggle a ``SET search_path`` past the gate
    # the executor enforces.
    database.get_default_schema_for_query.assert_called_once()
    call_args = mock_apply_rls.call_args.args
    assert call_args[1] == "my_catalog"
    assert call_args[2] == "my_schema"


@patch("axbi.commands.sql_lab.estimate.Query")
@patch("axbi.commands.sql_lab.estimate.db")
@patch("axbi.commands.sql_lab.estimate.apply_rls")
@patch("axbi.commands.sql_lab.estimate.is_feature_enabled", return_value=True)
@patch("axbi.commands.sql_lab.estimate.app")
def test_apply_sql_security_propagates_engine_schema_gate(
    mock_app: MagicMock,
    mock_is_feature_enabled: MagicMock,
    mock_apply_rls: MagicMock,
    mock_db: MagicMock,
    mock_query: MagicMock,
) -> None:
    """Default-schema resolution goes through ``get_default_schema_for_query``,
    so an engine-specific per-query security gate (e.g. the Postgres
    ``search_path`` check that rejects ``SET search_path = ...``) is enforced on
    the estimate path too, rather than being silently bypassed.
    """
    mock_app.config = {"DISALLOWED_SQL_FUNCTIONS": {}, "DISALLOWED_SQL_TABLES": {}}
    command = _make_command_with_db(
        "SET search_path = secret; SELECT * FROM t", allow_dml=True
    )
    database = cast(MagicMock, command._database)
    command._schema = ""
    command._catalog = None
    database.get_default_catalog.return_value = "default_catalog"
    database.get_default_schema_for_query.side_effect = _security_exception()

    with pytest.raises(AxBISecurityException):
        command._apply_sql_security("SET search_path = secret; SELECT * FROM t")

    # RLS injection must not happen once the schema gate has rejected the query.
    mock_apply_rls.assert_not_called()

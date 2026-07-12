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

"""
SQL Lab error responses must not include stacktrace information.

SQL Lab query execution errors should preserve tracebacks in server logs so
operators can debug failures, but returned payloads must not expose raw Python
tracebacks to clients.

Both the legacy ``axbi.sql_lab.handle_query_error`` function and the
newer ``axbi.sql.execution.celery_task._handle_query_error`` share the
same pattern and are covered here.

Specific failing call sites (as of the issue being filed):
- ``axbi/sql_lab.py``: ``logger.debug("Query %d: %s", query_id, ex)``
  in the outer ``except`` of ``get_sql_results``
- ``axbi/sql/execution/celery_task.py``: same pattern in
  ``execute_sql_task``
- Neither ``handle_query_error`` nor ``_handle_query_error`` includes a
  ``stacktrace`` key in the returned payload dict.

Reference: https://github.com/defai-digital/ax-bi/issues/28248
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_query_mock() -> MagicMock:
    """Return a minimal Query mock that satisfies handle_query_error."""
    query = MagicMock()
    query.status = "running"
    query.end_time = None
    query.tmp_table_name = "tmp"
    query.error_message = None
    query.database.db_engine_spec.extract_errors.return_value = []
    query.database.unique_name = "test_db"
    return query


# ---------------------------------------------------------------------------
# Legacy sql_lab.handle_query_error — no stacktrace when SHOW_STACKTRACE=True
# ---------------------------------------------------------------------------


def test_legacy_handle_query_error_payload_omits_stacktrace_when_enabled() -> None:
    """
    The dict returned by ``handle_query_error`` must NOT include a ``stacktrace``
    key when SHOW_STACKTRACE is True.
    """
    config = {"TROUBLESHOOTING_LINK": None, "SHOW_STACKTRACE": True}
    with (
        patch("axbi.sql_lab.db") as mock_db,
        patch("axbi.sql_lab.app") as mock_app,
    ):
        mock_app.config = config
        mock_db.session = MagicMock()

        from axbi.sql_lab import handle_query_error

        query = _make_query_mock()
        try:
            raise RuntimeError("boom")
        except RuntimeError as ex:
            payload = handle_query_error(ex, query)

    assert "stacktrace" not in payload, (
        "handle_query_error must NOT include 'stacktrace' when SHOW_STACKTRACE=True "
        "to avoid exposing internal details to clients. "
        f"Got keys: {list(payload.keys())}"
    )


# ---------------------------------------------------------------------------
# Legacy sql_lab.handle_query_error — no stacktrace when SHOW_STACKTRACE=False
# ---------------------------------------------------------------------------


def test_legacy_handle_query_error_payload_omits_stacktrace_when_disabled() -> None:
    """
    The dict returned by ``handle_query_error`` must NOT include a
    ``stacktrace`` key when SHOW_STACKTRACE is False (the default).

    This prevents raw Python tracebacks (file paths, module structure,
    library versions) from being exposed to unprivileged SQL Lab users.
    """
    config = {"TROUBLESHOOTING_LINK": None, "SHOW_STACKTRACE": False}
    with (
        patch("axbi.sql_lab.db") as mock_db,
        patch("axbi.sql_lab.app") as mock_app,
    ):
        mock_app.config = config
        mock_db.session = MagicMock()

        from axbi.sql_lab import handle_query_error

        query = _make_query_mock()
        try:
            raise RuntimeError("boom")
        except RuntimeError as ex:
            payload = handle_query_error(ex, query)

    assert "stacktrace" not in payload, (
        "handle_query_error must NOT include 'stacktrace' when SHOW_STACKTRACE=False "
        "to avoid exposing internal details to unprivileged users. "
        f"Got keys: {list(payload.keys())}"
    )


# ---------------------------------------------------------------------------
# Legacy sql_lab — outer except in get_sql_results logs exc_info
# ---------------------------------------------------------------------------


def test_legacy_get_sql_results_outer_except_logs_exc_info() -> None:
    """
    The outer ``except Exception`` block in ``get_sql_results`` must log with
    ``exc_info=True`` (or call ``logger.exception``) so that the full Python
    traceback appears in Celery worker logs.

    The current code at the time of filing calls:
        logger.debug("Query %d: %s", query_id, ex)
    which silently discards the traceback.

    Regression for #28248.
    """
    # Inspect the source of get_sql_results to detect the logging call.
    # This is a structural test: we verify the outer except block uses
    # exc_info rather than a plain debug-level call.
    import inspect

    import axbi.sql_lab as sql_lab_module

    source = inspect.getsource(sql_lab_module.get_sql_results)

    # The outer except must NOT rely solely on debug-without-exc_info.
    # We check that the function uses logger.exception, or passes exc_info=True.
    uses_exc_info = (
        "logger.exception(" in source
        or "exc_info=True" in source
        or "exc_info=ex" in source
    )

    assert uses_exc_info, (
        "get_sql_results must use logger.exception() or pass exc_info=True "
        "in the outer except block so the traceback is preserved in Celery "
        "worker logs (regression for #28248). "
        "Found source:\n" + source
    )


# ---------------------------------------------------------------------------
# New celery_task._handle_query_error — no stacktrace when SHOW_STACKTRACE=True
# ---------------------------------------------------------------------------


def test_new_handle_query_error_payload_omits_stacktrace_when_enabled() -> None:
    """
    The dict returned by
    ``axbi.sql.execution.celery_task._handle_query_error`` must NOT include a
    ``stacktrace`` key when SHOW_STACKTRACE is True.
    """
    from axbi.sql.execution import celery_task as ct

    query = _make_query_mock()
    config = {"TROUBLESHOOTING_LINK": None, "SHOW_STACKTRACE": True}

    with patch.object(ct, "db") as mock_db, patch.object(ct, "app") as mock_app:
        mock_app.config = config
        mock_db.session = MagicMock()

        try:
            raise RuntimeError("boom in new path")
        except RuntimeError as ex:
            payload = ct._handle_query_error(ex, query)

    assert "stacktrace" not in payload, (
        "_handle_query_error must NOT include 'stacktrace' when SHOW_STACKTRACE=True "
        "to avoid exposing internal details to clients. "
        f"Got keys: {list(payload.keys())}"
    )


# ---------------------------------------------------------------------------
# New celery_task._handle_query_error — no stacktrace when SHOW_STACKTRACE=False
# ---------------------------------------------------------------------------


def test_new_handle_query_error_payload_omits_stacktrace_when_disabled() -> None:
    """
    The dict returned by
    ``axbi.sql.execution.celery_task._handle_query_error`` must NOT
    include a ``stacktrace`` key when SHOW_STACKTRACE is False (the default).

    This prevents raw Python tracebacks from being exposed to unprivileged users.
    """
    from axbi.sql.execution import celery_task as ct

    query = _make_query_mock()
    config = {"TROUBLESHOOTING_LINK": None, "SHOW_STACKTRACE": False}

    with patch.object(ct, "db") as mock_db, patch.object(ct, "app") as mock_app:
        mock_app.config = config
        mock_db.session = MagicMock()

        try:
            raise RuntimeError("boom in new path")
        except RuntimeError as ex:
            payload = ct._handle_query_error(ex, query)

    assert "stacktrace" not in payload, (
        "_handle_query_error must NOT include 'stacktrace' when SHOW_STACKTRACE=False "
        "to avoid exposing internal details to unprivileged users. "
        f"Got keys: {list(payload.keys())}"
    )


# ---------------------------------------------------------------------------
# New celery_task — outer except in execute_sql_task logs exc_info
# ---------------------------------------------------------------------------


def test_new_execute_sql_task_outer_except_logs_exc_info() -> None:
    """
    The outer ``except Exception`` block in ``execute_sql_task`` must log with
    ``exc_info=True`` so the full traceback appears in Celery worker logs.

    Regression for #28248.
    """
    import inspect

    from axbi.sql.execution import celery_task as ct

    source = inspect.getsource(ct.execute_sql_task)

    uses_exc_info = (
        "logger.exception(" in source
        or "exc_info=True" in source
        or "exc_info=ex" in source
    )

    assert uses_exc_info, (
        "execute_sql_task must use logger.exception() or pass exc_info=True "
        "in the outer except block so the traceback is preserved in Celery "
        "worker logs (regression for #28248). "
        "Found source:\n" + source
    )

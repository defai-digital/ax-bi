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
Celery task for async SQL execution.

This module provides the Celery task for executing SQL queries asynchronously.
It is used by SQLExecutor.execute_async() to run queries in the background.
"""

from __future__ import annotations

import dataclasses
import logging
import uuid
from typing import Any

import msgpack
from celery.exceptions import SoftTimeLimitExceeded
from flask import current_app as app, has_app_context
from flask_babel import gettext as __

from axbi import (
    db,
    results_backend,
    security_manager,
)
from axbi.common.db_query_status import QueryStatus
from axbi.constants import QUERY_CANCEL_KEY
from axbi.errors import AxBIError, AxBIErrorType, ErrorLevel
from axbi.exceptions import (
    AxBIErrorException,
    AxBIErrorsException,
)
from axbi.extensions import celery_app
from axbi.models.sql_lab import Query
from axbi.result_set import AxBIResultSet
from axbi.sql.execution.executor import execute_sql_with_cursor
from axbi.sql.parse import SQLScript
from axbi.sqllab.utils import write_ipc_buffer
from axbi.utils import json
from axbi.utils.core import override_user, zlib_compress
from axbi.utils.dates import now_as_float
from axbi.utils.decorators import stats_timing
from axbi.utils.session_lifecycle import commit_session, reset_session_safely

logger = logging.getLogger(__name__)

BYTES_IN_MB = 1024 * 1024


def _get_query(query_id: int) -> Query:
    """Get the query by ID."""
    return db.session.query(Query).filter_by(id=query_id).one()


def _handle_query_error(
    ex: Exception,
    query: Query,
    payload: dict[str, Any] | None = None,
    prefix_message: str = "",
) -> dict[str, Any]:
    """Handle error while processing the SQL query."""
    payload = payload or {}
    msg = f"{prefix_message} {str(ex)}".strip()
    query.error_message = msg
    query.tmp_table_name = None
    # Preserve TIMED_OUT status if already set (from SoftTimeLimitExceeded handler)
    if query.status != QueryStatus.TIMED_OUT:
        query.status = QueryStatus.FAILED

    if not query.end_time:
        query.end_time = now_as_float()

    # Extract DB-specific errors
    if isinstance(ex, AxBIErrorException):
        errors = [ex.error]
    elif isinstance(ex, AxBIErrorsException):
        errors = ex.errors
    else:
        errors = query.database.db_engine_spec.extract_errors(
            str(ex), database_name=query.database.unique_name
        )

    errors_payload = [dataclasses.asdict(error) for error in errors]
    if errors:
        query.set_extra_json_key("errors", errors_payload)

    # Soft commit: a metadata write failure while recording a prior query
    # error must not hide the original SQL failure from the client, but must
    # still roll back so the scoped session is not left poisoned.
    if not commit_session(
        db.session,
        context=f"sql celery _handle_query_error query_id={getattr(query, 'id', None)}",
        soft=True,
    ):
        logger.error(
            "Failed to persist FAILED status for query id=%s",
            getattr(query, "id", None),
        )

    payload.update(
        {"status": query.status.value, "error": msg, "errors": errors_payload}
    )
    if troubleshooting_link := app.config.get("TROUBLESHOOTING_LINK"):
        payload["link"] = troubleshooting_link
    return payload


def _serialize_payload(payload: dict[Any, Any]) -> bytes:
    """Serialize payload for storage based on RESULTS_BACKEND_USE_MSGPACK config."""
    from axbi import results_backend_use_msgpack

    if results_backend_use_msgpack:
        return msgpack.dumps(payload, default=json.json_iso_dttm_ser, use_bin_type=True)
    return json.dumps(payload, default=json.json_iso_dttm_ser, ignore_nan=True).encode(
        "utf-8"
    )


def _prepare_statement_blocks(
    rendered_query: str,
    db_engine_spec: Any,
) -> tuple[SQLScript, list[str]]:
    """
    Parse SQL and build statement blocks for execution.

    Some databases (like BigQuery and Kusto) do not persist state across multiple
    statements if they're run separately (especially when using `NullPool`), so we run
    the query as a single block when the database engine spec requires it.
    """
    parsed_script = SQLScript(rendered_query, engine=db_engine_spec.engine)

    # Build statement blocks for execution
    if db_engine_spec.run_multiple_statements_as_one:
        blocks = [parsed_script.format(comments=db_engine_spec.allows_sql_comments)]
    else:
        blocks = [
            statement.format(comments=db_engine_spec.allows_sql_comments)
            for statement in parsed_script.statements
        ]

    return parsed_script, blocks


def _finalize_successful_query(
    query: Query,
    original_script: SQLScript,
    execution_results: list[tuple[str, AxBIResultSet | None, float, int]],
    payload: dict[str, Any],
    total_execution_time_ms: float,
) -> None:
    """Update query metadata and payload after successful execution."""
    # Calculate total rows across all statements
    total_rows = 0
    statements_data: list[dict[str, Any]] = []

    # Get original statement strings
    original_sqls = [stmt.format() for stmt in original_script.statements]

    for orig_sql, (exec_sql, result_set, exec_time, rowcount) in zip(
        original_sqls, execution_results, strict=False
    ):
        if result_set is not None:
            # SELECT statement
            total_rows += result_set.size
            data, columns = _serialize_result_set(result_set)
            statements_data.append(
                {
                    "original_sql": orig_sql,
                    "executed_sql": exec_sql,
                    "data": data,
                    "columns": columns,
                    "row_count": result_set.size,
                    "execution_time_ms": exec_time,
                }
            )
        else:
            # DML statement - no data, just row count
            statements_data.append(
                {
                    "original_sql": orig_sql,
                    "executed_sql": exec_sql,
                    "data": None,
                    "columns": [],
                    "row_count": rowcount,
                    "execution_time_ms": exec_time,
                }
            )

    query.rows = total_rows
    query.progress = 100
    query.set_extra_json_key("progress", None)
    # Store columns from last statement (for compatibility)
    if execution_results and execution_results[-1][1] is not None:
        query.set_extra_json_key("columns", execution_results[-1][1].columns)
    query.end_time = now_as_float()

    payload.update(
        {
            "status": QueryStatus.SUCCESS.value,
            "statements": statements_data,
            "total_execution_time_ms": total_execution_time_ms,
            "query": query.to_dict(),
        }
    )
    payload["query"]["state"] = QueryStatus.SUCCESS.value


def _store_results_in_backend(
    query: Query,
    payload: dict[str, Any],
    database: Any,
) -> None:
    """Store query results in the results backend."""
    key = str(uuid.uuid4())
    payload["query"]["resultsKey"] = key
    logger.info(
        "Query %s: Storing results in results backend, key: %s",
        str(query.id),
        key,
    )
    stats_logger = app.config["STATS_LOGGER"]
    with stats_timing("sqllab.query.results_backend_write", stats_logger):
        with stats_timing(
            "sqllab.query.results_backend_write_serialization", stats_logger
        ):
            serialized_payload = _serialize_payload(payload)

            # Check payload size limit
            if sql_lab_payload_max_mb := app.config.get("SQLLAB_PAYLOAD_MAX_MB"):
                serialized_payload_size = len(serialized_payload)
                max_bytes = sql_lab_payload_max_mb * BYTES_IN_MB

                if serialized_payload_size > max_bytes:
                    logger.info("Result size exceeds the allowed limit.")
                    raise AxBIErrorException(
                        AxBIError(
                            message=(
                                f"Result size "
                                f"({serialized_payload_size / BYTES_IN_MB:.2f} MB) "
                                f"exceeds the allowed limit of "
                                f"{sql_lab_payload_max_mb} MB."
                            ),
                            error_type=AxBIErrorType.RESULT_TOO_LARGE_ERROR,
                            level=ErrorLevel.ERROR,
                        )
                    )

        cache_timeout = database.cache_timeout
        if cache_timeout is None:
            cache_timeout = app.config["CACHE_DEFAULT_TIMEOUT"]

        compressed = zlib_compress(serialized_payload)
        logger.debug("*** serialized payload size: %i", len(serialized_payload))
        logger.debug("*** compressed payload size: %i", len(compressed))

        write_success = results_backend.set(key, compressed, cache_timeout)
        if not write_success:
            logger.error(
                "Query %s: Failed to store results in backend, key: %s",
                str(query.id),
                key,
            )
            stats_logger.incr("sqllab.results_backend.write_failure")
            query.results_key = None
            query.status = QueryStatus.FAILED
            query.error_message = (
                "Failed to store query results in the results backend. "
                "Please try again or contact your administrator."
            )
            commit_session(
                db.session,
                context=f"sql celery results_backend failure query_id={query.id}",
                soft=True,
            )
            raise AxBIErrorException(
                AxBIError(
                    message=__("Failed to store query results. Please try again."),
                    error_type=AxBIErrorType.RESULTS_BACKEND_ERROR,
                    level=ErrorLevel.ERROR,
                )
            )
        else:
            query.results_key = key
            logger.info(
                "Query %s: Successfully stored results in backend, key: %s",
                str(query.id),
                key,
            )


def _serialize_result_set(
    result_set: AxBIResultSet,
) -> tuple[bytes | list[Any], list[Any]]:
    """
    Serialize result set based on RESULTS_BACKEND_USE_MSGPACK config.

    When msgpack is enabled, uses Apache Arrow IPC format for efficiency.
    Otherwise, falls back to JSON-serializable records.

    :param result_set: Query result set to serialize
    :returns: Tuple of (serialized_data, columns)
    """
    from axbi import results_backend_use_msgpack
    from axbi.dataframe import df_to_records

    if results_backend_use_msgpack:
        if has_app_context():
            stats_logger = app.config["STATS_LOGGER"]
            with stats_timing(
                "sqllab.query.results_backend_pa_serialization", stats_logger
            ):
                data: bytes | list[Any] = write_ipc_buffer(
                    result_set.pa_table
                ).to_pybytes()
        else:
            data = write_ipc_buffer(result_set.pa_table).to_pybytes()
    else:
        df = result_set.to_pandas_df()
        data = df_to_records(df) or []

    return (data, result_set.columns)


@celery_app.task(name="query_execution.execute_sql")
def execute_sql_task(
    query_id: int,
    rendered_query: str,
    username: str | None = None,
    start_time: float | None = None,
) -> dict[str, Any] | None:
    """
    Execute SQL query asynchronously via Celery.

    This task is used by SQLExecutor.execute_async() to run queries
    in background workers with full feature support.

    :param query_id: ID of the Query model
    :param rendered_query: Pre-rendered SQL query to execute
    :param username: Username for context override
    :param start_time: Query start time for timing metrics
    :returns: Query result payload or None
    """
    with app.test_request_context():
        with override_user(security_manager.find_user(username)):
            try:
                return _execute_sql_statements(
                    query_id,
                    rendered_query,
                    start_time=start_time,
                )
            except Exception as ex:
                logger.exception("Query %d: %s", query_id, ex)
                stats_logger = app.config["STATS_LOGGER"]
                stats_logger.incr("error_sqllab_unhandled")
                # The original failure may have left the metadata-DB session
                # poisoned (e.g. connection drop). Recover before re-querying
                # so FAILED status can still be persisted.
                reset_session_safely(
                    context=f"sql celery unhandled error recovery query_id={query_id}"
                )
                try:
                    query = _get_query(query_id=query_id)
                    return _handle_query_error(ex, query)
                except Exception as recovery_ex:  # noqa: BLE001
                    logger.error(
                        "Query %d: failed to record error after session recovery: %s",
                        query_id,
                        recovery_ex,
                        exc_info=True,
                    )
                    return {
                        "status": QueryStatus.FAILED.value,
                        "error": str(ex),
                        "errors": [],
                    }


def _make_check_stopped_fn(query: Query) -> Any:
    """Create a function to check if query was stopped."""

    def check_stopped() -> bool:
        db.session.refresh(query)
        return query.status == QueryStatus.STOPPED

    return check_stopped


def _make_execute_fn(query: Query, db_engine_spec: Any) -> Any:
    """Create an execute function with stats timing."""

    def execute_with_stats(cursor: Any, sql: str) -> None:
        query.executed_sql = sql
        stats_logger = app.config["STATS_LOGGER"]
        with stats_timing("sqllab.query.time_executing_query", stats_logger):
            db_engine_spec.execute_with_cursor(cursor, sql, query)

    return execute_with_stats


def _make_log_query_fn(database: Any) -> Any:
    """Create a query logging function."""

    def log_query(sql: str, schema: str | None) -> None:
        if log_query_fn := app.config.get("QUERY_LOGGER"):
            log_query_fn(
                database.sqlalchemy_uri,
                sql,
                schema,
                __name__,
                security_manager,
                None,
            )

    return log_query


def _execute_sql_statements(
    query_id: int,
    rendered_query: str,
    start_time: float | None,
) -> dict[str, Any] | None:
    """Execute SQL statements and store results."""
    if start_time:
        stats_logger = app.config["STATS_LOGGER"]
        stats_logger.timing("sqllab.query.time_pending", now_as_float() - start_time)

    query = _get_query(query_id=query_id)
    payload: dict[str, Any] = {"query_id": query_id}
    database = query.database
    db_engine_spec = database.db_engine_spec
    db_engine_spec.patch()

    logger.info("Query %s: Set query to 'running'", str(query_id))
    query.status = QueryStatus.RUNNING
    query.start_running_time = now_as_float()
    execution_start_time = now_as_float()
    commit_session(
        db.session,
        context=f"sql celery set RUNNING query_id={query_id}",
    )

    # Parse original SQL (from user) to preserve before transformations
    original_script = SQLScript(query.sql, engine=db_engine_spec.engine)

    # Parse transformed SQL (with RLS, limits, etc.)
    parsed_script, blocks = _prepare_statement_blocks(rendered_query, db_engine_spec)

    with database.get_raw_connection(
        catalog=query.catalog,
        schema=query.schema,
    ) as conn:
        cursor = conn.cursor()

        cancel_query_id = db_engine_spec.get_cancel_query_id(cursor, query)
        if cancel_query_id is not None:
            query.set_extra_json_key(QUERY_CANCEL_KEY, cancel_query_id)
            commit_session(
                db.session,
                context=f"sql celery cancel_query_id query_id={query_id}",
            )

        try:
            execution_results = execute_sql_with_cursor(
                database=database,
                cursor=cursor,
                statements=blocks,
                query=query,
                log_query_fn=_make_log_query_fn(database),
                check_stopped_fn=_make_check_stopped_fn(query),
                execute_fn=_make_execute_fn(query, db_engine_spec),
            )
        except SoftTimeLimitExceeded as ex:
            query.status = QueryStatus.TIMED_OUT
            logger.warning("Query %d: Time limit exceeded", query.id)
            timeout_sec = app.config["SQLLAB_ASYNC_TIME_LIMIT_SEC"]
            raise AxBIErrorException(
                AxBIError(
                    message=__(
                        "The query was killed after %(sqllab_timeout)s seconds. "
                        "It might be too complex, or the database might be "
                        "under heavy load.",
                        sqllab_timeout=timeout_sec,
                    ),
                    error_type=AxBIErrorType.SQLLAB_TIMEOUT_ERROR,
                    level=ErrorLevel.ERROR,
                )
            ) from ex

        # Check if stopped
        if not execution_results:
            payload.update({"status": QueryStatus.STOPPED.value})
            return payload

        # Commit for mutations
        if parsed_script.has_mutation() or query.select_as_cta:
            conn.commit()  # pylint: disable=consider-using-transaction

    total_execution_time_ms = (now_as_float() - execution_start_time) * 1000
    _finalize_successful_query(
        query, original_script, execution_results, payload, total_execution_time_ms
    )

    if results_backend:
        _store_results_in_backend(query, payload, database)

    if query.status != QueryStatus.FAILED:
        query.status = QueryStatus.SUCCESS
    commit_session(
        db.session,
        context=f"sql celery finalize status query_id={query_id}",
    )

    return payload

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
"""Keep the semantic index fresh when datasets, columns, or metrics change.

Two complementary mechanisms run per change:

1. **Synchronous invalidation** — inside the same transaction as the change, the
   dataset's auto-generated documents are marked ``stale`` (or deleted, for a
   dataset delete). Because search only returns ``generated``/``approved``
   documents, possibly-outdated results stop being served immediately, even if
   no Celery worker is running.
2. **Asynchronous refresh** — after the transaction commits, a Celery task is
   enqueued to re-embed the dataset so its documents return fresh.

Every hook is defensive: a semantic-index failure is logged and swallowed so it
can never break a dataset/column/metric write. When Celery is unavailable, the
``superset semantic-index reindex-stale`` CLI command is the manual safety net.
"""

from __future__ import annotations

import logging
from typing import Any

import sqlalchemy as sqla
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Mapper, object_session, Session

logger = logging.getLogger(__name__)

# Key under which pending dataset ids are stashed on ``Session.info`` between the
# flush (where changes are observed) and the commit (where tasks are enqueued).
_PENDING_KEY = "semantic_index_pending_dataset_ids"


def _pending_ids(session: Session) -> set[int]:
    """Return the per-session set of dataset ids awaiting reindex."""

    return session.info.setdefault(_PENDING_KEY, set())


def _mark_stale(connection: Connection, dataset_id: int) -> None:
    """Mark a dataset's auto-generated documents stale within this transaction."""

    from superset.models.ai import AISemanticDocument

    table = AISemanticDocument.__table__
    connection.execute(
        sqla.update(table)
        .where(table.c.dataset_id == dataset_id)
        .where(table.c.review_status.in_(("generated", "approved")))
        .values(review_status="stale")
    )


def _delete_docs(connection: Connection, dataset_id: int) -> None:
    """Delete a dataset's documents within this transaction."""

    from superset.models.ai import AISemanticDocument

    table = AISemanticDocument.__table__
    connection.execute(sqla.delete(table).where(table.c.dataset_id == dataset_id))


def _queue_reindex(target: Any, dataset_id: int | None) -> None:
    """Record a dataset id for enqueue after the current transaction commits."""

    if dataset_id is None:
        return
    if (session := object_session(target)) is not None:
        _pending_ids(session).add(dataset_id)


def _on_dataset_change(_mapper: Mapper, connection: Connection, target: Any) -> None:
    """Handle SqlaTable insert/update: invalidate now, refresh after commit."""

    try:
        _mark_stale(connection, target.id)
        _queue_reindex(target, target.id)
    except Exception:  # pylint: disable=broad-except
        logger.warning(
            "Semantic index change hook failed for dataset %s",
            getattr(target, "id", None),
            exc_info=True,
        )


def _on_dataset_delete(_mapper: Mapper, connection: Connection, target: Any) -> None:
    """Handle SqlaTable delete: remove documents and cancel any pending reindex."""

    try:
        _delete_docs(connection, target.id)
        session = object_session(target)
        if session is not None:
            _pending_ids(session).discard(target.id)
    except Exception:  # pylint: disable=broad-except
        logger.warning(
            "Semantic index delete hook failed for dataset %s",
            getattr(target, "id", None),
            exc_info=True,
        )


def _on_child_change(_mapper: Mapper, connection: Connection, target: Any) -> None:
    """Handle a column/metric insert/update/delete by refreshing its dataset."""

    dataset_id = getattr(target, "table_id", None)
    try:
        if dataset_id is not None:
            _mark_stale(connection, dataset_id)
            _queue_reindex(target, dataset_id)
    except Exception:  # pylint: disable=broad-except
        logger.warning(
            "Semantic index child hook failed for dataset %s",
            dataset_id,
            exc_info=True,
        )


def _after_commit(session: Session) -> None:
    """Enqueue reindex tasks for datasets changed in the committed transaction."""

    dataset_ids = session.info.pop(_PENDING_KEY, None)
    if not dataset_ids:
        return

    # pylint: disable=import-outside-toplevel
    from superset import is_feature_enabled

    if not is_feature_enabled("GENAI_SEMANTIC_INDEX"):
        return

    from superset.semantic_index.tasks import reindex_dataset_semantic_documents

    for dataset_id in dataset_ids:
        try:
            reindex_dataset_semantic_documents.delay(dataset_id)
        except Exception:  # pylint: disable=broad-except
            # A missing/unavailable broker must not surface to the caller. The
            # documents are already marked stale; reindex-stale can recover them.
            logger.warning(
                "Failed to enqueue semantic reindex for dataset %s",
                dataset_id,
                exc_info=True,
            )


def _after_rollback(session: Session) -> None:
    """Discard pending reindex ids when the transaction is rolled back."""

    session.info.pop(_PENDING_KEY, None)


def register_semantic_index_listeners() -> None:
    """Attach the semantic-index change listeners.

    Called once at startup when ``GENAI_SEMANTIC_INDEX`` is enabled.
    """

    # pylint: disable=import-outside-toplevel
    from superset.connectors.sqla.models import SqlaTable, SqlMetric, TableColumn
    from superset.extensions import db

    sqla.event.listen(SqlaTable, "after_insert", _on_dataset_change)
    sqla.event.listen(SqlaTable, "after_update", _on_dataset_change)
    sqla.event.listen(SqlaTable, "after_delete", _on_dataset_delete)

    for model in (TableColumn, SqlMetric):
        sqla.event.listen(model, "after_insert", _on_child_change)
        sqla.event.listen(model, "after_update", _on_child_change)
        sqla.event.listen(model, "after_delete", _on_child_change)

    sqla.event.listen(db.session, "after_commit", _after_commit)
    sqla.event.listen(db.session, "after_rollback", _after_rollback)


def clear_semantic_index_listeners() -> None:
    """Detach the semantic-index change listeners (used in tests)."""

    # pylint: disable=import-outside-toplevel
    from superset.connectors.sqla.models import SqlaTable, SqlMetric, TableColumn
    from superset.extensions import db

    sqla.event.remove(SqlaTable, "after_insert", _on_dataset_change)
    sqla.event.remove(SqlaTable, "after_update", _on_dataset_change)
    sqla.event.remove(SqlaTable, "after_delete", _on_dataset_delete)

    for model in (TableColumn, SqlMetric):
        sqla.event.remove(model, "after_insert", _on_child_change)
        sqla.event.remove(model, "after_update", _on_child_change)
        sqla.event.remove(model, "after_delete", _on_child_change)

    sqla.event.remove(db.session, "after_commit", _after_commit)
    sqla.event.remove(db.session, "after_rollback", _after_rollback)

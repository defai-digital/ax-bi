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
"""Independent SQLAlchemy sessions for KV-backed distributed locks.

Lock acquire/release must be durable and visible to other processes
immediately. Using the request-scoped ``db.session`` under a nested
``@transaction`` would leave the lock row uncommitted until the outer unit
of work finishes — concurrent workers then race on the unique key instead of
joining cleanly. A short-lived session commits only the lock mutation.

SQLite is single-writer: an independent connection cannot commit while the
request session holds an open write transaction (e.g. ``task_lock`` nested
under ``@transaction`` after DAO writes). For concurrent SQLite workers,
configure Redis ``DISTRIBUTED_COORDINATION_CONFIG`` instead of KV locks.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from sqlalchemy.orm import Session, sessionmaker


@contextmanager
def independent_kv_session() -> Iterator[Session]:
    """Yield a short-lived Session that commits independently of ``db.session``.

    Binds to the same engine as the app scoped session so locks land in the
    same metadata database, but never shares the request unit of work.
    """
    # pylint: disable=import-outside-toplevel
    from axbi.extensions import db

    bind = db.session.get_bind()
    session: Session = sessionmaker(bind=bind)()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def delete_expired_lock_entries(session: Session, resource_value: str) -> None:
    """Bulk-delete expired lock rows for ``resource_value`` on ``session``."""
    # pylint: disable=import-outside-toplevel
    from sqlalchemy import and_

    from axbi.key_value.models import KeyValueEntry
    from axbi.utils.dates import naive_utcnow

    (
        session.query(KeyValueEntry)
        .filter(
            and_(
                KeyValueEntry.resource == resource_value,
                KeyValueEntry.expires_on <= naive_utcnow(),
            )
        )
        .delete(synchronize_session=False)
    )


def create_lock_entry(
    session: Session,
    *,
    resource_value: str,
    key: Any,
    encoded_value: bytes,
    expires_on: Any,
    created_by_fk: int | None,
) -> None:
    """Insert a lock row on ``session`` (caller commits via the context manager)."""
    # pylint: disable=import-outside-toplevel
    from uuid import UUID

    from axbi.key_value.models import KeyValueEntry
    from axbi.utils.dates import naive_utcnow

    entry = KeyValueEntry(
        resource=resource_value,
        value=encoded_value,
        created_on=naive_utcnow(),
        created_by_fk=created_by_fk,
        expires_on=expires_on,
    )
    if isinstance(key, UUID):
        entry.uuid = key
    else:
        entry.id = key
    session.add(entry)

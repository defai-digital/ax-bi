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

"""Shared SQLAlchemy scoped-session recovery helpers.

These helpers centralize rollback/remove hygiene for request handlers, Celery
workers, CLI commands, and MCP tools. Call sites that must fail closed should
use the strict variants; cleanup paths that must not mask a primary exception
should use the ``*_safely`` variants.
"""

from __future__ import annotations

import logging

from sqlalchemy.exc import DBAPIError

logger = logging.getLogger(__name__)


def rollback_session_safely(*, context: str) -> bool:
    """Rollback the scoped session without masking an existing failure."""
    from axbi.extensions import db

    try:
        db.session.rollback()  # pylint: disable=consider-using-transaction
    except Exception:  # noqa: BLE001
        logger.warning("Session rollback failed during %s", context, exc_info=True)
        return False
    return True


def remove_session_with_connection_recovery() -> None:
    """Remove the scoped session, invalidating a failed DBAPI connection.

    This strict operation propagates unrecoverable removal failures. Callers
    that must fail closed (for example authentication setup) use it directly.
    Error-cleanup paths should use :func:`remove_session_safely` instead.
    """
    from axbi.extensions import db

    try:
        db.session.remove()  # pylint: disable=consider-using-transaction
    except DBAPIError as exc:
        logger.warning(
            "Connection error during session removal; "
            "invalidating the connection and retrying: %s",
            exc,
        )
        try:
            # ``db.session`` is a SQLAlchemy ``scoped_session``. Invalidation
            # belongs to the concrete Session stored in its registry, not to
            # the scoped proxy itself.
            db.session().invalidate()
        except Exception as invalidate_exc:  # noqa: BLE001
            logger.debug(
                "Could not invalidate the session after a connection error: %s",
                invalidate_exc,
            )
        db.session.remove()  # pylint: disable=consider-using-transaction


def remove_session_safely(*, context: str) -> bool:
    """Remove the scoped session without masking an existing failure."""
    try:
        remove_session_with_connection_recovery()
    except Exception:  # noqa: BLE001
        logger.warning("Session removal failed during %s", context, exc_info=True)
        return False
    return True


def reset_session_safely(*, context: str) -> bool:
    """Attempt both rollback and removal, even when either operation fails."""
    rollback_succeeded = rollback_session_safely(context=context)
    removal_succeeded = remove_session_safely(context=context)
    return rollback_succeeded and removal_succeeded

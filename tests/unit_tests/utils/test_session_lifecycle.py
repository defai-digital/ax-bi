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

"""Tests for shared SQLAlchemy scoped-session recovery helpers."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.exc import OperationalError

from axbi.utils.session_lifecycle import (
    commit_session,
    remove_session_safely,
    remove_session_with_connection_recovery,
    reset_session_safely,
    rollback_session,
    rollback_session_safely,
)


class _RecoveryRequiredSession:
    """Session whose close succeeds only after connection invalidation."""

    def __init__(self) -> None:
        self.invalidated = False

    def invalidate(self) -> None:
        self.invalidated = True


class _ScopedSessionStub:
    """Model the callable/remove API exposed by SQLAlchemy scoped_session."""

    def __init__(self) -> None:
        self.current = _RecoveryRequiredSession()
        self.remove_calls = 0
        self.removed = False

    def __call__(self) -> _RecoveryRequiredSession:
        return self.current

    def remove(self) -> None:
        self.remove_calls += 1
        if not self.current.invalidated:
            raise OperationalError("SSL connection closed", None, None)
        self.removed = True


def test_commit_session_success() -> None:
    session = MagicMock()
    assert commit_session(session, context="test commit") is True
    session.commit.assert_called_once_with()
    session.rollback.assert_not_called()


def test_commit_session_failure_rolls_back_and_reraises() -> None:
    session = MagicMock()
    session.commit.side_effect = RuntimeError("disk full")

    with pytest.raises(RuntimeError, match="disk full"):
        commit_session(session, context="test commit")

    session.rollback.assert_called_once_with()


def test_commit_session_soft_returns_false_after_rollback() -> None:
    session = MagicMock()
    session.commit.side_effect = RuntimeError("disk full")

    assert commit_session(session, context="test commit", soft=True) is False
    session.rollback.assert_called_once_with()


def test_commit_session_soft_swallows_rollback_failure() -> None:
    session = MagicMock()
    session.commit.side_effect = RuntimeError("disk full")
    session.rollback.side_effect = RuntimeError("connection closed")

    assert commit_session(session, context="test commit", soft=True) is False
    session.rollback.assert_called_once_with()


def test_rollback_session_on_explicit_session() -> None:
    session = MagicMock()
    assert rollback_session(session, context="test rollback") is True
    session.rollback.assert_called_once_with()


def test_rollback_session_safely_reports_success() -> None:
    with patch("axbi.extensions.db") as mock_db:
        assert rollback_session_safely(context="test cleanup") is True

    mock_db.session.rollback.assert_called_once_with()


def test_rollback_session_safely_swallows_cleanup_failure() -> None:
    with patch("axbi.extensions.db") as mock_db:
        mock_db.session.rollback.side_effect = RuntimeError("connection is closed")

        assert rollback_session_safely(context="test cleanup") is False

    mock_db.session.rollback.assert_called_once_with()


def test_remove_session_recovers_from_dbapi_failure() -> None:
    with patch("axbi.extensions.db") as mock_db:
        mock_db.session.remove.side_effect = [
            OperationalError("SSL connection closed", None, None),
            None,
        ]

        remove_session_with_connection_recovery()

    mock_db.session.return_value.invalidate.assert_called_once_with()
    assert mock_db.session.remove.call_count == 2


def test_remove_session_invalidates_concrete_scoped_session() -> None:
    scoped_session = _ScopedSessionStub()

    with patch(
        "axbi.extensions.db",
        SimpleNamespace(session=scoped_session),
    ):
        remove_session_with_connection_recovery()

    assert scoped_session.current.invalidated is True
    assert scoped_session.removed is True
    assert scoped_session.remove_calls == 2


def test_remove_session_propagates_unrecoverable_failure() -> None:
    with patch("axbi.extensions.db") as mock_db:
        mock_db.session.remove.side_effect = RuntimeError("registry failure")

        with pytest.raises(RuntimeError, match="registry failure"):
            remove_session_with_connection_recovery()


def test_remove_session_safely_swallows_retry_failure() -> None:
    with patch("axbi.extensions.db") as mock_db:
        mock_db.session.remove.side_effect = RuntimeError("registry failure")

        assert remove_session_safely(context="test cleanup") is False


def test_reset_session_safely_attempts_both_operations() -> None:
    with patch("axbi.extensions.db") as mock_db:
        assert reset_session_safely(context="test cleanup") is True

    mock_db.session.rollback.assert_called_once_with()
    mock_db.session.remove.assert_called_once_with()

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

"""Tests for the MCP scoped-session recovery boundary."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from sqlalchemy.exc import OperationalError

from axbi.mcp_service.utils.session_utils import (
    remove_session_safely,
    remove_session_with_connection_recovery,
    reset_session_safely,
    rollback_session_safely,
)


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

    mock_db.session.invalidate.assert_called_once_with()
    assert mock_db.session.remove.call_count == 2


def test_remove_session_propagates_unrecoverable_failure() -> None:
    with patch("axbi.extensions.db") as mock_db:
        mock_db.session.remove.side_effect = RuntimeError("registry failure")

        with pytest.raises(RuntimeError, match="registry failure"):
            remove_session_with_connection_recovery()


def test_remove_session_safely_swallows_retry_failure() -> None:
    with patch("axbi.extensions.db") as mock_db:
        mock_db.session.remove.side_effect = [
            OperationalError("SSL connection closed", None, None),
            RuntimeError("registry failure"),
        ]

        assert remove_session_safely(context="test cleanup") is False

    mock_db.session.invalidate.assert_called_once_with()
    assert mock_db.session.remove.call_count == 2


def test_reset_session_safely_always_attempts_removal() -> None:
    with patch("axbi.extensions.db") as mock_db:
        mock_db.session.rollback.side_effect = RuntimeError("connection is closed")

        assert reset_session_safely(context="test cleanup") is False

    mock_db.session.rollback.assert_called_once_with()
    mock_db.session.remove.assert_called_once_with()

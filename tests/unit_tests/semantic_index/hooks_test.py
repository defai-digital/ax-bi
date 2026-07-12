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
"""Tests for semantic index change hooks."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from axbi.semantic_index import hooks
from axbi.semantic_index.hooks import (
    _after_commit,
    _after_rollback,
    _on_child_change,
    _on_dataset_change,
    _on_dataset_delete,
    _PENDING_KEY,
)


def _fake_session() -> SimpleNamespace:
    return SimpleNamespace(info={})


def test_dataset_change_marks_stale_and_queues() -> None:
    connection = MagicMock()
    target = SimpleNamespace(id=42)
    session = _fake_session()

    with patch.object(hooks, "object_session", return_value=session):
        _on_dataset_change(MagicMock(), connection, target)

    # Stale-marking UPDATE ran in the change transaction.
    assert connection.execute.call_count == 1
    # Dataset queued for post-commit reindex.
    assert session.info[_PENDING_KEY] == {42}


def test_dataset_delete_removes_docs_and_cancels_pending() -> None:
    connection = MagicMock()
    target = SimpleNamespace(id=7)
    session = _fake_session()
    session.info[_PENDING_KEY] = {7, 9}

    with patch.object(hooks, "object_session", return_value=session):
        _on_dataset_delete(MagicMock(), connection, target)

    assert connection.execute.call_count == 1
    # The deleted dataset is no longer queued for reindex; others remain.
    assert session.info[_PENDING_KEY] == {9}


def test_child_change_uses_parent_dataset_id() -> None:
    connection = MagicMock()
    column = SimpleNamespace(table_id=13)
    session = _fake_session()

    with patch.object(hooks, "object_session", return_value=session):
        _on_child_change(MagicMock(), connection, column)

    assert connection.execute.call_count == 1
    assert session.info[_PENDING_KEY] == {13}


def test_child_change_without_table_id_is_noop() -> None:
    connection = MagicMock()
    orphan = SimpleNamespace(table_id=None)
    session = _fake_session()

    with patch.object(hooks, "object_session", return_value=session):
        _on_child_change(MagicMock(), connection, orphan)

    connection.execute.assert_not_called()
    assert _PENDING_KEY not in session.info


def test_change_hook_swallows_errors() -> None:
    connection = MagicMock()
    connection.execute.side_effect = RuntimeError("boom")
    target = SimpleNamespace(id=1)

    with patch.object(hooks, "object_session", return_value=_fake_session()):
        # Must not raise: a semantic-index failure cannot break a dataset write.
        _on_dataset_change(MagicMock(), connection, target)


def test_after_commit_enqueues_and_clears() -> None:
    session = SimpleNamespace(info={_PENDING_KEY: {1, 2}})
    delay = MagicMock()

    with (
        patch("axbi.is_feature_enabled", return_value=True),
        patch("axbi.semantic_index.tasks.reindex_dataset_semantic_documents") as task,
    ):
        task.delay = delay
        _after_commit(session)

    assert delay.call_count == 2
    assert {call.args[0] for call in delay.call_args_list} == {1, 2}
    # Pending set consumed.
    assert _PENDING_KEY not in session.info


def test_after_commit_noop_when_feature_disabled() -> None:
    session = SimpleNamespace(info={_PENDING_KEY: {1}})

    with (
        patch("axbi.is_feature_enabled", return_value=False),
        patch("axbi.semantic_index.tasks.reindex_dataset_semantic_documents") as task,
    ):
        _after_commit(session)

    task.delay.assert_not_called()
    # Still consumed so ids don't leak into a later commit.
    assert _PENDING_KEY not in session.info


def test_after_commit_without_pending_is_noop() -> None:
    session = SimpleNamespace(info={})

    with patch("axbi.semantic_index.tasks.reindex_dataset_semantic_documents") as task:
        _after_commit(session)

    task.delay.assert_not_called()


def test_after_commit_swallows_enqueue_errors() -> None:
    session = SimpleNamespace(info={_PENDING_KEY: {5}})

    with (
        patch("axbi.is_feature_enabled", return_value=True),
        patch("axbi.semantic_index.tasks.reindex_dataset_semantic_documents") as task,
    ):
        task.delay.side_effect = RuntimeError("no broker")
        # A missing broker must not propagate to the committing caller.
        _after_commit(session)

    assert _PENDING_KEY not in session.info


def test_after_rollback_discards_pending() -> None:
    session = SimpleNamespace(info={_PENDING_KEY: {1, 2}})

    _after_rollback(session)

    assert _PENDING_KEY not in session.info

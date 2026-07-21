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
"""Unit tests for AxBIMetastoreCache session hygiene."""

from __future__ import annotations

from unittest.mock import patch
from uuid import uuid4

import pytest
from sqlalchemy.exc import SQLAlchemyError

from axbi.extensions.metastore_cache import AxBIMetastoreCache
from axbi.key_value.types import PickleKeyValueCodec


@pytest.fixture
def cache() -> AxBIMetastoreCache:
    return AxBIMetastoreCache(namespace=uuid4(), codec=PickleKeyValueCodec())


def test_set_returns_true_on_successful_commit(cache: AxBIMetastoreCache) -> None:
    with (
        patch("axbi.daos.key_value.KeyValueDAO.upsert_entry") as upsert,
        patch(
            "axbi.utils.session_lifecycle.commit_session", return_value=True
        ) as commit,
    ):
        assert cache.set("k", {"v": 1}) is True
        upsert.assert_called_once()
        commit.assert_called_once()
        assert commit.call_args.kwargs["soft"] is True


def test_set_returns_false_on_commit_failure(cache: AxBIMetastoreCache) -> None:
    with (
        patch("axbi.daos.key_value.KeyValueDAO.upsert_entry"),
        patch(
            "axbi.utils.session_lifecycle.commit_session", return_value=False
        ) as commit,
    ):
        assert cache.set("k", "v") is False
        commit.assert_called_once()


def test_set_returns_false_and_rolls_back_on_upsert_error(
    cache: AxBIMetastoreCache,
) -> None:
    with (
        patch(
            "axbi.daos.key_value.KeyValueDAO.upsert_entry",
            side_effect=SQLAlchemyError("boom"),
        ),
        patch("axbi.utils.session_lifecycle.rollback_session") as rollback,
        patch("axbi.utils.session_lifecycle.commit_session") as commit,
    ):
        assert cache.set("k", "v") is False
        commit.assert_not_called()
        rollback.assert_called_once()


def test_add_returns_false_and_rolls_back_on_create_error(
    cache: AxBIMetastoreCache,
) -> None:
    with (
        patch("axbi.daos.key_value.KeyValueDAO.delete_expired_entries"),
        patch(
            "axbi.daos.key_value.KeyValueDAO.create_entry",
            side_effect=SQLAlchemyError("boom"),
        ),
        patch("axbi.utils.session_lifecycle.rollback_session") as rollback,
        patch("axbi.utils.session_lifecycle.commit_session") as commit,
    ):
        assert cache.add("k", "v") is False
        commit.assert_not_called()
        rollback.assert_called_once()

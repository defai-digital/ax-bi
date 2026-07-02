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
"""Tests for semantic index repository helpers."""

from __future__ import annotations

from typing import Any, cast

import pytest

from superset.semantic_index.repository import _embedding_literals


def test_embedding_literals_validates_batch_count() -> None:
    with pytest.raises(ValueError, match="returned 1 vectors"):
        _embedding_literals(
            [[1.0, 2.0]],
            expected_count=2,
            expected_dimensions=2,
        )


def test_embedding_literals_validates_dimensions() -> None:
    with pytest.raises(ValueError, match="dimension 1"):
        _embedding_literals(
            [[1.0]],
            expected_count=1,
            expected_dimensions=2,
        )


def test_embedding_literals_rejects_scalar_embedding() -> None:
    with pytest.raises(ValueError, match="not a vector"):
        _embedding_literals(
            cast(Any, [1.0]),
            expected_count=1,
            expected_dimensions=2,
        )


def test_embedding_literals_returns_pgvector_literals() -> None:
    assert _embedding_literals(
        [[1.0, 2.0]],
        expected_count=1,
        expected_dimensions=2,
    ) == ["[1.0,2.0]"]

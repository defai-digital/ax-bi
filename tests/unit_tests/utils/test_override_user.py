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
"""Unit tests for override_user exception-safe restoration."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from flask import g

from axbi.utils.core import override_user


def test_override_user_restores_existing_user_after_exception(
    app_context: None,
) -> None:
    original = SimpleNamespace(username="original")
    override = SimpleNamespace(username="override")
    g.user = original

    def _raise_under_override() -> None:
        with override_user(override):
            assert g.user is override
            raise RuntimeError("boom")

    with pytest.raises(RuntimeError, match="boom"):
        _raise_under_override()

    assert g.user is original


def test_override_user_clears_user_when_unset_after_exception(
    app_context: None,
) -> None:
    if hasattr(g, "user"):
        delattr(g, "user")
    override = SimpleNamespace(username="override")

    def _raise_under_override() -> None:
        with override_user(override):
            assert g.user is override
            raise RuntimeError("boom")

    with pytest.raises(RuntimeError, match="boom"):
        _raise_under_override()

    assert not hasattr(g, "user")


def test_override_user_restores_on_success(app_context: None) -> None:
    original = SimpleNamespace(username="original")
    override = SimpleNamespace(username="override")
    g.user = original

    with override_user(override):
        assert g.user is override

    assert g.user is original

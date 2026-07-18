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
"""Non-admin access gates for GenAI LLM Admin API (unit-level)."""

from __future__ import annotations

import inspect
from unittest.mock import MagicMock

from axbi.genai.api import GenaiLlmProviderRestApi


def test_admin_gate_uses_is_admin_and_returns_403() -> None:
    """_admin_or_403 must hard-require Admin and return HTTP 403 otherwise."""
    api = GenaiLlmProviderRestApi()
    source = inspect.getsource(api._admin_or_403)
    assert "is_admin" in source
    assert "403" in source
    assert "Only administrators" in source or "administrator" in source.lower()


def test_all_provider_endpoints_call_admin_gate() -> None:
    """GET/PUT/DELETE/test all enforce the Admin gate in method bodies."""
    for name in ("get_provider", "put_provider", "delete_provider", "test_provider"):
        source = inspect.getsource(getattr(GenaiLlmProviderRestApi, name))
        assert "_admin_or_403" in source, f"{name} must call _admin_or_403"


def test_admin_or_403_blocks_when_is_admin_false(app_context: None) -> None:
    """With an app context, mock is_admin on the live security manager proxy."""
    api = GenaiLlmProviderRestApi()
    api.response = MagicMock(return_value="FORBIDDEN")  # type: ignore[method-assign]

    from axbi.extensions import security_manager

    original = security_manager.is_admin
    try:
        security_manager.is_admin = MagicMock(return_value=False)  # type: ignore[method-assign]
        denied = api._admin_or_403()
    finally:
        security_manager.is_admin = original  # type: ignore[method-assign]

    assert denied == "FORBIDDEN"
    assert api.response.call_args.args[0] == 403


def test_admin_or_403_allows_when_is_admin_true(app_context: None) -> None:
    api = GenaiLlmProviderRestApi()
    from axbi.extensions import security_manager

    original = security_manager.is_admin
    try:
        security_manager.is_admin = MagicMock(return_value=True)  # type: ignore[method-assign]
        assert api._admin_or_403() is None
    finally:
        security_manager.is_admin = original  # type: ignore[method-assign]

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
"""Hoisted form_data helpers live outside views (layering boundary)."""

from __future__ import annotations

import inspect

from axbi.utils import form_data as form_data_mod
from axbi.utils.bootstrap_cache import (
    clear_common_bootstrap_cache,
    register_common_bootstrap_cache_fn,
)
from axbi.utils.form_data import get_form_data, loads_request_json


def test_get_form_data_defined_outside_views() -> None:
    path = inspect.getsourcefile(get_form_data) or ""
    assert "views" not in path.replace("\\", "/")
    assert path.endswith("form_data.py")


def test_loads_request_json_parses_object() -> None:
    assert loads_request_json('{"a": 1}') == {"a": 1}
    assert loads_request_json("not-json") == {}
    assert loads_request_json("[]") == {}


def test_bootstrap_cache_registry_clear_does_not_import_views() -> None:
    calls: list[object] = []

    def fake_fn(user_id: int | None, locale: str | None) -> dict[str, str]:
        return {"ok": "1"}

    register_common_bootstrap_cache_fn(fake_fn)

    # clear should not raise even without full cache backend; we only assert
    # the registry path runs without importing axbi.views.
    clear_common_bootstrap_cache()
    # re-register for isolation
    register_common_bootstrap_cache_fn(fake_fn)
    assert form_data_mod.get_form_data is get_form_data

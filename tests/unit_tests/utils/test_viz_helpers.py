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
"""Tests for hoisted viz helpers (non-views layer)."""

from __future__ import annotations

import pytest

from axbi.exceptions import AxBIException
from axbi.utils.viz_helpers import get_datasource_info


def test_get_datasource_info_from_form_data() -> None:
    ds_id, ds_type = get_datasource_info(None, None, {"datasource": "42__table"})
    assert ds_id == 42
    assert ds_type == "table"


def test_get_datasource_info_missing_raises() -> None:
    with pytest.raises(AxBIException):
        get_datasource_info(None, None, {})


def test_get_datasource_info_deleted_raises() -> None:
    with pytest.raises(AxBIException):
        get_datasource_info(None, None, {"datasource": "None__table"})

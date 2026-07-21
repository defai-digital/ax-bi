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
"""Chart list digest must not trigger per-row user/RLS lookups."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from axbi.models.slice import Slice
from axbi.thumbnails.digest import get_chart_list_digest


def test_get_chart_list_digest_is_deterministic_and_cheap() -> None:
    chart = SimpleNamespace(id=42, params='{"viz_type":"table"}', changed_on="t1")
    with patch("axbi.thumbnails.digest.security_manager") as sm:
        a = get_chart_list_digest(chart)  # type: ignore[arg-type]
        b = get_chart_list_digest(chart)  # type: ignore[arg-type]
        assert a == b
        assert isinstance(a, str)
        assert len(a) > 0
        sm.find_user.assert_not_called()
        sm.prefetch_rls_filters.assert_not_called()


def test_thumbnail_url_none_when_thumbnails_disabled(app_context: None) -> None:
    chart = Slice()
    chart.id = 7
    chart.params = "{}"
    with patch("axbi.models.slice.is_feature_enabled", return_value=False):
        assert chart.thumbnail_url is None


def test_thumbnail_url_uses_list_digest_when_enabled(app_context: None) -> None:
    chart = Slice()
    chart.id = 7
    chart.params = '{"a":1}'
    with (
        patch("axbi.models.slice.is_feature_enabled", return_value=True),
        patch(
            "axbi.models.slice.get_chart_list_digest",
            return_value="deadbeef",
        ) as list_digest,
        patch("axbi.models.slice.get_chart_digest") as full_digest,
    ):
        url = chart.thumbnail_url
        assert url == "/api/v1/chart/7/thumbnail/deadbeef/"
        list_digest.assert_called_once_with(chart)
        full_digest.assert_not_called()

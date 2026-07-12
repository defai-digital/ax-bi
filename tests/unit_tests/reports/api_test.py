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
from typing import Any
from unittest.mock import patch

import rison

from axbi.exceptions import AxBIException
from tests.unit_tests.conftest import with_feature_flags


@with_feature_flags(ALERT_REPORTS=True)
def test_json_body_handlers_reject_malformed_json_body(
    client: Any,
    full_api_access: None,
) -> None:
    """Report write endpoints should reject malformed JSON consistently."""
    endpoints = [
        ("post", "/api/v1/report/subscribe"),
        ("post", "/api/v1/report/"),
        ("put", "/api/v1/report/1"),
    ]

    for method, url in endpoints:
        response = getattr(client, method)(
            url,
            data="{malformed",
            content_type="application/json",
        )

        assert response.status_code == 400
        assert response.json == {"message": {"_schema": ["Invalid input type."]}}


@with_feature_flags(ALERT_REPORTS=True)
@patch("axbi.reports.api.get_channels_with_search")
def test_slack_channels_success(
    mock_search: Any,
    client: Any,
    full_api_access: None,
) -> None:
    mock_search.return_value = [{"id": "C123", "name": "general"}]
    params = rison.dumps({})
    rv = client.get(f"/api/v1/report/slack_channels/?q={params}")
    assert rv.status_code == 200
    data = rv.json
    assert data["result"] == [{"id": "C123", "name": "general"}]


@with_feature_flags(ALERT_REPORTS=True)
@patch("axbi.reports.api.get_channels_with_search")
def test_slack_channels_handles_axbi_exception(
    mock_search: Any,
    client: Any,
    full_api_access: None,
) -> None:
    mock_search.side_effect = AxBIException("Slack API error")
    params = rison.dumps({})
    rv = client.get(f"/api/v1/report/slack_channels/?q={params}")
    assert rv.status_code == 422
    assert "Slack API error" in rv.json["message"]

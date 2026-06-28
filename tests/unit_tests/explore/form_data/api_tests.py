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
from __future__ import annotations

from typing import Any

INVALID_INPUT_MESSAGE = {"message": {"_schema": ["Invalid input type."]}}


def test_form_data_post_rejects_malformed_json_body(
    client: Any,
    full_api_access: None,
) -> None:
    """Malformed JSON request bodies should return form data validation errors."""
    response = client.post(
        "/api/v1/explore/form_data",
        data="{malformed",
        content_type="application/json",
    )

    assert response.status_code == 400
    assert response.json == INVALID_INPUT_MESSAGE


def test_form_data_put_rejects_malformed_json_body(
    client: Any,
    full_api_access: None,
) -> None:
    """Malformed JSON request bodies should return form data validation errors."""
    response = client.put(
        "/api/v1/explore/form_data/key",
        data="{malformed",
        content_type="application/json",
    )

    assert response.status_code == 400
    assert response.json == INVALID_INPUT_MESSAGE

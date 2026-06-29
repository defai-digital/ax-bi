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


def test_annotation_layer_post_rejects_malformed_json_body(
    client: Any,
    full_api_access: None,
) -> None:
    """Malformed JSON request bodies should return annotation layer validation."""
    response = client.post(
        "/api/v1/annotation_layer/",
        data="{malformed",
        content_type="application/json",
    )

    assert response.status_code == 400
    assert response.json == INVALID_INPUT_MESSAGE


def test_annotation_layer_put_rejects_malformed_json_body(
    client: Any,
    full_api_access: None,
) -> None:
    """Malformed JSON request bodies should return annotation layer validation."""
    response = client.put(
        "/api/v1/annotation_layer/1",
        data="{malformed",
        content_type="application/json",
    )

    assert response.status_code == 400
    assert response.json == INVALID_INPUT_MESSAGE


def test_annotation_post_rejects_malformed_json_body(
    client: Any,
    full_api_access: None,
) -> None:
    """Malformed JSON request bodies should return annotation validation."""
    response = client.post(
        "/api/v1/annotation_layer/1/annotation/",
        data="{malformed",
        content_type="application/json",
    )

    assert response.status_code == 400
    assert response.json == INVALID_INPUT_MESSAGE


def test_annotation_put_rejects_malformed_json_body(
    client: Any,
    full_api_access: None,
) -> None:
    """Malformed JSON request bodies should return annotation validation."""
    response = client.put(
        "/api/v1/annotation_layer/1/annotation/1",
        data="{malformed",
        content_type="application/json",
    )

    assert response.status_code == 400
    assert response.json == INVALID_INPUT_MESSAGE

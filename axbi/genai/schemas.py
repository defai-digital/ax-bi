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
"""Marshmallow schemas for Admin GenAI LLM provider APIs."""

from __future__ import annotations

from marshmallow import fields, Schema, validate


class LlmProviderPutSchema(Schema):
    """Admin body for creating/updating the server-side LLM provider.

    When ``enabled`` is false, provider/model may be omitted so Admins can
    Disable without re-validating full connection settings (secrets retained).
    """

    enabled = fields.Boolean(load_default=True)
    provider = fields.String(
        load_default=None,
        allow_none=True,
        validate=validate.OneOf(["anthropic", "openai", "openai_compatible"]),
    )
    base_url = fields.String(load_default=None, allow_none=True)
    model = fields.String(load_default=None, allow_none=True)
    api_key = fields.String(load_default=None, allow_none=True)
    timeout_seconds = fields.Integer(
        load_default=60, validate=validate.Range(min=1, max=300)
    )
    max_retries = fields.Integer(
        load_default=1, validate=validate.Range(min=0, max=3)
    )
    verify_tls = fields.Boolean(load_default=True)
    allow_http = fields.Boolean(load_default=False)
    allow_private_network = fields.Boolean(load_default=False)
    url_allowlist = fields.List(fields.String(), load_default=list)


class LlmProviderTestSchema(Schema):
    """Optional override body for Admin connection test (not persisted)."""

    enabled = fields.Boolean(load_default=True)
    provider = fields.String(
        load_default=None,
        allow_none=True,
        validate=validate.OneOf(["anthropic", "openai", "openai_compatible"]),
    )
    base_url = fields.String(load_default=None, allow_none=True)
    model = fields.String(load_default=None, allow_none=True)
    api_key = fields.String(load_default=None, allow_none=True)
    timeout_seconds = fields.Integer(
        load_default=None, allow_none=True, validate=validate.Range(min=1, max=300)
    )
    max_retries = fields.Integer(
        load_default=None, allow_none=True, validate=validate.Range(min=0, max=3)
    )
    verify_tls = fields.Boolean(load_default=None, allow_none=True)
    allow_http = fields.Boolean(load_default=None, allow_none=True)
    allow_private_network = fields.Boolean(load_default=None, allow_none=True)
    url_allowlist = fields.List(fields.String(), load_default=None, allow_none=True)

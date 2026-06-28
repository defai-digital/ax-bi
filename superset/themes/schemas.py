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

from marshmallow import fields, pre_load, Schema, validates, ValidationError

from superset.themes.utils import (
    is_valid_theme,
    sanitize_theme_tokens,
    validate_font_urls,
)
from superset.utils import json


def _sanitize_and_validate_theme_config(theme_config: Any) -> dict[str, Any]:
    """Sanitize and validate theme configuration.

    Applies token sanitization and font URL validation.
    Returns the sanitized configuration.
    """
    if not isinstance(theme_config, dict):
        raise ValidationError("Invalid theme configuration structure")

    sanitized_config = sanitize_theme_tokens(theme_config)

    # Validate and sanitize fontUrls if present
    if "token" in sanitized_config and isinstance(sanitized_config["token"], dict):
        font_urls = sanitized_config["token"].get("fontUrls")
        if font_urls is not None:
            sanitized_config["token"]["fontUrls"] = validate_font_urls(font_urls)

    # Validate theme structure
    if not is_valid_theme(sanitized_config):
        raise ValidationError("Invalid theme configuration structure")

    return sanitized_config


def sanitize_theme_json_data(value: Any) -> Any:
    """Return sanitized theme JSON data using its original representation."""
    try:
        theme_config = json.loads(value) if isinstance(value, str) else value
    except (TypeError, json.JSONDecodeError) as ex:
        raise ValidationError("Invalid JSON configuration") from ex

    sanitized_config = _sanitize_and_validate_theme_config(theme_config)
    if isinstance(value, dict):
        value.clear()
        value.update(sanitized_config)
        return value

    return json.dumps(sanitized_config) if isinstance(value, str) else sanitized_config


class SanitizedThemeJsonDataMixin:
    """Apply sanitized theme JSON back into deserialized payloads."""

    @pre_load
    def sanitize_json_data(
        self,
        data: dict[str, Any],
        **kwargs: Any,
    ) -> dict[str, Any]:
        if not isinstance(data, dict) or "json_data" not in data:
            return data

        try:
            data["json_data"] = sanitize_theme_json_data(data["json_data"])
        except ValidationError:
            # Let the field validator report the established field-specific error.
            return data

        return data


class ImportV1ThemeSchema(SanitizedThemeJsonDataMixin, Schema):
    theme_name = fields.String(required=True)
    json_data = fields.Raw(required=True)
    uuid = fields.UUID(required=True)
    version = fields.String(required=True)

    @validates("json_data")
    def validate_json_data(self, value: dict[str, Any], **kwargs: Any) -> None:
        sanitize_theme_json_data(value)


class ThemePostSchema(SanitizedThemeJsonDataMixin, Schema):
    theme_name = fields.String(required=True, allow_none=False)
    json_data = fields.String(required=True, allow_none=False)

    @validates("theme_name")
    def validate_theme_name(self, value: str, **kwargs: Any) -> None:
        if not value or not value.strip():
            raise ValidationError("Theme name cannot be empty.")

    @validates("json_data")
    def validate_and_sanitize_json_data(self, value: str, **kwargs: Any) -> None:
        sanitize_theme_json_data(value)


class ThemePutSchema(SanitizedThemeJsonDataMixin, Schema):
    theme_name = fields.String(required=True, allow_none=False)
    json_data = fields.String(required=True, allow_none=False)

    @validates("theme_name")
    def validate_theme_name(self, value: str, **kwargs: Any) -> None:
        if not value or not value.strip():
            raise ValidationError("Theme name cannot be empty.")

    @validates("json_data")
    def validate_and_sanitize_json_data(self, value: str, **kwargs: Any) -> None:
        sanitize_theme_json_data(value)


openapi_spec_methods_override = {
    "get": {"get": {"summary": "Get a theme"}},
    "get_list": {
        "get": {
            "summary": "Get a list of themes",
            "description": "Gets a list of themes, use Rison or JSON "
            "query parameters for filtering, sorting,"
            " pagination and for selecting specific"
            " columns and metadata.",
        }
    },
    "post": {"post": {"summary": "Create a theme"}},
    "put": {"put": {"summary": "Update a theme"}},
    "delete": {"delete": {"summary": "Delete a theme"}},
    "info": {"get": {"summary": "Get metadata information about this API resource"}},
}

get_delete_ids_schema = {"type": "array", "items": {"type": "integer"}}
get_export_ids_schema = {"type": "array", "items": {"type": "integer"}}

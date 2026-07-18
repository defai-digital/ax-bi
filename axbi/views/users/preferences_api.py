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

from flask import g, request, Response
from flask_appbuilder.api import expose, permission_name, safe
from flask_appbuilder.security.decorators import protect
from marshmallow import ValidationError

from axbi.commands.exceptions import CommandInvalidError
from axbi.commands.ux_preferences.get import GetUxPreferencesCommand
from axbi.commands.ux_preferences.update import UpdateUxPreferencesCommand
from axbi.extensions import event_logger
from axbi.views.base_api import BaseAxBIApi, requires_json, statsd_metrics
from axbi.views.users.schemas import (
    UX_PREFERENCES_MAX_PAYLOAD_BYTES,
    UxPreferencesPutSchema,
)


class UserPreferencesRestApi(BaseAxBIApi):
    """An API to read and update the current user's UX preferences"""

    resource_name = "me"
    openapi_spec_tag = "Current User"
    allow_browser_login = True
    openapi_spec_component_schemas = (UxPreferencesPutSchema,)

    ux_preferences_put_schema = UxPreferencesPutSchema()

    @staticmethod
    def _is_anonymous() -> bool:
        """Return whether the request is unauthenticated.

        Preferences are strictly per-user, so anonymous callers are rejected
        even though sibling ``/me`` routes are readable by the Public role.
        """
        user = getattr(g, "user", None)
        return user is None or user.is_anonymous

    @expose("/preferences/", methods=("GET",))
    @protect()
    @permission_name("read")
    @safe
    @statsd_metrics
    def get_preferences(self) -> Response:
        """Get the UX preferences of the user making the request.
        ---
        get:
          summary: Get the current user's UX preferences
          description: >-
            Returns the current user's namespaced ``ux.*`` UI preferences as
            a flat JSON object, or a 401 error if the user is unauthenticated.
          responses:
            200:
              description: The current user's UX preferences
              content:
                application/json:
                  schema:
                    type: object
                    properties:
                      result:
                        type: object
                        additionalProperties: true
            401:
              $ref: '#/components/responses/401'
        """
        if self._is_anonymous():
            return self.response_401()
        return self.response(200, result=GetUxPreferencesCommand(g.user.id).run())

    @expose("/preferences/", methods=("PUT",))
    @protect()
    @permission_name("write")
    @safe
    @statsd_metrics
    @event_logger.log_this_with_context(
        action=lambda self, *args, **kwargs: f"{self.__class__.__name__}.put",
        log_to_statsd=False,
    )
    @requires_json
    def update_preferences(self) -> Response:
        r"""Merge UX preferences for the user making the request.
        ---
        put:
          summary: Update the current user's UX preferences
          description: >-
            Merges the given ``ux.*`` preference entries into the current
            user's stored preferences. Keys must match ``^ux\.[a-z0-9_.-]+$``,
            values must be JSON scalars, and the payload is limited to 8KB.
          requestBody:
            required: true
            content:
              application/json:
                schema:
                  $ref: '#/components/schemas/UxPreferencesPutSchema'
          responses:
            200:
              description: The merged UX preferences
              content:
                application/json:
                  schema:
                    type: object
                    properties:
                      result:
                        type: object
                        additionalProperties: true
            400:
              $ref: '#/components/responses/400'
            401:
              $ref: '#/components/responses/401'
        """
        if self._is_anonymous():
            return self.response_401()
        if len(request.get_data(cache=True)) > UX_PREFERENCES_MAX_PAYLOAD_BYTES:
            return self.response_400(
                message=(
                    "UX preferences payload exceeds the "
                    f"{UX_PREFERENCES_MAX_PAYLOAD_BYTES} byte limit."
                )
            )
        try:
            item = self.ux_preferences_put_schema.load(
                request.get_json(cache=True, silent=True)
            )
        except ValidationError as error:
            return self.response_400(message=error.messages)
        try:
            merged = UpdateUxPreferencesCommand(g.user.id, item).run()
        except CommandInvalidError as error:
            return self.response_400(message=str(error))
        return self.response(200, result=merged)

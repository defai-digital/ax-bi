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
"""REST APIs for GenAI capabilities and Admin-only LLM provider settings."""

from __future__ import annotations

import logging
from typing import Any

from flask import current_app, request, Response
from flask_appbuilder.api import expose, protect, safe
from marshmallow import ValidationError
from pydantic import BaseModel, Field

from axbi.extensions import event_logger, security_manager
from axbi.genai.schemas import LlmProviderPutSchema, LlmProviderTestSchema
from axbi.genai.llm_config import (
    get_raw_provider_config,
    merge_provider_update,
    public_llm_capability,
    redact_provider_config,
)
from axbi.genai.llm_errors import (
    LLMError,
    LLMInvalidConfigError,
    LLMNotConfiguredError,
    LLMSsrfBlockedError,
)
from axbi.genai.llm_provider import StubLLMProvider
from axbi.genai.provider_factory import (
    build_provider_from_config,
    reset_provider,
)
from axbi.views.base_api import BaseAxBIApi, requires_json, statsd_metrics

logger = logging.getLogger(__name__)


class _ProbeResult(BaseModel):
    """Minimal schema for Admin connection tests."""

    ok: bool = Field(description="Whether the probe succeeded")


class GenaiCapabilitiesRestApi(BaseAxBIApi):
    """Authenticated capability discovery for GenAI / authoring clients."""

    resource_name = "genai"
    # Reuse Dashboard read so Gamma/Alpha can discover capabilities without a
    # new FAB permission rollout. Secrets are never returned here.
    class_permission_name = "Dashboard"
    method_permission_name = {
        "get_capabilities": "can_read",
    }
    openapi_spec_tag = "GenAI"
    allow_browser_login = True

    @expose("/capabilities/", methods=("GET",))
    @protect()
    @safe
    @statsd_metrics
    @event_logger.log_this_with_context(
        action=lambda self, *args, **kwargs: f"{self.__class__.__name__}.capabilities",
        log_to_statsd=False,
    )
    def get_capabilities(self) -> Response:
        """Return whether a server-side LLM is configured (no secrets).
        ---
        get:
          summary: GenAI capability discovery
          responses:
            200:
              description: Capability metadata
              content:
                application/json:
                  schema:
                    type: object
                    properties:
                      result:
                        type: object
            401:
              $ref: '#/components/responses/401'
        """
        result = public_llm_capability()
        result["source"] = "server"
        return self.response(200, result=result)


class GenaiLlmProviderRestApi(BaseAxBIApi):
    """Admin-only LLM provider configuration (URL, model, token).

    Production deployments should prefer environment / secret-manager injection
    into ``GENAI_LLM_PROVIDER_CONFIG``. PUT updates the running app config and
    is suitable for single-node Admin convenience; multi-worker fleets should
    still use env for durable secrets.
    """

    resource_name = "admin/genai/llm"
    # FAB permission surface Admin already holds; is_admin() is the real gate.
    class_permission_name = "Database"
    method_permission_name = {
        "get_provider": "can_read",
        "put_provider": "can_write",
        "delete_provider": "can_write",
        "test_provider": "can_write",
    }
    openapi_spec_tag = "GenAI Admin"
    allow_browser_login = True

    put_schema = LlmProviderPutSchema()
    test_schema = LlmProviderTestSchema()

    def _admin_or_403(self) -> Response | None:
        if not security_manager.is_admin():
            return self.response(
                403,
                message="Only administrators can manage LLM provider settings",
            )
        return None

    @expose("/provider/", methods=("GET",))
    @protect()
    @safe
    @statsd_metrics
    @event_logger.log_this_with_context(
        action=lambda self, *args, **kwargs: f"{self.__class__.__name__}.get_provider",
        log_to_statsd=False,
    )
    def get_provider(self) -> Response:
        """Get redacted LLM provider settings (Admin only).
        ---
        get:
          summary: Get LLM provider metadata
          responses:
            200:
              description: Redacted provider settings
            403:
              $ref: '#/components/responses/403'
        """
        if denied := self._admin_or_403():
            return denied
        return self.response(200, result=redact_provider_config())

    @expose("/provider/", methods=("PUT",))
    @protect()
    @safe
    @statsd_metrics
    @requires_json
    @event_logger.log_this_with_context(
        action=lambda self, *args, **kwargs: f"{self.__class__.__name__}.put_provider",
        log_to_statsd=False,
    )
    def put_provider(self) -> Response:
        """Create or update LLM provider settings (Admin only).
        ---
        put:
          summary: Set LLM provider
          requestBody:
            required: true
            content:
              application/json:
                schema:
                  type: object
          responses:
            200:
              description: Updated redacted settings
            403:
              $ref: '#/components/responses/403'
            400:
              $ref: '#/components/responses/400'
        """
        if denied := self._admin_or_403():
            return denied
        try:
            body: dict[str, Any] = self.put_schema.load(
                request.get_json(cache=True, silent=True) or {}
            )
        except ValidationError as error:
            return self.response_400(message=error.messages)

        existing = get_raw_provider_config()
        merged = merge_provider_update(existing, body)

        if body.get("enabled", True):
            try:
                provider = build_provider_from_config(merged)
                if isinstance(provider, StubLLMProvider):
                    return self.response(
                        400,
                        message="Provider configuration resolved to stub",
                        code="LLM_INVALID_CONFIG",
                    )
            except LLMSsrfBlockedError as ex:
                return self.response(400, message=str(ex), code=ex.code)
            except LLMInvalidConfigError as ex:
                return self.response(400, message=str(ex), code=ex.code)
            except LLMError as ex:
                return self.response(400, message=str(ex), code=ex.code)

        current_app.config["GENAI_LLM_PROVIDER_CONFIG"] = merged
        reset_provider()
        logger.info(
            "Admin updated GENAI LLM provider type=%s enabled=%s",
            merged.get("provider"),
            merged.get("enabled", True),
        )
        return self.response(
            200,
            result=redact_provider_config(merged),
            message=(
                "Provider saved in application config for this process. "
                "For multi-worker production, set GENAI_LLM_* environment variables."
            ),
        )

    @expose("/provider/", methods=("DELETE",))
    @protect()
    @safe
    @statsd_metrics
    @event_logger.log_this_with_context(
        action=lambda self, *args, **kwargs: f"{self.__class__.__name__}.delete_provider",
        log_to_statsd=False,
    )
    def delete_provider(self) -> Response:
        """Clear runtime LLM provider config (Admin only).
        ---
        delete:
          summary: Clear runtime LLM provider
          responses:
            200:
              description: Provider cleared
            403:
              $ref: '#/components/responses/403'
        """
        if denied := self._admin_or_403():
            return denied
        current_app.config["GENAI_LLM_PROVIDER_CONFIG"] = {}
        reset_provider()
        logger.info("Admin cleared runtime GENAI LLM provider config")
        return self.response(200, result=redact_provider_config({}), message="cleared")

    @expose("/provider/test/", methods=("POST",))
    @protect()
    @safe
    @statsd_metrics
    @event_logger.log_this_with_context(
        action=lambda self, *args, **kwargs: f"{self.__class__.__name__}.test_provider",
        log_to_statsd=False,
    )
    def test_provider(self) -> Response:
        """Run a minimal LLM probe (Admin only). Does not persist overrides.
        ---
        post:
          summary: Test LLM provider connection
          requestBody:
            required: false
            content:
              application/json:
                schema:
                  type: object
          responses:
            200:
              description: Probe result
            403:
              $ref: '#/components/responses/403'
        """
        if denied := self._admin_or_403():
            return denied
        payload = request.get_json(cache=True, silent=True) or {}
        try:
            body: dict[str, Any] = self.test_schema.load(payload)
        except ValidationError as error:
            return self.response_400(message=error.messages)

        overrides = {k: v for k, v in body.items() if v is not None}
        existing = get_raw_provider_config()
        candidate = merge_provider_update(existing, overrides) if overrides else existing

        try:
            provider = build_provider_from_config(candidate)
            if isinstance(provider, StubLLMProvider):
                raise LLMNotConfiguredError()
            result = provider.complete_json(
                system_prompt="Reply with JSON only.",
                user_prompt='Return {"ok": true}',
                response_schema=_ProbeResult,
                metadata={"operation": "admin_llm_test"},
            )
            ok = bool(getattr(result, "ok", False))
            return self.response(
                200,
                result={
                    "ok": ok,
                    "provider": provider.provider_name(),
                    "model": provider.model_name(),
                },
            )
        except LLMNotConfiguredError as ex:
            return self.response(
                400, message=str(ex), code=ex.code, result={"ok": False}
            )
        except LLMSsrfBlockedError as ex:
            return self.response(
                400, message=str(ex), code=ex.code, result={"ok": False}
            )
        except LLMInvalidConfigError as ex:
            return self.response(
                400, message=str(ex), code=ex.code, result={"ok": False}
            )
        except LLMError as ex:
            return self.response(
                502, message=str(ex), code=ex.code, result={"ok": False}
            )
        except Exception:  # noqa: BLE001 - Admin test must not leak stacks
            logger.exception("Admin LLM connection test failed")
            return self.response(
                502,
                message="LLM test failed",
                code="LLM_PROVIDER_ERROR",
                result={"ok": False},
            )

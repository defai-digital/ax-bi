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
"""Dedicated GenAI LLM audit events (no secrets in payloads)."""

from __future__ import annotations

import logging
import time
from typing import Any
from urllib.parse import urlparse

from axbi.extensions import event_logger, stats_logger_manager

logger = logging.getLogger(__name__)

# Stable action names (tech-spec §12).
ACTION_CONFIG_UPDATED = "genai.llm.config_updated"
ACTION_TEST_CONNECTION = "genai.llm.test_connection"
ACTION_COMPLETION = "genai.llm.completion"


def _safe_user_id() -> int | None:
    try:
        from axbi.utils.core import get_user_id

        return get_user_id()
    except Exception:  # pylint: disable=broad-except
        return None


def base_host_from_url(base_url: str | None) -> str | None:
    """Return hostname only for audit (never userinfo or path secrets)."""
    if not base_url:
        return None
    try:
        parsed = urlparse(str(base_url).strip())
        return parsed.hostname
    except Exception:  # pylint: disable=broad-except
        return None


def _emit(
    action: str,
    *,
    user_id: int | None = None,
    records: list[dict[str, Any]] | None = None,
    duration_ms: int | None = None,
    log_to_statsd: bool = True,
) -> None:
    """Best-effort event log write; never raises into product paths."""
    if log_to_statsd:
        try:
            stats_logger_manager.instance.incr(action)
        except Exception:  # pylint: disable=broad-except
            logger.debug("stats_logger incr failed for %s", action, exc_info=True)
    try:
        event_logger.log(
            user_id if user_id is not None else _safe_user_id(),
            action,
            records=records or [{}],
            dashboard_id=None,
            duration_ms=duration_ms,
            slice_id=None,
            referrer=None,
            curated_payload=None,
            curated_form_data=None,
        )
    except Exception:  # pylint: disable=broad-except
        logger.debug("event_logger failed for %s", action, exc_info=True)


def log_llm_config_updated(
    *,
    provider: str | None,
    enabled: bool,
    base_url: str | None = None,
    model: str | None = None,
    user_id: int | None = None,
    cleared: bool = False,
) -> None:
    """Audit Admin create/update/clear of the server LLM provider."""
    record = {
        "provider_type": provider,
        "enabled": enabled,
        "base_host": base_host_from_url(base_url),
        "model": model,
        "cleared": cleared,
        # Explicitly never include api_key / token material.
    }
    _emit(ACTION_CONFIG_UPDATED, user_id=user_id, records=[record])


def log_llm_test_connection(
    *,
    success: bool,
    provider: str | None = None,
    model: str | None = None,
    error_code: str | None = None,
    user_id: int | None = None,
    duration_ms: int | None = None,
) -> None:
    """Audit Admin connection probe (no secrets, no prompt content)."""
    record = {
        "success": success,
        "provider_type": provider,
        "model": model,
        "error_code": error_code,
    }
    _emit(
        ACTION_TEST_CONNECTION,
        user_id=user_id,
        records=[record],
        duration_ms=duration_ms,
    )


def log_llm_completion(
    *,
    operation: str,
    status: str,
    provider_type: str | None = None,
    model: str | None = None,
    latency_ms: int | None = None,
    user_id: int | None = None,
) -> None:
    """Audit outbound LLM completions (labels only — no prompts or tokens)."""
    record = {
        "operation": operation,
        "status": status,
        "provider_type": provider_type,
        "model": model,
    }
    _emit(
        ACTION_COMPLETION,
        user_id=user_id,
        records=[record],
        duration_ms=latency_ms,
    )


def timed_complete_json(
    provider: Any,
    *,
    system_prompt: str,
    user_prompt: str,
    response_schema: Any,
    metadata: dict[str, Any] | None = None,
) -> Any:
    """Call ``provider.complete_json`` and emit a completion audit event."""
    meta = dict(metadata or {})
    operation = str(
        meta.get("operation")
        or meta.get("action")
        or meta.get("tool")
        or "complete_json"
    )
    provider_type = None
    model = None
    try:
        provider_type = provider.provider_name()
        model = provider.model_name()
    except Exception:  # pylint: disable=broad-except
        logger.debug("Could not read provider identity for audit", exc_info=True)

    started = time.monotonic()
    try:
        result = provider.complete_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_schema=response_schema,
            metadata=meta,
        )
        latency_ms = int((time.monotonic() - started) * 1000)
        if provider_type != "stub":
            log_llm_completion(
                operation=operation,
                status="ok",
                provider_type=provider_type,
                model=model,
                latency_ms=latency_ms,
            )
        return result
    except Exception as exc:  # pylint: disable=broad-except
        latency_ms = int((time.monotonic() - started) * 1000)
        code = getattr(exc, "code", None) or type(exc).__name__
        if provider_type != "stub" or code == "LLM_NOT_CONFIGURED":
            log_llm_completion(
                operation=operation,
                status=str(code),
                provider_type=provider_type,
                model=model,
                latency_ms=latency_ms,
            )
        raise

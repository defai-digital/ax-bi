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
"""Normalize and redact Admin/operator LLM provider configuration."""

from __future__ import annotations

import os
from typing import Any

from flask import current_app, has_app_context

from axbi.genai.llm_errors import LLMInvalidConfigError

# Hard ceiling for outbound LLM HTTP timeouts (seconds).
MAX_TIMEOUT_SECONDS = 300
DEFAULT_TIMEOUT_SECONDS = 60
DEFAULT_OPENAI_BASE_URL = "https://api.openai.com/v1"

SUPPORTED_PROVIDERS = frozenset(
    {
        "anthropic",
        "openai",
        "openai_compatible",
    }
)


def _as_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "on"}:
        return True
    if text in {"0", "false", "no", "off", ""}:
        return False
    return default


def _as_int(value: Any, default: int, *, minimum: int, maximum: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = default
    return max(minimum, min(maximum, number))


def build_provider_config_from_env(
    environ: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Build ``GENAI_LLM_PROVIDER_CONFIG`` from environment variables.

    Empty ``GENAI_LLM_PROVIDER`` yields an empty dict (LLM optional).
    """
    env = environ if environ is not None else os.environ
    provider = (env.get("GENAI_LLM_PROVIDER") or "").strip().lower()
    if not provider:
        return {}

    config: dict[str, Any] = {
        "provider": provider,
        "api_key": env.get("GENAI_LLM_API_KEY")
        or env.get("ANTHROPIC_API_KEY")
        or env.get("OPENAI_API_KEY")
        or "",
        "model": env.get("GENAI_LLM_MODEL") or "",
        "enabled": _as_bool(env.get("GENAI_LLM_ENABLED"), default=True),
    }
    if env.get("GENAI_LLM_BASE_URL"):
        config["base_url"] = env["GENAI_LLM_BASE_URL"].strip()
    if env.get("GENAI_LLM_TIMEOUT_SECONDS"):
        config["timeout_seconds"] = env["GENAI_LLM_TIMEOUT_SECONDS"]
    if env.get("GENAI_LLM_MAX_RETRIES"):
        config["max_retries"] = env["GENAI_LLM_MAX_RETRIES"]
    if env.get("GENAI_LLM_ALLOW_HTTP") is not None:
        config["allow_http"] = env.get("GENAI_LLM_ALLOW_HTTP")
    if env.get("GENAI_LLM_VERIFY_TLS") is not None:
        config["verify_tls"] = env.get("GENAI_LLM_VERIFY_TLS")
    if env.get("GENAI_LLM_ALLOW_PRIVATE_NETWORK") is not None:
        config["allow_private_network"] = env.get("GENAI_LLM_ALLOW_PRIVATE_NETWORK")
    if env.get("GENAI_LLM_URL_ALLOWLIST"):
        config["url_allowlist"] = [
            part.strip()
            for part in env["GENAI_LLM_URL_ALLOWLIST"].split(",")
            if part.strip()
        ]
    return config


def get_raw_provider_config() -> dict[str, Any]:
    """Return the raw provider dict from Flask config when available."""
    if not has_app_context():
        return {}
    raw = current_app.config.get("GENAI_LLM_PROVIDER_CONFIG") or {}
    if not isinstance(raw, dict):
        return {}
    return dict(raw)


def normalize_provider_config(raw: dict[str, Any] | None) -> dict[str, Any]:
    """Normalize a provider config dict; empty when disabled or missing.

    Does not perform SSRF validation (that runs when constructing the client).
    """
    if not raw:
        return {}

    enabled = _as_bool(raw.get("enabled"), default=True)
    if not enabled:
        return {}

    provider = str(raw.get("provider") or "").strip().lower()
    if not provider:
        return {}

    timeout = _as_int(
        raw.get("timeout_seconds", raw.get("timeout", DEFAULT_TIMEOUT_SECONDS)),
        DEFAULT_TIMEOUT_SECONDS,
        minimum=1,
        maximum=MAX_TIMEOUT_SECONDS,
    )
    max_retries = _as_int(raw.get("max_retries", 1), 1, minimum=0, maximum=3)

    allowlist_raw = raw.get("url_allowlist") or raw.get("host_allowlist") or []
    if isinstance(allowlist_raw, str):
        allowlist = [p.strip() for p in allowlist_raw.split(",") if p.strip()]
    else:
        allowlist = [str(p).strip() for p in allowlist_raw if str(p).strip()]

    model = str(raw.get("model") or "").strip()
    api_key = raw.get("api_key")
    api_key_str = "" if api_key is None else str(api_key)

    base_url = raw.get("base_url")
    base_url_str = str(base_url).strip() if base_url else ""

    # Defaults for cloud OpenAI profile.
    if provider == "openai" and not base_url_str:
        base_url_str = DEFAULT_OPENAI_BASE_URL

    if provider == "anthropic" and not model:
        model = "claude-sonnet-4-20250514"
    if provider in {"openai", "openai_compatible"} and not model:
        model = "gpt-4o-mini" if provider == "openai" else "llama3.1"

    extra_headers = raw.get("extra_headers") or {}
    if not isinstance(extra_headers, dict):
        extra_headers = {}
    # Strip hop-by-hop / dangerous headers
    blocked = {"host", "content-length", "connection", "transfer-encoding"}
    safe_headers = {
        str(k): str(v)
        for k, v in extra_headers.items()
        if str(k).lower() not in blocked
    }

    return {
        "enabled": True,
        "provider": provider,
        "base_url": base_url_str or None,
        "model": model,
        "api_key": api_key_str,
        "timeout_seconds": timeout,
        "max_retries": max_retries,
        "verify_tls": _as_bool(raw.get("verify_tls"), default=True),
        "allow_http": _as_bool(raw.get("allow_http"), default=False),
        "allow_private_network": _as_bool(
            raw.get("allow_private_network"), default=False
        ),
        "url_allowlist": allowlist,
        "extra_headers": safe_headers,
        "max_tokens": _as_int(
            raw.get("max_tokens", 4096),
            4096,
            minimum=1,
            maximum=128000,
        ),
    }


def validate_normalized_config(config: dict[str, Any]) -> None:
    """Raise ``LLMInvalidConfigError`` when required fields are missing."""
    if not config:
        raise LLMInvalidConfigError("LLM provider is not configured")
    provider = config.get("provider")
    if provider not in SUPPORTED_PROVIDERS:
        raise LLMInvalidConfigError(
            f"Unsupported LLM provider {provider!r}. "
            f"Supported: {sorted(SUPPORTED_PROVIDERS)}"
        )
    if provider in {"openai", "openai_compatible"} and not config.get("base_url"):
        raise LLMInvalidConfigError(f"base_url is required for provider {provider!r}")
    if provider == "openai" and not (config.get("api_key") or "").strip():
        raise LLMInvalidConfigError("api_key is required for provider 'openai'")
    if not (config.get("model") or "").strip():
        raise LLMInvalidConfigError("model is required when LLM is enabled")


def is_llm_configured(raw: dict[str, Any] | None = None) -> bool:
    """Return True when a non-stub provider can be constructed from config."""
    try:
        cfg = normalize_provider_config(
            raw if raw is not None else get_raw_provider_config()
        )
        if not cfg:
            return False
        validate_normalized_config(cfg)
        return True
    except LLMInvalidConfigError:
        return False


def redact_provider_config(raw: dict[str, Any] | None = None) -> dict[str, Any]:
    """Admin-safe metadata: never includes the raw token value."""
    source = raw if raw is not None else get_raw_provider_config()
    if not source:
        return {
            "enabled": False,
            "provider": None,
            "base_url": None,
            "model": None,
            "api_key_set": False,
            "timeout_seconds": DEFAULT_TIMEOUT_SECONDS,
            "verify_tls": True,
            "allow_http": False,
            "allow_private_network": False,
            "configured": False,
        }

    enabled_flag = _as_bool(source.get("enabled"), default=True)
    normalized = normalize_provider_config(source) if enabled_flag else {}
    api_key = source.get("api_key")
    api_key_set = bool(api_key and str(api_key).strip())

    if not normalized:
        return {
            "enabled": False,
            "provider": str(source.get("provider") or "").strip().lower() or None,
            "base_url": source.get("base_url"),
            "model": source.get("model"),
            "api_key_set": api_key_set,
            "timeout_seconds": DEFAULT_TIMEOUT_SECONDS,
            "verify_tls": _as_bool(source.get("verify_tls"), default=True),
            "allow_http": _as_bool(source.get("allow_http"), default=False),
            "allow_private_network": _as_bool(
                source.get("allow_private_network"), default=False
            ),
            "configured": False,
        }

    return {
        "enabled": True,
        "provider": normalized["provider"],
        "base_url": normalized.get("base_url"),
        "model": normalized.get("model"),
        "api_key_set": api_key_set,
        "timeout_seconds": normalized["timeout_seconds"],
        "verify_tls": normalized["verify_tls"],
        "allow_http": normalized["allow_http"],
        "allow_private_network": normalized["allow_private_network"],
        "configured": True,
    }


def public_llm_capability(raw: dict[str, Any] | None = None) -> dict[str, Any]:
    """Capability fragment safe for non-admin clients (no secrets, no base_url)."""
    from axbi.genai.prompt_policy import bounded_samples_allowed

    redacted = redact_provider_config(raw)
    configured = bool(redacted.get("configured"))
    samples_ok = bounded_samples_allowed()
    return {
        "llm_configured": configured,
        "llm_provider_type": redacted.get("provider") if configured else None,
        "llm_model": redacted.get("model") if configured else None,
        "bounded_samples_allowed": samples_ok,
        # Feature surface (independent of whether credentials are present).
        # Clients still honor feature flags and RBAC on each tool call.
        "genai_features": {
            "plan_dashboard": True,
            "create_chart_from_intent": True,
            "prompt_to_dashboard": True,
            "semantic_assist": True,
            "bounded_samples": samples_ok,
        },
    }


def merge_provider_update(
    existing: dict[str, Any],
    update: dict[str, Any],
) -> dict[str, Any]:
    """Merge Admin PUT payload into existing config (omit api_key to keep)."""
    merged = dict(existing or {})
    for key, value in update.items():
        if key == "api_key" and (value is None or value == ""):
            continue
        if key in {
            "enabled",
            "provider",
            "base_url",
            "model",
            "api_key",
            "timeout_seconds",
            "max_retries",
            "verify_tls",
            "allow_http",
            "allow_private_network",
            "url_allowlist",
            "extra_headers",
            "max_tokens",
        }:
            merged[key] = value
    return merged

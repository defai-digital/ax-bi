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
"""Durable Admin LLM provider settings (encrypted secret at rest).

Stores the Admin-configured provider profile in the shared key-value table so
all app workers see the same Activate/Disable state. The API key is encrypted
with a Fernet key derived from ``SECRET_KEY``; non-secret fields are stored as
plain JSON for Admin troubleshooting.

Environment / ``GENAI_LLM_PROVIDER_CONFIG`` remains the bootstrap source when
no durable Admin settings exist (12-factor production). After Admin saves via
the UI/API, durable settings take precedence until cleared.
"""

from __future__ import annotations

import base64
import hashlib
import logging
from typing import Any

from cryptography.fernet import Fernet, InvalidToken
from flask import current_app, has_app_context

from axbi.key_value.shared_entries import (
    get_shared_value,
    upsert_shared_value,
)
from axbi.key_value.types import SharedKey
from axbi.utils.decorators import transaction

logger = logging.getLogger(__name__)

# Fields persisted in the durable blob (api_key is stored encrypted separately).
_PERSIST_KEYS = frozenset(
    {
        "enabled",
        "provider",
        "base_url",
        "model",
        "timeout_seconds",
        "max_retries",
        "verify_tls",
        "allow_http",
        "allow_private_network",
        "url_allowlist",
        "extra_headers",
        "max_tokens",
    }
)


def _fernet() -> Fernet:
    secret = current_app.config["SECRET_KEY"]
    if not isinstance(secret, (bytes, bytearray)):
        secret = str(secret).encode("utf-8")
    digest = hashlib.sha256(secret).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def _encrypt_api_key(api_key: str) -> str:
    return _fernet().encrypt(api_key.encode("utf-8")).decode("ascii")


def _decrypt_api_key(token: str) -> str:
    return _fernet().decrypt(token.encode("ascii")).decode("utf-8")


def config_fingerprint(raw: dict[str, Any] | None) -> str:
    """Stable fingerprint used to invalidate the process-local provider cache."""
    if not raw:
        return "empty"
    api_key = raw.get("api_key") or ""
    payload = "|".join(
        [
            str(raw.get("enabled")),
            str(raw.get("provider") or ""),
            str(raw.get("base_url") or ""),
            str(raw.get("model") or ""),
            hashlib.sha256(str(api_key).encode("utf-8")).hexdigest()[:24],
            str(raw.get("timeout_seconds") or ""),
            str(raw.get("verify_tls")),
            str(raw.get("allow_http")),
            str(raw.get("allow_private_network")),
            str(raw.get("max_retries") or ""),
            str(raw.get("max_tokens") or ""),
        ]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def load_durable_provider_config() -> dict[str, Any] | None:
    """Load durable Admin settings, or ``None`` when none have been saved.

    Returns a plain config dict with decrypted ``api_key`` (may be empty).
    """
    if not has_app_context():
        return None
    try:
        stored = get_shared_value(SharedKey.GENAI_LLM_PROVIDER)
    except Exception:  # noqa: BLE001 - missing table / no session must not break BI
        logger.debug("Durable GenAI LLM settings unavailable", exc_info=True)
        return None

    if not isinstance(stored, dict) or not stored:
        return None

    config: dict[str, Any] = {
        key: stored[key] for key in _PERSIST_KEYS if key in stored
    }

    encrypted = stored.get("api_key_encrypted")
    if encrypted:
        try:
            config["api_key"] = _decrypt_api_key(str(encrypted))
        except (InvalidToken, ValueError, TypeError) as ex:
            logger.error(
                "Failed to decrypt durable GenAI LLM api_key; treating as empty (%s)",
                type(ex).__name__,
            )
            config["api_key"] = ""
    else:
        config["api_key"] = ""

    return config


def save_durable_provider_config(config: dict[str, Any]) -> None:
    """Persist Admin provider settings with encrypted api_key."""
    blob: dict[str, Any] = {
        key: config[key] for key in _PERSIST_KEYS if key in config
    }
    api_key = config.get("api_key")
    if api_key is not None and str(api_key).strip():
        blob["api_key_encrypted"] = _encrypt_api_key(str(api_key))
    else:
        # Preserve existing encrypted secret when caller omitted a new key.
        existing = get_shared_value(SharedKey.GENAI_LLM_PROVIDER)
        if isinstance(existing, dict) and existing.get("api_key_encrypted"):
            blob["api_key_encrypted"] = existing["api_key_encrypted"]
    # upsert_shared_value is @transaction()-wrapped (commits).
    upsert_shared_value(SharedKey.GENAI_LLM_PROVIDER, blob)


@transaction()
def clear_durable_provider_config() -> None:
    """Remove durable Admin LLM settings (fall back to env/app config)."""
    from uuid import uuid3

    from axbi.daos.key_value import KeyValueDAO
    from axbi.key_value.types import KeyValueResource
    from axbi.key_value.utils import get_uuid_namespace

    namespace = get_uuid_namespace("")
    uuid_key = uuid3(namespace, SharedKey.GENAI_LLM_PROVIDER.value)
    KeyValueDAO.delete_entry(KeyValueResource.APP, uuid_key)

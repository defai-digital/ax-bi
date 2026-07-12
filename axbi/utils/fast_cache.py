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
"""Fast Data API Gateway cache writer.

Writes pre-serialized JSON chart data to Redis so the Node.js sidecar
(``ax-bi-websocket``) can serve cached responses directly from Redis,
bypassing the Flask backend entirely.

The fast-cache entry is a plain JSON string stored under the key
``{prefix}{cache_key}`` (default prefix: ``fc:``).  The Node.js gateway
reads this key and returns it as ``Content-Type: application/json``.

This module is intentionally simple and fire-and-forget: failures writing
to the fast cache are logged but never propagate to the caller, so a Redis
outage does not affect chart data responses.
"""

from __future__ import annotations

import logging
from typing import Any

from flask import current_app

logger = logging.getLogger(__name__)


def _get_redis_client() -> Any | None:
    """Return a Redis client from the data cache backend, or None.

    The fast-cache writer piggybacks on whichever Redis backend is
    configured in ``DATA_CACHE_CONFIG`` (or ``CACHE_CONFIG`` as a fallback).
    If the cache backend is not Redis-based (e.g. NullCache, filesystem),
    returns ``None`` and the writer is silently skipped.
    """
    try:
        from axbi.extensions import cache_manager

        # Prefer data_cache over default cache since chart data lives there
        cache = getattr(cache_manager, "data_cache", None) or cache_manager.cache
        underlying = getattr(cache, "cache", cache)

        # Flask-Caching RedisCache exposes _write_client or _read_client
        redis_client = getattr(underlying, "_write_client", None) or getattr(
            underlying, "_read_client", None
        )
        if redis_client is not None:
            return redis_client

        # Flask-Caching RedisCache also stores the raw client
        return getattr(underlying, "_client", None)
    except Exception:  # pylint: disable=broad-except
        logger.debug("Fast cache: unable to obtain Redis client", exc_info=True)
        return None


def set_fast_cache(
    key: str,
    json_str: str,
    timeout: int | None = None,
) -> None:
    """Write a pre-serialized JSON string to the fast-cache Redis key.

    This is a fire-and-forget operation: any error is caught and logged
    but never raised, so it cannot affect the chart data API response.

    :param key: The chart data cache key (same key used for the DataFrame cache)
    :param json_str: The fully serialized JSON response string
    :param timeout: Cache TTL in seconds; falls back to CACHE_DEFAULT_TIMEOUT
    """
    if not current_app.config.get("FAST_CACHE_ENABLED", False):
        return

    if not key:
        return

    prefix = current_app.config.get("FAST_CACHE_KEY_PREFIX", "fc:")
    full_key = f"{prefix}{key}"

    if timeout is None:
        timeout = current_app.config.get("CACHE_DEFAULT_TIMEOUT", 86400)

    try:
        redis_client = _get_redis_client()
        if redis_client is None:
            logger.debug("Fast cache: no Redis client available, skipping write")
            return

        redis_client.set(full_key, json_str, ex=timeout)
        logger.debug(
            "Fast cache SET: key=%s, size=%d, timeout=%d",
            full_key,
            len(json_str),
            timeout,
        )
    except Exception:  # pylint: disable=broad-except
        logger.warning("Fast cache: failed to write key %s", full_key, exc_info=True)


def get_fast_cache(key: str) -> str | None:
    """Read a fast-cache JSON string from Redis.

    Primarily used by the Node.js gateway, but available for Python-side
    consumers that want to check the fast-cache entry directly.

    :param key: The chart data cache key
    :returns: The cached JSON string, or None if not found
    """
    if not current_app.config.get("FAST_CACHE_ENABLED", False):
        return None

    if not key:
        return None

    prefix = current_app.config.get("FAST_CACHE_KEY_PREFIX", "fc:")
    full_key = f"{prefix}{key}"

    try:
        redis_client = _get_redis_client()
        if redis_client is None:
            return None

        value = redis_client.get(full_key)
        if value is not None:
            if isinstance(value, bytes):
                return value.decode("utf-8")
            return str(value)
        return None
    except Exception:  # pylint: disable=broad-except
        logger.warning("Fast cache: failed to read key %s", full_key, exc_info=True)
        return None

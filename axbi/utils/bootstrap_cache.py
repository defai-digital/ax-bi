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
"""Bootstrap cache helpers for non-views layers.

Models (e.g. Theme event listeners) must clear the common bootstrap memoize
cache without importing ``axbi.views``. The memoized function is registered
from the views package at import time.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)

_cached_common_bootstrap_data: Callable[..., Any] | None = None


def register_common_bootstrap_cache_fn(fn: Callable[..., Any]) -> None:
    """Register the memoized common-bootstrap function for later invalidation."""
    global _cached_common_bootstrap_data  # noqa: PLW0603
    _cached_common_bootstrap_data = fn


def clear_common_bootstrap_cache() -> None:
    """Invalidate the memoized common bootstrap payload (if registered)."""
    if _cached_common_bootstrap_data is None:
        logger.debug(
            "clear_common_bootstrap_cache: no bootstrap function registered yet"
        )
        return
    # Lazy import keeps this module free of Flask-app construction side effects
    from axbi.extensions import cache_manager

    try:
        cache_manager.cache.delete_memoized(_cached_common_bootstrap_data)
    except Exception as ex:  # pylint: disable=broad-except  # noqa: BLE001
        logger.warning("Failed to clear common bootstrap cache: %s", ex)

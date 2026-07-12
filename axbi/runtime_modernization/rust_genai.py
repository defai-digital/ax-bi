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
"""Optional Rust-backed GenAI helper kernels for runtime modernization."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import Any

try:
    from ax_genai import rank_assets as _imported_rust_rank_assets
except ImportError:  # pragma: no cover - exercised by fallback behavior
    _imported_rust_rank_assets = None

_rust_rank_assets: (
    Callable[[str, Sequence[Mapping[str, Any]], int], list[dict[str, Any]]] | None
) = _imported_rust_rank_assets


def rust_asset_ranking_kernel_available() -> bool:
    """Return whether the optional Rust asset-ranking extension is importable."""

    return _rust_rank_assets is not None


def rank_assets(
    query: str,
    candidates: Sequence[Mapping[str, Any]],
    limit: int,
) -> list[dict[str, Any]]:
    """Rank asset-search candidates with the optional Rust GenAI kernel."""

    if _rust_rank_assets is None:
        raise RuntimeError("Rust GenAI asset ranking kernel is not available")

    return _rust_rank_assets(query, candidates, limit)

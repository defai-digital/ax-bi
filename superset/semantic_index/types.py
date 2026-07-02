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
"""Typed values for the GenAI BI semantic index."""

from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from typing import Any

from superset.utils import json


@dataclass(frozen=True)
class SemanticDocument:
    """AI-ready text distilled from a governed Superset object."""

    object_type: str
    object_id: str
    object_name: str
    document_kind: str
    source: str
    content: str
    dataset_id: int | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def source_hash(self) -> str:
        """Return a stable hash for the document source payload."""

        payload = {
            "object_type": self.object_type,
            "object_id": self.object_id,
            "object_name": self.object_name,
            "document_kind": self.document_kind,
            "source": self.source,
            "content": self.content,
            "dataset_id": self.dataset_id,
            "extra": self.extra,
        }
        serialized = json.dumps(payload, sort_keys=True)
        return sha256(serialized.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class SemanticSearchResult:
    """Result returned from semantic document retrieval."""

    uuid: str
    object_type: str
    object_id: str
    object_name: str
    document_kind: str
    content: str
    distance: float | None
    dataset_id: int | None = None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SemanticIndexSummary:
    """Summary for a semantic index write operation."""

    documents_seen: int
    documents_written: int
    embedding_model: str
    embedding_dimension: int

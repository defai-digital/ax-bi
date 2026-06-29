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
import pytest

from superset.runtime_modernization.inventory import (
    get_candidate_inventory,
    get_inventory_item,
    get_runtime_inventory,
    MigrationDisposition,
    Runtime,
)


def test_runtime_inventory_names_are_unique() -> None:
    """Inventory areas are stable identifiers for follow-up tooling."""

    areas = [item.area for item in get_runtime_inventory()]

    assert len(areas) == len(set(areas))


def test_runtime_inventory_keeps_security_and_metadata_in_python() -> None:
    """Security-sensitive Superset core areas are not extraction candidates."""

    security = get_inventory_item("auth_rbac_security")
    metadata = get_inventory_item("metadata_models_daos")

    assert security.target_runtime == Runtime.PYTHON
    assert security.disposition == MigrationDisposition.KEEP
    assert metadata.target_runtime == Runtime.PYTHON
    assert metadata.disposition == MigrationDisposition.KEEP


def test_runtime_inventory_identifies_typescript_candidates() -> None:
    """AX-BI orchestration areas are TypeScript candidates."""

    candidates = {item.area: item for item in get_candidate_inventory()}

    assert candidates["mcp_orchestration"].target_runtime == Runtime.TYPESCRIPT
    assert candidates["genai_orchestration"].target_runtime == Runtime.TYPESCRIPT
    assert candidates["asset_search_indexing"].target_runtime == Runtime.TYPESCRIPT


def test_runtime_inventory_identifies_rust_candidates() -> None:
    """CPU-oriented kernels are Rust candidates only with required evidence."""

    candidates = {item.area: item for item in get_candidate_inventory()}

    assert candidates["sql_parsing_normalization"].target_runtime == Runtime.RUST
    assert (
        "benchmark improvement"
        in candidates["sql_parsing_normalization"].required_evidence
    )
    assert candidates["chart_validation_kernels"].target_runtime == Runtime.RUST


def test_get_inventory_item_raises_for_unknown_area() -> None:
    """Unknown inventory areas fail loudly."""

    with pytest.raises(KeyError, match="Unknown runtime modernization area"):
        get_inventory_item("missing")

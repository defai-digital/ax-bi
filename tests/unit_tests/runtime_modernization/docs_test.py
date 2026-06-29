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
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
DOCS_ROOT = REPO_ROOT / "ax-internal" / "docs"
BOUNDARY_ADR = DOCS_ROOT / "runtime-modernization-boundary-decision-adr.md"
INITIAL_ADR = DOCS_ROOT / "runtime-modernization-adr.md"
PHASED_PLAN = DOCS_ROOT / "runtime-modernization-phased-plan.md"


def test_runtime_modernization_boundary_adr_is_linked() -> None:
    """Boundary decision ADR is discoverable from the main planning docs."""

    boundary_name = "runtime-modernization-boundary-decision-adr.md"

    assert BOUNDARY_ADR.exists()
    assert boundary_name in INITIAL_ADR.read_text(encoding="utf-8")
    assert boundary_name in PHASED_PLAN.read_text(encoding="utf-8")


def test_runtime_modernization_boundary_adr_records_phase_six_decisions() -> None:
    """Boundary decision ADR records the large-boundary choices."""

    text = BOUNDARY_ADR.read_text(encoding="utf-8")

    assert "split by tool class" in text
    assert "No separate permission service is introduced" in text
    assert "Background jobs and Celery task families stay Python" in text
    assert "Rust owns only measured pure kernels" in text

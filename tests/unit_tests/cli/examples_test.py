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
"""Tests for the load_examples CLI orchestration."""

import sys
from types import ModuleType
from typing import Any, cast

from pytest_mock import MockerFixture


def test_load_examples_run_skips_auto_discovered_loaders(
    mocker: MockerFixture,
) -> None:
    """YAML config import owns bundled Parquet examples."""
    from superset.cli.examples import load_examples_run

    calls: list[tuple[str, bool | None]] = []
    examples_pkg = cast(Any, ModuleType("superset.examples"))
    examples = cast(Any, ModuleType("superset.examples.data_loading"))
    examples_pkg.data_loading = examples
    examples.AUTO_DISCOVERED_LOADERS = frozenset({"load_auto_dataset"})

    def load_css_templates() -> None:
        calls.append(("css", None))

    def load_auto_dataset(force: bool = False) -> None:
        calls.append(("auto", force))

    def load_big_data(force: bool = False) -> None:
        calls.append(("big_data", force))

    def load_examples_from_configs(
        force_data: bool = False,
        load_test_data: bool = False,
    ) -> None:
        calls.append(("configs", force_data))

    examples.load_css_templates = load_css_templates
    examples.load_auto_dataset = load_auto_dataset
    examples.load_big_data = load_big_data
    examples.load_examples_from_configs = load_examples_from_configs

    mocker.patch.dict(
        sys.modules,
        {
            "superset.examples": examples_pkg,
            "superset.examples.data_loading": examples,
        },
    )
    mocker.patch(
        "superset.cli.examples.database_utils.get_example_database",
        return_value="examples",
    )

    load_examples_run(load_big_data=True, force=True)

    assert calls == [
        ("css", None),
        ("big_data", True),
        ("configs", True),
    ]

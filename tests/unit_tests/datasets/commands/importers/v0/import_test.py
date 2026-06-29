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
from __future__ import annotations

import pytest
import yaml

from superset.commands.dataset.importers.v0 import ImportDatasetsCommand
from superset.commands.importers.exceptions import IncorrectVersionError
from superset.utils import json


def test_validate_accepts_v0_ui_export_dataset_params() -> None:
    """Valid v0 UI exports include object-shaped params with a database name."""
    contents = {
        "datasets.yaml": yaml.safe_dump(
            [
                {
                    "table_name": "birth_names",
                    "params": json.dumps({"database_name": "examples"}),
                }
            ]
        )
    }

    command = ImportDatasetsCommand(contents)
    command.validate()

    assert command._configs == {
        "datasets.yaml": [
            {
                "table_name": "birth_names",
                "params": '{"database_name": "examples"}',
            }
        ]
    }


@pytest.mark.parametrize(
    ("dataset", "message"),
    [
        ("not a dataset", "datasets.yaml has invalid dataset entry at index 0"),
        ({"params": "{"}, "datasets.yaml has invalid dataset params"),
        ({"params": "[]"}, "datasets.yaml has invalid dataset params"),
        ({"params": json.dumps({})}, "datasets.yaml has invalid dataset params"),
        (
            {"params": json.dumps({"database_name": None})},
            "datasets.yaml has invalid dataset params",
        ),
    ],
)
def test_validate_rejects_invalid_v0_ui_export_dataset_params(
    dataset: object,
    message: str,
) -> None:
    """Invalid v0 UI export params fail validation before import."""
    contents = {"datasets.yaml": yaml.safe_dump([dataset])}

    command = ImportDatasetsCommand(contents)

    with pytest.raises(IncorrectVersionError, match=message):
        command.validate()

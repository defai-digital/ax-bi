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

from types import SimpleNamespace

from pytest_mock import MockerFixture

from axbi.daos.ai import AISemanticAliasDAO


def test_semantic_alias_lookup_returns_nonempty_scoped_aliases(
    mocker: MockerFixture,
) -> None:
    """The DAO applies object and dataset scope before returning aliases."""
    query = mocker.patch("axbi.daos.ai.db.session.query").return_value
    query.filter.return_value = query
    query.all.return_value = [
        SimpleNamespace(alias="gross sales"),
        SimpleNamespace(alias=None),
    ]

    aliases = AISemanticAliasDAO.find_aliases_for_object(
        "column",
        "revenue",
        dataset_id=7,
    )

    assert aliases == ["gross sales"]
    assert query.filter.call_count == 2

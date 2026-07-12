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

import ast

from axbi.db_engine_specs import lint_metadata


def test_eval_ast_value_handles_removed_legacy_ast_aliases(monkeypatch):
    """
    Python 3.14 removed legacy ast.Str/ast.Num aliases.

    Metadata can contain attribute values such as DatabaseCategory.OPEN_SOURCE;
    those should still be parsed even when the legacy aliases are unavailable.
    """
    monkeypatch.delattr(ast, "Str", raising=False)
    monkeypatch.delattr(ast, "Num", raising=False)

    node = ast.parse("DatabaseCategory.OPEN_SOURCE").body[0].value

    assert lint_metadata._eval_ast_value(node) == "DatabaseCategory.OPEN_SOURCE"

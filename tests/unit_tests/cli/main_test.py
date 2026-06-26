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

from click.testing import CliRunner

from superset.cli.main import superset


def test_top_level_help_does_not_load_app(mocker) -> None:
    app_factory = mocker.Mock(side_effect=AssertionError("app should not load"))
    mocker.patch.object(superset, "create_app", app_factory)

    result = CliRunner().invoke(superset, ["--help"])

    assert result.exit_code == 0
    assert "The Apache Superset CLI" in result.output
    assert "mcp" in result.output
    assert "version" in result.output
    app_factory.assert_not_called()

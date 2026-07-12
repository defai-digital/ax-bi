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
from parameterized import parameterized

from axbi.commands.database.ssh_tunnel.exceptions import SSHTunnelDatabasePortError
from axbi.commands.database.test_connection import (
    get_log_connection_action,
    TestConnectionDatabaseCommand,
)
from axbi.databases.ssh_tunnel.models import SSHTunnel
from tests.unit_tests.conftest import with_feature_flags


@parameterized.expand(
    [
        ("foo", None, None, "foo"),
        ("foo", SSHTunnel, None, "foo.ssh_tunnel"),
        ("foo", SSHTunnel, Exception("oops"), "foo.Exception.ssh_tunnel"),
    ],
)
def test_get_log_connection_action(action, tunnel, exc, expected_result):
    assert expected_result == get_log_connection_action(action, tunnel, exc)


@with_feature_flags(SSH_TUNNELING=True)
def test_ssh_tunnel_allows_uri_without_port_when_backend_has_default() -> None:
    """
    Database URIs can omit the port when the backend has a known SSH default port.
    """
    command = TestConnectionDatabaseCommand(
        {
            "sqlalchemy_uri": "postgresql://user:password@localhost/test-db",
            "ssh_tunnel": {
                "server_address": "tunnel.example.com",
                "server_port": 22,
                "username": "user",
                "password": "password",
            },
        }
    )

    command.validate()


@with_feature_flags(SSH_TUNNELING=True)
def test_ssh_tunnel_requires_port_when_backend_has_no_default() -> None:
    """
    Database URIs need an explicit port when AxBI has no backend default.
    """
    command = TestConnectionDatabaseCommand(
        {
            "sqlalchemy_uri": "weird+db://user:password@localhost/test-db",
            "ssh_tunnel": {
                "server_address": "tunnel.example.com",
                "server_port": 22,
                "username": "user",
                "password": "password",
            },
        }
    )

    with pytest.raises(SSHTunnelDatabasePortError):
        command.validate()

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
from unittest.mock import patch

from flask import current_app

from axbi.commands.dashboard.filter_state.delete import DeleteFilterStateCommand
from axbi.commands.dashboard.filter_state.get import GetFilterStateCommand
from axbi.commands.dashboard.filter_state.update import UpdateFilterStateCommand
from axbi.commands.temporary_cache.parameters import CommandParameters


def test_get_filter_state_ignores_malformed_cache_entry() -> None:
    """Malformed dashboard filter-state cache entries behave like misses."""
    cmd_params = CommandParameters(resource_id=1, key="key")

    with (
        patch("axbi.commands.dashboard.filter_state.get.check_access"),
        patch(
            "axbi.commands.dashboard.filter_state.get.cache_key",
            return_value="1:key",
        ),
        patch(
            "axbi.commands.dashboard.filter_state.get.cache_manager"
        ) as mock_cache_manager,
    ):
        mock_cache_manager.filter_state_cache.get.return_value = "not-an-entry"

        assert GetFilterStateCommand(cmd_params).run() is None
        mock_cache_manager.filter_state_cache.set.assert_not_called()


def test_update_filter_state_ignores_malformed_cache_entry() -> None:
    """Malformed dashboard filter-state cache entries do not raise raw errors."""
    cmd_params = CommandParameters(resource_id=1, key="key", value='{"a": 1}')

    with (
        current_app.test_request_context(),
        patch("axbi.commands.dashboard.filter_state.update.check_access"),
        patch(
            "axbi.commands.dashboard.filter_state.update.cache_key",
            return_value="1:key",
        ),
        patch(
            "axbi.commands.dashboard.filter_state.update.cache_manager"
        ) as mock_cache_manager,
        patch(
            "axbi.commands.dashboard.filter_state.update.get_user_id",
            return_value=1,
        ),
    ):
        mock_cache_manager.filter_state_cache.get.return_value = {"owner": 1}

        assert UpdateFilterStateCommand(cmd_params).run() == "key"
        mock_cache_manager.filter_state_cache.set.assert_not_called()


def test_delete_filter_state_ignores_malformed_cache_entry() -> None:
    """Malformed dashboard filter-state cache entries do not raise raw errors."""
    cmd_params = CommandParameters(resource_id=1, key="key")

    with (
        current_app.test_request_context(),
        patch("axbi.commands.dashboard.filter_state.delete.check_access"),
        patch(
            "axbi.commands.dashboard.filter_state.delete.cache_key",
            return_value="1:key",
        ),
        patch(
            "axbi.commands.dashboard.filter_state.delete.cache_manager"
        ) as mock_cache_manager,
        patch(
            "axbi.commands.dashboard.filter_state.delete.get_user_id",
            return_value=1,
        ),
    ):
        mock_cache_manager.filter_state_cache.get.return_value = "not-an-entry"

        assert DeleteFilterStateCommand(cmd_params).run() is False
        mock_cache_manager.filter_state_cache.delete.assert_not_called()

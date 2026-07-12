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

from axbi.commands.explore.form_data.delete import DeleteFormDataCommand
from axbi.commands.explore.form_data.get import GetFormDataCommand
from axbi.commands.explore.form_data.parameters import CommandParameters
from axbi.commands.explore.form_data.update import UpdateFormDataCommand
from axbi.utils.core import DatasourceType


def test_get_form_data_ignores_malformed_cache_state() -> None:
    """Malformed Explore form-data cache states behave like misses."""
    cmd_params = CommandParameters(key="key")

    with (
        patch("axbi.commands.explore.form_data.get.check_access") as mock_check_access,
        patch(
            "axbi.commands.explore.form_data.get.cache_manager"
        ) as mock_cache_manager,
    ):
        mock_cache_manager.explore_form_data_cache.get.return_value = "not-a-state"

        assert GetFormDataCommand(cmd_params).run() is None
        mock_check_access.assert_not_called()
        mock_cache_manager.explore_form_data_cache.set.assert_not_called()


def test_update_form_data_ignores_malformed_cache_state() -> None:
    """Malformed Explore form-data cache states do not raise raw errors."""
    cmd_params = CommandParameters(
        datasource_id=1,
        datasource_type=DatasourceType.TABLE,
        chart_id=1,
        tab_id=1,
        key="key",
        form_data='{"datasource": "1__table"}',
    )

    with (
        current_app.test_request_context(),
        patch("axbi.commands.explore.form_data.update.check_access"),
        patch(
            "axbi.commands.explore.form_data.update.cache_manager"
        ) as mock_cache_manager,
        patch(
            "axbi.commands.explore.form_data.update.get_user_id",
            return_value=1,
        ),
    ):
        mock_cache_manager.explore_form_data_cache.get.return_value = {"owner": 1}

        assert UpdateFormDataCommand(cmd_params).run() == "key"
        mock_cache_manager.explore_form_data_cache.set.assert_not_called()


def test_delete_form_data_ignores_malformed_cache_state() -> None:
    """Malformed Explore form-data cache states do not raise raw errors."""
    cmd_params = CommandParameters(key="key")

    with (
        current_app.test_request_context(),
        patch(
            "axbi.commands.explore.form_data.delete.check_access"
        ) as mock_check_access,
        patch(
            "axbi.commands.explore.form_data.delete.cache_manager"
        ) as mock_cache_manager,
    ):
        mock_cache_manager.explore_form_data_cache.get.return_value = "not-a-state"

        assert DeleteFormDataCommand(cmd_params).run() is False
        mock_check_access.assert_not_called()
        mock_cache_manager.explore_form_data_cache.delete.assert_not_called()

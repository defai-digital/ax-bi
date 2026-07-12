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

from flask import current_app as app

from axbi.commands.dashboard.filter_state.utils import check_access
from axbi.commands.temporary_cache.entry import is_entry
from axbi.commands.temporary_cache.get import GetTemporaryCacheCommand
from axbi.commands.temporary_cache.parameters import CommandParameters
from axbi.extensions import cache_manager
from axbi.temporary_cache.utils import cache_key


class GetFilterStateCommand(GetTemporaryCacheCommand):
    def __init__(self, cmd_params: CommandParameters) -> None:
        super().__init__(cmd_params)
        self._refresh_timeout = app.config["FILTER_STATE_CACHE_CONFIG"].get(
            "REFRESH_TIMEOUT_ON_RETRIEVAL"
        )

    def get(self, cmd_params: CommandParameters) -> str | None:
        resource_id = cmd_params.resource_id
        key = cache_key(resource_id, cmd_params.key)
        check_access(resource_id)
        entry = cache_manager.filter_state_cache.get(key)
        if not is_entry(entry):
            return None
        if entry and self._refresh_timeout:
            cache_manager.filter_state_cache.set(key, entry)
        return entry["value"]

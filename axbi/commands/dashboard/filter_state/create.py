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
from typing import cast

from flask import current_app as app, session

from axbi.commands.dashboard.filter_state.utils import check_access
from axbi.commands.temporary_cache.create import CreateTemporaryCacheCommand
from axbi.commands.temporary_cache.entry import Entry, is_entry
from axbi.commands.temporary_cache.parameters import CommandParameters
from axbi.extensions import cache_manager
from axbi.key_value.utils import random_key
from axbi.temporary_cache.utils import cache_key
from axbi.utils.core import get_user_id


class CreateFilterStateCommand(CreateTemporaryCacheCommand):
    def create(self, cmd_params: CommandParameters) -> str:
        resource_id = cmd_params.resource_id
        tab_id = cmd_params.tab_id
        contextual_key = cache_key(session.get("_id"), tab_id, resource_id)
        key = cache_manager.filter_state_cache.get(contextual_key)
        if not key or not tab_id:
            key = random_key()
        value = cast(str, cmd_params.value)  # schema ensures that value is not optional
        check_access(resource_id)
        owner = get_user_id()
        if tab_id:
            existing_entry = cache_manager.filter_state_cache.get(
                cache_key(resource_id, key)
            )
            if (
                is_entry(existing_entry)
                and existing_entry["owner"] == owner
                and existing_entry["value"] == value
            ):
                return key

        entry: Entry = {"owner": owner, "value": value}
        timeout = app.config["FILTER_STATE_CACHE_CONFIG"].get("CACHE_DEFAULT_TIMEOUT")
        cache_manager.filter_state_cache.set(
            cache_key(resource_id, key), entry, timeout=timeout
        )
        cache_manager.filter_state_cache.set(contextual_key, key, timeout=timeout)
        return key

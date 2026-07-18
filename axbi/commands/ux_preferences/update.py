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

from typing import Any

from axbi.commands.base import BaseCommand
from axbi.commands.exceptions import CommandInvalidError
from axbi.daos.ux_preferences import UserUxPreferencesDAO
from axbi.utils import json
from axbi.utils.decorators import transaction
from axbi.views.users.schemas import UX_PREFERENCES_MAX_PAYLOAD_BYTES


class UpdateUxPreferencesCommand(BaseCommand):
    """Merge new ``ux.*`` entries into a user's UX preference document.

    Entries are merged key-by-key (a PUT carries a partial document); the
    stored document is never replaced wholesale by this command. The merged
    document is capped at ``UX_PREFERENCES_MAX_PAYLOAD_BYTES`` serialized
    bytes so it stays bounded as keys accumulate across PUTs.
    """

    def __init__(self, user_id: int, preferences: dict[str, Any]):
        self._user_id = user_id
        self._preferences = preferences

    @transaction()
    def run(self) -> dict[str, Any]:
        self.validate()
        merged = {
            **UserUxPreferencesDAO.get_preferences(self._user_id),
            **self._preferences,
        }
        if len(json.dumps(merged)) > UX_PREFERENCES_MAX_PAYLOAD_BYTES:
            raise CommandInvalidError(
                "UX preferences exceed the "
                f"{UX_PREFERENCES_MAX_PAYLOAD_BYTES} byte limit after merging."
            )
        # Pass only the new entries so the DAO can re-merge correctly if it
        # loses the first-insert race to a concurrent request.
        UserUxPreferencesDAO.upsert_preferences(self._user_id, self._preferences)
        return merged

    def validate(self) -> None:
        pass

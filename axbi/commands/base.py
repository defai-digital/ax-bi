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
from abc import ABC, abstractmethod
from typing import Any

from flask_appbuilder.security.sqla.models import User

from axbi.commands.utils import compute_owner_list, populate_owner_list


class BaseCommand(ABC):
    """
    Base class for all Command like AxBI Logic objects.

    Stability contract:
    - ``validate()`` must raise a command/validation exception on bad input and
      must not mutate durable state.
    - ``run()`` is the unit of work. Commands that write data should call
      ``validate()`` first and own persistence through ``@transaction`` / DAOs.
    - Prefer ``execute()`` at new call sites so validation always runs before
      work, even when a subclass forgets to invoke ``validate()`` inside
      ``run()``.
    """

    @abstractmethod
    def run(self) -> Any:
        """
        Run executes the command. Can raise command exceptions
        :raises: CommandException
        """

    @abstractmethod
    def validate(self) -> None:
        """
        Validate is normally called by run to validate data.
        Will raise exception if validation fails
        :raises: CommandException
        """

    def execute(self) -> Any:
        """
        Validate then run.

        Use this at transport boundaries (API, MCP, CLI) when the command's
        ``run()`` implementation is not already known to call ``validate()``.
        Commands that already validate inside ``run()`` remain safe: a second
        ``validate()`` must be side-effect free.
        """
        self.validate()
        return self.run()


class CreateMixin:  # pylint: disable=too-few-public-methods
    @staticmethod
    def populate_owners(owner_ids: list[int] | None = None) -> list[User]:
        """
        Populate list of owners, defaulting to the current user if `owner_ids` is
        undefined or empty. If current user is missing in `owner_ids`, current user
        is added unless belonging to the Admin role.

        :param owner_ids: list of owners by id's
        :raises OwnersNotFoundValidationError: if at least one owner can't be resolved
        :returns: Final list of owners
        """
        return populate_owner_list(owner_ids, default_to_user=True)


class UpdateMixin:
    @staticmethod
    def populate_owners(owner_ids: list[int] | None = None) -> list[User]:
        """
        Populate list of owners. If current user is missing in `owner_ids`, current user
        is added unless belonging to the Admin role.

        :param owner_ids: list of owners by id's
        :raises OwnersNotFoundValidationError: if at least one owner can't be resolved
        :returns: Final list of owners
        """
        return populate_owner_list(owner_ids, default_to_user=False)

    @staticmethod
    def compute_owners(
        current_owners: list[User] | None,
        new_owners: list[int] | None,
    ) -> list[User]:
        """
        Handle list of owners for update events.

        :param current_owners: list of current owners
        :param new_owners: list of new owners specified in the update payload
        :returns: Final list of owners
        """
        return compute_owner_list(current_owners, new_owners)

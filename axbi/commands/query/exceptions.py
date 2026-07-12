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
from flask_babel import lazy_gettext as _

from axbi.commands.exceptions import (
    CommandException,
    CommandInvalidError,
    CreateFailedError,
    DeleteFailedError,
    ForbiddenError,
    ImportFailedError,
)


class SavedQueryCreateFailedError(CreateFailedError):
    """Raised when persistence of a saved query fails."""

    message = _("Saved query could not be created.")


class SavedQueryDatabaseNotFoundError(CommandException):
    """Raised when a saved query references a missing database."""

    status = 404

    def __init__(self, database_id: int) -> None:
        super().__init__(
            _("Database with ID %(database_id)s not found", database_id=database_id)
        )


class SavedQueryDatabaseAccessDeniedError(ForbiddenError):
    """Raised when the caller cannot access a saved query's database."""

    def __init__(self, database_name: str) -> None:
        super().__init__(
            _(
                "Access denied to database %(database_name)s",
                database_name=database_name,
            )
        )


class SavedQueryUserNotFoundError(CommandException):
    """Raised when a saved query cannot be attributed to a session user."""

    status = 500
    message = _("Could not validate the user in the current session.")


class SavedQueryDeleteFailedError(DeleteFailedError):
    message = _("Saved queries could not be deleted.")


class SavedQueryNotFoundError(CommandException):
    message = _("Saved query not found.")


class SavedQueryImportError(ImportFailedError):
    message = _("Import saved query failed for an unknown reason.")


class SavedQueryInvalidError(CommandInvalidError):
    message = _("Saved query parameters are invalid.")

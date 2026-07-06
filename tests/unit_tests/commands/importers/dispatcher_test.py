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

import pytest

from superset.commands.exceptions import CommandInvalidError
from superset.commands.importers.dispatcher import ImportersCommand
from superset.commands.importers.exceptions import IncorrectVersionError


def test_importers_command_dispatches_to_first_matching_version() -> None:
    """Incompatible versions are skipped until one handles the payload."""
    events: list[tuple[str, dict[str, str], tuple[Any, ...], dict[str, Any]]] = []

    class SkippingImportCommand:
        def __init__(self, contents: dict[str, str], *args: Any, **kwargs: Any):
            events.append(("skip", contents, args, kwargs))

        def run(self) -> None:
            raise IncorrectVersionError()

    class MatchingImportCommand:
        def __init__(self, contents: dict[str, str], *args: Any, **kwargs: Any):
            events.append(("match", contents, args, kwargs))

        def run(self) -> None:
            events.append(("run", {}, (), {}))

    class TestImportersCommand(ImportersCommand):
        command_versions = (SkippingImportCommand, MatchingImportCommand)

    contents = {"metadata.yaml": "version: 1.0.0"}
    TestImportersCommand(contents, "extra", overwrite=True).run()

    assert events == [
        ("skip", contents, ("extra",), {"overwrite": True}),
        ("match", contents, ("extra",), {"overwrite": True}),
        ("run", {}, (), {}),
    ]


def test_importers_command_stops_on_validation_error() -> None:
    """A matching-but-invalid version should stop dispatch immediately."""

    class InvalidImportCommand:
        def __init__(self, contents: dict[str, str]):
            self.contents = contents

        def run(self) -> None:
            raise CommandInvalidError("invalid")

    class LaterImportCommand:
        def __init__(self, contents: dict[str, str]):
            self.contents = contents

        def run(self) -> None:
            raise AssertionError("later version should not run")

    class TestImportersCommand(ImportersCommand):
        command_versions = (InvalidImportCommand, LaterImportCommand)

    with pytest.raises(CommandInvalidError, match="invalid"):
        TestImportersCommand({"metadata.yaml": "version: 1.0.0"}).run()


def test_importers_command_raises_when_no_version_matches() -> None:
    """A payload that no command accepts reports a single command error."""

    class SkippingImportCommand:
        def __init__(self, contents: dict[str, str]):
            self.contents = contents

        def run(self) -> None:
            raise IncorrectVersionError()

    class TestImportersCommand(ImportersCommand):
        command_versions = (SkippingImportCommand,)

    with pytest.raises(CommandInvalidError, match="Could not find a valid command"):
        TestImportersCommand({"metadata.yaml": "version: 999.0.0"}).run()

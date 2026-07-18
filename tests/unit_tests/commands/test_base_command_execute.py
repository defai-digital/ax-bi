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

"""Tests for BaseCommand.execute stability contract."""

from __future__ import annotations

from typing import Any

import pytest

from axbi.commands.base import BaseCommand


class _RecordingCommand(BaseCommand):
    def __init__(self, *, fail_validate: bool = False) -> None:
        self.calls: list[str] = []
        self.fail_validate = fail_validate

    def validate(self) -> None:
        self.calls.append("validate")
        if self.fail_validate:
            raise ValueError("invalid")

    def run(self) -> Any:
        self.calls.append("run")
        return "ok"


def test_execute_validates_before_run() -> None:
    command = _RecordingCommand()
    assert command.execute() == "ok"
    assert command.calls == ["validate", "run"]


def test_execute_skips_run_when_validation_fails() -> None:
    command = _RecordingCommand(fail_validate=True)
    with pytest.raises(ValueError, match="invalid"):
        command.execute()
    assert command.calls == ["validate"]

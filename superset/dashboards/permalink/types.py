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
from collections.abc import Sequence
from typing import Any, TypedDict


class DashboardPermalinkState(TypedDict, total=False):
    dataMask: dict[str, Any] | None
    activeTabs: list[str] | None
    anchor: str | None
    # urlParams items are stored/transmitted as JSON arrays, so they
    # arrive at runtime as ``list[str]``; ``Sequence[str]`` keeps the
    # annotation permissive of both list and tuple shapes.
    urlParams: list[Sequence[str]] | None
    chartStates: dict[str, Any] | None


class DashboardPermalinkValue(TypedDict):
    dashboardId: str
    state: DashboardPermalinkState

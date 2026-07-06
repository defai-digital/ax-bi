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
from enum import Enum
from typing import Any, Literal, TypedDict

ThemeAlgorithmCombination = list[
    Literal["default"] | Literal["dark"] | Literal["compact"]
]


ThemeAlgorithmOption = (
    Literal["default"]
    | Literal["dark"]
    | Literal["compact"]
    | ThemeAlgorithmCombination
)


class Theme(TypedDict, total=False):
    """
    Represents a theme configuration.

    All keys are optional because theme configuration is partial.
    """

    token: dict[str, Any]
    components: dict[str, Any] | None
    algorithm: ThemeAlgorithmOption | None
    hashed: bool | None
    inherit: bool | None


class ThemeMode(str, Enum):
    DEFAULT = "default"
    DARK = "dark"
    SYSTEM = "system"
    COMPACT = "compact"

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
from typing import Any, TypedDict, TypeGuard


class Entry(TypedDict):
    owner: int | None
    value: str


def is_entry(value: Any) -> TypeGuard[Entry]:
    """Return true when a cached dashboard filter-state entry is usable."""
    if not isinstance(value, dict):
        return False

    owner = value.get("owner")
    return (
        (owner is None or isinstance(owner, int))
        and not isinstance(owner, bool)
        and isinstance(value.get("value"), str)
    )

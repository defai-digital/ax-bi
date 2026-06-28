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
from typing import Any

from superset.commands.explore.get import _get_slice_metadata
from superset.models.slice import Slice


def test_slice_metadata_handles_missing_timestamps(app: Any) -> None:
    """Explore metadata serialization should tolerate incomplete chart rows."""
    slc = Slice(created_on=None, changed_on=None)
    slc.owners = []
    slc.dashboards = []

    metadata = _get_slice_metadata(slc)

    assert metadata["created_on_humanized"] is None
    assert metadata["changed_on_humanized"] is None

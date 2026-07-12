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

from axbi.models.tasks import Task
from axbi.utils import json


def test_task_payload_dict_ignores_non_object_payload() -> None:
    """Task payloads should deserialize to dictionaries only."""
    task = Task(payload="[]")

    assert task.payload_dict == {}


def test_task_set_payload_merges_after_non_object_payload() -> None:
    """set_payload should tolerate previously malformed payload shape."""
    task = Task(payload="[]")

    task.set_payload({"status": "complete"})

    assert json.loads(task.payload) == {"status": "complete"}

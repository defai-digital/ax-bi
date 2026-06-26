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

from unittest.mock import MagicMock, patch


def test_delete_model_ids_in_batches_commits_each_batch() -> None:
    from superset.commands.prune import delete_model_ids_in_batches
    from superset.models.core import Log

    session = MagicMock()
    session.execute.side_effect = [
        MagicMock(rowcount=1),
        MagicMock(rowcount=1),
        MagicMock(rowcount=1),
    ]

    with patch("superset.commands.prune.db") as mock_db:
        mock_db.session = session
        total_deleted = delete_model_ids_in_batches(
            Log,
            [1, 2, 3],
            retention_period_days=30,
            table_name="logs",
            logger=MagicMock(),
            batch_size=1,
        )

    assert total_deleted == 3
    assert session.execute.call_count == 3
    assert session.commit.call_count == 3

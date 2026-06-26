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

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch


def test_query_prune_cutoff_is_naive_utc() -> None:
    """
    Query.changed_on defaults to datetime.utcnow, so the retention cutoff should
    use the shared naive UTC clock instead of local server time.
    """
    from superset.commands.sql_lab.query import QueryPruneCommand

    captured: dict[str, datetime] = {}

    def fake_execute(stmt):  # noqa: ANN001
        for param in stmt.compile().params.values():
            if isinstance(param, datetime):
                captured["cutoff"] = param
        result = MagicMock()
        result.scalars.return_value.all.return_value = []
        return result

    session = MagicMock()
    session.execute.side_effect = fake_execute

    with patch("superset.commands.sql_lab.query.db") as mock_db:
        mock_db.session = session
        QueryPruneCommand(retention_period_days=30).run()

    cutoff = captured["cutoff"]
    assert cutoff.tzinfo is None

    expected = datetime.utcnow() - timedelta(days=30)
    assert abs((cutoff - expected).total_seconds()) < 60

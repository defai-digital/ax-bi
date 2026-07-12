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
import logging
from datetime import timedelta

import sqlalchemy as sa

from axbi import db
from axbi.commands.base import BaseCommand
from axbi.commands.prune import delete_model_ids_in_batches
from axbi.models.core import Log
from axbi.utils.dates import naive_utcnow

logger = logging.getLogger(__name__)


# pylint: disable=consider-using-transaction
class LogPruneCommand(BaseCommand):
    """
    Command to prune the logs table by deleting rows older than the specified retention period.

    This command deletes records from the `Log` table that have not been changed within the
    specified number of days. It helps in maintaining the database by removing outdated entries
    and freeing up space.

    Attributes:
        retention_period_days (int): The number of days for which records should be retained.
                                     Records older than this period will be deleted.
        max_rows_per_run (int | None): The maximum number of rows to delete in a single run.
                                       If provided and greater than zero, rows are selected
                                       deterministically from the oldest first by id
                                       up to this limit in this execution.
    """  # noqa: E501

    def __init__(self, retention_period_days: int, max_rows_per_run: int | None = None):
        """
        :param retention_period_days: Number of days to keep in the logs table
        :param max_rows_per_run: The maximum number of rows to delete in a single run.
            If provided and greater than zero, rows are selected deterministically from the
            oldest first by id up to this limit in this execution.
        """  # noqa: E501
        self.retention_period_days = retention_period_days
        self.max_rows_per_run = max_rows_per_run

    def run(self) -> None:
        """
        Executes the prune command
        """
        # Select all IDs that need to be deleted
        # Log.dttm is stored as a naive UTC datetime (no tzinfo), so compute
        # the cutoff as a naive UTC datetime to avoid a naive/aware mismatch
        # that raises on PostgreSQL.
        cutoff = naive_utcnow() - timedelta(days=self.retention_period_days)
        select_stmt = sa.select(Log.id).where(Log.dttm < cutoff)

        # Optionally limited by max_rows_per_run
        # order by oldest first for deterministic deletion
        if self.max_rows_per_run is not None and self.max_rows_per_run > 0:
            select_stmt = select_stmt.order_by(Log.id.asc()).limit(
                self.max_rows_per_run
            )

        ids_to_delete = db.session.execute(select_stmt).scalars().all()

        delete_model_ids_in_batches(
            Log,
            ids_to_delete,
            retention_period_days=self.retention_period_days,
            table_name="logs",
            logger=logger,
        )

    def validate(self) -> None:
        pass

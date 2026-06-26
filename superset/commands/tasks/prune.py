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
from superset_core.tasks.types import TaskStatus

from superset import db
from superset.commands.base import BaseCommand
from superset.commands.prune import delete_model_ids_in_batches
from superset.utils.dates import naive_utcnow

logger = logging.getLogger(__name__)


# pylint: disable=consider-using-transaction
class TaskPruneCommand(BaseCommand):
    """
    Command to prune the tasks table by deleting rows older than the specified
    retention period.

    This command deletes records from the `Task` table that are in terminal states
    (success, failure, aborted, or timed_out) and have not been changed within the
    specified number of days. It helps in maintaining the database by removing
    outdated entries and freeing up space.

    Attributes:
        retention_period_days (int): The number of days for which records should be retained.
                                     Records older than this period will be deleted.
        max_rows_per_run (int | None): The maximum number of rows to delete in a single run.
                                       If provided and greater than zero, rows are selected
                                       deterministically from the oldest first (by timestamp then id)
                                       up to this limit in this execution.
    """  # noqa: E501

    def __init__(self, retention_period_days: int, max_rows_per_run: int | None = None):
        """
        :param retention_period_days: Number of days to keep in the tasks table
        :param max_rows_per_run: The maximum number of rows to delete in a single run.
            If provided and greater than zero, rows are selected deterministically from the
            oldest first (by timestamp then id) up to this limit in this execution.
        """  # noqa: E501
        self.retention_period_days = retention_period_days
        self.max_rows_per_run = max_rows_per_run

    def run(self) -> None:
        """
        Executes the prune command
        """
        # Select all IDs that need to be deleted
        # Only delete completed tasks (success, failure, or aborted)
        from superset.models.tasks import Task

        select_stmt = sa.select(Task.id).where(
            Task.ended_at < naive_utcnow() - timedelta(days=self.retention_period_days),
            Task.status.in_(
                [
                    TaskStatus.SUCCESS.value,
                    TaskStatus.FAILURE.value,
                    TaskStatus.ABORTED.value,
                    TaskStatus.TIMED_OUT.value,
                ]
            ),
        )

        # Optionally limited by max_rows_per_run
        # order by oldest first for deterministic deletion
        if self.max_rows_per_run is not None and self.max_rows_per_run > 0:
            select_stmt = select_stmt.order_by(
                Task.ended_at.asc(), Task.id.asc()
            ).limit(self.max_rows_per_run)

        ids_to_delete = db.session.execute(select_stmt).scalars().all()

        delete_model_ids_in_batches(
            Task,
            ids_to_delete,
            retention_period_days=self.retention_period_days,
            table_name="tasks",
            logger=logger,
        )

    def validate(self) -> None:
        pass

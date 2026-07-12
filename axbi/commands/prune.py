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
import time
from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa

from axbi import db

SQLITE_MAX_IN_CLAUSE_BATCH_SIZE = 999


def delete_model_ids_in_batches(
    model: type[Any],
    ids_to_delete: Sequence[Any],
    *,
    retention_period_days: int,
    table_name: str,
    logger: logging.Logger,
    batch_size: int = SQLITE_MAX_IN_CLAUSE_BATCH_SIZE,
) -> int:
    """Delete selected model IDs in batches and log prune progress."""
    total_deleted = 0
    start_time = time.time()
    total_rows = len(ids_to_delete)

    logger.info("Total rows to be deleted: %s", f"{total_rows:,}")

    next_logging_threshold = 1
    for i in range(0, total_rows, batch_size):
        batch_ids = ids_to_delete[i : i + batch_size]
        result = db.session.execute(sa.delete(model).where(model.id.in_(batch_ids)))
        total_deleted += result.rowcount

        # Commit each batch so a later failure does not roll back prior work.
        db.session.commit()

        percentage_complete = (total_deleted / total_rows) * 100
        if percentage_complete >= next_logging_threshold:
            logger.info(
                "Deleted %s rows from the %s table older than %s days (%d%% complete)",
                f"{total_deleted:,}",
                table_name,
                retention_period_days,
                percentage_complete,
            )
            next_logging_threshold += 1

    elapsed_time = time.time() - start_time
    minutes, seconds = divmod(elapsed_time, 60)
    formatted_time = f"{int(minutes):02}:{int(seconds):02}"
    logger.info(
        "Pruning complete: %s rows deleted in %s",
        f"{total_deleted:,}",
        formatted_time,
    )

    return total_deleted

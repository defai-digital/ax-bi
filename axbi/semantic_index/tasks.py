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
"""Background tasks for keeping the GenAI BI semantic index fresh."""

from __future__ import annotations

import logging

from axbi.extensions import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="semantic_index.reindex_dataset", soft_time_limit=600)
def reindex_dataset_semantic_documents(dataset_id: int) -> None:
    """Re-embed the semantic documents for a single dataset.

    Enqueued by the SQLAlchemy change hooks after a dataset, column, or metric
    is created or updated. The task is idempotent: it rebuilds documents,
    re-embeds them, and prunes documents for objects that no longer exist. If
    the dataset has been deleted, its documents are removed instead.
    """

    # pylint: disable=import-outside-toplevel
    from axbi import is_feature_enabled
    from axbi.connectors.sqla.models import SqlaTable
    from axbi.extensions import db
    from axbi.semantic_index.embedding import EmbeddingProviderError
    from axbi.semantic_index.repository import SemanticIndexRepository
    from axbi.semantic_index.service import SemanticIndexService

    if not is_feature_enabled("GENAI_SEMANTIC_INDEX"):
        return

    dataset = (
        db.session.query(SqlaTable).filter(SqlaTable.id == dataset_id).one_or_none()
    )
    if dataset is None:
        # The dataset was deleted before the task ran; drop any orphaned docs.
        SemanticIndexRepository().delete_dataset_documents(dataset_id)
        db.session.commit()
        return

    try:
        service = SemanticIndexService()
    except EmbeddingProviderError:
        # Provider is disabled/misconfigured. Leave the documents marked stale
        # (already excluded from search) so a later run can refresh them.
        logger.warning(
            "Semantic embedding provider unavailable; skipping reindex of dataset %s",
            dataset_id,
        )
        return

    try:
        summary = service.index_dataset(dataset_id)
        db.session.commit()
        logger.info(
            "Reindexed dataset %s: %s/%s semantic documents written",
            dataset_id,
            summary.documents_written,
            summary.documents_seen,
        )
    except Exception:
        db.session.rollback()
        logger.exception("Semantic reindex failed for dataset %s", dataset_id)

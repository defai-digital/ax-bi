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
"""
Auto-provision a local DuckDB database for zero-config file uploads.

When a user uploads a file via the Upload Data page, the system automatically
creates (or reuses) a local DuckDB database named "Local Files" so users do
not need to manually connect a database before uploading files.
"""

import json
import logging
import os

from flask import current_app

from superset import db
from superset.models.core import Database

logger = logging.getLogger(__name__)


def get_or_create_local_db() -> Database:
    """
    Return the auto-provisioned local DuckDB database.

    If a Database record with the configured LOCAL_DB_NAME already exists,
    it is returned directly. Otherwise a new DuckDB-backed database is
    created with file-upload, DML and async-query support enabled.

    The DuckDB file is stored at the path configured in LOCAL_DB_PATH
    (defaults to ``<UPLOAD_FOLDER>/local_files.duckdb``).

    :returns: A :class:`Database` instance pointing to the local DuckDB.
    """
    db_name = current_app.config.get("LOCAL_DB_NAME", "Local Files")
    db_path = current_app.config.get("LOCAL_DB_PATH")

    if not db_path:
        upload_folder = current_app.config.get("UPLOAD_FOLDER", "/tmp/")
        db_path = os.path.join(upload_folder, "local_files.duckdb")

    # Ensure the parent directory exists
    db_dir = os.path.dirname(db_path)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

    # Look for an existing local DB record
    local_db = (
        db.session.query(Database)
        .filter_by(database_name=db_name)
        .one_or_none()
    )

    if local_db:
        logger.debug("Reusing existing local database '%s' (id=%s)", db_name, local_db.id)
        return local_db

    # Build the DuckDB SQLAlchemy URI
    sqlalchemy_uri = f"duckdb:///{db_path}"

    local_db = Database(
        database_name=db_name,
        sqlalchemy_uri=sqlalchemy_uri,
        allow_file_upload=True,
        allow_run_async=True,
        allow_dml=True,
        allow_ctas=True,
        allow_cvas=False,
        expose_in_sqllab=True,
        extra=json.dumps(
            {
                "metadata_params": {},
                "engine_params": {},
                "metadata_cache_timeout": {},
                "schemas_allowed_for_file_upload": [],
            }
        ),
    )
    db.session.add(local_db)
    db.session.commit()

    logger.info(
        "Auto-provisioned local database '%s' (id=%s) at %s",
        db_name,
        local_db.id,
        db_path,
    )
    return local_db

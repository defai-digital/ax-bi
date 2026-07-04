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

import logging
import os
import tempfile

from flask import current_app

from superset import db
from superset.exceptions import SupersetException
from superset.models.core import Database
from superset.utils import json

logger = logging.getLogger(__name__)

LOCAL_DB_EXTRA = {
    "metadata_params": {},
    "engine_params": {},
    "metadata_cache_timeout": {},
    "schemas_allowed_for_file_upload": [None],
}
LOCAL_DB_ATTRS = {
    "allow_file_upload": True,
    "allow_run_async": True,
    "allow_dml": True,
    "allow_ctas": True,
    "allow_cvas": False,
    "expose_in_sqllab": True,
}


class LocalDatabaseConfigurationError(SupersetException):
    """Raised when the configured local upload database name is unavailable."""

    status = 422


def _get_raw_extra(database: Database) -> dict[str, object]:
    """Return raw database extra metadata, resetting malformed JSON."""
    try:
        extra = json.loads(database.extra or "{}")
    except (TypeError, json.JSONDecodeError):
        return dict(LOCAL_DB_EXTRA)
    if not isinstance(extra, dict):
        return dict(LOCAL_DB_EXTRA)
    return extra


def _repair_local_db(database: Database) -> bool:
    """Repair mutable flags and metadata on the auto-managed local database."""
    changed = False
    for attr, value in LOCAL_DB_ATTRS.items():
        if getattr(database, attr) != value:
            setattr(database, attr, value)
            changed = True

    extra = _get_raw_extra(database)
    if extra.get("schemas_allowed_for_file_upload") != [None]:
        extra["schemas_allowed_for_file_upload"] = [None]

    serialized_extra = json.dumps(extra)
    if database.extra != serialized_extra:
        database.extra = serialized_extra
        changed = True

    return changed


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
        upload_folder = current_app.config.get("UPLOAD_FOLDER", tempfile.gettempdir())
        db_path = os.path.join(upload_folder, "local_files.duckdb")
    sqlalchemy_uri = f"duckdb:///{db_path}"

    # Ensure the parent directory exists
    if db_dir := os.path.dirname(db_path):
        os.makedirs(db_dir, exist_ok=True)

    # Look for an existing local DB record
    local_db = db.session.query(Database).filter_by(database_name=db_name).one_or_none()

    if local_db:
        if local_db.sqlalchemy_uri != sqlalchemy_uri:
            raise LocalDatabaseConfigurationError(
                f"A database named '{db_name}' already exists but does not match the "
                "configured local upload DuckDB database. Rename that database "
                "or change LOCAL_DB_NAME."
            )
        if _repair_local_db(local_db):
            db.session.commit()
        logger.debug(
            "Reusing existing local database '%s' (id=%s)", db_name, local_db.id
        )
        return local_db

    local_db = Database(
        database_name=db_name,
        sqlalchemy_uri=sqlalchemy_uri,
        **LOCAL_DB_ATTRS,
        extra=json.dumps(LOCAL_DB_EXTRA),
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

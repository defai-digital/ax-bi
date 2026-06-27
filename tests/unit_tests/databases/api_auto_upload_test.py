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

# pylint: disable=unused-argument, redefined-outer-name

from __future__ import annotations

from io import BytesIO
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from flask import current_app
from pytest_mock import MockerFixture
from sqlalchemy.orm.session import Session

from superset import db
from superset.models.core import Database
from tests.unit_tests.conftest import with_feature_flags


class TestGetOrCreateLocalDb:
    """Tests for the get_or_create_local_db() function."""

    def test_creates_new_database_when_none_exists(
        self,
        session: Session,
        app_context: None,
    ) -> None:
        """
        Test that get_or_create_local_db creates a new DuckDB database
        when no "Local Files" database exists.
        """
        from superset.commands.database.uploaders.local_db import (
            get_or_create_local_db,
        )

        # Create the table
        Database.metadata.create_all(session.get_bind())  # pylint: disable=no-member

        # Make sure no "Local Files" database exists
        session.query(Database).filter_by(database_name="Local Files").delete()
        session.commit()

        local_db = get_or_create_local_db()

        assert local_db is not None
        assert local_db.database_name == "Local Files"
        assert "duckdb" in local_db.sqlalchemy_uri
        assert local_db.allow_file_upload is True
        assert local_db.allow_dml is True
        assert local_db.allow_run_async is True
        assert local_db.expose_in_sqllab is True
        assert local_db.get_schema_access_for_file_upload() == {None}

        # Clean up
        session.delete(local_db)
        session.commit()

    def test_reuses_existing_database(
        self,
        session: Session,
        app_context: None,
    ) -> None:
        """
        Test that get_or_create_local_db reuses an existing "Local Files"
        database instead of creating a new one.
        """
        from superset.commands.database.uploaders.local_db import (
            get_or_create_local_db,
        )

        # Create the table
        Database.metadata.create_all(session.get_bind())  # pylint: disable=no-member

        # Clean up any existing record first
        session.query(Database).filter_by(database_name="Local Files").delete()
        session.commit()

        # Create the DB the first time
        first_db = get_or_create_local_db()
        first_id = first_db.id

        # Call again - should return the same DB
        second_db = get_or_create_local_db()

        assert second_db.id == first_id
        assert second_db.database_name == "Local Files"

        # Clean up
        session.delete(second_db)
        session.commit()

    def test_repaired_existing_database_upload_flags(
        self,
        session: Session,
        app_context: None,
        mocker: MockerFixture,
    ) -> None:
        """
        Test that get_or_create_local_db repairs required flags when reusing
        the configured local DuckDB database.
        """
        import os
        import tempfile

        from superset.commands.database.uploaders.local_db import (
            get_or_create_local_db,
        )

        Database.metadata.create_all(session.get_bind())  # pylint: disable=no-member
        session.query(Database).filter_by(database_name="Local Files").delete()

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "local_files.duckdb")
            local_db = Database(
                database_name="Local Files",
                sqlalchemy_uri=f"duckdb:///{db_path}",
                allow_file_upload=False,
                allow_run_async=False,
                allow_dml=False,
                allow_ctas=False,
                allow_cvas=True,
                expose_in_sqllab=False,
                extra="{}",
            )
            session.add(local_db)
            session.commit()

            mocker.patch.dict(
                current_app.config,
                {"LOCAL_DB_PATH": db_path, "LOCAL_DB_NAME": "Local Files"},
            )

            repaired_db = get_or_create_local_db()

            assert repaired_db.id == local_db.id
            assert repaired_db.allow_file_upload is True
            assert repaired_db.allow_run_async is True
            assert repaired_db.allow_dml is True
            assert repaired_db.allow_ctas is True
            assert repaired_db.allow_cvas is False
            assert repaired_db.expose_in_sqllab is True
            assert repaired_db.get_schema_access_for_file_upload() == {None}

            session.delete(repaired_db)
            session.commit()

    def test_repairs_existing_database_malformed_extra(
        self,
        session: Session,
        app_context: None,
        mocker: MockerFixture,
    ) -> None:
        """
        Test that get_or_create_local_db repairs malformed extra metadata on
        the configured local DuckDB database.
        """
        import os
        import tempfile

        from superset.commands.database.uploaders.local_db import (
            get_or_create_local_db,
        )

        Database.metadata.create_all(session.get_bind())  # pylint: disable=no-member
        session.query(Database).filter_by(database_name="Local Files").delete()

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "local_files.duckdb")
            local_db = Database(
                database_name="Local Files",
                sqlalchemy_uri=f"duckdb:///{db_path}",
                allow_file_upload=True,
                allow_run_async=True,
                allow_dml=True,
                allow_ctas=True,
                allow_cvas=False,
                expose_in_sqllab=True,
                extra="{malformed",
            )
            session.add(local_db)
            session.commit()

            mocker.patch.dict(
                current_app.config,
                {"LOCAL_DB_PATH": db_path, "LOCAL_DB_NAME": "Local Files"},
            )

            repaired_db = get_or_create_local_db()

            assert repaired_db.id == local_db.id
            assert repaired_db.get_schema_access_for_file_upload() == {None}

            session.delete(repaired_db)
            session.commit()

    def test_repairs_existing_database_non_object_extra(
        self,
        session: Session,
        app_context: None,
        mocker: MockerFixture,
    ) -> None:
        """
        Test that get_or_create_local_db repairs non-object extra metadata on
        the configured local DuckDB database.
        """
        import os
        import tempfile

        from superset.commands.database.uploaders.local_db import (
            get_or_create_local_db,
        )

        Database.metadata.create_all(session.get_bind())  # pylint: disable=no-member
        session.query(Database).filter_by(database_name="Local Files").delete()

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "local_files.duckdb")
            local_db = Database(
                database_name="Local Files",
                sqlalchemy_uri=f"duckdb:///{db_path}",
                allow_file_upload=True,
                allow_run_async=True,
                allow_dml=True,
                allow_ctas=True,
                allow_cvas=False,
                expose_in_sqllab=True,
                extra="[]",
            )
            session.add(local_db)
            session.commit()

            mocker.patch.dict(
                current_app.config,
                {"LOCAL_DB_PATH": db_path, "LOCAL_DB_NAME": "Local Files"},
            )

            repaired_db = get_or_create_local_db()

            assert repaired_db.id == local_db.id
            assert repaired_db.get_schema_access_for_file_upload() == {None}

            session.delete(repaired_db)
            session.commit()

    def test_rejects_existing_database_name_with_different_uri(
        self,
        session: Session,
        app_context: None,
        mocker: MockerFixture,
    ) -> None:
        """
        Test that get_or_create_local_db fails closed on a name collision
        with a non-local database.
        """
        import os
        import tempfile

        from superset.commands.database.uploaders.local_db import (
            get_or_create_local_db,
            LocalDatabaseConfigurationError,
        )

        Database.metadata.create_all(session.get_bind())  # pylint: disable=no-member

        session.query(Database).filter_by(database_name="Local Files").delete()
        colliding_db = Database(
            database_name="Local Files",
            sqlalchemy_uri="sqlite://",
            allow_file_upload=True,
        )
        session.add(colliding_db)
        session.commit()

        with tempfile.TemporaryDirectory() as tmpdir:
            mocker.patch.dict(
                current_app.config,
                {
                    "LOCAL_DB_NAME": "Local Files",
                    "LOCAL_DB_PATH": os.path.join(tmpdir, "local_files.duckdb"),
                },
            )

            with pytest.raises(LocalDatabaseConfigurationError):
                get_or_create_local_db()

        assert (
            session.query(Database)
            .filter_by(database_name="Local Files")
            .one()
            .sqlalchemy_uri
            == "sqlite://"
        )

        session.delete(colliding_db)
        session.commit()

    def test_creates_parent_directory(
        self,
        session: Session,
        app_context: None,
        mocker: MockerFixture,
    ) -> None:
        """
        Test that get_or_create_local_db ensures the parent directory exists.
        """
        import os
        import tempfile

        from superset.commands.database.uploaders.local_db import (
            get_or_create_local_db,
        )

        # Create the table
        Database.metadata.create_all(session.get_bind())  # pylint: disable=no-member

        # Clean up any existing record
        session.query(Database).filter_by(database_name="Local Files").delete()
        session.commit()

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "subdir", "local_files.duckdb")
            mocker.patch.dict(
                current_app.config,
                {"LOCAL_DB_PATH": db_path, "LOCAL_DB_NAME": "Local Files"},
            )

            local_db = get_or_create_local_db()

            # The parent directory should have been created
            assert os.path.isdir(os.path.join(tmpdir, "subdir"))

            # Clean up
            session.delete(local_db)
            session.commit()


class TestAutoUploadEndpoint:
    """Tests for the POST /api/v1/database/auto_upload/ endpoint."""

    @with_feature_flags(ENABLE_LOCAL_FILE_UPLOAD=False)
    def test_auto_upload_returns_404_when_feature_disabled(
        self,
        session: Session,
        client: Any,
        full_api_access: None,
    ) -> None:
        """
        Test that auto_upload fails closed when local file upload is disabled.
        """
        data = {"file": (BytesIO(b"Name,Age\nAda,36\n"), "test.csv")}
        response = client.post(
            "/api/v1/database/auto_upload/",
            data=data,
            content_type="multipart/form-data",
        )
        assert response.status_code == 404

    def test_auto_upload_no_file(
        self,
        session: Session,
        client: Any,
        full_api_access: None,
    ) -> None:
        """
        Test that auto_upload returns 400 when no file is provided.
        """
        response = client.post(
            "/api/v1/database/auto_upload/",
            data={},
            content_type="multipart/form-data",
        )
        assert response.status_code == 400

    def test_auto_upload_unsupported_file_type(
        self,
        session: Session,
        client: Any,
        full_api_access: None,
    ) -> None:
        """
        Test that auto_upload returns 400 for unsupported file types.
        """
        data = {"file": (BytesIO(b"some data"), "test.json")}
        response = client.post(
            "/api/v1/database/auto_upload/",
            data=data,
            content_type="multipart/form-data",
        )
        assert response.status_code == 400
        assert "Unsupported file type" in response.json.get("message", "")

    @patch("superset.databases.api.UploadCommand")
    @patch("superset.databases.api.get_or_create_local_db")
    def test_auto_upload_csv_success(
        self,
        mock_get_local_db: MagicMock,
        mock_upload_command: MagicMock,
        session: Session,
        client: Any,
        full_api_access: None,
    ) -> None:
        """
        Test successful CSV upload via auto_upload endpoint.
        """

        # Setup mock local database
        mock_db = MagicMock()
        mock_db.id = 9999
        mock_get_local_db.return_value = mock_db

        # Mock UploadCommand so it doesn't actually run
        mock_cmd_instance = MagicMock()
        mock_upload_command.return_value = mock_cmd_instance

        # Create a mock SqlaTable that would be "found" after upload
        mock_table = MagicMock()
        mock_table.id = 12345

        csv_content = b"Name,Age,City\nJohn,30,New York\n"
        data = {"file": (BytesIO(csv_content), "test_data.csv")}

        with patch.object(db.session, "query", return_value=MagicMock()) as mock_query:
            mock_query.return_value.filter_by.return_value.one_or_none.return_value = (
                mock_table
            )

            response = client.post(
                "/api/v1/database/auto_upload/",
                data=data,
                content_type="multipart/form-data",
            )

        assert response.status_code == 201
        result = response.json
        assert result["database_id"] == 9999
        assert result["dataset_id"] == 12345
        assert "upload_test_data" in result["table_name"]

    @patch("superset.databases.api.UploadCommand")
    @patch("superset.databases.api.get_or_create_local_db")
    def test_auto_upload_truncates_generated_table_name_to_dataset_limit(
        self,
        mock_get_local_db: MagicMock,
        mock_upload_command: MagicMock,
        session: Session,
        client: Any,
        full_api_access: None,
    ) -> None:
        """
        Test auto_upload generated names fit the dataset table_name column.
        """
        mock_db = MagicMock()
        mock_db.id = 9999
        mock_get_local_db.return_value = mock_db

        mock_cmd_instance = MagicMock()
        mock_upload_command.return_value = mock_cmd_instance

        mock_table = MagicMock()
        mock_table.id = 12345

        long_filename = f"{'a' * 300}.csv"
        data = {"file": (BytesIO(b"Name,Age\nAda,36\n"), long_filename)}

        with patch.object(db.session, "query", return_value=MagicMock()) as mock_query:
            mock_query.return_value.filter_by.return_value.one_or_none.return_value = (
                mock_table
            )

            response = client.post(
                "/api/v1/database/auto_upload/",
                data=data,
                content_type="multipart/form-data",
            )

        assert response.status_code == 201
        table_name = response.json["table_name"]
        assert len(table_name) == 250
        assert mock_upload_command.call_args[0][1] == table_name

    @patch("superset.databases.api.UploadCommand")
    @patch("superset.databases.api.get_or_create_local_db")
    def test_auto_upload_blank_custom_table_name_falls_back_to_filename(
        self,
        mock_get_local_db: MagicMock,
        mock_upload_command: MagicMock,
        session: Session,
        client: Any,
        full_api_access: None,
    ) -> None:
        """
        Test a blank custom table_name does not discard the filename stem.
        """
        mock_db = MagicMock()
        mock_db.id = 9999
        mock_get_local_db.return_value = mock_db

        mock_cmd_instance = MagicMock()
        mock_upload_command.return_value = mock_cmd_instance

        mock_table = MagicMock()
        mock_table.id = 12345

        data = {
            "file": (BytesIO(b"Name,Age\nAda,36\n"), "sales.csv"),
            "table_name": "   ",
        }

        with patch.object(db.session, "query", return_value=MagicMock()) as mock_query:
            mock_query.return_value.filter_by.return_value.one_or_none.return_value = (
                mock_table
            )

            response = client.post(
                "/api/v1/database/auto_upload/",
                data=data,
                content_type="multipart/form-data",
            )

        assert response.status_code == 201
        table_name = response.json["table_name"]
        assert table_name.startswith("upload_sales_")
        assert not table_name.startswith("upload_upload_")
        assert mock_upload_command.call_args[0][1] == table_name

    @patch("superset.databases.api.UploadCommand")
    @patch("superset.databases.api.get_or_create_local_db")
    def test_auto_upload_returns_500_when_dataset_missing_after_upload(
        self,
        mock_get_local_db: MagicMock,
        mock_upload_command: MagicMock,
        session: Session,
        client: Any,
        full_api_access: None,
    ) -> None:
        """
        Test auto_upload does not report success when the dataset row is missing.
        """
        mock_db = MagicMock()
        mock_db.id = 9999
        mock_get_local_db.return_value = mock_db

        mock_cmd_instance = MagicMock()
        mock_upload_command.return_value = mock_cmd_instance

        data = {"file": (BytesIO(b"Name,Age\nAda,36\n"), "test_data.csv")}

        with patch.object(db.session, "query", return_value=MagicMock()) as mock_query:
            mock_query.return_value.filter_by.return_value.one_or_none.return_value = (
                None
            )

            response = client.post(
                "/api/v1/database/auto_upload/",
                data=data,
                content_type="multipart/form-data",
            )

        assert response.status_code == 500
        assert (
            response.json["message"]
            == "Upload succeeded but dataset could not be found"
        )

    @patch("superset.databases.api.UploadCommand")
    @patch("superset.databases.api.get_or_create_local_db")
    def test_auto_upload_preserves_superset_exception_status(
        self,
        mock_get_local_db: MagicMock,
        mock_upload_command: MagicMock,
        session: Session,
        client: Any,
        full_api_access: None,
    ) -> None:
        """
        Test auto_upload preserves command exception status codes.
        """
        from superset.commands.database.exceptions import DatabaseUploadFileTooLarge

        mock_db = MagicMock()
        mock_db.id = 9999
        mock_get_local_db.return_value = mock_db

        mock_cmd_instance = MagicMock()
        mock_cmd_instance.run.side_effect = DatabaseUploadFileTooLarge()
        mock_upload_command.return_value = mock_cmd_instance

        response = client.post(
            "/api/v1/database/auto_upload/",
            data={"file": (BytesIO(b"Name,Age\nAda,36\n"), "test_data.csv")},
            content_type="multipart/form-data",
        )

        assert response.status_code == 413
        assert (
            response.json["message"]
            == "Database upload file exceeds the maximum allowed size."
        )

    @patch("superset.databases.api.UploadCommand")
    @patch("superset.databases.api.get_or_create_local_db")
    def test_auto_upload_excel_success(
        self,
        mock_get_local_db: MagicMock,
        mock_upload_command: MagicMock,
        session: Session,
        client: Any,
        full_api_access: None,
    ) -> None:
        """
        Test successful Excel upload via auto_upload endpoint.
        """
        import pandas as pd

        mock_db = MagicMock()
        mock_db.id = 9999
        mock_get_local_db.return_value = mock_db

        mock_cmd_instance = MagicMock()
        mock_upload_command.return_value = mock_cmd_instance

        mock_table = MagicMock()
        mock_table.id = 54321

        # Create a real Excel file in memory
        buffer = BytesIO()
        df = pd.DataFrame({"Name": ["John"], "Age": [30]})
        df.to_excel(buffer, index=False)
        buffer.seek(0)

        data = {"file": (buffer, "report.xlsx")}

        with patch.object(db.session, "query", return_value=MagicMock()) as mock_query:
            mock_query.return_value.filter_by.return_value.one_or_none.return_value = (
                mock_table
            )

            response = client.post(
                "/api/v1/database/auto_upload/",
                data=data,
                content_type="multipart/form-data",
            )

        assert response.status_code == 201
        result = response.json
        assert result["database_id"] == 9999
        assert result["dataset_id"] == 54321
        assert "upload_report" in result["table_name"]


class TestAnalyticsDbSafety:
    """Tests for the DuckDB blocklist exemption in analytics_db_safety.py."""

    def test_duckdb_blocked_when_allow_false(
        self,
        app_context: None,
        mocker: MockerFixture,
    ) -> None:
        """
        Test that DuckDB is blocked when ALLOW_DUCKDB_CONNECTIONS is False.
        """
        from sqlalchemy.engine.url import make_url

        from superset.exceptions import SupersetSecurityException
        from superset.security.analytics_db_safety import check_sqlalchemy_uri

        mocker.patch.dict(
            current_app.config,
            {"ALLOW_DUCKDB_CONNECTIONS": False},
        )

        uri = make_url("duckdb:///test.db")
        with pytest.raises(SupersetSecurityException):
            check_sqlalchemy_uri(uri)

    def test_duckdb_allowed_when_allow_true(
        self,
        app_context: None,
        mocker: MockerFixture,
    ) -> None:
        """
        Test that DuckDB is allowed when ALLOW_DUCKDB_CONNECTIONS is True.
        """
        from sqlalchemy.engine.url import make_url

        from superset.security.analytics_db_safety import check_sqlalchemy_uri

        mocker.patch.dict(
            current_app.config,
            {"ALLOW_DUCKDB_CONNECTIONS": True},
        )

        uri = make_url("duckdb:///test.db")
        # Should not raise
        check_sqlalchemy_uri(uri)

    def test_sqlite_still_blocked_when_duckdb_allowed(
        self,
        app_context: None,
        mocker: MockerFixture,
    ) -> None:
        """
        Test that SQLite remains blocked even when ALLOW_DUCKDB_CONNECTIONS is True.
        """
        from sqlalchemy.engine.url import make_url

        from superset.exceptions import SupersetSecurityException
        from superset.security.analytics_db_safety import check_sqlalchemy_uri

        mocker.patch.dict(
            current_app.config,
            {"ALLOW_DUCKDB_CONNECTIONS": True},
        )

        uri = make_url("sqlite:///test.db")
        with pytest.raises(SupersetSecurityException):
            check_sqlalchemy_uri(uri)

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

from unittest.mock import Mock, patch

import pytest

from axbi.commands.theme.exceptions import (
    SystemThemeProtectedError,
    ThemeNotFoundError,
)
from axbi.commands.theme.seed import SeedSystemThemesCommand
from axbi.commands.theme.update import UpdateThemeCommand
from axbi.models.core import Theme
from tests.conftest import with_config


class TestUpdateThemeCommand:
    """Unit tests for UpdateThemeCommand"""

    @patch("axbi.commands.theme.update.ThemeDAO")
    def test_validate_theme_not_found(self, mock_theme_dao):
        """Test validation fails when theme doesn't exist"""
        # Arrange
        mock_theme_dao.find_by_id.return_value = None
        command = UpdateThemeCommand(123, {"theme_name": "test"})

        # Act & Assert
        with pytest.raises(ThemeNotFoundError):
            command.validate()

    @patch("axbi.commands.theme.update.ThemeDAO")
    def test_validate_system_theme_protection(self, mock_theme_dao):
        """Test validation fails when trying to update system theme"""
        # Arrange
        mock_theme = Mock(spec=Theme)
        mock_theme.is_system = True
        mock_theme_dao.find_by_id.return_value = mock_theme
        command = UpdateThemeCommand(123, {"theme_name": "test"})

        # Act & Assert
        with pytest.raises(SystemThemeProtectedError):
            command.validate()

    @patch("axbi.commands.theme.update.ThemeDAO")
    def test_validate_regular_theme_success(self, mock_theme_dao):
        """Test validation succeeds for regular (non-system) themes"""
        # Arrange
        mock_theme = Mock(spec=Theme)
        mock_theme.is_system = False
        mock_theme_dao.find_by_id.return_value = mock_theme
        command = UpdateThemeCommand(123, {"theme_name": "test"})

        # Act
        command.validate()  # Should not raise any exception

        # Assert
        assert command._model == mock_theme

    @patch("axbi.commands.theme.update.ThemeDAO")
    def test_run_success(self, mock_theme_dao):
        """Test successful theme update"""
        # Arrange
        mock_theme = Mock(spec=Theme)
        mock_theme.is_system = False
        mock_updated_theme = Mock(spec=Theme)
        mock_theme_dao.find_by_id.return_value = mock_theme
        mock_theme_dao.update.return_value = mock_updated_theme

        command = UpdateThemeCommand(123, {"theme_name": "updated_name"})

        # Act
        result = command.run()

        # Assert
        assert result == mock_updated_theme
        mock_theme_dao.update.assert_called_once_with(
            mock_theme, {"theme_name": "updated_name"}
        )


class TestSeedSystemThemesCommand:
    """Unit tests for SeedSystemThemesCommand"""

    @with_config(
        {
            "THEME_DEFAULT": None,
            "THEME_DARK": None,
        }
    )
    def test_run_no_themes_configured(self, app):
        """Test run when no themes are configured"""
        # Arrange
        command = SeedSystemThemesCommand()

        # Act
        command.run()  # Should complete without error

    @with_config(
        {
            "THEME_DEFAULT": {"algorithm": "default", "token": {}},
            "THEME_DARK": None,
        }
    )
    @patch("axbi.commands.theme.seed.db")
    def test_run_with_theme_default_only(self, mock_db, app):
        """Test run when only THEME_DEFAULT is configured"""
        # Arrange
        mock_session = Mock()
        mock_db.session = mock_session
        mock_session.query.return_value.filter.return_value.first.return_value = None

        command = SeedSystemThemesCommand()

        # Act
        command.run()

        # Assert
        mock_session.add.assert_called_once()
        # Note: commit is handled by @transaction() decorator, not directly called

    @with_config(
        {
            "THEME_DEFAULT": {"algorithm": "default", "token": {}},
            "THEME_DARK": None,
        }
    )
    @patch("axbi.commands.theme.seed.db")
    def test_run_update_existing_theme(self, mock_db, app):
        """Test run when theme already exists and needs updating"""
        # Arrange
        # Mock existing theme
        mock_existing_theme = Mock(spec=Theme)
        mock_existing_theme.json_data = '{"old": "data"}'

        mock_session = Mock()
        mock_db.session = mock_session
        mock_session.query.return_value.filter.return_value.first.return_value = (
            mock_existing_theme
        )

        command = SeedSystemThemesCommand()

        # Act
        command.run()

        # Assert
        assert '"algorithm": "default"' in mock_existing_theme.json_data
        # Note: commit is handled by @transaction() decorator, not directly called
        mock_session.add.assert_not_called()  # Should not add new theme

    @with_config(
        {
            "THEME_DEFAULT": {"algorithm": "default", "token": {}},
            "THEME_DARK": None,
        }
    )
    @patch("axbi.commands.theme.seed.db")
    @patch("axbi.commands.theme.seed.logger")
    def test_run_handles_database_error(self, mock_logger, mock_db, app):
        """Test run handles database errors gracefully"""
        # Arrange
        mock_session = Mock()
        mock_db.session = mock_session
        mock_session.query.side_effect = Exception("Database error")

        command = SeedSystemThemesCommand()

        # Act & Assert
        with pytest.raises(Exception, match="Database error"):
            command.run()  # Should raise exception due to @transaction() decorator

    @with_config(
        {
            "THEME_DEFAULT": {"algorithm": "default", "token": {}},
            "THEME_DARK": {"algorithm": "dark", "token": {}},
        }
    )
    @patch("axbi.commands.theme.seed.db")
    def test_run_with_both_themes(self, mock_db, app):
        """Test run when both THEME_DEFAULT and THEME_DARK are configured"""
        # Arrange
        mock_session = Mock()
        mock_db.session = mock_session
        mock_session.query.return_value.filter.return_value.first.return_value = None

        command = SeedSystemThemesCommand()

        # Act
        command.run()

        # Assert
        assert mock_session.add.call_count == 2  # Both themes should be added
        # Note: commit is handled by @transaction() decorator, not directly called

    @with_config(
        {
            "THEME_DEFAULT": {"uuid": "referenced-theme-uuid"},
            "THEME_DARK": None,
        }
    )
    @patch("axbi.commands.theme.seed.logger")
    @patch("axbi.commands.theme.seed.ThemeDAO")
    @patch("axbi.commands.theme.seed.db")
    def test_run_skips_uuid_reference_with_non_object_json(
        self,
        mock_db,
        mock_theme_dao,
        mock_logger,
        app,
    ):
        """Test UUID references with non-object JSON are skipped."""
        # Arrange
        mock_session = Mock()
        mock_db.session = mock_session
        mock_theme = Mock(spec=Theme)
        mock_theme.json_data = "[]"
        mock_theme_dao.find_by_uuid.return_value = mock_theme

        command = SeedSystemThemesCommand()

        # Act
        command.run()

        # Assert
        mock_session.query.assert_not_called()
        mock_logger.error.assert_called_once_with(
            "Theme JSON for UUID %s must be an object",
            "referenced-theme-uuid",
        )

    def test_validate(self):
        """Test validate method (should be no-op)"""
        # Arrange
        command = SeedSystemThemesCommand()

        # Act & Assert
        command.validate()  # Should complete without error

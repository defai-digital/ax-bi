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

from __future__ import annotations

import json
import threading
import time
from unittest.mock import Mock, patch

import pytest
from superset_core.extensions.types import Manifest

from superset_extensions_cli.cli import FrontendChangeHandler, app


# Dev Command Tests
@pytest.mark.cli
@patch("superset_extensions_cli.cli.Observer")
@patch("superset_extensions_cli.cli.validate_npm")
@patch("superset_extensions_cli.cli.init_frontend_deps")
@patch("superset_extensions_cli.cli.rebuild_frontend")
@patch("superset_extensions_cli.cli.rebuild_backend")
@patch("superset_extensions_cli.cli.build_manifest")
@patch("superset_extensions_cli.cli.write_manifest")
def test_dev_command_starts_watchers(
    mock_write_manifest,
    mock_build_manifest,
    mock_rebuild_backend,
    mock_rebuild_frontend,
    mock_init_frontend_deps,
    mock_validate_npm,
    mock_observer_class,
    cli_runner,
    isolated_filesystem,
    extension_setup_for_dev,
):
    """Test dev command starts file watchers."""
    # Setup mocks
    mock_rebuild_frontend.return_value = "remoteEntry.abc123.js"
    mock_build_manifest.return_value = Manifest(
        id="test-org.test-extension",
        publisher="test-org",
        name="test-extension",
        displayName="Test Extension",
        version="1.0.0",
    )

    mock_observer = Mock()
    mock_observer_class.return_value = mock_observer

    extension_setup_for_dev(isolated_filesystem)

    # Run dev command in a thread since it's blocking
    def run_dev():
        try:
            cli_runner.invoke(app, ["dev"], catch_exceptions=False)
        except KeyboardInterrupt:
            pass

    dev_thread = threading.Thread(target=run_dev)
    dev_thread.daemon = True
    dev_thread.start()

    # Let it start up
    time.sleep(0.1)

    # Verify observer methods were called
    mock_observer.schedule.assert_called()
    mock_observer.start.assert_called_once()

    # Initial setup calls
    mock_init_frontend_deps.assert_called_once()
    mock_validate_npm.assert_called()
    mock_rebuild_frontend.assert_called()
    mock_rebuild_backend.assert_called()
    mock_build_manifest.assert_called()
    mock_write_manifest.assert_called()


@pytest.mark.cli
@patch("superset_extensions_cli.cli.validate_npm")
@patch("superset_extensions_cli.cli.init_frontend_deps")
@patch("superset_extensions_cli.cli.rebuild_frontend")
@patch("superset_extensions_cli.cli.rebuild_backend")
@patch("superset_extensions_cli.cli.build_manifest")
@patch("superset_extensions_cli.cli.write_manifest")
def test_dev_command_initial_build(
    mock_write_manifest,
    mock_build_manifest,
    mock_rebuild_backend,
    mock_rebuild_frontend,
    mock_init_frontend_deps,
    mock_validate_npm,
    cli_runner,
    isolated_filesystem,
    extension_setup_for_dev,
):
    """Test dev command performs initial build setup."""
    # Setup mocks
    mock_rebuild_frontend.return_value = "remoteEntry.abc123.js"
    mock_build_manifest.return_value = Manifest(
        id="test-org.test-extension",
        publisher="test-org",
        name="test-extension",
        displayName="Test Extension",
        version="1.0.0",
    )

    extension_setup_for_dev(isolated_filesystem)

    with patch("superset_extensions_cli.cli.Observer") as mock_observer_class:
        mock_observer = Mock()
        mock_observer_class.return_value = mock_observer

        with patch("time.sleep", side_effect=KeyboardInterrupt):
            try:
                cli_runner.invoke(app, ["dev"], catch_exceptions=False)
            except KeyboardInterrupt:
                pass

    # Verify initial build steps
    frontend_dir = isolated_filesystem / "frontend"
    mock_validate_npm.assert_called_once()
    mock_init_frontend_deps.assert_called_once_with(frontend_dir)
    mock_rebuild_frontend.assert_called_once_with(isolated_filesystem, frontend_dir)
    mock_rebuild_backend.assert_called_once_with(isolated_filesystem)


@pytest.mark.cli
@patch("superset_extensions_cli.cli.Observer")
@patch("superset_extensions_cli.cli.validate_npm")
@patch("superset_extensions_cli.cli.init_frontend_deps")
@patch("superset_extensions_cli.cli.rebuild_frontend")
@patch("superset_extensions_cli.cli.rebuild_backend")
@patch("superset_extensions_cli.cli.build_manifest")
@patch("superset_extensions_cli.cli.write_manifest")
def test_dev_command_aborts_when_initial_frontend_build_fails(
    mock_write_manifest,
    mock_build_manifest,
    mock_rebuild_backend,
    mock_rebuild_frontend,
    mock_init_frontend_deps,
    mock_validate_npm,
    mock_observer_class,
    cli_runner,
    isolated_filesystem,
    extension_setup_for_dev,
):
    """Test dev exits before watching when the initial frontend build fails."""
    mock_rebuild_frontend.return_value = None
    extension_setup_for_dev(isolated_filesystem)

    result = cli_runner.invoke(app, ["dev"])

    assert result.exit_code == 1
    assert "Frontend build failed; aborting watch mode" in result.output
    mock_validate_npm.assert_called_once()
    mock_init_frontend_deps.assert_called_once_with(isolated_filesystem / "frontend")
    mock_rebuild_backend.assert_not_called()
    mock_build_manifest.assert_not_called()
    mock_write_manifest.assert_not_called()
    mock_observer_class.assert_not_called()


@pytest.mark.cli
@patch("superset_extensions_cli.cli.Observer")
@patch("superset_extensions_cli.cli.validate_npm")
@patch("superset_extensions_cli.cli.init_frontend_deps")
@patch("superset_extensions_cli.cli.rebuild_frontend")
@patch("superset_extensions_cli.cli.rebuild_backend")
@patch("superset_extensions_cli.cli.build_manifest")
@patch("superset_extensions_cli.cli.write_manifest")
def test_dev_command_rejects_changed_watch_directory_before_schedule(
    mock_write_manifest,
    mock_build_manifest,
    mock_rebuild_backend,
    mock_rebuild_frontend,
    mock_init_frontend_deps,
    mock_validate_npm,
    mock_observer_class,
    cli_runner,
    isolated_filesystem,
    extension_setup_for_dev,
):
    """Test dev refuses a watch directory changed before observer setup."""
    mock_rebuild_frontend.return_value = "remoteEntry.abc123.js"
    mock_build_manifest.return_value = Manifest(
        id="test-org.test-extension",
        publisher="test-org",
        name="test-extension",
        displayName="Test Extension",
        version="1.0.0",
    )
    mock_observer = Mock()
    frontend_dir = isolated_filesystem / "frontend"
    saved_frontend_dir = isolated_filesystem / "saved-frontend"
    replacement_frontend_dir = isolated_filesystem / "replacement-frontend"
    replacement_frontend_dir.mkdir()

    def replace_frontend_before_observer_schedule():
        frontend_dir.rename(saved_frontend_dir)
        replacement_frontend_dir.rename(frontend_dir)
        return mock_observer

    mock_observer_class.side_effect = replace_frontend_before_observer_schedule
    extension_setup_for_dev(isolated_filesystem)

    result = cli_runner.invoke(app, ["dev"])

    assert result.exit_code == 1
    assert "frontend path changed before watch setup" in result.output
    mock_observer.schedule.assert_not_called()
    mock_observer.start.assert_not_called()


@pytest.mark.cli
@patch("superset_extensions_cli.cli.Observer")
@patch("superset_extensions_cli.cli.validate_npm")
@patch("superset_extensions_cli.cli.init_frontend_deps")
@patch("superset_extensions_cli.cli.rebuild_frontend")
@patch("superset_extensions_cli.cli.rebuild_backend")
@patch("superset_extensions_cli.cli.build_manifest")
@patch("superset_extensions_cli.cli.write_manifest")
def test_dev_command_rejects_watch_directory_content_change_before_schedule(
    mock_write_manifest,
    mock_build_manifest,
    mock_rebuild_backend,
    mock_rebuild_frontend,
    mock_init_frontend_deps,
    mock_validate_npm,
    mock_observer_class,
    cli_runner,
    isolated_filesystem,
    extension_setup_for_dev,
):
    """Test dev refuses watch directory content changes before observer setup."""
    mock_rebuild_frontend.return_value = "remoteEntry.abc123.js"
    mock_build_manifest.return_value = Manifest(
        id="test-org.test-extension",
        publisher="test-org",
        name="test-extension",
        displayName="Test Extension",
        version="1.0.0",
    )
    mock_observer = Mock()
    frontend_dir = isolated_filesystem / "frontend"

    def change_frontend_before_observer_schedule():
        (frontend_dir / "unexpected.txt").write_text("unexpected")
        return mock_observer

    mock_observer_class.side_effect = change_frontend_before_observer_schedule
    extension_setup_for_dev(isolated_filesystem)

    result = cli_runner.invoke(app, ["dev"])

    assert result.exit_code == 1
    assert "frontend path changed before watch setup" in result.output
    mock_observer.schedule.assert_not_called()
    mock_observer.start.assert_not_called()
    assert (frontend_dir / "unexpected.txt").read_text() == "unexpected"


@pytest.mark.cli
@patch("superset_extensions_cli.cli.Observer")
@patch("superset_extensions_cli.cli.validate_npm")
@patch("superset_extensions_cli.cli.init_frontend_deps")
@patch("superset_extensions_cli.cli.rebuild_frontend")
@patch("superset_extensions_cli.cli.rebuild_backend")
@patch("superset_extensions_cli.cli.build_manifest")
@patch("superset_extensions_cli.cli.write_manifest")
def test_dev_command_rejects_watch_parent_change_before_schedule(
    mock_write_manifest,
    mock_build_manifest,
    mock_rebuild_backend,
    mock_rebuild_frontend,
    mock_init_frontend_deps,
    mock_validate_npm,
    mock_observer_class,
    cli_runner,
    isolated_filesystem,
    extension_setup_for_dev,
    monkeypatch,
):
    """Test dev refuses a watch directory moved under a replaced parent."""
    project_dir = isolated_filesystem / "project"
    project_dir.mkdir()
    extension_setup_for_dev(project_dir)
    monkeypatch.chdir(project_dir)
    mock_rebuild_frontend.return_value = "remoteEntry.abc123.js"
    mock_build_manifest.return_value = Manifest(
        id="test-org.test-extension",
        publisher="test-org",
        name="test-extension",
        displayName="Test Extension",
        version="1.0.0",
    )
    mock_observer = Mock()
    frontend_dir = project_dir / "frontend"
    saved_project_dir = isolated_filesystem / "saved-project"
    replacement_project_dir = isolated_filesystem / "replacement-project"

    def replace_frontend_parent_before_observer_schedule():
        project_dir.rename(saved_project_dir)
        replacement_project_dir.mkdir()
        (saved_project_dir / "frontend").rename(replacement_project_dir / "frontend")
        (saved_project_dir / "backend").rename(replacement_project_dir / "backend")
        (saved_project_dir / "extension.json").rename(
            replacement_project_dir / "extension.json"
        )
        replacement_project_dir.rename(project_dir)
        return mock_observer

    mock_observer_class.side_effect = replace_frontend_parent_before_observer_schedule

    result = cli_runner.invoke(app, ["dev"])

    assert result.exit_code == 1
    assert "frontend path changed before watch setup" in result.output
    mock_observer.schedule.assert_not_called()
    mock_observer.start.assert_not_called()
    assert not (saved_project_dir / "frontend").exists()
    assert frontend_dir.is_dir()


@pytest.mark.cli
@patch("superset_extensions_cli.cli.validate_npm")
def test_dev_command_validates_before_building(
    mock_validate_npm, cli_runner, isolated_filesystem
):
    """Test dev command validates the extension before building or watching."""
    extension_json = {
        "publisher": "test-org",
        "name": "test-extension",
        "displayName": "Test Extension",
        "version": "1.0.0",
        "permissions": [],
    }
    (isolated_filesystem / "extension.json").write_text(json.dumps(extension_json))
    (isolated_filesystem / "frontend").write_text("not a directory")

    result = cli_runner.invoke(app, ["dev"])

    assert result.exit_code == 1
    mock_validate_npm.assert_called_once()
    assert "frontend path exists but is not a directory" in result.output
    assert not (isolated_filesystem / "dist").exists()


# FrontendChangeHandler Tests
@pytest.mark.unit
def test_frontend_change_handler_init():
    """Test FrontendChangeHandler initialization."""
    mock_trigger = Mock()
    handler = FrontendChangeHandler(trigger_build=mock_trigger)

    assert handler.trigger_build == mock_trigger


@pytest.mark.unit
@pytest.mark.parametrize(
    "source_path",
    [
        "/path/to/frontend/dist/file.js",
        "/path/to/frontend/dist/assets/style.css",
        r"C:\path\to\frontend\dist\file.js",
    ],
)
def test_frontend_change_handler_ignores_dist_changes(source_path):
    """Test FrontendChangeHandler ignores changes in dist directory."""
    mock_trigger = Mock()
    handler = FrontendChangeHandler(trigger_build=mock_trigger)

    # Create mock event with dist path
    mock_event = Mock()
    mock_event.src_path = source_path

    handler.on_any_event(mock_event)

    # Should not trigger build for dist changes
    mock_trigger.assert_not_called()


@pytest.mark.unit
@pytest.mark.parametrize(
    "source_path",
    [
        "/path/to/frontend/src/component.tsx",
        "/path/to/frontend/webpack.config.js",
        "/path/to/frontend/package.json",
        "/path/to/frontend/dist-helper/source.ts",
        r"C:\path\to\frontend\dist-helper\source.ts",
    ],
)
def test_frontend_change_handler_triggers_on_source_changes(source_path):
    """Test FrontendChangeHandler triggers build on source changes."""
    mock_trigger = Mock()
    handler = FrontendChangeHandler(trigger_build=mock_trigger)

    # Create mock event with source path
    mock_event = Mock()
    mock_event.src_path = source_path

    handler.on_any_event(mock_event)

    # Should trigger build for source changes
    mock_trigger.assert_called_once()


# Dev Utility Functions Tests
@pytest.mark.unit
def test_frontend_watcher_function_coverage(isolated_filesystem):
    """Test frontend watcher function for coverage."""
    # Create extension.json
    extension_json = {
        "publisher": "test-org",
        "name": "test-extension",
        "displayName": "Test Extension",
        "version": "1.0.0",
        "permissions": [],
    }
    (isolated_filesystem / "extension.json").write_text(json.dumps(extension_json))

    # Create dist directory
    dist_dir = isolated_filesystem / "dist"
    dist_dir.mkdir()

    mock_manifest = Manifest(
        id="test-org.test-extension",
        publisher="test-org",
        name="test-extension",
        displayName="Test Extension",
        version="1.0.0",
    )
    with patch("superset_extensions_cli.cli.rebuild_frontend") as mock_rebuild:
        with patch("superset_extensions_cli.cli.build_manifest") as mock_build:
            with patch("superset_extensions_cli.cli.write_manifest") as mock_write:
                mock_rebuild.return_value = "remoteEntry.abc123.js"
                mock_build.return_value = mock_manifest

                # Simulate frontend watcher function logic
                frontend_dir = isolated_filesystem / "frontend"
                frontend_dir.mkdir()

                # Actually call the functions to simulate the frontend_watcher
                if (
                    remote_entry := mock_rebuild(isolated_filesystem, frontend_dir)
                ) is not None:
                    manifest = mock_build(isolated_filesystem, remote_entry)
                    mock_write(isolated_filesystem, manifest)

                mock_rebuild.assert_called_once_with(isolated_filesystem, frontend_dir)
                mock_build.assert_called_once_with(
                    isolated_filesystem, "remoteEntry.abc123.js"
                )
                mock_write.assert_called_once_with(isolated_filesystem, mock_manifest)


@pytest.mark.unit
def test_backend_watcher_function_coverage(isolated_filesystem):
    """Test backend watcher function only rebuilds backend files."""
    # Create backend directory
    backend_dir = isolated_filesystem / "backend"
    backend_dir.mkdir()

    with patch("superset_extensions_cli.cli.rebuild_backend") as mock_rebuild:
        # Simulate backend watcher function - it only rebuilds backend
        if backend_dir.exists():
            mock_rebuild(isolated_filesystem)

        # Backend watcher should only call rebuild_backend
        mock_rebuild.assert_called_once_with(isolated_filesystem)

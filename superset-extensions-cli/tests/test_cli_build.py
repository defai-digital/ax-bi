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
import shutil
from pathlib import Path
from unittest.mock import Mock, patch

import click
import pytest
import superset_extensions_cli.cli as cli
from superset_core.extensions.types import Manifest
from superset_extensions_cli.cli import (
    app,
    build_manifest,
    clean_dist,
    cleanup_dist_replacement_backup,
    copy_backend_files,
    copy_frontend_dist,
    copy_output_file,
    create_temporary_output_directory,
    ensure_output_directory,
    ensure_output_file_parent,
    get_directory_path_identity,
    init_frontend_deps,
    publish_output_file,
    publish_staged_output_directory,
    remove_output_file,
    rollback_dist_replacement,
    start_dist_replacement,
    validate_output_file,
    validate_output_file_parent,
    write_manifest,
)

from tests.utils import (
    assert_directory_exists,
    assert_file_exists,
)


@pytest.fixture
def extension_with_build_structure():
    """Create extension structure suitable for build testing."""

    def _create(base_path, include_frontend=True, include_backend=True):
        # Create required directories
        if include_frontend:
            frontend_dir = base_path / "frontend"
            frontend_dir.mkdir()

            # Create conventional frontend entry point
            frontend_src_dir = frontend_dir / "src"
            frontend_src_dir.mkdir()
            (frontend_src_dir / "index.tsx").write_text("// Frontend entry point")

        if include_backend:
            backend_dir = base_path / "backend"
            backend_dir.mkdir()

            # Create conventional backend structure
            backend_src_dir = backend_dir / "src" / "test_org" / "test_extension"
            backend_src_dir.mkdir(parents=True)

            # Create conventional entry point file
            (backend_src_dir / "entrypoint.py").write_text("# Backend entry point")
            (backend_src_dir / "__init__.py").write_text("")

            # Create parent __init__.py files for namespace packages
            (backend_dir / "src" / "test_org" / "__init__.py").write_text("")

            # Create pyproject.toml matching the template structure
            pyproject_content = """[project]
name = "test_org-test_extension"
version = "1.0.0"
license = "Apache-2.0"

[tool.apache_superset_extensions.build]
# Files to include in the extension build/bundle
include = [
    "src/test_org/test_extension/**/*.py",
]
exclude = []
"""
            (backend_dir / "pyproject.toml").write_text(pyproject_content)

        # Create extension.json
        extension_json = {
            "publisher": "test-org",
            "name": "test-extension",
            "displayName": "Test Extension",
            "version": "1.0.0",
            "permissions": [],
        }

        (base_path / "extension.json").write_text(json.dumps(extension_json))

        return {
            "frontend_dir": frontend_dir if include_frontend else None,
            "backend_dir": backend_dir if include_backend else None,
        }

    return _create


# Build Command Tests
@pytest.mark.cli
@patch("superset_extensions_cli.cli.validate_npm")
@patch("superset_extensions_cli.cli.init_frontend_deps")
@patch("superset_extensions_cli.cli.run_frontend_build")
@patch("superset_extensions_cli.cli.copy_frontend_dist")
@patch("superset_extensions_cli.cli.rebuild_backend")
@patch("superset_extensions_cli.cli.read_toml")
def test_build_command_success_flow(
    mock_read_toml,
    mock_rebuild_backend,
    mock_copy_frontend_dist,
    mock_run_frontend_build,
    mock_init_frontend_deps,
    mock_validate_npm,
    cli_runner,
    isolated_filesystem,
    extension_with_build_structure,
):
    """Test build command success flow."""
    # Setup mocks
    mock_run_frontend_build.return_value = Mock(returncode=0)
    mock_copy_frontend_dist.return_value = "remoteEntry.abc123.js"
    mock_read_toml.return_value = {
        "project": {"name": "test", "version": "1.0.0"},
        "tool": {
            "apache_superset_extensions": {
                "build": {"include": ["src/test_org/test_extension/**/*.py"]}
            }
        },
    }

    # Create extension structure
    dirs = extension_with_build_structure(isolated_filesystem)

    result = cli_runner.invoke(app, ["build"])

    assert result.exit_code == 0
    assert "✅ Full build completed in dist/" in result.output

    # Verify function calls
    mock_validate_npm.assert_called_once()
    mock_init_frontend_deps.assert_called_once_with(dirs["frontend_dir"])
    mock_run_frontend_build.assert_called_once_with(dirs["frontend_dir"])
    mock_copy_frontend_dist.assert_called_once_with(isolated_filesystem)
    mock_rebuild_backend.assert_called_once()


@pytest.mark.cli
@patch("superset_extensions_cli.cli.validate_npm")
@patch("superset_extensions_cli.cli.init_frontend_deps")
@patch("superset_extensions_cli.cli.run_frontend_build")
@patch("superset_extensions_cli.cli.copy_frontend_dist")
@patch("superset_extensions_cli.cli.rebuild_backend")
@patch("superset_extensions_cli.cli.read_toml")
def test_build_command_handles_frontend_build_failure(
    mock_read_toml,
    mock_rebuild_backend,
    mock_copy_frontend_dist,
    mock_run_frontend_build,
    mock_init_frontend_deps,
    mock_validate_npm,
    cli_runner,
    isolated_filesystem,
    extension_with_build_structure,
):
    """Test build command handles frontend build failure."""
    # Setup mocks
    mock_run_frontend_build.return_value = Mock(returncode=1)
    mock_read_toml.return_value = {
        "project": {"name": "test", "version": "1.0.0"},
        "tool": {
            "apache_superset_extensions": {
                "build": {"include": ["src/test_org/test_extension/**/*.py"]}
            }
        },
    }

    # Create extension structure
    extension_with_build_structure(isolated_filesystem)
    previous_dist = isolated_filesystem / "dist"
    previous_dist.mkdir()
    (previous_dist / "manifest.json").write_text("previous")

    result = cli_runner.invoke(app, ["build"])

    assert result.exit_code == 1
    assert "Frontend build failed; aborting full build" in result.output
    assert "✅ Full build completed in dist/" not in result.output
    assert (previous_dist / "manifest.json").read_text() == "previous"
    mock_copy_frontend_dist.assert_not_called()
    mock_rebuild_backend.assert_not_called()


@pytest.mark.cli
@patch("superset_extensions_cli.cli.validate_npm")
@patch("superset_extensions_cli.cli.init_frontend_deps")
@patch("superset_extensions_cli.cli.run_frontend_build")
@patch("superset_extensions_cli.cli.copy_frontend_dist")
@patch("superset_extensions_cli.cli.rebuild_backend")
@patch("superset_extensions_cli.cli.read_toml")
def test_build_command_restores_existing_dist_on_backend_failure(
    mock_read_toml,
    mock_rebuild_backend,
    mock_copy_frontend_dist,
    mock_run_frontend_build,
    mock_init_frontend_deps,
    mock_validate_npm,
    cli_runner,
    isolated_filesystem,
    extension_with_build_structure,
):
    """Test full build restores previous dist when backend output fails."""
    mock_run_frontend_build.return_value = Mock(returncode=0)
    mock_copy_frontend_dist.return_value = "remoteEntry.abc123.js"
    mock_rebuild_backend.side_effect = click.ClickException("backend failed")
    mock_read_toml.return_value = {
        "project": {"name": "test", "version": "1.0.0"},
        "tool": {
            "apache_superset_extensions": {
                "build": {"include": ["src/test_org/test_extension/**/*.py"]}
            }
        },
    }

    extension_with_build_structure(isolated_filesystem)
    previous_dist = isolated_filesystem / "dist"
    previous_dist.mkdir()
    (previous_dist / "manifest.json").write_text("previous")

    result = cli_runner.invoke(app, ["build"])

    assert result.exit_code == 1
    assert "backend failed" in result.output
    assert (previous_dist / "manifest.json").read_text() == "previous"
    assert list(isolated_filesystem.glob(".dist-backup.*.tmp")) == []


@pytest.mark.cli
@patch("superset_extensions_cli.cli.validate_npm")
@patch("superset_extensions_cli.cli.init_frontend_deps")
@patch("superset_extensions_cli.cli.run_frontend_build")
@patch("superset_extensions_cli.cli.copy_frontend_dist")
@patch("superset_extensions_cli.cli.rebuild_backend")
@patch("superset_extensions_cli.cli.read_toml")
def test_build_command_reports_original_and_rollback_failures(
    mock_read_toml,
    mock_rebuild_backend,
    mock_copy_frontend_dist,
    mock_run_frontend_build,
    mock_init_frontend_deps,
    mock_validate_npm,
    cli_runner,
    isolated_filesystem,
    extension_with_build_structure,
    monkeypatch,
):
    """Test full build reports both original failure and failed dist restore."""
    mock_run_frontend_build.return_value = Mock(returncode=0)
    mock_copy_frontend_dist.return_value = "remoteEntry.abc123.js"
    mock_rebuild_backend.side_effect = click.ClickException("backend failed")
    mock_read_toml.return_value = {
        "project": {"name": "test", "version": "1.0.0"},
        "tool": {
            "apache_superset_extensions": {
                "build": {"include": ["src/test_org/test_extension/**/*.py"]}
            }
        },
    }

    extension_with_build_structure(isolated_filesystem)
    previous_dist = isolated_filesystem / "dist"
    previous_dist.mkdir()
    (previous_dist / "manifest.json").write_text("previous")
    original_replace = Path.replace

    def fail_backup_restore(path, target):
        if path.parent.name.startswith(".dist-backup.") and target == previous_dist:
            raise OSError("restore denied")
        return original_replace(path, target)

    monkeypatch.setattr(Path, "replace", fail_backup_restore)

    result = cli_runner.invoke(app, ["build"])

    assert result.exit_code == 1
    assert "backend failed" in result.output
    assert "Failed to restore previous dist directory: restore denied" in result.output


@pytest.mark.cli
@patch("superset_extensions_cli.cli.validate_npm")
@patch("superset_extensions_cli.cli.init_frontend_deps")
@patch("superset_extensions_cli.cli.run_frontend_build")
@patch("superset_extensions_cli.cli.copy_frontend_dist")
@patch("superset_extensions_cli.cli.rebuild_backend")
@patch("superset_extensions_cli.cli.read_toml")
def test_build_command_rejects_changed_dist_backup_during_rollback(
    mock_read_toml,
    mock_rebuild_backend,
    mock_copy_frontend_dist,
    mock_run_frontend_build,
    mock_init_frontend_deps,
    mock_validate_npm,
    cli_runner,
    isolated_filesystem,
    extension_with_build_structure,
):
    """Test full build refuses to restore a changed dist backup."""
    mock_run_frontend_build.return_value = Mock(returncode=0)
    mock_copy_frontend_dist.return_value = "remoteEntry.abc123.js"
    mock_read_toml.return_value = {
        "project": {"name": "test", "version": "1.0.0"},
        "tool": {
            "apache_superset_extensions": {
                "build": {"include": ["src/test_org/test_extension/**/*.py"]}
            }
        },
    }

    extension_with_build_structure(isolated_filesystem)
    previous_dist = isolated_filesystem / "dist"
    previous_dist.mkdir()
    (previous_dist / "manifest.json").write_text("previous")
    replacement_backup = isolated_filesystem / "replacement-dist"
    replacement_backup.mkdir()
    (replacement_backup / "manifest.json").write_text("replacement")
    saved_backup = isolated_filesystem / "saved-backup-dist"

    def fail_after_backup_swap(_cwd):
        backup_path = next(isolated_filesystem.glob(".dist-backup.*.tmp/dist"))
        backup_path.rename(saved_backup)
        replacement_backup.rename(backup_path)
        raise click.ClickException("backend failed")

    mock_rebuild_backend.side_effect = fail_after_backup_swap

    result = cli_runner.invoke(app, ["build"])

    assert result.exit_code == 1
    assert "backend failed" in result.output
    assert (
        "Failed to restore previous dist directory: backup path changed"
        in result.output
    )
    assert (saved_backup / "manifest.json").read_text() == "previous"


@pytest.mark.cli
@patch("superset_extensions_cli.cli.validate_npm")
@patch("superset_extensions_cli.cli.init_frontend_deps")
@patch("superset_extensions_cli.cli.run_frontend_build")
@patch("superset_extensions_cli.cli.copy_frontend_dist")
@patch("superset_extensions_cli.cli.rebuild_backend")
@patch("superset_extensions_cli.cli.read_toml")
def test_build_command_rejects_changed_restored_dist_during_rollback(
    mock_read_toml,
    mock_rebuild_backend,
    mock_copy_frontend_dist,
    mock_run_frontend_build,
    mock_init_frontend_deps,
    mock_validate_npm,
    cli_runner,
    isolated_filesystem,
    extension_with_build_structure,
    monkeypatch,
):
    """Test full build verifies the restored dist directory."""
    mock_run_frontend_build.return_value = Mock(returncode=0)
    mock_copy_frontend_dist.return_value = "remoteEntry.abc123.js"
    mock_rebuild_backend.side_effect = click.ClickException("backend failed")
    mock_read_toml.return_value = {
        "project": {"name": "test", "version": "1.0.0"},
        "tool": {
            "apache_superset_extensions": {
                "build": {"include": ["src/test_org/test_extension/**/*.py"]}
            }
        },
    }

    extension_with_build_structure(isolated_filesystem)
    previous_dist = isolated_filesystem / "dist"
    previous_dist.mkdir()
    (previous_dist / "manifest.json").write_text("previous")
    replacement_dist = isolated_filesystem / "replacement-dist"
    replacement_dist.mkdir()
    (replacement_dist / "manifest.json").write_text("replacement")
    saved_restored = isolated_filesystem / "saved-restored-dist"
    original_replace = Path.replace

    def swap_restored_dist(path, target):
        result = original_replace(path, target)
        if target == previous_dist and path.parent.name.startswith(".dist-backup."):
            previous_dist.rename(saved_restored)
            replacement_dist.rename(previous_dist)
        return result

    monkeypatch.setattr(Path, "replace", swap_restored_dist)

    result = cli_runner.invoke(app, ["build"])

    assert result.exit_code == 1
    assert "backend failed" in result.output
    assert (
        "Failed to restore previous dist directory: restored backup path changed"
        in result.output
    )
    assert (saved_restored / "manifest.json").read_text() == "previous"
    assert (previous_dist / "manifest.json").read_text() == "replacement"


@pytest.mark.cli
@patch("superset_extensions_cli.cli.validate_npm")
@patch("superset_extensions_cli.cli.init_frontend_deps")
@patch("superset_extensions_cli.cli.run_frontend_build")
@patch("superset_extensions_cli.cli.copy_frontend_dist")
@patch("superset_extensions_cli.cli.rebuild_backend")
@patch("superset_extensions_cli.cli.read_toml")
def test_build_command_reports_failed_dist_cleanup_during_rollback(
    mock_read_toml,
    mock_rebuild_backend,
    mock_copy_frontend_dist,
    mock_run_frontend_build,
    mock_init_frontend_deps,
    mock_validate_npm,
    cli_runner,
    isolated_filesystem,
    extension_with_build_structure,
    monkeypatch,
):
    """Test full build reports rollback cleanup failures instead of hiding them."""
    mock_run_frontend_build.return_value = Mock(returncode=0)
    mock_copy_frontend_dist.return_value = "remoteEntry.abc123.js"
    mock_rebuild_backend.side_effect = click.ClickException("backend failed")
    mock_read_toml.return_value = {
        "project": {"name": "test", "version": "1.0.0"},
        "tool": {
            "apache_superset_extensions": {
                "build": {"include": ["src/test_org/test_extension/**/*.py"]}
            }
        },
    }

    extension_with_build_structure(isolated_filesystem)
    previous_dist = isolated_filesystem / "dist"
    previous_dist.mkdir()
    (previous_dist / "manifest.json").write_text("previous")

    from superset_extensions_cli import cli

    original_remove_output_directory = cli.remove_output_directory

    def fail_partial_dist_cleanup(path, label, expected_identity=None):
        if path == previous_dist and label == "dist directory":
            raise click.ClickException("cleanup denied")
        original_remove_output_directory(path, label, expected_identity)

    monkeypatch.setattr(cli, "remove_output_directory", fail_partial_dist_cleanup)

    result = cli_runner.invoke(app, ["build"])

    assert result.exit_code == 1
    assert "backend failed" in result.output
    assert "Failed to clean failed dist directory before restore" in result.output
    assert "cleanup denied" in result.output


@pytest.mark.cli
@patch("superset_extensions_cli.cli.validate_npm")
@patch("superset_extensions_cli.cli.init_frontend_deps")
@patch("superset_extensions_cli.cli.run_frontend_build")
@patch("superset_extensions_cli.cli.copy_frontend_dist")
@patch("superset_extensions_cli.cli.rebuild_backend")
@patch("superset_extensions_cli.cli.read_toml")
def test_build_command_rejects_changed_dist_during_rollback_cleanup(
    mock_read_toml,
    mock_rebuild_backend,
    mock_copy_frontend_dist,
    mock_run_frontend_build,
    mock_init_frontend_deps,
    mock_validate_npm,
    cli_runner,
    isolated_filesystem,
    extension_with_build_structure,
):
    """Test rollback refuses to clean a dist path changed after replacement."""
    mock_run_frontend_build.return_value = Mock(returncode=0)
    mock_copy_frontend_dist.return_value = "remoteEntry.abc123.js"
    mock_read_toml.return_value = {
        "project": {"name": "test", "version": "1.0.0"},
        "tool": {
            "apache_superset_extensions": {
                "build": {"include": ["src/test_org/test_extension/**/*.py"]}
            }
        },
    }

    extension_with_build_structure(isolated_filesystem)
    previous_dist = isolated_filesystem / "dist"
    previous_dist.mkdir()
    (previous_dist / "manifest.json").write_text("previous")
    failed_dist = isolated_filesystem / "failed-dist"
    replacement_dist = isolated_filesystem / "replacement-dist"
    replacement_dist.mkdir()
    (replacement_dist / "manifest.json").write_text("replacement")

    def fail_after_dist_swap(_cwd):
        current_dist = isolated_filesystem / "dist"
        current_dist.rename(failed_dist)
        replacement_dist.rename(current_dist)
        raise click.ClickException("backend failed")

    mock_rebuild_backend.side_effect = fail_after_dist_swap

    result = cli_runner.invoke(app, ["build"])

    assert result.exit_code == 1
    assert "backend failed" in result.output
    assert "Failed to clean failed dist directory before restore" in result.output
    assert "dist directory path changed before rollback cleanup" in result.output
    assert ((isolated_filesystem / "dist") / "manifest.json").read_text() == (
        "replacement"
    )
    assert failed_dist.exists()


@pytest.mark.unit
def test_rollback_dist_replacement_rejects_changed_dist_during_cleanup(
    isolated_filesystem,
    monkeypatch,
):
    """Test rollback cleanup refuses a dist path changed after preflight."""
    dist_dir = isolated_filesystem / "dist"
    dist_dir.mkdir()
    (dist_dir / "manifest.json").write_text("failed")
    replacement_dist = isolated_filesystem / "replacement-dist"
    replacement_dist.mkdir()
    (replacement_dist / "manifest.json").write_text("replacement")
    saved_failed_dist = isolated_filesystem / "saved-failed-dist"

    from superset_extensions_cli import cli

    replacement_identity = get_directory_path_identity(dist_dir)
    assert replacement_identity is not None
    original_ensure_directory_identity_unchanged = (
        cli.ensure_directory_identity_unchanged
    )

    def swap_dist_after_preflight(path, label, identity, operation="metadata update"):
        original_ensure_directory_identity_unchanged(
            path,
            label,
            identity,
            operation,
        )
        if path == dist_dir and label == "dist directory":
            dist_dir.rename(saved_failed_dist)
            replacement_dist.rename(dist_dir)

    monkeypatch.setattr(
        cli,
        "ensure_directory_identity_unchanged",
        swap_dist_after_preflight,
    )

    with pytest.raises(
        click.ClickException,
        match=(
            "Failed to clean failed dist directory before restore: "
            "Refusing to clean dist directory: path changed"
        ),
    ):
        rollback_dist_replacement(
            isolated_filesystem,
            None,
            None,
            None,
            None,
            replacement_identity,
        )

    assert (saved_failed_dist / "manifest.json").read_text() == "failed"
    assert (dist_dir / "manifest.json").read_text() == "replacement"


@pytest.mark.cli
@patch("superset_extensions_cli.cli.validate_npm")
@patch("superset_extensions_cli.cli.init_frontend_deps")
@patch("superset_extensions_cli.cli.run_frontend_build")
def test_build_command_restores_existing_dist_when_remote_entry_missing(
    mock_run_frontend_build,
    mock_init_frontend_deps,
    mock_validate_npm,
    cli_runner,
    isolated_filesystem,
    extension_with_build_structure,
):
    """Test full build restores previous dist when frontend dist lacks remoteEntry."""
    mock_run_frontend_build.return_value = Mock(returncode=0)
    extension_with_build_structure(isolated_filesystem, include_backend=False)
    frontend_dist = isolated_filesystem / "frontend" / "dist"
    frontend_dist.mkdir()
    (frontend_dist / "main.js").write_text("main content")
    previous_dist = isolated_filesystem / "dist"
    previous_dist.mkdir()
    (previous_dist / "manifest.json").write_text("previous")

    result = cli_runner.invoke(app, ["build"])

    assert result.exit_code == 1
    assert "No remote entry file found" in result.output
    assert (previous_dist / "manifest.json").read_text() == "previous"
    assert list(isolated_filesystem.glob(".dist-backup.*.tmp")) == []


@pytest.mark.cli
@patch("superset_extensions_cli.cli.validate_npm")
def test_build_command_rejects_changed_backend_before_metadata_read(
    mock_validate_npm,
    cli_runner,
    isolated_filesystem,
    extension_with_build_structure,
    monkeypatch,
):
    """Test build refuses a changed backend directory before metadata reads."""
    extension_with_build_structure(isolated_filesystem, include_frontend=False)
    backend_dir = isolated_filesystem / "backend"
    saved_backend_dir = isolated_filesystem / "saved-backend"
    replacement_backend_dir = isolated_filesystem / "replacement-backend"
    replacement_backend_dir.mkdir()
    (replacement_backend_dir / "pyproject.toml").write_text(
        """[project]
name = "replacement"
version = "9.9.9"

[tool.apache_superset_extensions.build]
include = ["**/*.py"]
exclude = []
"""
    )

    from superset_extensions_cli import cli

    original_start_dist_replacement = cli.start_dist_replacement

    def swap_backend_after_source_decision(cwd):
        result = original_start_dist_replacement(cwd)
        backend_dir.rename(saved_backend_dir)
        replacement_backend_dir.rename(backend_dir)
        return result

    monkeypatch.setattr(
        "superset_extensions_cli.cli.start_dist_replacement",
        swap_backend_after_source_decision,
    )

    result = cli_runner.invoke(app, ["build"])

    assert result.exit_code == 1
    assert "backend path changed before build" in result.output
    assert not (isolated_filesystem / "dist" / "backend").exists()
    assert (backend_dir / "pyproject.toml").read_text().find("replacement") != -1


# Clean Dist Tests
@pytest.mark.unit
def test_clean_dist_removes_existing_dist_directory(isolated_filesystem):
    """Test clean_dist removes existing dist directory and recreates it."""
    # Create dist directory with some content
    dist_dir = isolated_filesystem / "dist"
    dist_dir.mkdir()
    (dist_dir / "some_file.txt").write_text("test content")
    (dist_dir / "subdir").mkdir()

    clean_dist(isolated_filesystem)

    # Should exist but be empty
    assert_directory_exists(dist_dir)
    assert list(dist_dir.iterdir()) == []


@pytest.mark.unit
def test_clean_dist_creates_dist_directory_if_missing(isolated_filesystem):
    """Test clean_dist creates dist directory when it doesn't exist."""
    dist_dir = isolated_filesystem / "dist"
    assert not dist_dir.exists()

    clean_dist(isolated_filesystem)

    assert_directory_exists(dist_dir)


@pytest.mark.unit
def test_start_dist_replacement_restores_dist_when_replacement_create_fails(
    isolated_filesystem, monkeypatch
):
    """Test dist replacement setup restores old dist if new dist creation fails."""
    dist_dir = isolated_filesystem / "dist"
    dist_dir.mkdir()
    (dist_dir / "manifest.json").write_text("previous")

    def fail_replacement_dist(path, label):
        if path == dist_dir and not path.exists():
            raise click.ClickException("cannot create replacement dist")
        ensure_output_directory(path, label)

    monkeypatch.setattr(
        "superset_extensions_cli.cli.ensure_output_directory",
        fail_replacement_dist,
    )

    with pytest.raises(
        click.ClickException,
        match="cannot create replacement dist",
    ):
        start_dist_replacement(isolated_filesystem)

    assert (dist_dir / "manifest.json").read_text() == "previous"
    assert list(isolated_filesystem.glob(".dist-backup.*.tmp")) == []


@pytest.mark.unit
def test_start_dist_replacement_rejects_changed_restored_dist(
    isolated_filesystem,
    monkeypatch,
):
    """Test dist replacement setup verifies restored dist after create failure."""
    dist_dir = isolated_filesystem / "dist"
    dist_dir.mkdir()
    (dist_dir / "manifest.json").write_text("previous")
    replacement_dist = isolated_filesystem / "replacement-dist"
    replacement_dist.mkdir()
    (replacement_dist / "manifest.json").write_text("replacement")
    saved_restored = isolated_filesystem / "saved-restored-dist"
    original_ensure_output_directory = ensure_output_directory
    original_replace = Path.replace

    def fail_replacement_dist(path, label):
        if path == dist_dir and not path.exists():
            raise click.ClickException("cannot create replacement dist")
        original_ensure_output_directory(path, label)

    def swap_restored_dist(path, target):
        result = original_replace(path, target)
        if target == dist_dir and path.parent.name.startswith(".dist-backup."):
            dist_dir.rename(saved_restored)
            replacement_dist.rename(dist_dir)
        return result

    monkeypatch.setattr(
        "superset_extensions_cli.cli.ensure_output_directory",
        fail_replacement_dist,
    )
    monkeypatch.setattr(Path, "replace", swap_restored_dist)

    with pytest.raises(
        click.ClickException,
        match=(
            "cannot create replacement dist; also failed to restore previous "
            "dist directory: restored backup path changed"
        ),
    ):
        start_dist_replacement(isolated_filesystem)

    assert (saved_restored / "manifest.json").read_text() == "previous"
    assert (dist_dir / "manifest.json").read_text() == "replacement"
    assert list(isolated_filesystem.glob(".dist-backup.*.tmp"))


@pytest.mark.unit
def test_start_dist_replacement_rejects_changed_dist_before_backup_move(
    isolated_filesystem,
    monkeypatch,
):
    """Test dist replacement refuses a dist path changed before backup move."""
    dist_dir = isolated_filesystem / "dist"
    dist_dir.mkdir()
    (dist_dir / "manifest.json").write_text("previous")
    saved_dist = isolated_filesystem / "saved-dist"
    replacement_dist = isolated_filesystem / "replacement-dist"
    replacement_dist.mkdir()
    (replacement_dist / "manifest.json").write_text("replacement")

    from superset_extensions_cli import cli

    original_create_temporary_output_directory = cli.create_temporary_output_directory

    def swap_dist_after_backup_root_creation(parent, prefix, label):
        backup_root = original_create_temporary_output_directory(parent, prefix, label)
        if parent == isolated_filesystem and prefix.startswith(".dist-backup."):
            dist_dir.rename(saved_dist)
            replacement_dist.rename(dist_dir)
        return backup_root

    monkeypatch.setattr(
        cli,
        "create_temporary_output_directory",
        swap_dist_after_backup_root_creation,
    )

    with pytest.raises(
        click.ClickException,
        match="Failed to back up dist directory: path changed",
    ):
        start_dist_replacement(isolated_filesystem)

    assert (saved_dist / "manifest.json").read_text() == "previous"
    assert (dist_dir / "manifest.json").read_text() == "replacement"
    assert list(isolated_filesystem.glob(".dist-backup.*.tmp")) == []


@pytest.mark.unit
def test_start_dist_replacement_rejects_swapped_dist_backup(
    isolated_filesystem,
    monkeypatch,
):
    """Test dist replacement setup aborts if the backed-up dist path changes."""
    dist_dir = isolated_filesystem / "dist"
    dist_dir.mkdir()
    (dist_dir / "manifest.json").write_text("previous")
    replacement_dir = isolated_filesystem / "replacement-dist"
    replacement_dir.mkdir()
    (replacement_dir / "manifest.json").write_text("replacement")
    saved_original = isolated_filesystem / "saved-original-dist"
    original_replace = Path.replace

    def replace_dist_with_replacement(path, target):
        if (
            path == dist_dir
            and target.name == "dist"
            and target.parent.name.startswith(".dist-backup.")
        ):
            original_replace(dist_dir, saved_original)
            original_replace(replacement_dir, dist_dir)
        return original_replace(path, target)

    monkeypatch.setattr(Path, "replace", replace_dist_with_replacement)

    with pytest.raises(
        click.ClickException,
        match="Failed to back up dist directory: path changed",
    ):
        start_dist_replacement(isolated_filesystem)

    assert (saved_original / "manifest.json").read_text() == "previous"
    assert not dist_dir.exists()
    assert not replacement_dir.exists()
    assert list(isolated_filesystem.glob(".dist-backup.*.tmp")) == []


@pytest.mark.unit
def test_cleanup_dist_replacement_backup_rejects_changed_backup_root(
    isolated_filesystem,
):
    """Test full-build backup cleanup refuses a changed backup root."""
    backup_root = isolated_filesystem / ".dist-backup.test.tmp"
    backup_root.mkdir()
    (backup_root / "dist").mkdir()
    (backup_root / "dist" / "manifest.json").write_text("previous")
    backup_root_identity = get_directory_path_identity(backup_root)
    assert backup_root_identity is not None
    saved_backup_root = isolated_filesystem / "saved-dist-backup"
    replacement_backup_root = isolated_filesystem / "replacement-dist-backup"
    replacement_backup_root.mkdir()
    (replacement_backup_root / "replacement.txt").write_text("replacement")

    backup_root.rename(saved_backup_root)
    replacement_backup_root.rename(backup_root)

    cleanup_dist_replacement_backup(backup_root, backup_root_identity)

    assert_file_exists(backup_root / "replacement.txt")
    assert_file_exists(saved_backup_root / "dist" / "manifest.json")


@pytest.mark.unit
def test_clean_dist_rejects_symlinked_dist_directory(isolated_filesystem):
    """Test clean_dist refuses a symlinked dist path."""
    outside_dir = isolated_filesystem / "outside"
    outside_dir.mkdir()
    (outside_dir / "artifact.txt").write_text("keep")
    (isolated_filesystem / "dist").symlink_to(outside_dir)

    with pytest.raises(click.ClickException, match="path is a symlink"):
        clean_dist(isolated_filesystem)

    assert_file_exists(outside_dir / "artifact.txt")


@pytest.mark.unit
def test_clean_dist_rejects_dist_file(isolated_filesystem):
    """Test clean_dist refuses a dist path that is not a directory."""
    (isolated_filesystem / "dist").write_text("not a directory")

    with pytest.raises(click.ClickException, match="not a directory"):
        clean_dist(isolated_filesystem)


@pytest.mark.unit
def test_create_temporary_output_directory_rejects_symlinked_parent(
    isolated_filesystem,
):
    """Test temporary output creation refuses symlinked parent directories."""
    outside_dir = isolated_filesystem / "outside"
    outside_dir.mkdir()
    output_link = isolated_filesystem / "dist"
    output_link.symlink_to(outside_dir)

    with pytest.raises(
        click.ClickException,
        match="Refusing to write parent for temporary frontend output directory: path is a symlink",
    ):
        create_temporary_output_directory(
            output_link,
            ".frontend.",
            "temporary frontend output directory",
        )

    assert list(outside_dir.iterdir()) == []


@pytest.mark.unit
def test_create_temporary_output_directory_rejects_non_directory_parent(
    isolated_filesystem,
):
    """Test temporary output creation refuses file parent paths."""
    output_parent = isolated_filesystem / "dist"
    output_parent.write_text("not a directory")

    with pytest.raises(
        click.ClickException,
        match="Refusing to write parent for temporary frontend output directory: path exists but is not a directory",
    ):
        create_temporary_output_directory(
            output_parent,
            ".frontend.",
            "temporary frontend output directory",
        )

    assert output_parent.read_text() == "not a directory"


@pytest.mark.unit
def test_create_temporary_output_directory_rejects_changed_parent(
    isolated_filesystem,
    monkeypatch,
):
    """Test temporary output creation refuses a changed parent directory."""
    output_parent = isolated_filesystem / "dist"
    output_parent.mkdir()
    saved_parent = isolated_filesystem / "saved-dist"
    replacement_parent = isolated_filesystem / "replacement-dist"
    replacement_parent.mkdir()

    from superset_extensions_cli import cli

    original_mkdtemp = cli.tempfile.mkdtemp

    def swap_parent_before_mkdtemp(*args, **kwargs):
        if kwargs.get("dir") == output_parent:
            output_parent.rename(saved_parent)
            replacement_parent.rename(output_parent)
        return original_mkdtemp(*args, **kwargs)

    monkeypatch.setattr(cli.tempfile, "mkdtemp", swap_parent_before_mkdtemp)

    with pytest.raises(
        click.ClickException,
        match="Refusing to create temporary frontend output directory: parent path changed",
    ):
        create_temporary_output_directory(
            output_parent,
            ".frontend.",
            "temporary frontend output directory",
        )

    assert saved_parent.is_dir()
    assert output_parent.is_dir()
    assert list(output_parent.iterdir()) == []


@pytest.mark.unit
def test_create_temporary_output_directory_rejects_changed_temp_cleanup_path(
    isolated_filesystem,
    monkeypatch,
):
    """Test temporary cleanup refuses a temp path changed after creation."""
    output_parent = isolated_filesystem / "dist"
    output_parent.mkdir()
    saved_parent = isolated_filesystem / "saved-dist"
    replacement_parent = isolated_filesystem / "replacement-dist"
    replacement_parent.mkdir()
    saved_temp = isolated_filesystem / "saved-temp"
    replacement_temp = isolated_filesystem / "replacement-temp"
    replacement_temp.mkdir()
    (replacement_temp / "replacement.txt").write_text("replacement")

    from superset_extensions_cli import cli

    original_get_directory_path_identity = cli.get_directory_path_identity
    temp_path: Path | None = None

    def swap_temp_before_parent_recheck(path):
        nonlocal temp_path
        identity = original_get_directory_path_identity(path)
        if (
            path.parent == output_parent
            and path.name.startswith(".frontend.")
            and temp_path is None
        ):
            temp_path = path
            path.rename(saved_temp)
            output_parent.rename(saved_parent)
            replacement_parent.rename(output_parent)
            replacement_temp.rename(path)
        return identity

    monkeypatch.setattr(
        cli,
        "get_directory_path_identity",
        swap_temp_before_parent_recheck,
    )

    with pytest.raises(
        click.ClickException,
        match="Refusing to create temporary frontend output directory: parent path changed",
    ):
        create_temporary_output_directory(
            output_parent,
            ".frontend.",
            "temporary frontend output directory",
        )

    assert temp_path is not None
    assert_file_exists(temp_path / "replacement.txt")
    assert saved_temp.exists()


@pytest.mark.unit
def test_ensure_output_directory_rejects_symlinked_parent(isolated_filesystem):
    """Test output directory creation refuses symlinked parent directories."""
    outside_dir = isolated_filesystem / "outside"
    outside_dir.mkdir()
    output_link = isolated_filesystem / "dist"
    output_link.symlink_to(outside_dir)

    with pytest.raises(
        click.ClickException,
        match="Refusing to write dist/frontend directory: parent directory is a symlink",
    ):
        ensure_output_directory(output_link / "frontend", "dist/frontend directory")

    assert not (outside_dir / "frontend").exists()


@pytest.mark.unit
def test_ensure_output_directory_rejects_broken_symlinked_parent(
    isolated_filesystem,
):
    """Test output directory creation refuses broken symlink parent directories."""
    output_link = isolated_filesystem / "dist"
    output_link.symlink_to(isolated_filesystem / "missing-dist")

    with pytest.raises(
        click.ClickException,
        match="Refusing to write dist/frontend directory: parent directory is a symlink",
    ):
        ensure_output_directory(output_link / "frontend", "dist/frontend directory")

    assert output_link.is_symlink()
    assert not (isolated_filesystem / "missing-dist").exists()


@pytest.mark.unit
def test_ensure_output_directory_rejects_non_directory_parent(isolated_filesystem):
    """Test output directory creation refuses file parent paths."""
    output_parent = isolated_filesystem / "dist"
    output_parent.write_text("not a directory")

    with pytest.raises(
        click.ClickException,
        match="Refusing to write dist/frontend directory: parent exists but is not a directory",
    ):
        ensure_output_directory(output_parent / "frontend", "dist/frontend directory")

    assert output_parent.read_text() == "not a directory"


@pytest.mark.unit
def test_ensure_output_directory_rejects_changed_parent(
    isolated_filesystem,
    monkeypatch,
):
    """Test output directory creation refuses a changed parent directory."""
    output_parent = isolated_filesystem / "dist"
    output_parent.mkdir()
    output_path = output_parent / "frontend"
    saved_parent = isolated_filesystem / "saved-dist"
    replacement_parent = isolated_filesystem / "replacement-dist"
    replacement_parent.mkdir()
    original_mkdir = Path.mkdir
    swapped = False

    def swap_parent_before_mkdir(path, *args, **kwargs):
        nonlocal swapped
        if path == output_path and not swapped:
            output_parent.rename(saved_parent)
            replacement_parent.rename(output_parent)
            swapped = True
        return original_mkdir(path, *args, **kwargs)

    monkeypatch.setattr(Path, "mkdir", swap_parent_before_mkdir)

    with pytest.raises(
        click.ClickException,
        match="Refusing to create dist/frontend directory: parent path changed",
    ):
        ensure_output_directory(output_path, "dist/frontend directory")

    assert saved_parent.is_dir()
    assert output_path.is_dir()


@pytest.mark.unit
def test_validate_output_file_rejects_symlinked_parent(isolated_filesystem):
    """Test output file validation refuses symlinked parent directories."""
    outside_dir = isolated_filesystem / "outside"
    outside_dir.mkdir()
    output_dir = isolated_filesystem / "dist"
    output_dir.symlink_to(outside_dir)

    with pytest.raises(
        click.ClickException,
        match="Refusing to write dist/manifest.json: parent directory is a symlink",
    ):
        validate_output_file(output_dir / "manifest.json", "dist/manifest.json")

    assert not (outside_dir / "manifest.json").exists()


@pytest.mark.unit
def test_validate_output_file_rejects_symlinked_ancestor(isolated_filesystem):
    """Test output file validation refuses symlinked ancestor directories."""
    outside_dir = isolated_filesystem / "outside"
    outside_nested = outside_dir / "nested"
    outside_nested.mkdir(parents=True)
    output_dir = isolated_filesystem / "dist"
    output_dir.symlink_to(outside_dir)

    with pytest.raises(
        click.ClickException,
        match="Refusing to write nested manifest: parent directory is a symlink",
    ):
        validate_output_file(
            output_dir / "nested" / "manifest.json",
            "nested manifest",
        )

    assert not (outside_nested / "manifest.json").exists()


@pytest.mark.unit
def test_validate_output_file_rejects_non_directory_parent(isolated_filesystem):
    """Test output file validation refuses file parent paths."""
    output_parent = isolated_filesystem / "dist"
    output_parent.write_text("not a directory")

    with pytest.raises(
        click.ClickException,
        match="Refusing to write dist/manifest.json: parent exists but is not a directory",
    ):
        validate_output_file(output_parent / "manifest.json", "dist/manifest.json")

    assert output_parent.read_text() == "not a directory"


@pytest.mark.unit
def test_validate_output_file_rejects_non_directory_ancestor(isolated_filesystem):
    """Test output file validation refuses nested paths below file ancestors."""
    output_parent = isolated_filesystem / "dist"
    output_parent.write_text("not a directory")

    with pytest.raises(
        click.ClickException,
        match="Refusing to write nested manifest: parent exists but is not a directory",
    ):
        validate_output_file(
            output_parent / "nested" / "manifest.json",
            "nested manifest",
        )

    assert output_parent.read_text() == "not a directory"


@pytest.mark.unit
def test_publish_output_file_revalidates_target(isolated_filesystem):
    """Test staged file publishing refuses a symlinked final target."""
    staged_file = isolated_filesystem / ".bundle.tmp"
    staged_file.write_text("new bundle")
    outside_file = isolated_filesystem / "outside.supx"
    outside_file.write_text("outside bundle")
    output_path = isolated_filesystem / "bundle.supx"
    output_path.symlink_to(outside_file)

    with pytest.raises(
        click.ClickException,
        match="Refusing to write bundle: path is a symlink",
    ):
        publish_output_file(staged_file, output_path, "bundle")

    assert outside_file.read_text() == "outside bundle"
    assert staged_file.read_text() == "new bundle"


@pytest.mark.unit
def test_publish_output_file_rejects_symlinked_staged_file(isolated_filesystem):
    """Test staged file publishing refuses a symlinked staged file."""
    staged_target = isolated_filesystem / "outside.tmp"
    staged_target.write_text("outside")
    staged_link = isolated_filesystem / ".bundle.tmp"
    staged_link.symlink_to(staged_target)
    output_path = isolated_filesystem / "bundle.supx"

    with pytest.raises(
        click.ClickException,
        match="Refusing to publish bundle: staged path is a symlink",
    ):
        publish_output_file(staged_link, output_path, "bundle")

    assert not output_path.exists()
    assert staged_target.read_text() == "outside"


@pytest.mark.unit
def test_publish_output_file_rejects_non_file_staged_path(isolated_filesystem):
    """Test staged file publishing refuses a staged directory."""
    staged_dir = isolated_filesystem / ".bundle.tmp"
    staged_dir.mkdir()
    output_path = isolated_filesystem / "bundle.supx"

    with pytest.raises(
        click.ClickException,
        match="Refusing to publish bundle: staged path is not a file",
    ):
        publish_output_file(staged_dir, output_path, "bundle")

    assert not output_path.exists()
    assert staged_dir.is_dir()


@pytest.mark.unit
def test_publish_output_file_rejects_changed_target_parent(
    isolated_filesystem,
    monkeypatch,
):
    """Test staged file publishing refuses a changed target parent."""
    staged_file = isolated_filesystem / ".bundle.tmp"
    staged_file.write_text("new bundle")
    output_dir = isolated_filesystem / "output"
    output_dir.mkdir()
    output_path = output_dir / "bundle.supx"
    saved_output_dir = isolated_filesystem / "saved-output"
    replacement_output_dir = isolated_filesystem / "replacement-output"
    replacement_output_dir.mkdir()

    original_get_directory_path_identity = cli.get_directory_path_identity
    parent_identity_reads = 0

    def swap_target_parent_before_publish(path):
        nonlocal parent_identity_reads
        if path == output_dir:
            parent_identity_reads += 1
            if parent_identity_reads == 2:
                output_dir.rename(saved_output_dir)
                replacement_output_dir.rename(output_dir)
        return original_get_directory_path_identity(path)

    monkeypatch.setattr(
        cli,
        "get_directory_path_identity",
        swap_target_parent_before_publish,
    )

    with pytest.raises(
        click.ClickException,
        match="Refusing to publish bundle: target parent path changed",
    ):
        publish_output_file(staged_file, output_path, "bundle")

    assert staged_file.read_text() == "new bundle"
    assert saved_output_dir.is_dir()
    assert output_dir.is_dir()
    assert not output_path.exists()


@pytest.mark.unit
def test_publish_output_file_restores_existing_target_when_staged_file_changes(
    isolated_filesystem,
    monkeypatch,
):
    """Test staged file publishing restores an old target after a staged-file swap."""
    staged_file = isolated_filesystem / ".bundle.tmp"
    staged_file.write_text("new bundle")
    output_path = isolated_filesystem / "bundle.supx"
    output_path.write_text("original bundle")
    replacement_file = isolated_filesystem / "replacement.supx"
    replacement_file.write_text("replacement bundle")
    original_replace = Path.replace

    def replace_staged_with_replacement(path, target):
        if path == staged_file and target == output_path:
            staged_file.unlink()
            replacement_file.replace(staged_file)
        return original_replace(path, target)

    monkeypatch.setattr(Path, "replace", replace_staged_with_replacement)

    with pytest.raises(
        click.ClickException,
        match="staged path changed during publish",
    ):
        publish_output_file(staged_file, output_path, "bundle")

    assert output_path.read_text() == "original bundle"
    assert not replacement_file.exists()
    assert list(isolated_filesystem.glob(".bundle.supx-backup.*.tmp")) == []


@pytest.mark.unit
def test_publish_output_file_rejects_changed_target_during_backup(
    isolated_filesystem,
    monkeypatch,
):
    """Test staged file publishing refuses a changed backup source."""
    staged_file = isolated_filesystem / ".bundle.tmp"
    staged_file.write_text("new bundle")
    output_path = isolated_filesystem / "bundle.supx"
    output_path.write_text("original bundle")
    replacement_file = isolated_filesystem / "replacement.supx"
    replacement_file.write_text("replacement bundle")

    from superset_extensions_cli import cli

    original_copy_output_file = cli.copy_output_file

    def swap_target_before_copy(source, target, label):
        if source == output_path:
            output_path.unlink()
            replacement_file.replace(output_path)
        original_copy_output_file(source, target, label)

    monkeypatch.setattr(cli, "copy_output_file", swap_target_before_copy)

    with pytest.raises(
        click.ClickException,
        match="Failed to back up bundle: path changed",
    ):
        publish_output_file(staged_file, output_path, "bundle")

    assert staged_file.read_text() == "new bundle"
    assert output_path.read_text() == "replacement bundle"
    assert list(isolated_filesystem.glob(".bundle.supx-backup.*.tmp")) == []


@pytest.mark.unit
def test_publish_output_file_rejects_changed_target_before_backup_copy(
    isolated_filesystem,
    monkeypatch,
):
    """Test staged file publishing refuses a changed target before backup copy."""
    staged_file = isolated_filesystem / ".bundle.tmp"
    staged_file.write_text("new bundle")
    output_path = isolated_filesystem / "bundle.supx"
    output_path.write_text("original bundle")
    replacement_file = isolated_filesystem / "replacement.supx"
    replacement_file.write_text("replacement bundle")
    saved_output = isolated_filesystem / "saved-bundle.supx"

    from superset_extensions_cli import cli

    original_create_temporary_output_directory = cli.create_temporary_output_directory

    def swap_target_after_backup_root_creation(parent, prefix, label):
        backup_root = original_create_temporary_output_directory(parent, prefix, label)
        if parent == output_path.parent and prefix.startswith(".bundle.supx-backup."):
            output_path.rename(saved_output)
            replacement_file.replace(output_path)
        return backup_root

    monkeypatch.setattr(
        cli,
        "create_temporary_output_directory",
        swap_target_after_backup_root_creation,
    )

    with pytest.raises(
        click.ClickException,
        match="Failed to back up bundle: path changed",
    ):
        publish_output_file(staged_file, output_path, "bundle")

    assert staged_file.read_text() == "new bundle"
    assert saved_output.read_text() == "original bundle"
    assert output_path.read_text() == "replacement bundle"
    assert list(isolated_filesystem.glob(".bundle.supx-backup.*.tmp")) == []


@pytest.mark.unit
def test_publish_output_file_rejects_changed_backup_during_rollback(
    isolated_filesystem,
    monkeypatch,
):
    """Test staged file publishing refuses to restore a changed backup."""
    staged_file = isolated_filesystem / ".bundle.tmp"
    staged_file.write_text("new bundle")
    output_path = isolated_filesystem / "bundle.supx"
    output_path.write_text("original bundle")
    replacement_staged = isolated_filesystem / "replacement-staged.supx"
    replacement_staged.write_text("replacement staged")
    replacement_backup = isolated_filesystem / "replacement-backup.supx"
    replacement_backup.write_text("replacement backup")
    saved_backup = isolated_filesystem / "saved-backup.supx"
    original_replace = Path.replace

    def replace_staged_and_swap_backup(path, target):
        if path == staged_file and target == output_path:
            staged_file.unlink()
            replacement_staged.replace(staged_file)
        result = original_replace(path, target)
        if path == staged_file and target == output_path:
            backup_path = next(
                isolated_filesystem.glob(".bundle.supx-backup.*.tmp/bundle.supx")
            )
            backup_path.rename(saved_backup)
            replacement_backup.replace(backup_path)
        return result

    monkeypatch.setattr(Path, "replace", replace_staged_and_swap_backup)

    with pytest.raises(
        click.ClickException,
        match="also failed to restore previous bundle: backup path changed",
    ):
        publish_output_file(staged_file, output_path, "bundle")

    assert saved_backup.read_text() == "original bundle"
    assert not output_path.exists()
    assert list(isolated_filesystem.glob(".bundle.supx-backup.*.tmp"))


@pytest.mark.unit
def test_publish_output_file_rejects_changed_restored_target(
    isolated_filesystem,
    monkeypatch,
):
    """Test staged file publishing verifies the target after backup restore."""
    staged_file = isolated_filesystem / ".bundle.tmp"
    staged_file.write_text("new bundle")
    output_path = isolated_filesystem / "bundle.supx"
    output_path.write_text("original bundle")
    replacement_staged = isolated_filesystem / "replacement-staged.supx"
    replacement_staged.write_text("replacement staged")
    replacement_output = isolated_filesystem / "replacement-output.supx"
    replacement_output.write_text("replacement output")
    saved_restored = isolated_filesystem / "saved-restored.supx"
    original_replace = Path.replace

    def swap_staged_and_restored_target(path, target):
        if path == staged_file and target == output_path:
            staged_file.unlink()
            replacement_staged.replace(staged_file)
        result = original_replace(path, target)
        if target == output_path and path.parent.name.startswith(
            ".bundle.supx-backup."
        ):
            output_path.rename(saved_restored)
            replacement_output.replace(output_path)
        return result

    monkeypatch.setattr(Path, "replace", swap_staged_and_restored_target)

    with pytest.raises(
        click.ClickException,
        match="also failed to restore previous bundle: restored backup path changed",
    ):
        publish_output_file(staged_file, output_path, "bundle")

    assert saved_restored.read_text() == "original bundle"
    assert output_path.read_text() == "replacement output"
    assert list(isolated_filesystem.glob(".bundle.supx-backup.*.tmp"))


@pytest.mark.unit
def test_publish_output_file_rejects_changed_target_during_cleanup(
    isolated_filesystem,
    monkeypatch,
):
    """Test failed file publishing does not clean a swapped target."""
    staged_file = isolated_filesystem / ".bundle.tmp"
    staged_file.write_text("new bundle")
    output_path = isolated_filesystem / "bundle.supx"
    output_path.write_text("original bundle")
    failed_publish = isolated_filesystem / "failed-bundle.supx"
    replacement_output = isolated_filesystem / "replacement-bundle.supx"
    replacement_output.write_text("replacement bundle")

    from superset_extensions_cli import cli

    original_validate_output_file = cli.validate_output_file

    def swap_target_after_publish(path, label):
        if (
            path == output_path
            and not staged_file.exists()
            and not failed_publish.exists()
        ):
            output_path.rename(failed_publish)
            replacement_output.replace(output_path)
        original_validate_output_file(path, label)

    monkeypatch.setattr(cli, "validate_output_file", swap_target_after_publish)

    with pytest.raises(
        click.ClickException,
        match=(
            "also failed to clean failed bundle: Refusing to clean bundle: path changed"
        ),
    ):
        publish_output_file(staged_file, output_path, "bundle")

    assert output_path.read_text() == "replacement bundle"
    assert failed_publish.read_text() == "new bundle"
    assert list(isolated_filesystem.glob(".bundle.supx-backup.*.tmp"))


@pytest.mark.unit
def test_publish_output_file_rejects_changed_directory_target_during_cleanup(
    isolated_filesystem,
    monkeypatch,
):
    """Test failed file publishing does not clean a swapped directory target."""
    staged_file = isolated_filesystem / ".bundle.tmp"
    staged_file.write_text("new bundle")
    output_path = isolated_filesystem / "bundle.supx"
    failed_publish = isolated_filesystem / "failed-bundle.supx"
    failed_directory = isolated_filesystem / "failed-bundle-dir"
    failed_directory.mkdir()
    (failed_directory / "failed.txt").write_text("failed directory")
    replacement_directory = isolated_filesystem / "replacement-bundle-dir"
    replacement_directory.mkdir()
    (replacement_directory / "replacement.txt").write_text("replacement directory")
    saved_failed_directory = isolated_filesystem / "saved-failed-bundle-dir"

    from superset_extensions_cli import cli

    original_get_read_path_identity = cli.get_read_path_identity
    original_get_directory_path_identity = cli.get_directory_path_identity
    directory_swapped = False

    def replace_published_file_with_directory(path):
        if (
            path == output_path
            and not staged_file.exists()
            and not failed_publish.exists()
            and output_path.is_file()
        ):
            output_path.rename(failed_publish)
            failed_directory.rename(output_path)
        return original_get_read_path_identity(path)

    def swap_directory_after_failure_identity(path):
        nonlocal directory_swapped
        identity = original_get_directory_path_identity(path)
        if path == output_path and identity is not None and not directory_swapped:
            directory_swapped = True
            output_path.rename(saved_failed_directory)
            replacement_directory.rename(output_path)
        return identity

    monkeypatch.setattr(
        cli,
        "get_read_path_identity",
        replace_published_file_with_directory,
    )
    monkeypatch.setattr(
        cli,
        "get_directory_path_identity",
        swap_directory_after_failure_identity,
    )

    with pytest.raises(
        click.ClickException,
        match=(
            "also failed to clean failed bundle: Refusing to clean bundle: path changed"
        ),
    ):
        publish_output_file(staged_file, output_path, "bundle")

    assert failed_publish.read_text() == "new bundle"
    assert (saved_failed_directory / "failed.txt").read_text() == "failed directory"
    assert (output_path / "replacement.txt").read_text() == "replacement directory"


@pytest.mark.unit
def test_remove_output_file_rejects_changed_path_before_unlink(
    isolated_filesystem,
    monkeypatch,
):
    """Test file cleanup refuses a path changed after initial validation."""
    output_path = isolated_filesystem / "bundle.supx"
    output_path.write_text("failed bundle")
    saved_output = isolated_filesystem / "saved-bundle.supx"
    replacement_output = isolated_filesystem / "replacement-bundle.supx"
    replacement_output.write_text("replacement bundle")

    from superset_extensions_cli import cli

    expected_identity = cli.get_read_path_identity(output_path)
    assert expected_identity is not None
    original_get_read_path_identity = cli.get_read_path_identity
    calls = 0

    def swap_target_after_initial_check(path):
        nonlocal calls
        calls += 1
        if path == output_path and calls == 2:
            output_path.rename(saved_output)
            replacement_output.replace(output_path)
        return original_get_read_path_identity(path)

    monkeypatch.setattr(cli, "get_read_path_identity", swap_target_after_initial_check)

    with pytest.raises(
        click.ClickException,
        match="Refusing to clean bundle: path changed",
    ):
        remove_output_file(output_path, "bundle", expected_identity)

    assert saved_output.read_text() == "failed bundle"
    assert output_path.read_text() == "replacement bundle"


@pytest.mark.unit
def test_remove_output_file_rejects_changed_parent_before_unlink(
    isolated_filesystem,
    monkeypatch,
):
    """Test file cleanup refuses the same file moved under a new parent."""
    output_dir = isolated_filesystem / "output"
    output_dir.mkdir()
    output_path = output_dir / "bundle.supx"
    output_path.write_text("failed bundle")
    saved_output_dir = isolated_filesystem / "saved-output"
    replacement_output_dir = isolated_filesystem / "replacement-output"

    from superset_extensions_cli import cli

    expected_identity = cli.get_read_path_identity(output_path)
    expected_parent_identity = cli.get_directory_path_identity(output_dir)
    assert expected_identity is not None
    assert expected_parent_identity is not None
    original_get_read_path_identity = cli.get_read_path_identity
    calls = 0

    def move_file_under_replaced_parent(path):
        nonlocal calls
        calls += 1
        if path == output_path and calls == 2:
            output_dir.rename(saved_output_dir)
            replacement_output_dir.mkdir()
            (saved_output_dir / "bundle.supx").rename(
                replacement_output_dir / "bundle.supx"
            )
            replacement_output_dir.rename(output_dir)
        return original_get_read_path_identity(path)

    monkeypatch.setattr(cli, "get_read_path_identity", move_file_under_replaced_parent)

    with pytest.raises(
        click.ClickException,
        match="Refusing to clean bundle: path changed",
    ):
        remove_output_file(
            output_path,
            "bundle",
            expected_identity,
            expected_parent_identity=expected_parent_identity,
        )

    assert not (saved_output_dir / "bundle.supx").exists()
    assert output_path.read_text() == "failed bundle"


@pytest.mark.unit
def test_remove_output_file_rejects_changed_content_before_unlink(
    isolated_filesystem,
):
    """Test file cleanup refuses a file changed after identity capture."""
    output_path = isolated_filesystem / "bundle.supx"
    output_path.write_text("failed bundle")

    from superset_extensions_cli import cli

    expected_identity = cli.get_read_path_identity(output_path)
    assert expected_identity is not None
    output_path.write_text("replacement bundle")

    with pytest.raises(
        click.ClickException,
        match="Refusing to clean bundle: path changed",
    ):
        remove_output_file(output_path, "bundle", expected_identity)

    assert output_path.read_text() == "replacement bundle"


@pytest.mark.unit
def test_publish_output_file_rejects_changed_backup_cleanup_root(
    isolated_filesystem,
    monkeypatch,
):
    """Test backup cleanup refuses a changed temporary file backup root."""
    staged_file = isolated_filesystem / ".bundle.tmp"
    staged_file.write_text("new bundle")
    output_path = isolated_filesystem / "bundle.supx"
    output_path.write_text("original bundle")
    replacement_backup_root = isolated_filesystem / "replacement-backup-root"
    replacement_backup_root.mkdir()
    (replacement_backup_root / "replacement.txt").write_text("replacement")
    saved_backup_root = isolated_filesystem / "saved-backup-root"
    swapped_backup_root: Path | None = None
    original_replace = Path.replace

    def swap_backup_root_after_publish(path, target):
        nonlocal swapped_backup_root
        result = original_replace(path, target)
        if path == staged_file and target == output_path:
            backup_root = next(isolated_filesystem.glob(".bundle.supx-backup.*.tmp"))
            backup_root.rename(saved_backup_root)
            replacement_backup_root.rename(backup_root)
            swapped_backup_root = backup_root
        return result

    monkeypatch.setattr(Path, "replace", swap_backup_root_after_publish)

    publish_output_file(staged_file, output_path, "bundle")

    assert swapped_backup_root is not None
    assert output_path.read_text() == "new bundle"
    assert (swapped_backup_root / "replacement.txt").read_text() == "replacement"
    assert (saved_backup_root / "bundle.supx").read_text() == "original bundle"


@pytest.mark.unit
def test_publish_staged_output_directory_rejects_symlinked_staged_dir(
    isolated_filesystem,
):
    """Test staged directory publishing refuses a symlinked staged directory."""
    staged_target = isolated_filesystem / "outside-frontend"
    staged_target.mkdir()
    (staged_target / "asset.js").write_text("outside")
    staged_link = isolated_filesystem / ".frontend.tmp"
    staged_link.symlink_to(staged_target)
    output_path = isolated_filesystem / "frontend"

    with pytest.raises(
        click.ClickException,
        match="Refusing to publish dist/frontend directory: staged path is a symlink",
    ):
        publish_staged_output_directory(
            staged_link,
            output_path,
            "dist/frontend directory",
        )

    assert not output_path.exists()
    assert_file_exists(staged_target / "asset.js")


@pytest.mark.unit
def test_publish_staged_output_directory_rejects_non_directory_staged_path(
    isolated_filesystem,
):
    """Test staged directory publishing refuses a staged file."""
    staged_file = isolated_filesystem / ".frontend.tmp"
    staged_file.write_text("not a directory")
    output_path = isolated_filesystem / "frontend"

    with pytest.raises(
        click.ClickException,
        match="Refusing to publish dist/frontend directory: staged path is not a directory",
    ):
        publish_staged_output_directory(
            staged_file,
            output_path,
            "dist/frontend directory",
        )

    assert not output_path.exists()
    assert staged_file.read_text() == "not a directory"


@pytest.mark.unit
def test_publish_staged_output_directory_rejects_changed_target_parent(
    isolated_filesystem,
    monkeypatch,
):
    """Test staged directory publishing refuses a changed target parent."""
    staged_dir = isolated_filesystem / ".frontend.tmp"
    staged_dir.mkdir()
    (staged_dir / "new.js").write_text("new")
    output_dir = isolated_filesystem / "dist"
    output_dir.mkdir()
    output_path = output_dir / "frontend"
    saved_output_dir = isolated_filesystem / "saved-dist"
    replacement_output_dir = isolated_filesystem / "replacement-dist"
    replacement_output_dir.mkdir()

    original_get_directory_path_identity = cli.get_directory_path_identity
    parent_identity_reads = 0

    def swap_target_parent_before_publish(path):
        nonlocal parent_identity_reads
        if path == output_dir:
            parent_identity_reads += 1
            if parent_identity_reads == 2:
                output_dir.rename(saved_output_dir)
                replacement_output_dir.rename(output_dir)
        return original_get_directory_path_identity(path)

    monkeypatch.setattr(
        cli,
        "get_directory_path_identity",
        swap_target_parent_before_publish,
    )

    with pytest.raises(
        click.ClickException,
        match=(
            "Refusing to publish dist/frontend directory: target parent path changed"
        ),
    ):
        publish_staged_output_directory(
            staged_dir,
            output_path,
            "dist/frontend directory",
        )

    assert_file_exists(staged_dir / "new.js")
    assert saved_output_dir.is_dir()
    assert output_dir.is_dir()
    assert not output_path.exists()


@pytest.mark.unit
def test_publish_staged_output_directory_restores_existing_target_when_staged_dir_changes(
    isolated_filesystem,
    monkeypatch,
):
    """Test staged directory publishing restores an old target after a staged-dir swap."""
    staged_dir = isolated_filesystem / ".frontend.tmp"
    staged_dir.mkdir()
    (staged_dir / "new.js").write_text("new")
    output_path = isolated_filesystem / "frontend"
    output_path.mkdir()
    (output_path / "old.js").write_text("old")
    outside_dir = isolated_filesystem / "outside-frontend"
    outside_dir.mkdir()
    (outside_dir / "outside.js").write_text("outside")
    original_replace = Path.replace

    def replace_staged_with_symlink(path, target):
        if path == staged_dir and target == output_path:
            shutil.rmtree(staged_dir)
            staged_dir.symlink_to(outside_dir)
        return original_replace(path, target)

    monkeypatch.setattr(Path, "replace", replace_staged_with_symlink)

    with pytest.raises(
        click.ClickException,
        match="Refusing to write dist/frontend directory: path is a symlink",
    ):
        publish_staged_output_directory(
            staged_dir,
            output_path,
            "dist/frontend directory",
        )

    assert_file_exists(output_path / "old.js")
    assert not output_path.is_symlink()
    assert_file_exists(outside_dir / "outside.js")
    assert list(isolated_filesystem.glob(".frontend-backup.*.tmp")) == []


@pytest.mark.unit
def test_publish_staged_output_directory_rejects_changed_target_before_backup_move(
    isolated_filesystem,
    monkeypatch,
):
    """Test directory publishing refuses a target changed before backup move."""
    staged_dir = isolated_filesystem / ".frontend.tmp"
    staged_dir.mkdir()
    (staged_dir / "new.js").write_text("new")
    output_path = isolated_filesystem / "frontend"
    output_path.mkdir()
    (output_path / "old.js").write_text("old")
    saved_output = isolated_filesystem / "saved-frontend"
    replacement_output = isolated_filesystem / "replacement-frontend"
    replacement_output.mkdir()
    (replacement_output / "replacement.js").write_text("replacement")

    from superset_extensions_cli import cli

    original_create_temporary_output_directory = cli.create_temporary_output_directory

    def swap_target_after_backup_root_creation(parent, prefix, label):
        backup_root = original_create_temporary_output_directory(parent, prefix, label)
        if parent == output_path.parent and prefix.startswith(".frontend-backup."):
            output_path.rename(saved_output)
            replacement_output.rename(output_path)
        return backup_root

    monkeypatch.setattr(
        cli,
        "create_temporary_output_directory",
        swap_target_after_backup_root_creation,
    )

    with pytest.raises(
        click.ClickException,
        match="Failed to back up dist/frontend directory: path changed",
    ):
        publish_staged_output_directory(
            staged_dir,
            output_path,
            "dist/frontend directory",
        )

    assert_file_exists(saved_output / "old.js")
    assert_file_exists(output_path / "replacement.js")
    assert_file_exists(staged_dir / "new.js")
    assert list(isolated_filesystem.glob(".frontend-backup.*.tmp")) == []


@pytest.mark.unit
def test_publish_staged_output_directory_restores_existing_target_when_staged_dir_replaced(
    isolated_filesystem,
    monkeypatch,
):
    """Test staged directory publishing rejects a replacement staged directory."""
    staged_dir = isolated_filesystem / ".frontend.tmp"
    staged_dir.mkdir()
    (staged_dir / "new.js").write_text("new")
    output_path = isolated_filesystem / "frontend"
    output_path.mkdir()
    (output_path / "old.js").write_text("old")
    replacement_dir = isolated_filesystem / "replacement-frontend"
    replacement_dir.mkdir()
    (replacement_dir / "replacement.js").write_text("replacement")
    original_replace = Path.replace

    def replace_staged_with_replacement(path, target):
        if path == staged_dir and target == output_path:
            shutil.rmtree(staged_dir)
            original_replace(replacement_dir, staged_dir)
        return original_replace(path, target)

    monkeypatch.setattr(Path, "replace", replace_staged_with_replacement)

    with pytest.raises(
        click.ClickException,
        match="staged path changed during publish",
    ):
        publish_staged_output_directory(
            staged_dir,
            output_path,
            "dist/frontend directory",
        )

    assert_file_exists(output_path / "old.js")
    assert not (output_path / "replacement.js").exists()
    assert not replacement_dir.exists()
    assert list(isolated_filesystem.glob(".frontend-backup.*.tmp")) == []


@pytest.mark.unit
def test_publish_staged_output_directory_rejects_changed_backup_during_rollback(
    isolated_filesystem,
    monkeypatch,
):
    """Test staged directory publishing refuses to restore a changed backup."""
    staged_dir = isolated_filesystem / ".frontend.tmp"
    staged_dir.mkdir()
    (staged_dir / "new.js").write_text("new")
    output_path = isolated_filesystem / "frontend"
    output_path.mkdir()
    (output_path / "old.js").write_text("old")
    replacement_backup = isolated_filesystem / "replacement-backup"
    replacement_backup.mkdir()
    (replacement_backup / "replacement.js").write_text("replacement")
    saved_backup = isolated_filesystem / "saved-backup"
    original_replace = Path.replace

    def replace_staged_and_swap_backup(path, target):
        result = original_replace(path, target)
        if path == staged_dir and target == output_path:
            backup_path = next(
                isolated_filesystem.glob(".frontend-backup.*.tmp/frontend")
            )
            backup_path.rename(saved_backup)
            replacement_backup.rename(backup_path)
            shutil.rmtree(output_path)
            output_path.mkdir()
            (output_path / "changed.js").write_text("changed")
        return result

    monkeypatch.setattr(Path, "replace", replace_staged_and_swap_backup)

    with pytest.raises(
        click.ClickException,
        match=(
            "also failed to restore previous dist/frontend directory: "
            "backup path changed"
        ),
    ):
        publish_staged_output_directory(
            staged_dir,
            output_path,
            "dist/frontend directory",
        )

    assert_file_exists(saved_backup / "old.js")
    assert not output_path.exists()
    assert list(isolated_filesystem.glob(".frontend-backup.*.tmp"))


@pytest.mark.unit
def test_publish_staged_output_directory_rejects_changed_restored_target(
    isolated_filesystem,
    monkeypatch,
):
    """Test staged directory publishing verifies the target after backup restore."""
    staged_dir = isolated_filesystem / ".frontend.tmp"
    staged_dir.mkdir()
    (staged_dir / "new.js").write_text("new")
    output_path = isolated_filesystem / "frontend"
    output_path.mkdir()
    (output_path / "old.js").write_text("old")
    replacement_staged = isolated_filesystem / "replacement-staged"
    replacement_staged.mkdir()
    (replacement_staged / "replacement.js").write_text("replacement staged")
    replacement_output = isolated_filesystem / "replacement-output"
    replacement_output.mkdir()
    (replacement_output / "replacement.js").write_text("replacement output")
    saved_restored = isolated_filesystem / "saved-restored"
    original_replace = Path.replace

    def swap_staged_and_restored_target(path, target):
        if path == staged_dir and target == output_path:
            shutil.rmtree(staged_dir)
            replacement_staged.rename(staged_dir)
        result = original_replace(path, target)
        if target == output_path and path.parent.name.startswith(".frontend-backup."):
            output_path.rename(saved_restored)
            replacement_output.rename(output_path)
        return result

    monkeypatch.setattr(Path, "replace", swap_staged_and_restored_target)

    with pytest.raises(
        click.ClickException,
        match=(
            "also failed to restore previous dist/frontend directory: "
            "restored backup path changed"
        ),
    ):
        publish_staged_output_directory(
            staged_dir,
            output_path,
            "dist/frontend directory",
        )

    assert_file_exists(saved_restored / "old.js")
    assert_file_exists(output_path / "replacement.js")
    assert list(isolated_filesystem.glob(".frontend-backup.*.tmp"))


@pytest.mark.unit
def test_publish_staged_output_directory_rejects_changed_target_during_cleanup(
    isolated_filesystem,
    monkeypatch,
):
    """Test failed directory publishing does not clean a swapped target."""
    staged_dir = isolated_filesystem / ".frontend.tmp"
    staged_dir.mkdir()
    (staged_dir / "new.js").write_text("new")
    output_path = isolated_filesystem / "frontend"
    output_path.mkdir()
    (output_path / "old.js").write_text("old")
    failed_publish = isolated_filesystem / "failed-frontend"
    replacement_output = isolated_filesystem / "replacement-frontend"
    replacement_output.mkdir()
    (replacement_output / "replacement.js").write_text("replacement")

    from superset_extensions_cli import cli

    original_validate_output_directory = cli.validate_output_directory

    def swap_target_after_publish(path, label):
        if (
            path == output_path
            and not staged_dir.exists()
            and not failed_publish.exists()
        ):
            output_path.rename(failed_publish)
            replacement_output.rename(output_path)
        original_validate_output_directory(path, label)

    monkeypatch.setattr(cli, "validate_output_directory", swap_target_after_publish)

    with pytest.raises(
        click.ClickException,
        match=(
            "also failed to clean failed dist/frontend directory: "
            "Refusing to clean dist/frontend directory: path changed"
        ),
    ):
        publish_staged_output_directory(
            staged_dir,
            output_path,
            "dist/frontend directory",
        )

    assert_file_exists(output_path / "replacement.js")
    assert_file_exists(failed_publish / "new.js")
    assert list(isolated_filesystem.glob(".frontend-backup.*.tmp"))


@pytest.mark.unit
def test_publish_staged_output_directory_rejects_changed_target_content_during_cleanup(
    isolated_filesystem,
    monkeypatch,
):
    """Test failed directory publishing does not clean changed target contents."""
    staged_dir = isolated_filesystem / ".frontend.tmp"
    staged_dir.mkdir()
    (staged_dir / "new.js").write_text("new")
    output_path = isolated_filesystem / "frontend"
    output_path.mkdir()
    (output_path / "old.js").write_text("old")

    from superset_extensions_cli import cli

    original_validate_output_directory = cli.validate_output_directory

    def change_target_after_publish(path, label):
        if path == output_path and not staged_dir.exists():
            (output_path / "added.js").write_text("added")
        original_validate_output_directory(path, label)

    monkeypatch.setattr(cli, "validate_output_directory", change_target_after_publish)

    with pytest.raises(
        click.ClickException,
        match=(
            "also failed to clean failed dist/frontend directory: "
            "Refusing to clean dist/frontend directory: path changed"
        ),
    ):
        publish_staged_output_directory(
            staged_dir,
            output_path,
            "dist/frontend directory",
        )

    assert_file_exists(output_path / "new.js")
    assert_file_exists(output_path / "added.js")
    assert list(isolated_filesystem.glob(".frontend-backup.*.tmp"))


@pytest.mark.unit
def test_publish_staged_output_directory_rejects_file_target_during_cleanup(
    isolated_filesystem,
    monkeypatch,
):
    """Test failed directory publishing does not unlink a swapped file target."""
    staged_dir = isolated_filesystem / ".frontend.tmp"
    staged_dir.mkdir()
    (staged_dir / "new.js").write_text("new")
    output_path = isolated_filesystem / "frontend"
    output_path.mkdir()
    (output_path / "old.js").write_text("old")
    failed_publish = isolated_filesystem / "failed-frontend"

    from superset_extensions_cli import cli

    original_validate_output_directory = cli.validate_output_directory

    def swap_target_to_file_after_publish(path, label):
        if (
            path == output_path
            and not staged_dir.exists()
            and not failed_publish.exists()
        ):
            output_path.rename(failed_publish)
            output_path.write_text("replacement file")
        original_validate_output_directory(path, label)

    monkeypatch.setattr(
        cli, "validate_output_directory", swap_target_to_file_after_publish
    )

    with pytest.raises(
        click.ClickException,
        match=(
            "also failed to clean failed dist/frontend directory: "
            "Refusing to clean dist/frontend directory: path changed"
        ),
    ):
        publish_staged_output_directory(
            staged_dir,
            output_path,
            "dist/frontend directory",
        )

    assert output_path.read_text() == "replacement file"
    assert_file_exists(failed_publish / "new.js")
    assert list(isolated_filesystem.glob(".frontend-backup.*.tmp"))


@pytest.mark.unit
def test_publish_staged_output_directory_ignores_backup_cleanup_failure(
    isolated_filesystem, monkeypatch
):
    """Test successful staged directory publishing is not undone by backup cleanup."""
    staged_dir = isolated_filesystem / ".frontend.tmp"
    staged_dir.mkdir()
    (staged_dir / "new.js").write_text("new")
    output_path = isolated_filesystem / "frontend"
    output_path.mkdir()
    (output_path / "old.js").write_text("old")

    from superset_extensions_cli import cli

    original_remove_output_directory = cli.remove_output_directory

    def fail_backup_cleanup(path, label, expected_identity=None):
        if path.name.startswith(".frontend-backup."):
            raise click.ClickException("backup cleanup failed")
        original_remove_output_directory(path, label, expected_identity)

    monkeypatch.setattr(cli, "remove_output_directory", fail_backup_cleanup)

    publish_staged_output_directory(staged_dir, output_path, "dist/frontend directory")

    assert_file_exists(output_path / "new.js")
    assert not (output_path / "old.js").exists()
    assert list(isolated_filesystem.glob(".frontend-backup.*.tmp"))


@pytest.mark.unit
def test_publish_staged_output_directory_rejects_changed_backup_cleanup_root(
    isolated_filesystem,
    monkeypatch,
):
    """Test backup cleanup refuses a changed temporary backup root."""
    staged_dir = isolated_filesystem / ".frontend.tmp"
    staged_dir.mkdir()
    (staged_dir / "new.js").write_text("new")
    output_path = isolated_filesystem / "frontend"
    output_path.mkdir()
    (output_path / "old.js").write_text("old")
    replacement_backup_root = isolated_filesystem / "replacement-backup-root"
    replacement_backup_root.mkdir()
    (replacement_backup_root / "replacement.txt").write_text("replacement")
    saved_backup_root = isolated_filesystem / "saved-backup-root"
    swapped_backup_root: Path | None = None
    original_replace = Path.replace

    def swap_backup_root_after_publish(path, target):
        nonlocal swapped_backup_root
        result = original_replace(path, target)
        if path == staged_dir and target == output_path:
            backup_root = next(isolated_filesystem.glob(".frontend-backup.*.tmp"))
            backup_root.rename(saved_backup_root)
            replacement_backup_root.rename(backup_root)
            swapped_backup_root = backup_root
        return result

    monkeypatch.setattr(Path, "replace", swap_backup_root_after_publish)

    publish_staged_output_directory(staged_dir, output_path, "dist/frontend directory")

    assert swapped_backup_root is not None
    assert_file_exists(output_path / "new.js")
    assert_file_exists(swapped_backup_root / "replacement.txt")
    assert_file_exists(saved_backup_root / "frontend" / "old.js")


@pytest.mark.unit
def test_validate_output_file_parent_does_not_create_missing_parent(
    isolated_filesystem,
):
    """Test output parent validation does not create missing directories."""
    root = isolated_filesystem / "dist" / "backend"
    target = root / "src" / "test_org" / "module.py"

    validate_output_file_parent(target, root, "backend file src/test_org/module.py")

    assert not root.exists()
    assert not target.parent.exists()


@pytest.mark.unit
def test_validate_output_file_parent_rejects_broken_symlinked_root(
    isolated_filesystem,
):
    """Test output file parent validation refuses a broken symlinked root."""
    root = isolated_filesystem / "dist" / "backend"
    root.parent.mkdir()
    root.symlink_to(isolated_filesystem / "missing-backend-output")
    target = root / "src" / "test_org" / "module.py"

    with pytest.raises(
        click.ClickException,
        match="Refusing to write backend file .*parent directory is a symlink",
    ):
        validate_output_file_parent(target, root, "backend file src/test_org/module.py")

    assert root.is_symlink()
    assert not (isolated_filesystem / "missing-backend-output").exists()


@pytest.mark.unit
def test_ensure_output_file_parent_rejects_changed_root(
    isolated_filesystem,
    monkeypatch,
):
    """Test output file parent creation refuses a changed root directory."""
    root = isolated_filesystem / "dist" / "backend"
    root.mkdir(parents=True)
    target = root / "src" / "test_org" / "module.py"
    saved_root = isolated_filesystem / "saved-backend"
    replacement_root = isolated_filesystem / "replacement-backend"
    replacement_root.mkdir()
    original_mkdir = Path.mkdir
    swapped = False

    def swap_root_before_mkdir(path, *args, **kwargs):
        nonlocal swapped
        if path == target.parent and not swapped:
            root.rename(saved_root)
            replacement_root.rename(root)
            swapped = True
        return original_mkdir(path, *args, **kwargs)

    monkeypatch.setattr(Path, "mkdir", swap_root_before_mkdir)

    with pytest.raises(
        click.ClickException,
        match="Refusing to create parent for backend file .*parent path changed",
    ):
        ensure_output_file_parent(
            target,
            root,
            "backend file src/test_org/module.py",
        )

    assert saved_root.is_dir()
    assert target.parent.is_dir()


@pytest.mark.unit
def test_copy_output_file_rejects_source_changed_during_copy(
    isolated_filesystem,
    monkeypatch,
):
    """Test output file copy refuses a source changed during copy."""
    source_file = isolated_filesystem / "source.py"
    source_file.write_text("# original")
    replacement_file = isolated_filesystem / "replacement.py"
    replacement_file.write_text("# replacement")
    target_file = isolated_filesystem / "target.py"
    original_copy2 = shutil.copy2

    def swap_source_after_copy(source, target, *args, **kwargs):
        result = original_copy2(source, target, *args, **kwargs)
        if source == source_file:
            source_file.unlink()
            replacement_file.replace(source_file)
        return result

    monkeypatch.setattr(
        "superset_extensions_cli.cli.shutil.copy2", swap_source_after_copy
    )

    with pytest.raises(
        click.ClickException,
        match="Refusing to copy backend file module.py: source path changed during copy",
    ):
        copy_output_file(source_file, target_file, "backend file module.py")

    assert source_file.read_text() == "# replacement"
    assert target_file.read_text() == "# original"


@pytest.mark.unit
def test_copy_output_file_rejects_target_changed_during_copy(
    isolated_filesystem,
    monkeypatch,
):
    """Test output file copy refuses a target changed during copy."""
    source_file = isolated_filesystem / "source.py"
    source_file.write_text("# source")
    outside_file = isolated_filesystem / "outside.py"
    outside_file.write_text("# outside")
    target_file = isolated_filesystem / "target.py"
    original_copy2 = shutil.copy2

    def swap_target_after_copy(source, target, *args, **kwargs):
        result = original_copy2(source, target, *args, **kwargs)
        if target == target_file:
            target_file.unlink()
            target_file.symlink_to(outside_file)
        return result

    monkeypatch.setattr(
        "superset_extensions_cli.cli.shutil.copy2", swap_target_after_copy
    )

    with pytest.raises(
        click.ClickException,
        match="Refusing to copy backend file target.py: target path changed during copy",
    ):
        copy_output_file(source_file, target_file, "backend file target.py")

    assert target_file.is_symlink()
    assert outside_file.read_text() == "# outside"


@pytest.mark.unit
def test_copy_output_file_rejects_target_parent_changed_during_copy(
    isolated_filesystem,
    monkeypatch,
):
    """Test output file copy refuses a swapped target parent directory."""
    source_file = isolated_filesystem / "source.py"
    source_file.write_text("# source")
    target_parent = isolated_filesystem / "target-parent"
    target_parent.mkdir()
    target_file = target_parent / "target.py"
    saved_target_parent = isolated_filesystem / "saved-target-parent"
    replacement_parent = isolated_filesystem / "replacement-target-parent"
    replacement_parent.mkdir()
    original_copy2 = shutil.copy2

    def swap_target_parent_after_copy(source, target, *args, **kwargs):
        result = original_copy2(source, target, *args, **kwargs)
        if target == target_file:
            target_parent.rename(saved_target_parent)
            replacement_parent.rename(target_parent)
        return result

    monkeypatch.setattr(
        "superset_extensions_cli.cli.shutil.copy2",
        swap_target_parent_after_copy,
    )

    with pytest.raises(
        click.ClickException,
        match=(
            "Refusing to copy backend file target.py: "
            "target parent path changed during copy"
        ),
    ):
        copy_output_file(source_file, target_file, "backend file target.py")

    assert (saved_target_parent / "target.py").read_text() == "# source"
    assert target_parent.is_dir()
    assert not target_file.exists()


@pytest.mark.unit
def test_copy_output_file_rejects_target_content_changed_during_copy(
    isolated_filesystem,
    monkeypatch,
):
    """Test output file copy refuses target content changed at the same path."""
    source_file = isolated_filesystem / "source.py"
    source_file.write_text("# source")
    target_file = isolated_filesystem / "target.py"
    original_copy2 = shutil.copy2

    def change_target_after_copy(source, target, *args, **kwargs):
        result = original_copy2(source, target, *args, **kwargs)
        if target == target_file:
            target_file.write_text("# tampered")
        return result

    monkeypatch.setattr(
        "superset_extensions_cli.cli.shutil.copy2", change_target_after_copy
    )

    with pytest.raises(
        click.ClickException,
        match=(
            "Refusing to copy backend file target.py: "
            "target content changed during copy"
        ),
    ):
        copy_output_file(source_file, target_file, "backend file target.py")

    assert source_file.read_text() == "# source"
    assert target_file.read_text() == "# tampered"


@pytest.mark.unit
def test_copy_output_file_rejects_symlinked_target(isolated_filesystem):
    """Test output file copy refuses a symlinked target path."""
    source_file = isolated_filesystem / "source.py"
    source_file.write_text("# source")
    outside_file = isolated_filesystem / "outside.py"
    outside_file.write_text("# outside")
    target_link = isolated_filesystem / "target.py"
    target_link.symlink_to(outside_file)

    with pytest.raises(
        click.ClickException,
        match="Refusing to write backend file target.py: path is a symlink",
    ):
        copy_output_file(source_file, target_link, "backend file target.py")

    assert outside_file.read_text() == "# outside"


@pytest.mark.unit
def test_copy_output_file_rejects_symlinked_target_parent(isolated_filesystem):
    """Test output file copy refuses a target below a symlinked parent."""
    source_file = isolated_filesystem / "source.py"
    source_file.write_text("# source")
    outside_dir = isolated_filesystem / "outside"
    outside_dir.mkdir()
    target_parent_link = isolated_filesystem / "linked"
    target_parent_link.symlink_to(outside_dir)

    with pytest.raises(
        click.ClickException,
        match="Refusing to write backend file linked/target.py: parent directory is a symlink",
    ):
        copy_output_file(
            source_file,
            target_parent_link / "target.py",
            "backend file linked/target.py",
        )

    assert list(outside_dir.iterdir()) == []


# Frontend Dependencies Tests
@pytest.mark.unit
@patch("subprocess.run")
def test_init_frontend_deps_skips_when_node_modules_exists(
    mock_run, isolated_filesystem
):
    """Test init_frontend_deps skips npm ci when node_modules exists."""
    frontend_dir = isolated_filesystem / "frontend"
    frontend_dir.mkdir()
    (frontend_dir / "node_modules").mkdir()

    init_frontend_deps(frontend_dir)

    # Should not call subprocess.run for npm ci
    mock_run.assert_not_called()


@pytest.mark.unit
@patch("subprocess.run")
def test_init_frontend_deps_rejects_symlinked_node_modules(
    mock_run, isolated_filesystem
):
    """Test init_frontend_deps refuses symlinked node_modules directories."""
    frontend_dir = isolated_filesystem / "frontend"
    frontend_dir.mkdir()
    outside_node_modules = isolated_filesystem / "outside-node-modules"
    outside_node_modules.mkdir()
    (frontend_dir / "node_modules").symlink_to(outside_node_modules)

    with pytest.raises(click.ClickException, match="node_modules path is a symlink"):
        init_frontend_deps(frontend_dir)

    mock_run.assert_not_called()


@pytest.mark.unit
@patch("subprocess.run")
def test_init_frontend_deps_rejects_node_modules_file(mock_run, isolated_filesystem):
    """Test init_frontend_deps refuses non-directory node_modules paths."""
    frontend_dir = isolated_filesystem / "frontend"
    frontend_dir.mkdir()
    (frontend_dir / "node_modules").write_text("not a directory")

    with pytest.raises(click.ClickException, match="node_modules path exists"):
        init_frontend_deps(frontend_dir)

    mock_run.assert_not_called()


@pytest.mark.unit
@patch("subprocess.run")
def test_init_frontend_deps_rejects_symlinked_package_lock(
    mock_run, isolated_filesystem
):
    """Test init_frontend_deps refuses symlinked package lock files."""
    frontend_dir = isolated_filesystem / "frontend"
    frontend_dir.mkdir()
    outside_lock = isolated_filesystem / "outside-package-lock.json"
    outside_lock.write_text("{}")
    (frontend_dir / "package-lock.json").symlink_to(outside_lock)

    with pytest.raises(
        click.ClickException, match="package-lock.json path is a symlink"
    ):
        init_frontend_deps(frontend_dir)

    mock_run.assert_not_called()


@pytest.mark.unit
@patch("subprocess.run")
def test_init_frontend_deps_rejects_package_lock_directory(
    mock_run, isolated_filesystem
):
    """Test init_frontend_deps refuses non-file package lock paths."""
    frontend_dir = isolated_filesystem / "frontend"
    frontend_dir.mkdir()
    (frontend_dir / "package-lock.json").mkdir()

    with pytest.raises(click.ClickException, match="package-lock.json path exists"):
        init_frontend_deps(frontend_dir)

    mock_run.assert_not_called()


@pytest.mark.unit
@patch("subprocess.run")
@patch("superset_extensions_cli.cli.validate_npm")
def test_init_frontend_deps_runs_npm_i_when_missing(
    mock_validate_npm, mock_run, isolated_filesystem
):
    """Test init_frontend_deps runs npm ci when node_modules is missing."""
    frontend_dir = isolated_filesystem / "frontend"
    frontend_dir.mkdir()

    # Mock successful npm ci
    mock_run.return_value = Mock(returncode=0)

    init_frontend_deps(frontend_dir)

    # Should validate npm and run npm ci
    mock_validate_npm.assert_called_once()
    mock_run.assert_called_once_with(["npm", "i"], cwd=frontend_dir, text=True)


@pytest.mark.unit
@patch("subprocess.run")
@patch("superset_extensions_cli.cli.validate_npm")
def test_init_frontend_deps_uses_validated_npm_path(
    mock_validate_npm, mock_run, isolated_filesystem
):
    """Test dependency install uses the npm executable that validation resolved."""
    frontend_dir = isolated_filesystem / "frontend"
    frontend_dir.mkdir()
    npm_path = isolated_filesystem / "npm"
    npm_path.write_text("npm")
    npm_identity = cli.get_output_copy_source_identity(npm_path)
    assert npm_identity is not None
    mock_validate_npm.return_value = cli.ValidatedNpmExecutable(
        str(npm_path),
        npm_identity,
    )
    mock_run.return_value = Mock(returncode=0)

    init_frontend_deps(frontend_dir)

    mock_validate_npm.assert_called_once()
    mock_run.assert_called_once_with(
        [str(npm_path), "i"],
        cwd=frontend_dir,
        text=True,
    )


@pytest.mark.unit
@patch("subprocess.run")
@patch("superset_extensions_cli.cli.validate_npm")
def test_init_frontend_deps_rejects_changed_validated_npm_path(
    mock_validate_npm, mock_run, isolated_filesystem
):
    """Test dependency install refuses a changed validated npm executable."""
    frontend_dir = isolated_filesystem / "frontend"
    frontend_dir.mkdir()
    npm_path = isolated_filesystem / "npm"
    npm_path.write_text("npm")
    npm_identity = cli.get_output_copy_source_identity(npm_path)
    assert npm_identity is not None
    npm_path.write_text("changed npm")
    mock_validate_npm.return_value = cli.ValidatedNpmExecutable(
        str(npm_path),
        npm_identity,
    )

    with pytest.raises(
        click.ClickException,
        match="npm executable changed before launch",
    ):
        init_frontend_deps(frontend_dir)

    mock_run.assert_not_called()


@pytest.mark.unit
@patch("subprocess.run")
def test_init_frontend_deps_rejects_changed_frontend_before_install(
    mock_run,
    isolated_filesystem,
    monkeypatch,
):
    """Test dependency install refuses a changed frontend directory."""
    frontend_dir = isolated_filesystem / "frontend"
    frontend_dir.mkdir()
    saved_frontend = isolated_filesystem / "saved-frontend"
    replacement_frontend = isolated_filesystem / "replacement-frontend"
    replacement_frontend.mkdir()

    def swap_frontend_during_npm_validation():
        frontend_dir.rename(saved_frontend)
        replacement_frontend.rename(frontend_dir)

    monkeypatch.setattr(
        "superset_extensions_cli.cli.validate_npm",
        swap_frontend_during_npm_validation,
    )

    with pytest.raises(
        click.ClickException,
        match="frontend path changed before dependency install",
    ):
        init_frontend_deps(frontend_dir)

    mock_run.assert_not_called()
    assert saved_frontend.is_dir()
    assert frontend_dir.is_dir()


@pytest.mark.unit
@patch("subprocess.run")
def test_init_frontend_deps_rejects_frontend_content_change_before_install(
    mock_run,
    isolated_filesystem,
    monkeypatch,
):
    """Test dependency install refuses frontend content changes before launch."""
    frontend_dir = isolated_filesystem / "frontend"
    frontend_dir.mkdir()

    def add_frontend_entry_during_npm_validation():
        (frontend_dir / "unexpected.txt").write_text("unexpected")

    monkeypatch.setattr(
        "superset_extensions_cli.cli.validate_npm",
        add_frontend_entry_during_npm_validation,
    )

    with pytest.raises(
        click.ClickException,
        match="frontend path changed before dependency install",
    ):
        init_frontend_deps(frontend_dir)

    mock_run.assert_not_called()
    assert (frontend_dir / "unexpected.txt").read_text() == "unexpected"


@pytest.mark.unit
@patch("subprocess.run")
def test_init_frontend_deps_rejects_frontend_parent_change_before_install(
    mock_run,
    isolated_filesystem,
    monkeypatch,
):
    """Test dependency install refuses a frontend directory moved under a new parent."""
    project_dir = isolated_filesystem / "project"
    frontend_dir = project_dir / "frontend"
    frontend_dir.mkdir(parents=True)
    saved_project_dir = isolated_filesystem / "saved-project"
    replacement_project_dir = isolated_filesystem / "replacement-project"

    def move_frontend_under_replaced_parent():
        project_dir.rename(saved_project_dir)
        replacement_project_dir.mkdir()
        (saved_project_dir / "frontend").rename(replacement_project_dir / "frontend")
        replacement_project_dir.rename(project_dir)

    monkeypatch.setattr(
        "superset_extensions_cli.cli.validate_npm",
        move_frontend_under_replaced_parent,
    )

    with pytest.raises(
        click.ClickException,
        match="frontend path changed before dependency install",
    ):
        init_frontend_deps(frontend_dir)

    mock_run.assert_not_called()
    assert not (saved_project_dir / "frontend").exists()
    assert frontend_dir.is_dir()


@pytest.mark.unit
@patch("subprocess.run")
def test_init_frontend_deps_rejects_node_modules_symlink_before_install(
    mock_run,
    isolated_filesystem,
    monkeypatch,
):
    """Test dependency install rechecks node_modules before npm launch."""
    frontend_dir = isolated_filesystem / "frontend"
    frontend_dir.mkdir()
    outside_node_modules = isolated_filesystem / "outside-node-modules"
    outside_node_modules.mkdir()

    def create_node_modules_symlink_during_npm_validation():
        (frontend_dir / "node_modules").symlink_to(outside_node_modules)

    monkeypatch.setattr(
        "superset_extensions_cli.cli.validate_npm",
        create_node_modules_symlink_during_npm_validation,
    )

    with pytest.raises(click.ClickException, match="node_modules path is a symlink"):
        init_frontend_deps(frontend_dir)

    mock_run.assert_not_called()
    assert (frontend_dir / "node_modules").is_symlink()


@pytest.mark.unit
@patch("subprocess.run")
@patch("superset_extensions_cli.cli.validate_npm")
def test_init_frontend_deps_exits_on_npm_ci_failure(
    mock_validate_npm, mock_run, isolated_filesystem
):
    """Test init_frontend_deps exits when npm ci fails."""
    frontend_dir = isolated_filesystem / "frontend"
    frontend_dir.mkdir()

    # Mock failed npm ci
    mock_run.return_value = Mock(returncode=1)

    with pytest.raises(SystemExit) as exc_info:
        init_frontend_deps(frontend_dir)

    assert exc_info.value.code == 1


@pytest.mark.unit
@patch("subprocess.run")
@patch("superset_extensions_cli.cli.validate_npm")
def test_init_frontend_deps_exits_on_npm_launch_error(
    mock_validate_npm, mock_run, isolated_filesystem, capsys
):
    """Test init_frontend_deps exits cleanly when npm cannot launch."""
    frontend_dir = isolated_filesystem / "frontend"
    frontend_dir.mkdir()

    mock_run.side_effect = PermissionError("Permission denied")

    with pytest.raises(SystemExit) as exc_info:
        init_frontend_deps(frontend_dir)

    assert exc_info.value.code == 1
    mock_validate_npm.assert_called_once()
    assert "`npm i` failed. Aborting. Permission denied" in capsys.readouterr().err


# Build Manifest Tests
@pytest.mark.unit
def test_build_manifest_creates_correct_manifest_structure(
    isolated_filesystem, extension_with_build_structure
):
    """Test build_manifest creates correct manifest from extension.json."""
    # Create extension structure with both frontend and backend
    extension_with_build_structure(
        isolated_filesystem, include_frontend=True, include_backend=True
    )

    # Update extension.json with additional fields
    extension_data = {
        "publisher": "test-org",
        "name": "test-extension",
        "displayName": "Test Extension",
        "version": "1.0.0",
        "permissions": ["read_data"],
        "dependencies": ["some_dep"],
    }
    extension_json = isolated_filesystem / "extension.json"
    extension_json.write_text(json.dumps(extension_data))

    manifest = build_manifest(isolated_filesystem, "remoteEntry.abc123.js")

    # Verify manifest structure
    assert manifest.id == "test-org.test-extension"  # Composite ID
    assert manifest.publisher == "test-org"
    assert manifest.name == "test-extension"
    assert manifest.displayName == "Test Extension"
    assert manifest.version == "1.0.0"
    assert manifest.permissions == ["read_data"]
    assert manifest.dependencies == ["some_dep"]

    # Verify frontend section
    assert manifest.frontend is not None
    assert manifest.frontend.remoteEntry == "remoteEntry.abc123.js"
    assert manifest.frontend.moduleFederationName == "testOrg_testExtension"

    # Verify backend section and conventional entrypoint
    assert manifest.backend is not None
    assert manifest.backend.entrypoint == "test_org.test_extension.entrypoint"


@pytest.mark.unit
def test_build_manifest_handles_minimal_extension(isolated_filesystem):
    """Test build_manifest with minimal extension.json (no frontend/backend)."""
    extension_data = {
        "publisher": "minimal-org",
        "name": "minimal-extension",
        "displayName": "Minimal Extension",
        "version": "0.1.0",
        "permissions": [],
    }
    extension_json = isolated_filesystem / "extension.json"
    extension_json.write_text(json.dumps(extension_data))

    manifest = build_manifest(isolated_filesystem, None)

    assert manifest.id == "minimal-org.minimal-extension"  # Composite ID
    assert manifest.publisher == "minimal-org"
    assert manifest.name == "minimal-extension"
    assert manifest.displayName == "Minimal Extension"
    assert manifest.version == "0.1.0"
    assert manifest.permissions == []
    assert manifest.dependencies == []  # Default empty list
    assert manifest.frontend is None
    assert manifest.backend is None


@pytest.mark.unit
def test_build_manifest_rejects_symlinked_backend_directory(isolated_filesystem):
    """Test build_manifest refuses a symlinked backend directory."""
    extension_data = {
        "publisher": "test-org",
        "name": "test-extension",
        "displayName": "Test Extension",
        "version": "1.0.0",
        "permissions": [],
    }
    (isolated_filesystem / "extension.json").write_text(json.dumps(extension_data))
    outside_backend = isolated_filesystem / "outside-backend"
    outside_backend.mkdir()
    (isolated_filesystem / "backend").symlink_to(outside_backend)

    with pytest.raises(click.ClickException, match="backend path is a symlink"):
        build_manifest(isolated_filesystem, None)


@pytest.mark.unit
def test_build_manifest_exits_when_extension_json_missing(isolated_filesystem):
    """Test build_manifest fails when extension.json is missing."""
    with pytest.raises(click.ClickException, match="extension.json not found"):
        build_manifest(isolated_filesystem, "remoteEntry.js")


@pytest.mark.unit
@pytest.mark.parametrize("extension_json", ["{ invalid json", "[]"])
def test_build_manifest_rejects_invalid_extension_json(
    isolated_filesystem, extension_json
):
    """Test build_manifest fails when extension.json is malformed."""
    (isolated_filesystem / "extension.json").write_text(extension_json)

    with pytest.raises(click.ClickException, match="Invalid extension.json"):
        build_manifest(isolated_filesystem, "remoteEntry.js")


@pytest.mark.unit
def test_write_manifest_creates_missing_dist_directory(isolated_filesystem):
    """Test write_manifest creates dist when it is missing."""
    manifest = Manifest(
        id="test-org.test-extension",
        publisher="test-org",
        name="test-extension",
        displayName="Test Extension",
        version="1.0.0",
    )

    write_manifest(isolated_filesystem, manifest)

    assert_file_exists(isolated_filesystem / "dist" / "manifest.json")


@pytest.mark.unit
def test_write_manifest_rejects_invalid_dist_path(isolated_filesystem):
    """Test write_manifest refuses unsafe dist paths."""
    manifest = Manifest(
        id="test-org.test-extension",
        publisher="test-org",
        name="test-extension",
        displayName="Test Extension",
        version="1.0.0",
    )
    (isolated_filesystem / "dist").write_text("not a directory")

    with pytest.raises(click.ClickException, match="not a directory"):
        write_manifest(isolated_filesystem, manifest)


@pytest.mark.unit
def test_write_manifest_rejects_symlinked_dist_path(isolated_filesystem):
    """Test write_manifest refuses symlinked dist paths."""
    manifest = Manifest(
        id="test-org.test-extension",
        publisher="test-org",
        name="test-extension",
        displayName="Test Extension",
        version="1.0.0",
    )
    outside_dir = isolated_filesystem / "outside"
    outside_dir.mkdir()
    (isolated_filesystem / "dist").symlink_to(outside_dir)

    with pytest.raises(click.ClickException, match="path is a symlink"):
        write_manifest(isolated_filesystem, manifest)

    assert not (outside_dir / "manifest.json").exists()


@pytest.mark.unit
def test_write_manifest_rejects_symlinked_manifest_path(isolated_filesystem):
    """Test write_manifest refuses symlinked manifest output paths."""
    manifest = Manifest(
        id="test-org.test-extension",
        publisher="test-org",
        name="test-extension",
        displayName="Test Extension",
        version="1.0.0",
    )
    dist_dir = isolated_filesystem / "dist"
    dist_dir.mkdir()
    outside_manifest = isolated_filesystem / "outside-manifest.json"
    outside_manifest.write_text("keep")
    (dist_dir / "manifest.json").symlink_to(outside_manifest)

    with pytest.raises(click.ClickException, match="dist/manifest.json"):
        write_manifest(isolated_filesystem, manifest)

    assert outside_manifest.read_text() == "keep"


@pytest.mark.unit
def test_write_manifest_reports_write_errors(isolated_filesystem, monkeypatch):
    """Test write_manifest reports filesystem write failures cleanly."""
    manifest = Manifest(
        id="test-org.test-extension",
        publisher="test-org",
        name="test-extension",
        displayName="Test Extension",
        version="1.0.0",
    )
    manifest_path = isolated_filesystem / "dist" / "manifest.json"
    manifest_path.parent.mkdir()
    manifest_path.write_text("original manifest")
    original_replace = Path.replace

    def fail_manifest_replace(path, target):
        if target == manifest_path:
            raise OSError("disk full")
        return original_replace(path, target)

    monkeypatch.setattr(Path, "replace", fail_manifest_replace)

    with pytest.raises(
        click.ClickException,
        match="Failed to write dist/manifest.json: disk full",
    ):
        write_manifest(isolated_filesystem, manifest)

    assert manifest_path.read_text() == "original manifest"
    assert list(manifest_path.parent.glob(".manifest.json.*.tmp")) == []


@pytest.mark.unit
def test_write_manifest_rejects_changed_existing_manifest_before_write(
    isolated_filesystem,
    monkeypatch,
):
    """Test manifest writes bind the final write to the validated file."""
    manifest = Manifest(
        id="test-org.test-extension",
        publisher="test-org",
        name="test-extension",
        displayName="Test Extension",
        version="1.0.0",
    )
    manifest_path = isolated_filesystem / "dist" / "manifest.json"
    manifest_path.parent.mkdir()
    manifest_path.write_text("original manifest")
    original_write_text_atomic = cli.write_text_atomic

    def change_manifest_before_write(path, content, **kwargs):
        if path == manifest_path:
            manifest_path.write_text("changed manifest")
        return original_write_text_atomic(path, content, **kwargs)

    monkeypatch.setattr(cli, "write_text_atomic", change_manifest_before_write)

    with pytest.raises(
        click.ClickException,
        match="Failed to write dist/manifest.json: Refusing to promote through changed target",
    ):
        write_manifest(isolated_filesystem, manifest)

    assert manifest_path.read_text() == "changed manifest"
    assert list(manifest_path.parent.glob(".manifest.json.*.tmp")) == []


@pytest.mark.unit
def test_write_manifest_rejects_created_manifest_before_write(
    isolated_filesystem,
    monkeypatch,
):
    """Test manifest writes refuse a target created after missing preflight."""
    manifest = Manifest(
        id="test-org.test-extension",
        publisher="test-org",
        name="test-extension",
        displayName="Test Extension",
        version="1.0.0",
    )
    manifest_path = isolated_filesystem / "dist" / "manifest.json"
    original_write_text_atomic = cli.write_text_atomic

    def create_manifest_before_write(path, content, **kwargs):
        if path == manifest_path:
            manifest_path.write_text("created manifest")
        return original_write_text_atomic(path, content, **kwargs)

    monkeypatch.setattr(cli, "write_text_atomic", create_manifest_before_write)

    with pytest.raises(
        click.ClickException,
        match="Failed to write dist/manifest.json: Refusing to promote over existing target",
    ):
        write_manifest(isolated_filesystem, manifest)

    assert manifest_path.read_text() == "created manifest"
    assert list(manifest_path.parent.glob(".manifest.json.*.tmp")) == []


# Frontend Build Tests
@pytest.mark.unit
def test_clean_dist_frontend_removes_frontend_dist(isolated_filesystem):
    """Test clean_dist_frontend removes frontend/dist directory specifically."""
    from superset_extensions_cli.cli import clean_dist_frontend

    # Create dist/frontend structure
    dist_dir = isolated_filesystem / "dist"
    dist_dir.mkdir(parents=True)
    frontend_dist = dist_dir / "frontend"
    frontend_dist.mkdir()
    (frontend_dist / "some_file.js").write_text("content")

    clean_dist_frontend(isolated_filesystem)

    # Frontend dist should be removed, but dist should remain
    assert dist_dir.exists()
    assert not frontend_dist.exists()


@pytest.mark.unit
def test_clean_dist_frontend_handles_nonexistent_directory(isolated_filesystem):
    """Test clean_dist_frontend handles case where frontend dist doesn't exist."""
    from superset_extensions_cli.cli import clean_dist_frontend

    # No dist directory exists
    clean_dist_frontend(isolated_filesystem)

    # Should not raise error


@pytest.mark.unit
def test_clean_dist_frontend_rejects_symlinked_directory(isolated_filesystem):
    """Test clean_dist_frontend refuses a symlinked frontend output path."""
    from superset_extensions_cli.cli import clean_dist_frontend

    dist_dir = isolated_filesystem / "dist"
    dist_dir.mkdir()
    outside_dir = isolated_filesystem / "outside-frontend"
    outside_dir.mkdir()
    (outside_dir / "artifact.js").write_text("keep")
    (dist_dir / "frontend").symlink_to(outside_dir)

    with pytest.raises(click.ClickException, match="path is a symlink"):
        clean_dist_frontend(isolated_filesystem)

    assert_file_exists(outside_dir / "artifact.js")


@pytest.mark.unit
def test_clean_dist_frontend_rejects_symlinked_parent(isolated_filesystem):
    """Test clean_dist_frontend refuses a symlinked dist parent."""
    from superset_extensions_cli.cli import clean_dist_frontend

    outside_dir = isolated_filesystem / "outside-dist"
    outside_frontend = outside_dir / "frontend"
    outside_frontend.mkdir(parents=True)
    (outside_frontend / "artifact.js").write_text("keep")
    (isolated_filesystem / "dist").symlink_to(outside_dir)

    with pytest.raises(
        click.ClickException,
        match="Refusing to clean dist/frontend directory: parent directory is a symlink",
    ):
        clean_dist_frontend(isolated_filesystem)

    assert_file_exists(outside_frontend / "artifact.js")


@pytest.mark.unit
def test_clean_dist_frontend_rejects_non_directory_parent(isolated_filesystem):
    """Test clean_dist_frontend refuses file parent paths."""
    from superset_extensions_cli.cli import clean_dist_frontend

    output_parent = isolated_filesystem / "dist"
    output_parent.write_text("not a directory")

    with pytest.raises(
        click.ClickException,
        match="Refusing to clean dist/frontend directory: parent exists but is not a directory",
    ):
        clean_dist_frontend(isolated_filesystem)

    assert output_parent.read_text() == "not a directory"


@pytest.mark.unit
def test_clean_dist_frontend_rejects_changed_directory(
    isolated_filesystem,
    monkeypatch,
):
    """Test clean_dist_frontend refuses a directory changed before deletion."""
    from superset_extensions_cli import cli
    from superset_extensions_cli.cli import clean_dist_frontend

    frontend_dir = isolated_filesystem / "dist" / "frontend"
    frontend_dir.mkdir(parents=True)
    (frontend_dir / "artifact.js").write_text("old")
    replacement_dir = isolated_filesystem / "replacement-frontend"
    replacement_dir.mkdir()
    (replacement_dir / "replacement.js").write_text("replacement")
    saved_original = isolated_filesystem / "saved-frontend"
    original_get_directory_path_identity = cli.get_directory_path_identity
    identity_reads = 0

    def replace_frontend_after_initial_identity(path):
        nonlocal identity_reads
        identity = original_get_directory_path_identity(path)
        if path == frontend_dir:
            identity_reads += 1
            if identity_reads == 1:
                frontend_dir.rename(saved_original)
                replacement_dir.rename(frontend_dir)
        return identity

    monkeypatch.setattr(
        cli,
        "get_directory_path_identity",
        replace_frontend_after_initial_identity,
    )

    with pytest.raises(
        click.ClickException,
        match="Refusing to clean dist/frontend directory: path changed",
    ):
        clean_dist_frontend(isolated_filesystem)

    assert_file_exists(saved_original / "artifact.js")
    assert_file_exists(frontend_dir / "replacement.js")


@pytest.mark.unit
def test_run_frontend_build_with_output_messages(isolated_filesystem):
    """Test run_frontend_build produces expected output messages."""
    from superset_extensions_cli.cli import run_frontend_build

    frontend_dir = isolated_filesystem / "frontend"
    frontend_dir.mkdir()

    with (
        patch("subprocess.run") as mock_run,
        patch("superset_extensions_cli.cli.validate_npm", return_value="npm"),
    ):
        mock_result = Mock(returncode=0)
        mock_run.return_value = mock_result

        result = run_frontend_build(frontend_dir)

        assert result.returncode == 0
        mock_run.assert_called_once_with(
            ["npm", "run", "build"], cwd=frontend_dir, text=True
        )


@pytest.mark.unit
def test_run_frontend_build_uses_validated_npm_path(isolated_filesystem):
    """Test frontend builds use the npm executable that validation resolved."""
    from superset_extensions_cli.cli import run_frontend_build

    frontend_dir = isolated_filesystem / "frontend"
    frontend_dir.mkdir()
    npm_path = isolated_filesystem / "npm"
    npm_path.write_text("npm")
    npm_identity = cli.get_output_copy_source_identity(npm_path)
    assert npm_identity is not None

    with (
        patch("subprocess.run") as mock_run,
        patch(
            "superset_extensions_cli.cli.validate_npm",
            return_value=cli.ValidatedNpmExecutable(str(npm_path), npm_identity),
        ),
    ):
        mock_result = Mock(returncode=0)
        mock_run.return_value = mock_result

        result = run_frontend_build(frontend_dir)

        assert result.returncode == 0
        mock_run.assert_called_once_with(
            [str(npm_path), "run", "build"],
            cwd=frontend_dir,
            text=True,
        )


@pytest.mark.unit
def test_run_frontend_build_rejects_changed_validated_npm_path(
    isolated_filesystem,
):
    """Test frontend builds refuse a changed validated npm executable."""
    from superset_extensions_cli.cli import run_frontend_build

    frontend_dir = isolated_filesystem / "frontend"
    frontend_dir.mkdir()
    npm_path = isolated_filesystem / "npm"
    npm_path.write_text("npm")
    npm_identity = cli.get_output_copy_source_identity(npm_path)
    assert npm_identity is not None
    npm_path.write_text("changed npm")

    with (
        patch("subprocess.run") as mock_run,
        patch(
            "superset_extensions_cli.cli.validate_npm",
            return_value=cli.ValidatedNpmExecutable(str(npm_path), npm_identity),
        ),
        pytest.raises(
            click.ClickException,
            match="npm executable changed before launch",
        ),
    ):
        run_frontend_build(frontend_dir)

    mock_run.assert_not_called()


@pytest.mark.unit
def test_run_frontend_build_returns_failure_on_launch_error(
    isolated_filesystem, capsys
):
    """Test run_frontend_build handles npm launch errors without a traceback."""
    from superset_extensions_cli.cli import run_frontend_build

    frontend_dir = isolated_filesystem / "frontend"
    frontend_dir.mkdir()

    with (
        patch("subprocess.run") as mock_run,
        patch("superset_extensions_cli.cli.validate_npm", return_value="npm"),
    ):
        mock_run.side_effect = PermissionError("Permission denied")

        result = run_frontend_build(frontend_dir)

    assert result.returncode == 1
    assert "Failed to run `npm run build`: Permission denied" in capsys.readouterr().err


@pytest.mark.unit
@patch("subprocess.run")
def test_run_frontend_build_rejects_changed_frontend_before_launch(
    mock_run,
    isolated_filesystem,
    monkeypatch,
):
    """Test frontend build refuses a changed frontend directory."""
    from superset_extensions_cli import cli
    from superset_extensions_cli.cli import run_frontend_build

    frontend_dir = isolated_filesystem / "frontend"
    frontend_dir.mkdir()
    saved_frontend = isolated_filesystem / "saved-frontend"
    replacement_frontend = isolated_filesystem / "replacement-frontend"
    replacement_frontend.mkdir()
    original_get_directory_path_identity = cli.get_directory_path_identity
    identity_reads = 0

    def swap_frontend_after_build_identity(path):
        nonlocal identity_reads
        identity = original_get_directory_path_identity(path)
        if path == frontend_dir:
            identity_reads += 1
            if identity_reads == 3:
                frontend_dir.rename(saved_frontend)
                replacement_frontend.rename(frontend_dir)
        return identity

    monkeypatch.setattr(
        cli,
        "get_directory_path_identity",
        swap_frontend_after_build_identity,
    )
    monkeypatch.setattr(cli, "validate_npm", lambda: "npm")

    with pytest.raises(
        click.ClickException,
        match="frontend path changed before frontend build",
    ):
        run_frontend_build(frontend_dir)

    mock_run.assert_not_called()
    assert saved_frontend.is_dir()
    assert frontend_dir.is_dir()


@pytest.mark.unit
@patch("subprocess.run")
def test_run_frontend_build_rejects_frontend_content_change_before_launch(
    mock_run,
    isolated_filesystem,
    monkeypatch,
):
    """Test frontend build refuses content changes after the build snapshot."""
    from superset_extensions_cli import cli
    from superset_extensions_cli.cli import run_frontend_build

    frontend_dir = isolated_filesystem / "frontend"
    frontend_dir.mkdir()
    original_get_directory_path_identity = cli.get_directory_path_identity
    identity_reads = 0

    def change_frontend_after_build_identity(path):
        nonlocal identity_reads
        identity = original_get_directory_path_identity(path)
        if path == frontend_dir:
            identity_reads += 1
            if identity_reads == 3:
                (frontend_dir / "unexpected.txt").write_text("unexpected")
        return identity

    monkeypatch.setattr(
        cli,
        "get_directory_path_identity",
        change_frontend_after_build_identity,
    )
    monkeypatch.setattr(cli, "validate_npm", lambda: "npm")

    with pytest.raises(
        click.ClickException,
        match="frontend path changed before frontend build",
    ):
        run_frontend_build(frontend_dir)

    mock_run.assert_not_called()
    assert (frontend_dir / "unexpected.txt").read_text() == "unexpected"


@pytest.mark.unit
@patch("subprocess.run")
def test_run_frontend_build_rejects_frontend_parent_change_before_launch(
    mock_run,
    isolated_filesystem,
    monkeypatch,
):
    """Test frontend build refuses a frontend directory moved under a new parent."""
    from superset_extensions_cli import cli
    from superset_extensions_cli.cli import run_frontend_build

    project_dir = isolated_filesystem / "project"
    frontend_dir = project_dir / "frontend"
    frontend_dir.mkdir(parents=True)
    saved_project_dir = isolated_filesystem / "saved-project"
    replacement_project_dir = isolated_filesystem / "replacement-project"

    def move_frontend_under_replaced_parent():
        project_dir.rename(saved_project_dir)
        replacement_project_dir.mkdir()
        (saved_project_dir / "frontend").rename(replacement_project_dir / "frontend")
        replacement_project_dir.rename(project_dir)
        return "npm"

    monkeypatch.setattr(cli, "validate_npm", move_frontend_under_replaced_parent)

    with pytest.raises(
        click.ClickException,
        match="frontend path changed before frontend build",
    ):
        run_frontend_build(frontend_dir)

    mock_run.assert_not_called()
    assert not (saved_project_dir / "frontend").exists()
    assert frontend_dir.is_dir()


@pytest.mark.unit
@pytest.mark.parametrize(
    "return_code,expected_result",
    [
        (0, "remoteEntry.abc123.js"),
        (1, None),
    ],
)
def test_rebuild_frontend_handles_build_results(
    isolated_filesystem, return_code, expected_result
):
    """Test rebuild_frontend handles different build results."""
    from superset_extensions_cli.cli import rebuild_frontend

    # Create frontend structure
    frontend_dir = isolated_filesystem / "frontend"
    frontend_dir.mkdir()

    if return_code == 0:
        # Create frontend/dist with remoteEntry for success case
        frontend_dist = frontend_dir / "dist"
        frontend_dist.mkdir()
        (frontend_dist / "remoteEntry.abc123.js").write_text("content")

        # Create dist directory
        dist_dir = isolated_filesystem / "dist"
        dist_dir.mkdir()

    with patch("superset_extensions_cli.cli.run_frontend_build") as mock_build:
        mock_build.return_value = Mock(returncode=return_code)

        result = rebuild_frontend(isolated_filesystem, frontend_dir)

        assert result == expected_result


@pytest.mark.unit
def test_rebuild_frontend_preserves_existing_output_on_build_failure(
    isolated_filesystem,
):
    """Test failed frontend builds do not remove the existing staged frontend."""
    from superset_extensions_cli.cli import rebuild_frontend

    frontend_dir = isolated_filesystem / "frontend"
    frontend_dir.mkdir()
    existing_output = isolated_filesystem / "dist" / "frontend" / "dist"
    existing_output.mkdir(parents=True)
    (existing_output / "remoteEntry.previous.js").write_text("previous")

    with patch("superset_extensions_cli.cli.run_frontend_build") as mock_build:
        mock_build.return_value = Mock(returncode=1)

        result = rebuild_frontend(isolated_filesystem, frontend_dir)

    assert result is None
    assert (existing_output / "remoteEntry.previous.js").read_text() == "previous"


# Backend Build Tests
@pytest.mark.unit
def test_rebuild_backend_calls_copy_and_shows_message(isolated_filesystem):
    """Test rebuild_backend calls copy_backend_files and shows success message."""
    from superset_extensions_cli.cli import rebuild_backend

    # Create extension.json
    extension_json = {
        "publisher": "test-org",
        "name": "test-extension",
        "displayName": "Test Extension",
        "version": "1.0.0",
        "permissions": [],
    }
    (isolated_filesystem / "extension.json").write_text(json.dumps(extension_json))

    with patch("superset_extensions_cli.cli.copy_backend_files") as mock_copy:
        rebuild_backend(isolated_filesystem)

        mock_copy.assert_called_once_with(isolated_filesystem)


@pytest.mark.unit
def test_copy_backend_files_skips_non_files(isolated_filesystem):
    """Test copy_backend_files skips directories and non-files."""
    # Create backend structure with directory
    backend_dir = isolated_filesystem / "backend"
    backend_src = backend_dir / "src" / "test_org" / "test_ext"
    backend_src.mkdir(parents=True)
    (backend_src / "__init__.py").write_text("# init")

    # Create a subdirectory (should be skipped)
    subdir = backend_src / "subdir"
    subdir.mkdir()

    # Create pyproject.toml with build configuration
    pyproject_content = """[project]
name = "test_org-test_ext"
version = "1.0.0"
license = "Apache-2.0"

[tool.apache_superset_extensions.build]
include = [
    "src/test_org/test_ext/**/*",
]
exclude = []
"""
    (backend_dir / "pyproject.toml").write_text(pyproject_content)

    # Create extension.json
    extension_data = {
        "publisher": "test-org",
        "name": "test-ext",
        "displayName": "Test Extension",
        "version": "1.0.0",
        "permissions": [],
    }
    (isolated_filesystem / "extension.json").write_text(json.dumps(extension_data))

    # Create dist directory
    clean_dist(isolated_filesystem)

    copy_backend_files(isolated_filesystem)

    # Verify only files were copied, not directories
    dist_dir = isolated_filesystem / "dist"
    assert_file_exists(
        dist_dir / "backend" / "src" / "test_org" / "test_ext" / "__init__.py"
    )

    # Directory should not be copied as a file
    copied_subdir = dist_dir / "backend" / "src" / "test_org" / "test_ext" / "subdir"
    # The directory might exist but should be empty since we skip non-files
    if copied_subdir.exists():
        assert list(copied_subdir.iterdir()) == []


@pytest.mark.unit
def test_copy_backend_files_copies_matched_files(isolated_filesystem):
    """Test copy_backend_files copies files matching patterns from pyproject.toml."""
    # Create backend source files
    backend_dir = isolated_filesystem / "backend"
    backend_src = backend_dir / "src" / "test_org" / "test_ext"
    backend_src.mkdir(parents=True)
    (backend_src / "__init__.py").write_text("# init")
    (backend_src / "main.py").write_text("# main")

    # Create pyproject.toml with build configuration
    pyproject_content = """[project]
name = "test_org-test_ext"
version = "1.0.0"
license = "Apache-2.0"

[tool.apache_superset_extensions.build]
include = [
    "src/test_org/test_ext/**/*.py",
]
exclude = []
"""
    (backend_dir / "pyproject.toml").write_text(pyproject_content)

    # Create extension.json
    extension_data = {
        "publisher": "test-org",
        "name": "test-ext",
        "displayName": "Test Extension",
        "version": "1.0.0",
        "permissions": [],
    }
    (isolated_filesystem / "extension.json").write_text(json.dumps(extension_data))

    # Create dist directory
    clean_dist(isolated_filesystem)

    copy_backend_files(isolated_filesystem)

    # Verify files were copied
    dist_dir = isolated_filesystem / "dist"
    assert_file_exists(
        dist_dir / "backend" / "src" / "test_org" / "test_ext" / "__init__.py"
    )
    assert_file_exists(
        dist_dir / "backend" / "src" / "test_org" / "test_ext" / "main.py"
    )


@pytest.mark.unit
def test_copy_backend_files_deduplicates_overlapping_include_patterns(
    isolated_filesystem, monkeypatch
):
    """Test overlapping backend include patterns copy each target once."""
    backend_dir = isolated_filesystem / "backend"
    backend_src = backend_dir / "src" / "test_org" / "test_ext"
    backend_src.mkdir(parents=True)
    source_file = backend_src / "__init__.py"
    source_file.write_text("# init")

    pyproject_content = """[project]
name = "test_org-test_ext"
version = "1.0.0"
license = "Apache-2.0"

[tool.apache_superset_extensions.build]
include = [
    "src/**/*.py",
    "src/test_org/test_ext/**/*.py",
]
exclude = []
"""
    (backend_dir / "pyproject.toml").write_text(pyproject_content)

    original_copy2 = shutil.copy2
    copied_sources: list[Path] = []

    def track_copy(source, target, *args, **kwargs):
        copied_sources.append(source)
        return original_copy2(source, target, *args, **kwargs)

    monkeypatch.setattr("superset_extensions_cli.cli.shutil.copy2", track_copy)

    clean_dist(isolated_filesystem)
    copy_backend_files(isolated_filesystem)

    dist_file = (
        isolated_filesystem
        / "dist"
        / "backend"
        / "src"
        / "test_org"
        / "test_ext"
        / "__init__.py"
    )
    assert_file_exists(dist_file)
    assert copied_sources == [source_file]


@pytest.mark.unit
def test_copy_backend_files_removes_stale_output_files(isolated_filesystem):
    """Test copy_backend_files replaces stale backend output with current files."""
    backend_dir = isolated_filesystem / "backend"
    backend_src = backend_dir / "src" / "test_org" / "test_ext"
    backend_src.mkdir(parents=True)
    (backend_src / "current.py").write_text("# current")

    pyproject_content = """[project]
name = "test_org-test_ext"
version = "1.0.0"
license = "Apache-2.0"

[tool.apache_superset_extensions.build]
include = [
    "src/test_org/test_ext/**/*.py",
]
exclude = []
"""
    (backend_dir / "pyproject.toml").write_text(pyproject_content)

    stale_output = (
        isolated_filesystem / "dist" / "backend" / "src" / "test_org" / "test_ext"
    )
    stale_output.mkdir(parents=True)
    (stale_output / "stale.py").write_text("# stale")

    copy_backend_files(isolated_filesystem)

    assert_file_exists(stale_output / "current.py")
    assert not (stale_output / "stale.py").exists()
    assert list((isolated_filesystem / "dist").glob(".backend*.tmp")) == []


@pytest.mark.unit
def test_copy_backend_files_reports_copy_failures(isolated_filesystem):
    """Test copy_backend_files reports copy failures with backend file context."""
    backend_dir = isolated_filesystem / "backend"
    backend_src = backend_dir / "src" / "test_org" / "test_ext"
    backend_src.mkdir(parents=True)
    (backend_src / "__init__.py").write_text("# init")

    pyproject_content = """[project]
name = "test_org-test_ext"
version = "1.0.0"
license = "Apache-2.0"

[tool.apache_superset_extensions.build]
include = [
    "src/test_org/test_ext/__init__.py",
]
exclude = []
"""
    (backend_dir / "pyproject.toml").write_text(pyproject_content)

    clean_dist(isolated_filesystem)
    existing_output = isolated_filesystem / "dist" / "backend" / "existing.py"
    existing_output.parent.mkdir(parents=True)
    existing_output.write_text("# existing")

    with patch(
        "superset_extensions_cli.cli.shutil.copy2",
        side_effect=OSError("disk full"),
    ):
        with pytest.raises(
            click.ClickException,
            match="Failed to copy backend file .*__init__\\.py: disk full",
        ):
            copy_backend_files(isolated_filesystem)

    assert existing_output.read_text() == "# existing"
    assert list((isolated_filesystem / "dist").glob(".backend.*.tmp")) == []


@pytest.mark.unit
def test_copy_backend_files_rejects_source_changed_before_copy(
    isolated_filesystem,
    monkeypatch,
):
    """Test backend staging refuses a source path changed after planning."""
    backend_dir = isolated_filesystem / "backend"
    backend_src = backend_dir / "src" / "test_org" / "test_ext"
    backend_src.mkdir(parents=True)
    source_file = backend_src / "__init__.py"
    source_file.write_text("# init")
    outside_file = isolated_filesystem / "outside.py"
    outside_file.write_text("# outside")

    pyproject_content = """[project]
name = "test_org-test_ext"
version = "1.0.0"
license = "Apache-2.0"

[tool.apache_superset_extensions.build]
include = [
    "src/test_org/test_ext/__init__.py",
]
exclude = []
"""
    (backend_dir / "pyproject.toml").write_text(pyproject_content)

    from superset_extensions_cli import cli

    original_create_temporary_output_directory = cli.create_temporary_output_directory

    def swap_source_after_planning(parent, prefix, label):
        temp_dir = original_create_temporary_output_directory(parent, prefix, label)
        if prefix == ".backend.":
            source_file.unlink()
            source_file.symlink_to(outside_file)
        return temp_dir

    monkeypatch.setattr(
        cli,
        "create_temporary_output_directory",
        swap_source_after_planning,
    )

    with pytest.raises(
        click.ClickException,
        match="Refusing to copy backend file .*source path changed before copy",
    ):
        copy_backend_files(isolated_filesystem)

    assert source_file.is_symlink()
    assert outside_file.read_text() == "# outside"
    assert not (
        isolated_filesystem
        / "dist"
        / "backend"
        / "src"
        / "test_org"
        / "test_ext"
        / "__init__.py"
    ).exists()
    assert list((isolated_filesystem / "dist").glob(".backend.*.tmp")) == []


@pytest.mark.unit
def test_copy_backend_files_rejects_source_root_changed_before_copy(
    isolated_filesystem,
    monkeypatch,
):
    """Test backend staging refuses a replaced backend root before copying."""
    backend_dir = isolated_filesystem / "backend"
    backend_src = backend_dir / "src" / "test_org" / "test_ext"
    backend_src.mkdir(parents=True)
    source_file = backend_src / "__init__.py"
    source_file.write_text("# init")
    pyproject_content = """[project]
name = "test_org-test_ext"
version = "1.0.0"
license = "Apache-2.0"

[tool.apache_superset_extensions.build]
include = [
    "src/test_org/test_ext/__init__.py",
]
exclude = []
"""
    (backend_dir / "pyproject.toml").write_text(pyproject_content)
    saved_backend_dir = isolated_filesystem / "saved-backend"
    replacement_backend_dir = isolated_filesystem / "replacement-backend"

    from superset_extensions_cli import cli

    original_create_temporary_output_directory = cli.create_temporary_output_directory

    def replace_backend_root_after_planning(parent, prefix, label):
        temp_dir = original_create_temporary_output_directory(parent, prefix, label)
        if prefix == ".backend.":
            backend_dir.rename(saved_backend_dir)
            replacement_source_dir = (
                replacement_backend_dir / "src" / "test_org" / "test_ext"
            )
            replacement_source_dir.mkdir(parents=True)
            saved_source_file = (
                saved_backend_dir / "src" / "test_org" / "test_ext" / "__init__.py"
            )
            saved_source_file.rename(replacement_source_dir / "__init__.py")
            replacement_backend_dir.rename(backend_dir)
        return temp_dir

    monkeypatch.setattr(
        cli,
        "create_temporary_output_directory",
        replace_backend_root_after_planning,
    )

    with pytest.raises(
        click.ClickException,
        match="backend path changed before copy",
    ):
        copy_backend_files(isolated_filesystem)

    assert not (
        saved_backend_dir / "src" / "test_org" / "test_ext" / "__init__.py"
    ).exists()
    assert source_file.read_text() == "# init"
    assert not (
        isolated_filesystem
        / "dist"
        / "backend"
        / "src"
        / "test_org"
        / "test_ext"
        / "__init__.py"
    ).exists()
    assert list((isolated_filesystem / "dist").glob(".backend.*.tmp")) == []


@pytest.mark.unit
def test_copy_backend_files_rejects_changed_staged_cleanup_root(
    isolated_filesystem,
    monkeypatch,
):
    """Test backend copy failure does not clean a swapped staged root."""
    backend_dir = isolated_filesystem / "backend"
    backend_src = backend_dir / "src" / "test_org" / "test_ext"
    backend_src.mkdir(parents=True)
    (backend_src / "__init__.py").write_text("# init")

    pyproject_content = """[project]
name = "test_org-test_ext"
version = "1.0.0"
license = "Apache-2.0"

[tool.apache_superset_extensions.build]
include = [
    "src/test_org/test_ext/__init__.py",
]
exclude = []
"""
    (backend_dir / "pyproject.toml").write_text(pyproject_content)
    replacement_root = isolated_filesystem / "replacement-backend-stage"
    replacement_root.mkdir()
    (replacement_root / "replacement.txt").write_text("replacement")
    saved_root = isolated_filesystem / "saved-backend-stage"
    swapped_root: Path | None = None

    from superset_extensions_cli import cli

    def swap_staged_root_during_copy(source, target, label):
        nonlocal swapped_root
        staged_root = next(
            parent for parent in target.parents if parent.name.startswith(".backend.")
        )
        staged_root.rename(saved_root)
        replacement_root.rename(staged_root)
        swapped_root = staged_root
        raise click.ClickException("copy failed")

    monkeypatch.setattr(cli, "copy_output_file", swap_staged_root_during_copy)

    with pytest.raises(click.ClickException, match="copy failed"):
        copy_backend_files(isolated_filesystem)

    assert swapped_root is not None
    assert_file_exists(swapped_root / "replacement.txt")
    assert saved_root.exists()


@pytest.mark.unit
def test_copy_backend_files_restores_existing_output_on_publish_failure(
    isolated_filesystem, monkeypatch
):
    """Test copy_backend_files restores old output when publishing staged output fails."""
    backend_dir = isolated_filesystem / "backend"
    backend_src = backend_dir / "src" / "test_org" / "test_ext"
    backend_src.mkdir(parents=True)
    (backend_src / "__init__.py").write_text("# init")

    pyproject_content = """[project]
name = "test_org-test_ext"
version = "1.0.0"
license = "Apache-2.0"

[tool.apache_superset_extensions.build]
include = [
    "src/test_org/test_ext/__init__.py",
]
exclude = []
"""
    (backend_dir / "pyproject.toml").write_text(pyproject_content)

    existing_output = isolated_filesystem / "dist" / "backend" / "existing.py"
    existing_output.parent.mkdir(parents=True)
    existing_output.write_text("# existing")
    backend_output_dir = isolated_filesystem / "dist" / "backend"
    original_replace = Path.replace

    def fail_staged_publish(path, target):
        if path.name.startswith(".backend.") and target == backend_output_dir:
            raise OSError("permission denied")
        return original_replace(path, target)

    monkeypatch.setattr(Path, "replace", fail_staged_publish)

    with pytest.raises(
        click.ClickException,
        match="Failed to publish dist/backend directory: permission denied",
    ):
        copy_backend_files(isolated_filesystem)

    assert existing_output.read_text() == "# existing"
    assert list((isolated_filesystem / "dist").glob(".backend*.tmp")) == []


@pytest.mark.unit
def test_copy_backend_files_handles_various_glob_patterns(isolated_filesystem):
    """Test copy_backend_files correctly handles different glob pattern formats."""
    # Create backend structure with files in different locations
    backend_dir = isolated_filesystem / "backend"
    backend_src = backend_dir / "src" / "test_org" / "test_ext"
    backend_src.mkdir(parents=True)

    # Create files that should match different pattern types
    (backend_src / "__init__.py").write_text("# init")
    (backend_src / "main.py").write_text("# main")
    (backend_dir / "config.py").write_text("# config")  # Root level file

    # Create subdirectory with files
    subdir = backend_src / "utils"
    subdir.mkdir()
    (subdir / "helper.py").write_text("# helper")

    # Create pyproject.toml with various glob patterns that would fail with old logic
    pyproject_content = """[project]
name = "test_org-test_ext"
version = "1.0.0"
license = "Apache-2.0"

[tool.apache_superset_extensions.build]
include = [
    "config.py",                                  # No '/' - would break old logic
    "**/*.py",                                    # Starts with '**' - would break old logic
    "src/test_org/test_ext/main.py",              # Specific file
]
exclude = []
"""
    (backend_dir / "pyproject.toml").write_text(pyproject_content)

    # Create extension.json
    extension_data = {
        "publisher": "test-org",
        "name": "test-ext",
        "displayName": "Test Extension",
        "version": "1.0.0",
        "permissions": [],
    }
    (isolated_filesystem / "extension.json").write_text(json.dumps(extension_data))

    # Create dist directory
    clean_dist(isolated_filesystem)

    copy_backend_files(isolated_filesystem)

    # Verify files were copied according to patterns
    dist_dir = isolated_filesystem / "dist"

    # config.py (pattern: "config.py")
    assert_file_exists(dist_dir / "backend" / "config.py")

    # All .py files should be included (pattern: "**/*.py")
    assert_file_exists(
        dist_dir / "backend" / "src" / "test_org" / "test_ext" / "__init__.py"
    )
    assert_file_exists(
        dist_dir / "backend" / "src" / "test_org" / "test_ext" / "utils" / "helper.py"
    )

    # Specific file (pattern: "src/test_org/test_ext/main.py")
    assert_file_exists(
        dist_dir / "backend" / "src" / "test_org" / "test_ext" / "main.py"
    )


@pytest.mark.unit
def test_copy_backend_files_supports_legitimate_nested_patterns(isolated_filesystem):
    """Test copy_backend_files copies deeply nested files via recursive globs."""
    backend_dir = isolated_filesystem / "backend"
    nested = backend_dir / "src" / "test_org" / "test_ext" / "deep" / "deeper"
    nested.mkdir(parents=True)
    (nested / "module.py").write_text("# nested module")

    pyproject_content = """[project]
name = "test_org-test_ext"
version = "1.0.0"
license = "Apache-2.0"

[tool.apache_superset_extensions.build]
include = [
    "src/test_org/test_ext/**/*.py",
]
exclude = []
"""
    (backend_dir / "pyproject.toml").write_text(pyproject_content)

    extension_data = {
        "publisher": "test-org",
        "name": "test-ext",
        "displayName": "Test Extension",
        "version": "1.0.0",
        "permissions": [],
    }
    (isolated_filesystem / "extension.json").write_text(json.dumps(extension_data))

    clean_dist(isolated_filesystem)
    copy_backend_files(isolated_filesystem)

    dist_dir = isolated_filesystem / "dist"
    assert_file_exists(
        dist_dir
        / "backend"
        / "src"
        / "test_org"
        / "test_ext"
        / "deep"
        / "deeper"
        / "module.py"
    )


@pytest.mark.unit
@pytest.mark.parametrize(
    "bad_pattern",
    [
        "../../.ssh/*",
        "../config",
        r"..\config",
        "src/../../secret.txt",
        r"src\..\..\secret.txt",
        "/etc/passwd",
        r"C:\Windows\win.ini",
        r"\Windows\win.ini",
    ],
)
def test_copy_backend_files_rejects_patterns_escaping_backend_dir(
    isolated_filesystem, bad_pattern
):
    """Test copy_backend_files refuses include patterns that escape backend_dir."""
    # Create a sensitive file outside the backend directory.
    (isolated_filesystem / "secret.txt").write_text("SECRET")
    (isolated_filesystem / "config").write_text("SECRET")

    backend_dir = isolated_filesystem / "backend"
    backend_src = backend_dir / "src" / "test_org" / "test_ext"
    backend_src.mkdir(parents=True)
    (backend_src / "__init__.py").write_text("# init")

    pyproject_content = f"""[project]
name = "test_org-test_ext"
version = "1.0.0"
license = "Apache-2.0"

[tool.apache_superset_extensions.build]
include = [
    '{bad_pattern}',
]
exclude = []
"""
    (backend_dir / "pyproject.toml").write_text(pyproject_content)

    extension_data = {
        "publisher": "test-org",
        "name": "test-ext",
        "displayName": "Test Extension",
        "version": "1.0.0",
        "permissions": [],
    }
    (isolated_filesystem / "extension.json").write_text(json.dumps(extension_data))

    clean_dist(isolated_filesystem)

    with pytest.raises(click.ClickException, match="Invalid include pattern"):
        copy_backend_files(isolated_filesystem)

    # Nothing outside the backend directory should have been staged into dist,
    # including paths reachable via ".." from inside dist/backend.
    dist_dir = isolated_filesystem / "dist"
    assert not (dist_dir / "secret.txt").exists()
    assert not (dist_dir / "config").exists()


@pytest.mark.unit
@pytest.mark.parametrize(
    "build_config",
    [
        'include = "src/**/*.py"\nexclude = []',
        'include = ["src/**/*.py"]\nexclude = "*.py"',
        'include = ["src/**/*.py", 123]\nexclude = []',
        'include = ["src/**/*.py"]\nexclude = [123]',
    ],
)
def test_copy_backend_files_rejects_invalid_build_pattern_config(
    isolated_filesystem, build_config
):
    """Test copy_backend_files validates include and exclude pattern shapes."""
    backend_dir = isolated_filesystem / "backend"
    backend_src = backend_dir / "src" / "test_org" / "test_ext"
    backend_src.mkdir(parents=True)
    (backend_src / "__init__.py").write_text("# init")

    pyproject_content = f"""[project]
name = "test_org-test_ext"
version = "1.0.0"
license = "Apache-2.0"

[tool.apache_superset_extensions.build]
{build_config}
"""
    (backend_dir / "pyproject.toml").write_text(pyproject_content)

    clean_dist(isolated_filesystem)

    with pytest.raises(click.ClickException, match="Invalid backend build config"):
        copy_backend_files(isolated_filesystem)

    assert not (isolated_filesystem / "dist" / "backend").exists()


@pytest.mark.unit
def test_copy_backend_files_rejects_invalid_build_parent_config(
    isolated_filesystem,
):
    """Test copy_backend_files validates parent build config tables."""
    backend_dir = isolated_filesystem / "backend"
    backend_src = backend_dir / "src" / "test_org" / "test_ext"
    backend_src.mkdir(parents=True)
    (backend_src / "__init__.py").write_text("# init")

    pyproject_content = """[project]
name = "test_org-test_ext"
version = "1.0.0"
license = "Apache-2.0"

[tool]
apache_superset_extensions = "invalid"
"""
    (backend_dir / "pyproject.toml").write_text(pyproject_content)

    clean_dist(isolated_filesystem)

    with pytest.raises(click.ClickException, match="Invalid backend build config"):
        copy_backend_files(isolated_filesystem)


@pytest.mark.unit
def test_copy_backend_files_rejects_malformed_pyproject_toml(
    isolated_filesystem,
):
    """Test copy_backend_files reports malformed backend pyproject.toml cleanly."""
    backend_dir = isolated_filesystem / "backend"
    backend_src = backend_dir / "src" / "test_org" / "test_ext"
    backend_src.mkdir(parents=True)
    (backend_src / "__init__.py").write_text("# init")
    (backend_dir / "pyproject.toml").write_text("[ invalid toml")

    clean_dist(isolated_filesystem)

    with pytest.raises(click.ClickException, match="Invalid backend pyproject.toml"):
        copy_backend_files(isolated_filesystem)

    assert not (isolated_filesystem / "dist" / "backend").exists()


@pytest.mark.unit
def test_copy_backend_files_rejects_missing_pyproject_toml(
    isolated_filesystem,
):
    """Test copy_backend_files reports missing backend pyproject.toml cleanly."""
    backend_dir = isolated_filesystem / "backend"
    backend_src = backend_dir / "src" / "test_org" / "test_ext"
    backend_src.mkdir(parents=True)
    (backend_src / "__init__.py").write_text("# init")

    clean_dist(isolated_filesystem)

    with pytest.raises(click.ClickException, match="backend pyproject.toml not found"):
        copy_backend_files(isolated_filesystem)

    assert not (isolated_filesystem / "dist" / "backend").exists()


@pytest.mark.unit
def test_copy_backend_files_rejects_symlinked_pyproject_toml(
    isolated_filesystem,
):
    """Test copy_backend_files refuses symlinked backend build metadata."""
    backend_dir = isolated_filesystem / "backend"
    backend_src = backend_dir / "src" / "test_org" / "test_ext"
    backend_src.mkdir(parents=True)
    (backend_src / "__init__.py").write_text("# init")
    outside_pyproject = isolated_filesystem / "outside-pyproject.toml"
    outside_pyproject.write_text(
        """[project]
name = "test_org-test_ext"
version = "1.0.0"
license = "Apache-2.0"

[tool.apache_superset_extensions.build]
include = [
    "src/test_org/test_ext/**/*.py",
]
exclude = []
"""
    )
    (backend_dir / "pyproject.toml").symlink_to(outside_pyproject)

    clean_dist(isolated_filesystem)

    with pytest.raises(
        click.ClickException,
        match="Refusing to read backend/pyproject.toml: path is a symlink",
    ):
        copy_backend_files(isolated_filesystem)

    assert not (
        isolated_filesystem / "dist" / "backend" / "src" / "test_org" / "test_ext"
    ).exists()


@pytest.mark.unit
def test_copy_backend_files_rejects_symlinked_backend_root(isolated_filesystem):
    """Test copy_backend_files refuses a symlinked backend root."""
    outside_backend = isolated_filesystem / "outside-backend"
    backend_src = outside_backend / "src" / "test_org" / "test_ext"
    backend_src.mkdir(parents=True)
    (backend_src / "__init__.py").write_text("# init")
    pyproject_content = """[project]
name = "test_org-test_ext"
version = "1.0.0"
license = "Apache-2.0"

[tool.apache_superset_extensions.build]
include = [
    "src/test_org/test_ext/**/*.py",
]
exclude = []
"""
    (outside_backend / "pyproject.toml").write_text(pyproject_content)
    (isolated_filesystem / "backend").symlink_to(outside_backend)

    clean_dist(isolated_filesystem)

    with pytest.raises(click.ClickException, match="backend path is a symlink"):
        copy_backend_files(isolated_filesystem)

    assert not (isolated_filesystem / "dist" / "backend").exists()


@pytest.mark.unit
def test_copy_backend_files_rejects_symlinked_backend_output_root(
    isolated_filesystem,
):
    """Test copy_backend_files refuses a symlinked dist/backend output root."""
    backend_dir = isolated_filesystem / "backend"
    backend_src = backend_dir / "src" / "test_org" / "test_ext"
    backend_src.mkdir(parents=True)
    (backend_src / "__init__.py").write_text("# init")
    pyproject_content = """[project]
name = "test_org-test_ext"
version = "1.0.0"
license = "Apache-2.0"

[tool.apache_superset_extensions.build]
include = [
    "src/test_org/test_ext/**/*.py",
]
exclude = []
"""
    (backend_dir / "pyproject.toml").write_text(pyproject_content)

    dist_dir = isolated_filesystem / "dist"
    dist_dir.mkdir()
    outside_output = isolated_filesystem / "outside-backend-output"
    outside_output.mkdir()
    (dist_dir / "backend").symlink_to(outside_output)

    with pytest.raises(
        click.ClickException,
        match="Refusing to write backend file .*parent directory is a symlink",
    ):
        copy_backend_files(isolated_filesystem)

    assert not (
        outside_output / "src" / "test_org" / "test_ext" / "__init__.py"
    ).exists()


@pytest.mark.unit
def test_copy_backend_files_rejects_nested_symlinked_backend_output_parent(
    isolated_filesystem,
):
    """Test copy_backend_files refuses nested symlinked output parents."""
    backend_dir = isolated_filesystem / "backend"
    backend_src = backend_dir / "src" / "test_org" / "test_ext"
    nested_src = backend_src / "nested"
    nested_src.mkdir(parents=True)
    (backend_src / "top.py").write_text("# top")
    (nested_src / "module.py").write_text("# nested")
    pyproject_content = """[project]
name = "test_org-test_ext"
version = "1.0.0"
license = "Apache-2.0"

[tool.apache_superset_extensions.build]
include = [
    "src/test_org/test_ext/**/*.py",
]
exclude = []
"""
    (backend_dir / "pyproject.toml").write_text(pyproject_content)

    output_pkg = isolated_filesystem / "dist" / "backend" / "src" / "test_org"
    output_pkg.mkdir(parents=True)
    outside_output = isolated_filesystem / "outside-nested-backend-output"
    outside_output.mkdir()
    (output_pkg / "test_ext").symlink_to(outside_output)

    with pytest.raises(
        click.ClickException,
        match="Refusing to write backend file .*parent directory is a symlink",
    ):
        copy_backend_files(isolated_filesystem)

    assert not (outside_output / "top.py").exists()
    assert not (outside_output / "nested" / "module.py").exists()


@pytest.mark.unit
def test_copy_backend_files_rejects_symlinked_backend_output_file(
    isolated_filesystem,
):
    """Test copy_backend_files refuses symlinked output file targets."""
    backend_dir = isolated_filesystem / "backend"
    backend_src = backend_dir / "src" / "test_org" / "test_ext"
    backend_src.mkdir(parents=True)
    (backend_src / "__init__.py").write_text("# init")
    pyproject_content = """[project]
name = "test_org-test_ext"
version = "1.0.0"
license = "Apache-2.0"

[tool.apache_superset_extensions.build]
include = [
    "src/test_org/test_ext/**/*.py",
]
exclude = []
"""
    (backend_dir / "pyproject.toml").write_text(pyproject_content)

    output_pkg = (
        isolated_filesystem / "dist" / "backend" / "src" / "test_org" / "test_ext"
    )
    output_pkg.mkdir(parents=True)
    outside_file = isolated_filesystem / "outside-init.py"
    outside_file.write_text("# keep")
    (output_pkg / "__init__.py").symlink_to(outside_file)

    with pytest.raises(
        click.ClickException,
        match="Refusing to write backend file .*path is a symlink",
    ):
        copy_backend_files(isolated_filesystem)

    assert outside_file.read_text() == "# keep"


@pytest.mark.unit
def test_copy_backend_files_stages_symlink_at_matched_path(isolated_filesystem):
    """Symlinked files inside backend are staged at the matched path, not the target."""
    backend_dir = isolated_filesystem / "backend"
    target_dir = backend_dir / "src" / "common"
    target_dir.mkdir(parents=True)
    (target_dir / "module.py").write_text("# shared module")

    link_dir = backend_dir / "src" / "test_org" / "test_ext" / "common"
    link_dir.mkdir(parents=True)
    link = link_dir / "module.py"
    link.symlink_to(target_dir / "module.py")

    pyproject_content = """[project]
name = "test_org-test_ext"
version = "1.0.0"
license = "Apache-2.0"

[tool.apache_superset_extensions.build]
include = [
    "src/test_org/test_ext/**/*.py",
]
exclude = []
"""
    (backend_dir / "pyproject.toml").write_text(pyproject_content)

    extension_data = {
        "publisher": "test-org",
        "name": "test-ext",
        "displayName": "Test Extension",
        "version": "1.0.0",
        "permissions": [],
    }
    (isolated_filesystem / "extension.json").write_text(json.dumps(extension_data))

    clean_dist(isolated_filesystem)
    copy_backend_files(isolated_filesystem)

    dist_dir = isolated_filesystem / "dist"
    # Staged at the configured (symlink) path, not the resolved target path.
    assert_file_exists(
        dist_dir / "backend" / "src" / "test_org" / "test_ext" / "common" / "module.py"
    )
    assert not (dist_dir / "backend" / "src" / "common" / "module.py").exists()


# Removed obsolete tests:
# - test_copy_backend_files_handles_no_backend_config: This scenario can't happen since copy_backend_files is only called when backend exists
# - test_copy_backend_files_exits_when_extension_json_missing: Validation catches this before copy_backend_files is called


# Frontend Dist Copy Tests
@pytest.mark.unit
def test_copy_frontend_dist_copies_files_correctly(isolated_filesystem):
    """Test copy_frontend_dist copies frontend build files to dist."""
    # Create frontend/dist structure
    frontend_dist = isolated_filesystem / "frontend" / "dist"
    frontend_dist.mkdir(parents=True)

    # Create some files including remoteEntry
    (frontend_dist / "remoteEntry.abc123.js").write_text("remote entry content")
    (frontend_dist / "main.js").write_text("main js content")

    # Create subdirectory with file
    assets_dir = frontend_dist / "assets"
    assets_dir.mkdir()
    (assets_dir / "style.css").write_text("css content")

    # Create dist directory
    clean_dist(isolated_filesystem)

    remote_entry = copy_frontend_dist(isolated_filesystem)

    assert remote_entry == "remoteEntry.abc123.js"

    # Verify files were copied
    dist_dir = isolated_filesystem / "dist"
    assert_file_exists(dist_dir / "frontend" / "dist" / "remoteEntry.abc123.js")
    assert_file_exists(dist_dir / "frontend" / "dist" / "main.js")
    assert_file_exists(dist_dir / "frontend" / "dist" / "assets" / "style.css")
    assert list(dist_dir.glob(".frontend*.tmp")) == []


@pytest.mark.unit
def test_copy_frontend_dist_reports_copy_failures(isolated_filesystem):
    """Test copy_frontend_dist reports copy failures with frontend asset context."""
    frontend_dist = isolated_filesystem / "frontend" / "dist"
    frontend_dist.mkdir(parents=True)
    (frontend_dist / "remoteEntry.abc123.js").write_text("remote entry content")

    clean_dist(isolated_filesystem)
    existing_output = isolated_filesystem / "dist" / "frontend" / "dist" / "old.js"
    existing_output.parent.mkdir(parents=True)
    existing_output.write_text("old content")

    with patch(
        "superset_extensions_cli.cli.shutil.copy2",
        side_effect=OSError("disk full"),
    ):
        with pytest.raises(
            click.ClickException,
            match="Failed to copy frontend asset remoteEntry\\.abc123\\.js: disk full",
        ):
            copy_frontend_dist(isolated_filesystem)

    assert existing_output.read_text() == "old content"
    assert list((isolated_filesystem / "dist").glob(".frontend*.tmp")) == []


@pytest.mark.unit
def test_copy_frontend_dist_rejects_source_changed_before_copy(
    isolated_filesystem,
    monkeypatch,
):
    """Test frontend staging refuses a source path changed after planning."""
    frontend_dist = isolated_filesystem / "frontend" / "dist"
    frontend_dist.mkdir(parents=True)
    source_file = frontend_dist / "main.js"
    source_file.write_text("main content")
    (frontend_dist / "remoteEntry.abc123.js").write_text("remote entry content")
    outside_file = isolated_filesystem / "outside.js"
    outside_file.write_text("outside")

    from superset_extensions_cli import cli

    original_create_temporary_output_directory = cli.create_temporary_output_directory

    def swap_source_after_planning(parent, prefix, label):
        temp_dir = original_create_temporary_output_directory(parent, prefix, label)
        if prefix == ".frontend.":
            source_file.unlink()
            source_file.symlink_to(outside_file)
        return temp_dir

    monkeypatch.setattr(
        cli,
        "create_temporary_output_directory",
        swap_source_after_planning,
    )

    with pytest.raises(
        click.ClickException,
        match="Refusing to copy frontend asset .*source path changed before copy",
    ):
        copy_frontend_dist(isolated_filesystem)

    assert source_file.is_symlink()
    assert outside_file.read_text() == "outside"
    assert not (isolated_filesystem / "dist" / "frontend" / "dist" / "main.js").exists()
    assert list((isolated_filesystem / "dist").glob(".frontend*.tmp")) == []


@pytest.mark.unit
def test_copy_frontend_dist_rejects_source_root_changed_before_copy(
    isolated_filesystem,
    monkeypatch,
):
    """Test frontend staging refuses a replaced frontend/dist root before copying."""
    frontend_dist = isolated_filesystem / "frontend" / "dist"
    frontend_dist.mkdir(parents=True)
    main_file = frontend_dist / "main.js"
    main_file.write_text("main content")
    remote_entry = frontend_dist / "remoteEntry.abc123.js"
    remote_entry.write_text("remote entry content")
    saved_frontend_dist = isolated_filesystem / "saved-frontend-dist"
    replacement_frontend_dist = isolated_filesystem / "replacement-frontend-dist"

    from superset_extensions_cli import cli

    original_create_temporary_output_directory = cli.create_temporary_output_directory

    def replace_frontend_dist_after_planning(parent, prefix, label):
        temp_dir = original_create_temporary_output_directory(parent, prefix, label)
        if prefix == ".frontend.":
            frontend_dist.rename(saved_frontend_dist)
            replacement_frontend_dist.mkdir()
            (saved_frontend_dist / "main.js").rename(
                replacement_frontend_dist / "main.js"
            )
            (saved_frontend_dist / "remoteEntry.abc123.js").rename(
                replacement_frontend_dist / "remoteEntry.abc123.js"
            )
            replacement_frontend_dist.rename(frontend_dist)
        return temp_dir

    monkeypatch.setattr(
        cli,
        "create_temporary_output_directory",
        replace_frontend_dist_after_planning,
    )

    with pytest.raises(
        click.ClickException,
        match="frontend/dist path changed before copy",
    ):
        copy_frontend_dist(isolated_filesystem)

    assert not (saved_frontend_dist / "main.js").exists()
    assert main_file.read_text() == "main content"
    assert not (isolated_filesystem / "dist" / "frontend" / "dist" / "main.js").exists()
    assert list((isolated_filesystem / "dist").glob(".frontend*.tmp")) == []


@pytest.mark.unit
def test_copy_frontend_dist_rejects_source_parent_changed_before_copy(
    isolated_filesystem,
    monkeypatch,
):
    """Test frontend staging refuses a replaced frontend parent before copying."""
    frontend_dir = isolated_filesystem / "frontend"
    frontend_dist = frontend_dir / "dist"
    frontend_dist.mkdir(parents=True)
    main_file = frontend_dist / "main.js"
    main_file.write_text("main content")
    remote_entry = frontend_dist / "remoteEntry.abc123.js"
    remote_entry.write_text("remote entry content")
    saved_frontend_dir = isolated_filesystem / "saved-frontend"
    replacement_frontend_dir = isolated_filesystem / "replacement-frontend"

    from superset_extensions_cli import cli

    original_create_temporary_output_directory = cli.create_temporary_output_directory

    def replace_frontend_parent_after_planning(parent, prefix, label):
        temp_dir = original_create_temporary_output_directory(parent, prefix, label)
        if prefix == ".frontend.":
            frontend_dir.rename(saved_frontend_dir)
            replacement_frontend_dir.mkdir()
            (saved_frontend_dir / "dist").rename(replacement_frontend_dir / "dist")
            replacement_frontend_dir.rename(frontend_dir)
        return temp_dir

    monkeypatch.setattr(
        cli,
        "create_temporary_output_directory",
        replace_frontend_parent_after_planning,
    )

    with pytest.raises(
        click.ClickException,
        match="frontend/dist path changed before copy",
    ):
        copy_frontend_dist(isolated_filesystem)

    assert not (saved_frontend_dir / "dist").exists()
    assert main_file.read_text() == "main content"
    assert not (isolated_filesystem / "dist" / "frontend" / "dist" / "main.js").exists()
    assert list((isolated_filesystem / "dist").glob(".frontend*.tmp")) == []


@pytest.mark.unit
def test_copy_frontend_dist_rejects_changed_staged_cleanup_root(
    isolated_filesystem,
    monkeypatch,
):
    """Test frontend copy failure does not clean a swapped staged root."""
    frontend_dist = isolated_filesystem / "frontend" / "dist"
    frontend_dist.mkdir(parents=True)
    (frontend_dist / "main.js").write_text("main content")
    (frontend_dist / "remoteEntry.abc123.js").write_text("remote entry content")
    replacement_root = isolated_filesystem / "replacement-frontend-stage"
    replacement_root.mkdir()
    (replacement_root / "replacement.txt").write_text("replacement")
    saved_root = isolated_filesystem / "saved-frontend-stage"
    swapped_root: Path | None = None

    from superset_extensions_cli import cli

    def swap_staged_root_during_copy(source, target, label):
        nonlocal swapped_root
        staged_root = next(
            parent for parent in target.parents if parent.name.startswith(".frontend.")
        )
        staged_root.rename(saved_root)
        replacement_root.rename(staged_root)
        swapped_root = staged_root
        raise click.ClickException("copy failed")

    monkeypatch.setattr(cli, "copy_output_file", swap_staged_root_during_copy)

    with pytest.raises(click.ClickException, match="copy failed"):
        copy_frontend_dist(isolated_filesystem)

    assert swapped_root is not None
    assert_file_exists(swapped_root / "replacement.txt")
    assert saved_root.exists()


@pytest.mark.unit
def test_copy_frontend_dist_removes_stale_output_files(isolated_filesystem):
    """Test copy_frontend_dist replaces stale frontend output with current files."""
    frontend_dist = isolated_filesystem / "frontend" / "dist"
    frontend_dist.mkdir(parents=True)
    (frontend_dist / "remoteEntry.abc123.js").write_text("remote entry content")

    stale_output = isolated_filesystem / "dist" / "frontend" / "dist"
    stale_output.mkdir(parents=True)
    (stale_output / "stale.js").write_text("stale content")

    copy_frontend_dist(isolated_filesystem)

    assert_file_exists(stale_output / "remoteEntry.abc123.js")
    assert not (stale_output / "stale.js").exists()
    assert list((isolated_filesystem / "dist").glob(".frontend*.tmp")) == []


@pytest.mark.unit
def test_copy_frontend_dist_restores_existing_output_on_publish_failure(
    isolated_filesystem, monkeypatch
):
    """Test copy_frontend_dist restores old output when publishing staged output fails."""
    frontend_dist = isolated_filesystem / "frontend" / "dist"
    frontend_dist.mkdir(parents=True)
    (frontend_dist / "remoteEntry.abc123.js").write_text("remote entry content")

    existing_output = isolated_filesystem / "dist" / "frontend" / "dist" / "old.js"
    existing_output.parent.mkdir(parents=True)
    existing_output.write_text("old content")
    frontend_output_dir = isolated_filesystem / "dist" / "frontend"
    original_replace = Path.replace

    def fail_staged_publish(path, target):
        if path.name.startswith(".frontend.") and target == frontend_output_dir:
            raise OSError("permission denied")
        return original_replace(path, target)

    monkeypatch.setattr(Path, "replace", fail_staged_publish)

    with pytest.raises(
        click.ClickException,
        match="Failed to publish dist/frontend directory: permission denied",
    ):
        copy_frontend_dist(isolated_filesystem)

    assert existing_output.read_text() == "old content"
    assert list((isolated_filesystem / "dist").glob(".frontend*.tmp")) == []


@pytest.mark.unit
def test_copy_frontend_dist_stages_symlink_at_matched_path(isolated_filesystem):
    """Test frontend symlinks inside dist are staged at the matched path."""
    frontend_dist = isolated_filesystem / "frontend" / "dist"
    frontend_dist.mkdir(parents=True)
    (frontend_dist / "remoteEntry.abc123.js").write_text("remote entry content")
    target_dir = frontend_dist / "assets"
    target_dir.mkdir()
    (target_dir / "style.css").write_text("css content")
    link_dir = frontend_dist / "linked"
    link_dir.mkdir()
    link = link_dir / "style.css"
    link.symlink_to(target_dir / "style.css")

    clean_dist(isolated_filesystem)
    remote_entry = copy_frontend_dist(isolated_filesystem)

    assert remote_entry == "remoteEntry.abc123.js"
    dist_dir = isolated_filesystem / "dist"
    assert_file_exists(dist_dir / "frontend" / "dist" / "linked" / "style.css")
    assert_file_exists(dist_dir / "frontend" / "dist" / "assets" / "style.css")


@pytest.mark.unit
def test_copy_frontend_dist_rejects_symlink_outside_dist(isolated_filesystem):
    """Test copy_frontend_dist refuses symlinks that escape frontend/dist."""
    frontend_dist = isolated_filesystem / "frontend" / "dist"
    frontend_dist.mkdir(parents=True)
    (frontend_dist / "remoteEntry.abc123.js").write_text("remote entry content")
    (isolated_filesystem / "secret.txt").write_text("SECRET")
    link = frontend_dist / "leaked.txt"
    link.symlink_to(isolated_filesystem / "secret.txt")

    clean_dist(isolated_filesystem)

    with pytest.raises(click.ClickException):
        copy_frontend_dist(isolated_filesystem)

    leaked_file = isolated_filesystem / "dist" / "frontend" / "dist" / "leaked.txt"
    assert not leaked_file.exists()


@pytest.mark.unit
def test_copy_frontend_dist_rejects_symlinked_dist_root(isolated_filesystem):
    """Test copy_frontend_dist refuses a symlinked frontend/dist root."""
    frontend_dir = isolated_filesystem / "frontend"
    frontend_dir.mkdir()
    outside_dist = isolated_filesystem / "outside-dist"
    outside_dist.mkdir()
    (outside_dist / "remoteEntry.abc123.js").write_text("remote entry content")
    (outside_dist / "main.js").write_text("main content")
    (frontend_dir / "dist").symlink_to(outside_dist)

    clean_dist(isolated_filesystem)

    with pytest.raises(click.ClickException, match="frontend/dist path is a symlink"):
        copy_frontend_dist(isolated_filesystem)

    copied_entry = (
        isolated_filesystem / "dist" / "frontend" / "dist" / "remoteEntry.abc123.js"
    )
    assert not copied_entry.exists()


@pytest.mark.unit
def test_copy_frontend_dist_rejects_symlinked_frontend_root(isolated_filesystem):
    """Test copy_frontend_dist refuses a symlinked frontend root."""
    outside_frontend = isolated_filesystem / "outside-frontend"
    outside_dist = outside_frontend / "dist"
    outside_dist.mkdir(parents=True)
    (outside_dist / "remoteEntry.abc123.js").write_text("remote entry content")
    (outside_dist / "main.js").write_text("main content")
    (isolated_filesystem / "frontend").symlink_to(outside_frontend)

    clean_dist(isolated_filesystem)

    with pytest.raises(click.ClickException, match="frontend path is a symlink"):
        copy_frontend_dist(isolated_filesystem)

    copied_entry = (
        isolated_filesystem / "dist" / "frontend" / "dist" / "remoteEntry.abc123.js"
    )
    assert not copied_entry.exists()


@pytest.mark.unit
def test_copy_frontend_dist_rejects_symlinked_frontend_output_root(
    isolated_filesystem,
):
    """Test copy_frontend_dist refuses a symlinked dist/frontend output root."""
    frontend_dist = isolated_filesystem / "frontend" / "dist"
    frontend_dist.mkdir(parents=True)
    (frontend_dist / "remoteEntry.abc123.js").write_text("remote entry content")
    (frontend_dist / "main.js").write_text("main content")

    dist_dir = isolated_filesystem / "dist"
    dist_dir.mkdir()
    outside_output = isolated_filesystem / "outside-frontend-output"
    outside_output.mkdir()
    (dist_dir / "frontend").symlink_to(outside_output)

    with pytest.raises(
        click.ClickException,
        match="Refusing to write frontend asset .*parent directory is a symlink",
    ):
        copy_frontend_dist(isolated_filesystem)

    assert not (outside_output / "dist" / "remoteEntry.abc123.js").exists()


@pytest.mark.unit
def test_copy_frontend_dist_rejects_symlinked_frontend_dist_output_root(
    isolated_filesystem,
):
    """Test copy_frontend_dist refuses a symlinked dist/frontend/dist output root."""
    frontend_dist = isolated_filesystem / "frontend" / "dist"
    frontend_dist.mkdir(parents=True)
    (frontend_dist / "remoteEntry.abc123.js").write_text("remote entry content")
    (frontend_dist / "main.js").write_text("main content")

    output_frontend = isolated_filesystem / "dist" / "frontend"
    output_frontend.mkdir(parents=True)
    outside_output = isolated_filesystem / "outside-frontend-dist-output"
    outside_output.mkdir()
    (output_frontend / "dist").symlink_to(outside_output)

    with pytest.raises(
        click.ClickException,
        match="Refusing to write frontend asset .*parent directory is a symlink",
    ):
        copy_frontend_dist(isolated_filesystem)

    assert not (outside_output / "remoteEntry.abc123.js").exists()


@pytest.mark.unit
def test_copy_frontend_dist_rejects_nested_symlinked_output_parent(
    isolated_filesystem,
):
    """Test copy_frontend_dist refuses nested symlinked output parents."""
    frontend_dist = isolated_filesystem / "frontend" / "dist"
    assets_dir = frontend_dist / "assets"
    assets_dir.mkdir(parents=True)
    (frontend_dist / "remoteEntry.abc123.js").write_text("remote entry content")
    (assets_dir / "style.css").write_text("css content")

    output_dist = isolated_filesystem / "dist" / "frontend" / "dist"
    output_dist.mkdir(parents=True)
    outside_output = isolated_filesystem / "outside-nested-frontend-output"
    outside_output.mkdir()
    (output_dist / "assets").symlink_to(outside_output)

    with pytest.raises(
        click.ClickException,
        match="Refusing to write frontend asset .*parent directory is a symlink",
    ):
        copy_frontend_dist(isolated_filesystem)

    assert not (output_dist / "remoteEntry.abc123.js").exists()
    assert not (outside_output / "style.css").exists()


@pytest.mark.unit
def test_copy_frontend_dist_validates_targets_before_creating_output(
    isolated_filesystem,
):
    """Test frontend target validation runs before creating output directories."""
    frontend_dist = isolated_filesystem / "frontend" / "dist"
    assets_dir = frontend_dist / "assets"
    assets_dir.mkdir(parents=True)
    (frontend_dist / "remoteEntry.abc123.js").write_text("remote entry content")
    (assets_dir / "style.css").write_text("css content")

    output_dist_parent = isolated_filesystem / "dist" / "frontend"
    output_dist_parent.mkdir(parents=True)
    outside_output = isolated_filesystem / "outside-nested-frontend-output"
    outside_output.mkdir()
    (output_dist_parent / "dist").symlink_to(outside_output)

    with pytest.raises(
        click.ClickException,
        match="Refusing to write frontend asset .*parent directory is a symlink",
    ):
        copy_frontend_dist(isolated_filesystem)

    assert not (outside_output / "assets").exists()


@pytest.mark.unit
def test_copy_frontend_dist_rejects_symlinked_output_file(isolated_filesystem):
    """Test copy_frontend_dist refuses symlinked output file targets."""
    frontend_dist = isolated_filesystem / "frontend" / "dist"
    frontend_dist.mkdir(parents=True)
    (frontend_dist / "remoteEntry.abc123.js").write_text("remote entry content")
    (frontend_dist / "main.js").write_text("main content")

    output_dist = isolated_filesystem / "dist" / "frontend" / "dist"
    output_dist.mkdir(parents=True)
    outside_file = isolated_filesystem / "outside-main.js"
    outside_file.write_text("keep")
    (output_dist / "main.js").symlink_to(outside_file)

    with pytest.raises(
        click.ClickException,
        match="Refusing to write frontend asset .*path is a symlink",
    ):
        copy_frontend_dist(isolated_filesystem)

    assert outside_file.read_text() == "keep"


@pytest.mark.unit
def test_copy_frontend_dist_rejects_multiple_remote_entries(isolated_filesystem):
    """Test copy_frontend_dist rejects ambiguous remote entry outputs."""
    frontend_dist = isolated_filesystem / "frontend" / "dist"
    frontend_dist.mkdir(parents=True)
    (frontend_dist / "remoteEntry.abc123.js").write_text("remote entry content")
    (frontend_dist / "remoteEntry.xyz789.js").write_text("remote entry content")
    (frontend_dist / "main.js").write_text("main content")

    clean_dist(isolated_filesystem)

    with pytest.raises(click.ClickException, match="Multiple remote entry files found"):
        copy_frontend_dist(isolated_filesystem)

    copied_main = isolated_filesystem / "dist" / "frontend" / "dist" / "main.js"
    assert not copied_main.exists()


@pytest.mark.unit
def test_copy_frontend_dist_rejects_nested_remote_entry(isolated_filesystem):
    """Test copy_frontend_dist rejects remote entries outside frontend/dist root."""
    frontend_dist = isolated_filesystem / "frontend" / "dist"
    frontend_dist.mkdir(parents=True)
    nested_dir = frontend_dist / "assets"
    nested_dir.mkdir()
    (nested_dir / "remoteEntry.abc123.js").write_text("remote entry content")
    (frontend_dist / "main.js").write_text("main content")

    clean_dist(isolated_filesystem)

    with pytest.raises(click.ClickException, match="Remote entry file must be"):
        copy_frontend_dist(isolated_filesystem)

    copied_main = isolated_filesystem / "dist" / "frontend" / "dist" / "main.js"
    assert not copied_main.exists()


@pytest.mark.unit
def test_copy_frontend_dist_rejects_missing_remote_entry(isolated_filesystem):
    """Test copy_frontend_dist rejects frontend output without a remoteEntry."""
    # Create frontend/dist without remoteEntry file
    frontend_dist = isolated_filesystem / "frontend" / "dist"
    frontend_dist.mkdir(parents=True)
    (frontend_dist / "main.js").write_text("main content")

    clean_dist(isolated_filesystem)

    with pytest.raises(click.ClickException, match="No remote entry file found"):
        copy_frontend_dist(isolated_filesystem)

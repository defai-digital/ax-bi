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
from superset_core.extensions.types import Manifest
from superset_extensions_cli.cli import (
    app,
    build_manifest,
    clean_dist,
    copy_backend_files,
    copy_frontend_dist,
    create_temporary_output_directory,
    ensure_output_directory,
    init_frontend_deps,
    publish_output_file,
    publish_staged_output_directory,
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

    def fail_partial_dist_cleanup(path, label):
        if path == previous_dist and label == "dist directory":
            raise click.ClickException("cleanup denied")
        original_remove_output_directory(path, label)

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

    def fail_backup_cleanup(path, label):
        if path.name.startswith(".frontend-backup."):
            raise click.ClickException("backup cleanup failed")
        original_remove_output_directory(path, label)

    monkeypatch.setattr(cli, "remove_output_directory", fail_backup_cleanup)

    publish_staged_output_directory(staged_dir, output_path, "dist/frontend directory")

    assert_file_exists(output_path / "new.js")
    assert not (output_path / "old.js").exists()
    assert list(isolated_filesystem.glob(".frontend-backup.*.tmp"))


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
def test_run_frontend_build_with_output_messages(isolated_filesystem):
    """Test run_frontend_build produces expected output messages."""
    from superset_extensions_cli.cli import run_frontend_build

    frontend_dir = isolated_filesystem / "frontend"
    frontend_dir.mkdir()

    with patch("subprocess.run") as mock_run:
        mock_result = Mock(returncode=0)
        mock_run.return_value = mock_result

        result = run_frontend_build(frontend_dir)

        assert result.returncode == 0
        mock_run.assert_called_once_with(
            ["npm", "run", "build"], cwd=frontend_dir, text=True
        )


@pytest.mark.unit
def test_run_frontend_build_returns_failure_on_launch_error(
    isolated_filesystem, capsys
):
    """Test run_frontend_build handles npm launch errors without a traceback."""
    from superset_extensions_cli.cli import run_frontend_build

    frontend_dir = isolated_filesystem / "frontend"
    frontend_dir.mkdir()

    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = PermissionError("Permission denied")

        result = run_frontend_build(frontend_dir)

    assert result.returncode == 1
    assert "Failed to run `npm run build`: Permission denied" in capsys.readouterr().err


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

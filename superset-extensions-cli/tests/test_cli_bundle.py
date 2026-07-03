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
import zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import click
import pytest
from superset_extensions_cli.cli import app, get_bundle_default_filename

from tests.utils import assert_file_exists


# Bundle Command Tests
@pytest.mark.cli
@patch("superset_extensions_cli.cli.build")
def test_bundle_command_creates_zip_with_default_name(
    mock_build, cli_runner, isolated_filesystem, extension_setup_for_bundling
):
    """Test bundle command creates zip file with default name."""
    # Mock the build command to do nothing (we'll set up dist manually)
    mock_build.return_value = None

    # Setup extension for bundling (this creates the dist structure)
    extension_setup_for_bundling(isolated_filesystem)

    result = cli_runner.invoke(app, ["bundle"])

    assert result.exit_code == 0
    assert "✅ Bundle created: test-extension-1.0.0.supx" in result.output

    # Verify zip file was created
    zip_path = isolated_filesystem / "test-extension-1.0.0.supx"
    assert_file_exists(zip_path)

    # Verify zip contents
    with zipfile.ZipFile(zip_path, "r") as zipf:
        file_list = zipf.namelist()
        assert "manifest.json" in file_list
        assert "frontend/dist/remoteEntry.abc123.js" in file_list
        assert "frontend/dist/main.js" in file_list
        assert "backend/src/test_org/test_extension/__init__.py" in file_list


@pytest.mark.cli
def test_bundle_default_filename_uses_manifest_metadata():
    """Test default bundle filenames are derived as a single safe filename."""
    assert (
        get_bundle_default_filename("test-extension", "1.0.0")
        == "test-extension-1.0.0.supx"
    )


@pytest.mark.cli
@pytest.mark.parametrize(
    "extension_name, extension_version",
    [
        ("test-extension", "../1.0.0"),
        ("test-extension", r"..\1.0.0"),
        ("test/extension", "1.0.0"),
        (r"test\extension", "1.0.0"),
    ],
)
def test_bundle_default_filename_rejects_path_metadata(
    extension_name, extension_version
):
    """Test manifest metadata cannot produce a nested bundle path."""
    with pytest.raises(
        click.ClickException,
        match="Invalid bundle default filename from manifest metadata",
    ):
        get_bundle_default_filename(extension_name, extension_version)


@pytest.mark.cli
@patch("superset_extensions_cli.cli.build")
def test_bundle_command_with_custom_output_filename(
    mock_build, cli_runner, isolated_filesystem, extension_setup_for_bundling
):
    """Test bundle command with custom output filename."""
    # Mock the build command
    mock_build.return_value = None

    extension_setup_for_bundling(isolated_filesystem)

    custom_name = "my_custom_bundle.supx"
    result = cli_runner.invoke(app, ["bundle", "--output", custom_name])

    assert result.exit_code == 0
    assert f"✅ Bundle created: {custom_name}" in result.output

    # Verify custom-named zip file was created
    zip_path = isolated_filesystem / custom_name
    assert_file_exists(zip_path)


@pytest.mark.cli
@patch("superset_extensions_cli.cli.build")
def test_bundle_command_with_output_directory(
    mock_build, cli_runner, isolated_filesystem, extension_setup_for_bundling
):
    """Test bundle command with output directory."""
    # Mock the build command
    mock_build.return_value = None

    extension_setup_for_bundling(isolated_filesystem)

    # Create output directory
    output_dir = isolated_filesystem / "output"
    output_dir.mkdir()

    result = cli_runner.invoke(app, ["bundle", "--output", str(output_dir)])

    assert result.exit_code == 0

    # Verify zip file was created in output directory
    expected_path = output_dir / "test-extension-1.0.0.supx"
    assert_file_exists(expected_path)
    assert f"✅ Bundle created: {expected_path}" in result.output


@pytest.mark.cli
@patch("superset_extensions_cli.cli.build")
def test_bundle_command_fails_without_manifest(
    mock_build, cli_runner, isolated_filesystem
):
    """Test bundle command fails when manifest.json doesn't exist."""
    # Mock build to succeed but not create manifest
    mock_build.return_value = None

    # Create empty dist directory
    (isolated_filesystem / "dist").mkdir()

    result = cli_runner.invoke(app, ["bundle"])

    assert result.exit_code == 1
    assert "dist/manifest.json not found" in result.output


@pytest.mark.cli
@patch("superset_extensions_cli.cli.build")
def test_bundle_rejects_symlinked_dist_root(
    mock_build, cli_runner, isolated_filesystem
):
    """Test bundle refuses a symlinked dist root."""
    mock_build.return_value = None

    outside_dist = isolated_filesystem / "outside-dist"
    outside_dist.mkdir()
    (outside_dist / "manifest.json").write_text(
        json.dumps(
            {
                "id": "test-org.test-extension",
                "publisher": "test-org",
                "name": "test-extension",
                "displayName": "Test Extension",
                "version": "1.0.0",
                "permissions": [],
            }
        )
    )
    (isolated_filesystem / "dist").symlink_to(outside_dist)

    result = cli_runner.invoke(app, ["bundle"])

    assert result.exit_code == 1
    assert "dist path is a symlink" in result.output
    assert not (isolated_filesystem / "test-extension-1.0.0.supx").exists()


@pytest.mark.cli
@patch("superset_extensions_cli.cli.build")
def test_bundle_command_fails_with_malformed_manifest_json(
    mock_build, cli_runner, isolated_filesystem
):
    """Test bundle command fails cleanly when manifest.json is malformed."""
    mock_build.return_value = None

    dist_dir = isolated_filesystem / "dist"
    dist_dir.mkdir()
    (dist_dir / "manifest.json").write_text("{ invalid json")

    result = cli_runner.invoke(app, ["bundle"])

    assert result.exit_code == 1
    assert "Invalid dist/manifest.json" in result.output


@pytest.mark.cli
@patch("superset_extensions_cli.cli.build")
def test_bundle_reports_manifest_read_errors(
    mock_build, cli_runner, isolated_filesystem, monkeypatch
):
    """Test bundle reports filesystem failures while reading manifest."""
    mock_build.return_value = None

    dist_dir = isolated_filesystem / "dist"
    dist_dir.mkdir()
    manifest_path = dist_dir / "manifest.json"
    manifest_path.write_text("{}")
    original_read_text = Path.read_text

    def fail_manifest_read(path, *args, **kwargs):
        if path == manifest_path:
            raise OSError("permission denied")
        return original_read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", fail_manifest_read)

    result = cli_runner.invoke(app, ["bundle"])

    assert result.exit_code == 1
    assert "Failed to read dist/manifest.json: permission denied" in result.output
    assert "Invalid dist/manifest.json" not in result.output
    assert not (isolated_filesystem / "test-extension-1.0.0.supx").exists()


@pytest.mark.cli
@patch("superset_extensions_cli.cli.build")
def test_bundle_fails_when_manifest_becomes_unsafe_during_read(
    mock_build, cli_runner, isolated_filesystem, monkeypatch
):
    """Test bundle refuses manifest content when the read boundary changes."""
    mock_build.return_value = None

    dist_dir = isolated_filesystem / "dist"
    dist_dir.mkdir()
    manifest_path = dist_dir / "manifest.json"
    manifest_path.write_text("{}")
    outside_manifest = isolated_filesystem / "outside-manifest.json"
    outside_manifest.write_text(
        json.dumps(
            {
                "id": "test-org.test-extension",
                "publisher": "test-org",
                "name": "test-extension",
                "displayName": "Test Extension",
                "version": "1.0.0",
                "permissions": [],
            }
        )
    )
    original_read_text = Path.read_text

    def replace_manifest_during_read(path, *args, **kwargs):
        if path == manifest_path:
            manifest_path.unlink()
            manifest_path.symlink_to(outside_manifest)
            return original_read_text(outside_manifest, *args, **kwargs)
        return original_read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", replace_manifest_during_read)

    result = cli_runner.invoke(app, ["bundle"])

    assert result.exit_code == 1
    assert "Failed to read dist/manifest.json" in result.output
    assert "path is a symlink" in result.output
    assert not (isolated_filesystem / "test-extension-1.0.0.supx").exists()


@pytest.mark.cli
@patch("superset_extensions_cli.cli.build")
def test_bundle_fails_when_manifest_is_replaced_during_read(
    mock_build, cli_runner, isolated_filesystem, monkeypatch
):
    """Test bundle refuses manifest content when file identity changes."""
    mock_build.return_value = None

    dist_dir = isolated_filesystem / "dist"
    dist_dir.mkdir()
    manifest_path = dist_dir / "manifest.json"
    manifest_path.write_text("{}")
    replacement_manifest = isolated_filesystem / "replacement-manifest.json"
    replacement_manifest.write_text(
        json.dumps(
            {
                "id": "test-org.test-extension",
                "publisher": "test-org",
                "name": "test-extension",
                "displayName": "Test Extension",
                "version": "1.0.0",
                "permissions": [],
            }
        )
    )
    original_read_text = Path.read_text

    def replace_manifest_during_read(path, *args, **kwargs):
        if path == manifest_path:
            content = original_read_text(replacement_manifest, *args, **kwargs)
            manifest_path.unlink()
            manifest_path.write_text(content)
            return content
        return original_read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", replace_manifest_during_read)

    result = cli_runner.invoke(app, ["bundle"])

    assert result.exit_code == 1
    assert "Failed to read dist/manifest.json" in result.output
    assert "path changed during read" in result.output
    assert not (isolated_filesystem / "test-extension-1.0.0.supx").exists()


@pytest.mark.cli
@patch("superset_extensions_cli.cli.build")
def test_bundle_fails_when_manifest_parent_is_replaced_during_read(
    mock_build, cli_runner, isolated_filesystem, monkeypatch
):
    """Test bundle refuses manifest content when parent identity changes."""
    mock_build.return_value = None

    dist_dir = isolated_filesystem / "dist"
    dist_dir.mkdir()
    manifest_path = dist_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "id": "test-org.test-extension",
                "publisher": "test-org",
                "name": "test-extension",
                "displayName": "Test Extension",
                "version": "1.0.0",
                "permissions": [],
            }
        )
    )
    saved_dist = isolated_filesystem / "saved-dist"
    replacement_dist = isolated_filesystem / "replacement-dist"
    original_read_text = Path.read_text

    def replace_parent_during_read(path, *args, **kwargs):
        if path == manifest_path:
            dist_dir.rename(saved_dist)
            replacement_dist.mkdir()
            (saved_dist / "manifest.json").rename(replacement_dist / "manifest.json")
            replacement_dist.rename(dist_dir)
        return original_read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", replace_parent_during_read)

    result = cli_runner.invoke(app, ["bundle"])

    assert result.exit_code == 1
    assert "Failed to read dist/manifest.json" in result.output
    assert "path changed during read" in result.output
    assert not (saved_dist / "manifest.json").exists()
    assert not (isolated_filesystem / "test-extension-1.0.0.supx").exists()


@pytest.mark.cli
@patch("superset_extensions_cli.cli.build")
def test_bundle_command_fails_with_invalid_manifest_schema(
    mock_build, cli_runner, isolated_filesystem
):
    """Test bundle command fails cleanly when manifest.json is incomplete."""
    mock_build.return_value = None

    dist_dir = isolated_filesystem / "dist"
    dist_dir.mkdir()
    (dist_dir / "manifest.json").write_text(json.dumps({"version": "1.0.0"}))

    result = cli_runner.invoke(app, ["bundle"])

    assert result.exit_code == 1
    assert "Invalid dist/manifest.json" in result.output


@pytest.mark.cli
@patch("superset_extensions_cli.cli.build")
def test_bundle_rejects_manifest_metadata_that_builds_nested_default_filename(
    mock_build, cli_runner, isolated_filesystem, monkeypatch
):
    """Test bundle fails before writing when metadata builds a nested filename."""
    mock_build.return_value = None

    dist_dir = isolated_filesystem / "dist"
    dist_dir.mkdir()
    (dist_dir / "manifest.json").write_text("{}")

    monkeypatch.setattr(
        "superset_extensions_cli.cli.Manifest.model_validate_json",
        lambda _: SimpleNamespace(name="test/extension", version="1.0.0"),
    )

    result = cli_runner.invoke(app, ["bundle"])

    assert result.exit_code == 1
    assert "Invalid bundle default filename from manifest metadata" in result.output
    assert not (isolated_filesystem / "test").exists()


@pytest.mark.cli
@patch("superset_extensions_cli.cli.build")
def test_bundle_rejects_manifest_symlink(mock_build, cli_runner, isolated_filesystem):
    """Test bundle refuses to read a symlinked manifest."""
    mock_build.return_value = None

    dist_dir = isolated_filesystem / "dist"
    dist_dir.mkdir()
    outside_manifest = isolated_filesystem / "outside-manifest.json"
    outside_manifest.write_text(
        json.dumps(
            {
                "id": "test-org.test-extension",
                "publisher": "test-org",
                "name": "test-extension",
                "displayName": "Test Extension",
                "version": "1.0.0",
                "permissions": [],
            }
        )
    )
    (dist_dir / "manifest.json").symlink_to(outside_manifest)

    result = cli_runner.invoke(app, ["bundle"])

    assert result.exit_code == 1
    assert "Refusing to read dist/manifest.json: path is a symlink" in result.output
    assert not (isolated_filesystem / "test-extension-1.0.0.supx").exists()


@pytest.mark.cli
@patch("superset_extensions_cli.cli.build")
def test_bundle_rejects_manifest_directory(mock_build, cli_runner, isolated_filesystem):
    """Test bundle refuses manifest paths that are not files."""
    mock_build.return_value = None

    dist_dir = isolated_filesystem / "dist"
    dist_dir.mkdir()
    (dist_dir / "manifest.json").mkdir()

    result = cli_runner.invoke(app, ["bundle"])

    assert result.exit_code == 1
    assert "dist/manifest.json: path exists but is not a file" in result.output


@pytest.mark.cli
@patch("superset_extensions_cli.cli.build")
def test_bundle_command_handles_zip_creation_error(
    mock_build, cli_runner, isolated_filesystem, extension_setup_for_bundling
):
    """Test bundle command handles zip file creation errors."""
    # Mock the build command
    mock_build.return_value = None

    extension_setup_for_bundling(isolated_filesystem)

    # Try to bundle to an invalid location (directory that doesn't exist)
    invalid_path = isolated_filesystem / "nonexistent" / "bundle.supx"

    with patch("zipfile.ZipFile", side_effect=OSError("Permission denied")):
        result = cli_runner.invoke(app, ["bundle", "--output", str(invalid_path)])

        assert result.exit_code == 1
        assert "Failed to create bundle" in result.output


@pytest.mark.cli
@patch("superset_extensions_cli.cli.build")
def test_bundle_preserves_existing_output_on_zip_write_error(
    mock_build,
    cli_runner,
    isolated_filesystem,
    extension_setup_for_bundling,
    monkeypatch,
):
    """Test bundle writes atomically when archive creation fails mid-write."""
    mock_build.return_value = None
    extension_setup_for_bundling(isolated_filesystem)
    output_path = isolated_filesystem / "existing.supx"
    output_path.write_text("original bundle")

    def fail_zip_write(self, *args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(zipfile.ZipFile, "write", fail_zip_write)

    result = cli_runner.invoke(app, ["bundle", "--output", str(output_path)])

    assert result.exit_code == 1
    assert "Failed to create bundle" in result.output
    assert "disk full" in result.output
    assert output_path.read_text() == "original bundle"
    assert list(isolated_filesystem.glob(".existing.supx.*.tmp")) == []


@pytest.mark.cli
@patch("superset_extensions_cli.cli.build")
def test_bundle_preserves_existing_output_on_publish_error(
    mock_build,
    cli_runner,
    isolated_filesystem,
    extension_setup_for_bundling,
    monkeypatch,
):
    """Test bundle keeps old output when publishing the staged archive fails."""
    mock_build.return_value = None
    extension_setup_for_bundling(isolated_filesystem)
    output_path = isolated_filesystem / "existing.supx"
    output_path.write_text("original bundle")
    original_replace = Path.replace

    def fail_bundle_publish(path, target):
        if target == output_path:
            raise OSError("permission denied")
        return original_replace(path, target)

    monkeypatch.setattr(Path, "replace", fail_bundle_publish)

    result = cli_runner.invoke(app, ["bundle", "--output", str(output_path)])

    assert result.exit_code == 1
    assert "Failed to create bundle" in result.output
    assert "Failed to publish bundle: permission denied" in result.output
    assert output_path.read_text() == "original bundle"
    assert list(isolated_filesystem.glob(".existing.supx.*.tmp")) == []


@pytest.mark.cli
@patch("superset_extensions_cli.cli.build")
def test_bundle_revalidates_output_path_before_publish(
    mock_build,
    cli_runner,
    isolated_filesystem,
    extension_setup_for_bundling,
    monkeypatch,
):
    """Test bundle refuses an output path changed after archive creation."""
    mock_build.return_value = None
    extension_setup_for_bundling(isolated_filesystem)
    output_path = isolated_filesystem / "existing.supx"
    output_path.write_text("original bundle")
    outside_file = isolated_filesystem / "outside.supx"
    outside_file.write_text("outside bundle")
    original_zip_write = zipfile.ZipFile.write

    def replace_output_with_symlink_after_zip_write(self, *args, **kwargs):
        result = original_zip_write(self, *args, **kwargs)
        if output_path.exists() and not output_path.is_symlink():
            output_path.unlink()
            output_path.symlink_to(outside_file)
        return result

    monkeypatch.setattr(
        zipfile.ZipFile,
        "write",
        replace_output_with_symlink_after_zip_write,
    )

    result = cli_runner.invoke(app, ["bundle", "--output", str(output_path)])

    assert result.exit_code == 1
    assert "Failed to create bundle" in result.output
    assert "Refusing to write bundle to symlink" in result.output
    assert output_path.is_symlink()
    assert outside_file.read_text() == "outside bundle"
    assert list(isolated_filesystem.glob(".existing.supx.*.tmp")) == []


@pytest.mark.cli
@patch("superset_extensions_cli.cli.build")
def test_bundle_rejects_changed_temp_archive_before_publish(
    mock_build,
    cli_runner,
    isolated_filesystem,
    extension_setup_for_bundling,
    monkeypatch,
):
    """Test bundle refuses to publish a replaced temporary archive."""
    mock_build.return_value = None
    extension_setup_for_bundling(isolated_filesystem)
    saved_temp = isolated_filesystem / "saved-temp.supx"
    replacement_temp = isolated_filesystem / "replacement-temp.supx"
    replacement_temp.write_text("replacement bundle")
    swapped_temp_path: Path | None = None
    original_zip_write = zipfile.ZipFile.write

    def swap_temp_after_zip_write(self, *args, **kwargs):
        nonlocal swapped_temp_path
        result = original_zip_write(self, *args, **kwargs)
        if swapped_temp_path is None:
            temp_archive = Path(self.filename)
            temp_archive.rename(saved_temp)
            replacement_temp.replace(temp_archive)
            swapped_temp_path = temp_archive
        return result

    monkeypatch.setattr(zipfile.ZipFile, "write", swap_temp_after_zip_write)

    result = cli_runner.invoke(app, ["bundle"])

    assert result.exit_code == 1
    assert "Failed to create bundle" in result.output
    assert "temporary archive is not a valid zip" in result.output
    assert swapped_temp_path is not None
    assert swapped_temp_path.read_text() == "replacement bundle"
    assert saved_temp.exists()
    assert not (isolated_filesystem / "test-extension-1.0.0.supx").exists()


@pytest.mark.cli
@patch("superset_extensions_cli.cli.build")
def test_bundle_rejects_invalid_temp_archive_before_publish(
    mock_build,
    cli_runner,
    isolated_filesystem,
    extension_setup_for_bundling,
    monkeypatch,
):
    """Test bundle verifies the temporary archive before publishing."""
    mock_build.return_value = None
    extension_setup_for_bundling(isolated_filesystem)
    original_exit = zipfile.ZipFile.__exit__
    rewritten_temp_path: Path | None = None

    def rewrite_temp_archive_after_zip_close(self, exc_type, exc_value, traceback):
        nonlocal rewritten_temp_path
        result = original_exit(self, exc_type, exc_value, traceback)
        if rewritten_temp_path is None:
            temp_archive = Path(self.filename)
            if temp_archive.name.startswith(".test-extension-1.0.0.supx."):
                temp_archive.write_text("not a zip")
                rewritten_temp_path = temp_archive
        return result

    monkeypatch.setattr(
        zipfile.ZipFile, "__exit__", rewrite_temp_archive_after_zip_close
    )

    result = cli_runner.invoke(app, ["bundle"])

    assert result.exit_code == 1
    assert "Failed to create bundle" in result.output
    assert "temporary archive is not a valid zip" in result.output
    assert rewritten_temp_path is not None
    assert not rewritten_temp_path.exists()
    assert not (isolated_filesystem / "test-extension-1.0.0.supx").exists()


@pytest.mark.cli
@patch("superset_extensions_cli.cli.build")
def test_bundle_rejects_source_changed_during_archive_verification(
    mock_build,
    cli_runner,
    isolated_filesystem,
    extension_setup_for_bundling,
    monkeypatch,
):
    """Test bundle refuses source content changed during archive verification."""
    mock_build.return_value = None
    extension_setup_for_bundling(isolated_filesystem)
    source_file = isolated_filesystem / "dist" / "frontend" / "dist" / "main.js"
    original_read_bytes = Path.read_bytes
    changed = False

    def change_source_during_read(path):
        nonlocal changed
        if path == source_file and not changed:
            content = original_read_bytes(path)
            path.write_bytes(content + b"\nchanged")
            changed = True
            return content
        return original_read_bytes(path)

    monkeypatch.setattr(Path, "read_bytes", change_source_during_read)

    result = cli_runner.invoke(app, ["bundle"])

    assert result.exit_code == 1
    assert "Failed to create bundle" in result.output
    assert "source path changed before copy" in result.output
    assert changed
    assert not (isolated_filesystem / "test-extension-1.0.0.supx").exists()


@pytest.mark.cli
@patch("superset_extensions_cli.cli.build")
def test_bundle_rejects_temp_archive_content_changed_before_publish(
    mock_build,
    cli_runner,
    isolated_filesystem,
    extension_setup_for_bundling,
    monkeypatch,
):
    """Test bundle refuses a temporary archive rewritten before publish."""
    mock_build.return_value = None
    extension_setup_for_bundling(isolated_filesystem)

    from superset_extensions_cli import cli

    original_validate_bundle_output_path = cli.validate_bundle_output_path
    validation_calls = 0

    def rewrite_temp_archive_before_publish(path):
        nonlocal validation_calls
        original_validate_bundle_output_path(path)
        validation_calls += 1
        if validation_calls == 2:
            temp_archive = next(
                isolated_filesystem.glob(".test-extension-*.supx.*.tmp")
            )
            temp_archive.write_text("rewritten temporary archive")

    monkeypatch.setattr(
        cli,
        "validate_bundle_output_path",
        rewrite_temp_archive_before_publish,
    )

    result = cli_runner.invoke(app, ["bundle"])

    assert result.exit_code == 1
    assert "Failed to create bundle" in result.output
    assert "staged path changed before publish" in result.output
    assert not (isolated_filesystem / "test-extension-1.0.0.supx").exists()


@pytest.mark.cli
@patch("superset_extensions_cli.cli.build")
def test_bundle_rejects_output_parent_changed_before_temp_creation(
    mock_build,
    cli_runner,
    isolated_filesystem,
    extension_setup_for_bundling,
    monkeypatch,
):
    """Test bundle refuses an output parent changed during entry planning."""
    mock_build.return_value = None
    extension_setup_for_bundling(isolated_filesystem)
    output_dir = isolated_filesystem / "output"
    output_dir.mkdir()
    output_path = output_dir / "bundle.supx"
    saved_output_dir = isolated_filesystem / "saved-output"
    replacement_output_dir = isolated_filesystem / "replacement-output"
    replacement_output_dir.mkdir()

    from superset_extensions_cli import cli

    original_get_copy_source_identity = cli.get_copy_source_identity
    swapped = False

    def swap_output_parent_during_entry_planning(source, root):
        nonlocal swapped
        identity = original_get_copy_source_identity(source, root)
        if identity is not None and not swapped:
            output_dir.rename(saved_output_dir)
            replacement_output_dir.rename(output_dir)
            swapped = True
        return identity

    monkeypatch.setattr(
        cli,
        "get_copy_source_identity",
        swap_output_parent_during_entry_planning,
    )

    result = cli_runner.invoke(app, ["bundle", "--output", str(output_path)])

    assert result.exit_code == 1
    assert "Failed to create bundle" in result.output
    assert "parent directory changed" in result.output
    assert saved_output_dir.is_dir()
    assert output_dir.is_dir()
    assert not (output_dir / "bundle.supx").exists()


@pytest.mark.cli
@patch("superset_extensions_cli.cli.build")
def test_bundle_rejects_output_directory_changed_after_path_selection(
    mock_build,
    cli_runner,
    isolated_filesystem,
    extension_setup_for_bundling,
    monkeypatch,
):
    """Test bundle refuses a directory output changed after path selection."""
    mock_build.return_value = None
    extension_setup_for_bundling(isolated_filesystem)
    output_dir = isolated_filesystem / "output"
    output_dir.mkdir()
    saved_output_dir = isolated_filesystem / "saved-output"
    replacement_output_dir = isolated_filesystem / "replacement-output"
    replacement_output_dir.mkdir()

    from superset_extensions_cli import cli

    original_get_directory_path_identity = cli.get_directory_path_identity
    identity_reads = 0

    def swap_output_directory_after_path_selection(path):
        nonlocal identity_reads
        identity = original_get_directory_path_identity(path)
        if path == output_dir:
            identity_reads += 1
            if identity_reads == 1:
                output_dir.rename(saved_output_dir)
                replacement_output_dir.rename(output_dir)
        return identity

    monkeypatch.setattr(
        cli,
        "get_directory_path_identity",
        swap_output_directory_after_path_selection,
    )

    result = cli_runner.invoke(app, ["bundle", "--output", str(output_dir)])

    assert result.exit_code == 1
    assert "Failed to create bundle" in result.output
    assert "output directory changed" in result.output
    assert saved_output_dir.is_dir()
    assert output_dir.is_dir()
    assert not (output_dir / "test-extension-1.0.0.supx").exists()


@pytest.mark.cli
@patch("superset_extensions_cli.cli.build")
def test_bundle_includes_all_files_recursively(
    mock_build, cli_runner, isolated_filesystem
):
    """Test that bundle includes all files from dist directory recursively."""
    # Mock the build command
    mock_build.return_value = None

    # Create complex dist structure
    dist_dir = isolated_filesystem / "dist"
    dist_dir.mkdir(parents=True)

    # Manifest
    manifest = {
        "id": "complex-org.complex-extension",
        "publisher": "complex-org",
        "name": "complex-extension",
        "displayName": "Complex Extension",
        "version": "2.1.0",
        "permissions": [],
    }
    (dist_dir / "manifest.json").write_text(json.dumps(manifest))

    # Frontend files with nested structure
    frontend_dir = dist_dir / "frontend" / "dist"
    frontend_dir.mkdir(parents=True)
    (frontend_dir / "remoteEntry.xyz789.js").write_text("// entry")

    assets_dir = frontend_dir / "assets"
    assets_dir.mkdir()
    (assets_dir / "style.css").write_text("/* css */")
    (assets_dir / "image.png").write_bytes(b"fake image data")

    # Backend files with nested structure
    backend_dir = dist_dir / "backend" / "src" / "complex_extension"
    backend_dir.mkdir(parents=True)
    (backend_dir / "__init__.py").write_text("# init")
    (backend_dir / "core.py").write_text("# core")

    utils_dir = backend_dir / "utils"
    utils_dir.mkdir()
    (utils_dir / "helpers.py").write_text("# helpers")

    result = cli_runner.invoke(app, ["bundle"])

    assert result.exit_code == 0

    # Verify zip file and contents
    zip_path = isolated_filesystem / "complex-extension-2.1.0.supx"
    assert_file_exists(zip_path)

    with zipfile.ZipFile(zip_path, "r") as zipf:
        file_list = set(zipf.namelist())

        # Verify all files are included
        expected_files = {
            "manifest.json",
            "frontend/dist/remoteEntry.xyz789.js",
            "frontend/dist/assets/style.css",
            "frontend/dist/assets/image.png",
            "backend/src/complex_extension/__init__.py",
            "backend/src/complex_extension/core.py",
            "backend/src/complex_extension/utils/helpers.py",
        }

        assert expected_files.issubset(file_list), (
            f"Missing files: {expected_files - file_list}"
        )


@pytest.mark.cli
@patch("superset_extensions_cli.cli.build")
def test_bundle_skips_cli_temporary_dist_artifacts(
    mock_build, cli_runner, isolated_filesystem
):
    """Test bundle excludes stale CLI temporary artifacts from dist."""
    mock_build.return_value = None

    dist_dir = isolated_filesystem / "dist"
    dist_dir.mkdir(parents=True)
    manifest = {
        "id": "test-org.test-extension",
        "publisher": "test-org",
        "name": "test-extension",
        "displayName": "Test Extension",
        "version": "1.0.0",
        "permissions": [],
    }
    (dist_dir / "manifest.json").write_text(json.dumps(manifest))
    frontend_dir = dist_dir / "frontend" / "dist"
    frontend_dir.mkdir(parents=True)
    (frontend_dir / "remoteEntry.abc123.js").write_text("// entry")
    backend_dir = dist_dir / "backend"
    backend_dir.mkdir()
    (backend_dir / "module.py").write_text("# module")

    frontend_backup = dist_dir / ".frontend-backup.abcd.tmp" / "frontend"
    frontend_backup.mkdir(parents=True)
    (frontend_backup / "old.js").write_text("old")
    backend_staging = dist_dir / ".backend.abcd.tmp" / "backend"
    backend_staging.mkdir(parents=True)
    (backend_staging / "old.py").write_text("old")
    (dist_dir / ".test-extension-1.0.0.supx.abcd.tmp").write_text("partial")
    releases_dir = dist_dir / "releases"
    releases_dir.mkdir()
    (releases_dir / ".test-extension-1.0.0.supx.abcd.tmp").write_text("partial")

    result = cli_runner.invoke(app, ["bundle"])

    assert result.exit_code == 0
    with zipfile.ZipFile(isolated_filesystem / "test-extension-1.0.0.supx") as zipf:
        file_list = set(zipf.namelist())

    assert "manifest.json" in file_list
    assert "frontend/dist/remoteEntry.abc123.js" in file_list
    assert "backend/module.py" in file_list
    assert not any(name.startswith(".frontend-backup.") for name in file_list)
    assert not any(name.startswith(".backend.") for name in file_list)
    assert ".test-extension-1.0.0.supx.abcd.tmp" not in file_list
    assert "releases/.test-extension-1.0.0.supx.abcd.tmp" not in file_list


@pytest.mark.cli
@patch("superset_extensions_cli.cli.build")
def test_bundle_rejects_dist_symlink_outside_dist(
    mock_build, cli_runner, isolated_filesystem
):
    """Test bundle command refuses files that resolve outside dist."""
    mock_build.return_value = None

    dist_dir = isolated_filesystem / "dist"
    dist_dir.mkdir(parents=True)
    manifest = {
        "id": "test-org.test-extension",
        "publisher": "test-org",
        "name": "test-extension",
        "displayName": "Test Extension",
        "version": "1.0.0",
        "permissions": [],
    }
    (dist_dir / "manifest.json").write_text(json.dumps(manifest))
    (isolated_filesystem / "secret.txt").write_text("SECRET")
    (dist_dir / "leaked.txt").symlink_to(isolated_filesystem / "secret.txt")

    result = cli_runner.invoke(app, ["bundle"])

    assert result.exit_code == 1
    assert "resolved path is outside the dist directory" in result.output
    assert not (isolated_filesystem / "test-extension-1.0.0.supx").exists()


@pytest.mark.cli
@patch("superset_extensions_cli.cli.build")
def test_bundle_rejects_dist_entry_changed_before_zip_write(
    mock_build,
    cli_runner,
    isolated_filesystem,
    extension_setup_for_bundling,
    monkeypatch,
):
    """Test bundle refuses a dist file changed after entry planning."""
    mock_build.return_value = None
    extension_setup_for_bundling(isolated_filesystem)
    source_file = isolated_filesystem / "dist" / "frontend" / "dist" / "main.js"
    outside_file = isolated_filesystem / "outside.js"
    outside_file.write_text("outside")
    original_enter = zipfile.ZipFile.__enter__

    def replace_source_with_symlink_on_zip_open(self):
        result = original_enter(self)
        if source_file.exists() and not source_file.is_symlink():
            source_file.unlink()
            source_file.symlink_to(outside_file)
        return result

    monkeypatch.setattr(
        zipfile.ZipFile, "__enter__", replace_source_with_symlink_on_zip_open
    )

    result = cli_runner.invoke(app, ["bundle"])

    assert result.exit_code == 1
    assert "Failed to create bundle" in result.output
    assert "Refusing to copy bundle entry frontend/dist/main.js" in result.output
    assert "source path changed before copy" in result.output
    assert source_file.is_symlink()
    assert outside_file.read_text() == "outside"
    assert not (isolated_filesystem / "test-extension-1.0.0.supx").exists()
    assert list(isolated_filesystem.glob(".test-extension-1.0.0.supx.*.tmp")) == []


@pytest.mark.cli
@patch("superset_extensions_cli.cli.build")
def test_bundle_rejects_dist_root_changed_before_zip_write(
    mock_build,
    cli_runner,
    isolated_filesystem,
    extension_setup_for_bundling,
    monkeypatch,
):
    """Test bundle refuses a replaced dist root before writing entries."""
    mock_build.return_value = None
    extension_setup_for_bundling(isolated_filesystem)
    dist_dir = isolated_filesystem / "dist"
    saved_dist = isolated_filesystem / "saved-dist"
    replacement_dist = isolated_filesystem / "replacement-dist"
    original_enter = zipfile.ZipFile.__enter__

    def replace_dist_root_on_zip_open(self):
        result = original_enter(self)
        if dist_dir.exists() and not saved_dist.exists():
            dist_dir.rename(saved_dist)
            replacement_dist.mkdir()
            for item in sorted(saved_dist.rglob("*"), key=lambda path: len(path.parts)):
                relative_item = item.relative_to(saved_dist)
                replacement_item = replacement_dist / relative_item
                if item.is_dir():
                    replacement_item.mkdir()
                elif item.is_file():
                    replacement_item.parent.mkdir(parents=True, exist_ok=True)
                    item.rename(replacement_item)
            replacement_dist.rename(dist_dir)
        return result

    monkeypatch.setattr(zipfile.ZipFile, "__enter__", replace_dist_root_on_zip_open)

    result = cli_runner.invoke(app, ["bundle"])

    assert result.exit_code == 1
    assert "Failed to create bundle" in result.output
    assert "dist path changed before bundle copy" in result.output
    assert (dist_dir / "manifest.json").exists()
    assert not (saved_dist / "manifest.json").exists()
    assert not (isolated_filesystem / "test-extension-1.0.0.supx").exists()
    assert list(isolated_filesystem.glob(".test-extension-1.0.0.supx.*.tmp")) == []


@pytest.mark.cli
@patch("superset_extensions_cli.cli.build")
def test_bundle_rejects_dist_symlink_to_external_output(
    mock_build, cli_runner, isolated_filesystem
):
    """Test bundle refuses dist symlinks even when they point at the output file."""
    mock_build.return_value = None

    dist_dir = isolated_filesystem / "dist"
    dist_dir.mkdir(parents=True)
    manifest = {
        "id": "test-org.test-extension",
        "publisher": "test-org",
        "name": "test-extension",
        "displayName": "Test Extension",
        "version": "1.0.0",
        "permissions": [],
    }
    (dist_dir / "manifest.json").write_text(json.dumps(manifest))
    output_path = isolated_filesystem / "bundle.supx"
    output_path.write_text("existing bundle")
    (dist_dir / "bundle-link.supx").symlink_to(output_path)

    result = cli_runner.invoke(app, ["bundle", "--output", str(output_path)])

    assert result.exit_code == 1
    assert "resolved path is outside the dist directory" in result.output
    assert output_path.read_text() == "existing bundle"


@pytest.mark.cli
@patch("superset_extensions_cli.cli.build")
def test_bundle_skips_output_file_inside_dist(
    mock_build, cli_runner, isolated_filesystem
):
    """Test bundle command does not include the archive when output is in dist."""
    mock_build.return_value = None

    dist_dir = isolated_filesystem / "dist"
    dist_dir.mkdir(parents=True)
    manifest = {
        "id": "test-org.test-extension",
        "publisher": "test-org",
        "name": "test-extension",
        "displayName": "Test Extension",
        "version": "1.0.0",
        "permissions": [],
    }
    (dist_dir / "manifest.json").write_text(json.dumps(manifest))
    output_path = dist_dir / "bundle.supx"

    result = cli_runner.invoke(app, ["bundle", "--output", str(output_path)])

    assert result.exit_code == 0
    with zipfile.ZipFile(output_path, "r") as zipf:
        file_list = set(zipf.namelist())
    assert "manifest.json" in file_list
    assert "bundle.supx" not in file_list


@pytest.mark.cli
@patch("superset_extensions_cli.cli.build")
def test_bundle_rejects_symlink_output_path(
    mock_build, cli_runner, isolated_filesystem, extension_setup_for_bundling
):
    """Test bundle refuses output paths that are symlinks."""
    mock_build.return_value = None
    extension_setup_for_bundling(isolated_filesystem)
    target = isolated_filesystem / "target.supx"
    target.write_text("original")
    output_path = isolated_filesystem / "bundle.supx"
    output_path.symlink_to(target)

    result = cli_runner.invoke(app, ["bundle", "--output", str(output_path)])

    assert result.exit_code == 1
    assert "Refusing to write bundle to symlink" in result.output
    assert target.read_text() == "original"


@pytest.mark.cli
@patch("superset_extensions_cli.cli.build")
def test_bundle_rejects_symlink_output_directory(
    mock_build, cli_runner, isolated_filesystem, extension_setup_for_bundling
):
    """Test bundle refuses output directories that are symlinks."""
    mock_build.return_value = None
    extension_setup_for_bundling(isolated_filesystem)
    outside_dir = isolated_filesystem / "outside"
    outside_dir.mkdir()
    output_dir = isolated_filesystem / "output"
    output_dir.symlink_to(outside_dir)

    result = cli_runner.invoke(app, ["bundle", "--output", str(output_dir)])

    assert result.exit_code == 1
    assert "Refusing to write bundle through symlinked directory" in result.output
    assert not (outside_dir / "test-extension-1.0.0.supx").exists()


@pytest.mark.cli
@patch("superset_extensions_cli.cli.build")
def test_bundle_rejects_nested_symlink_output_directory(
    mock_build, cli_runner, isolated_filesystem, extension_setup_for_bundling
):
    """Test bundle refuses output directories below a symlinked ancestor."""
    mock_build.return_value = None
    extension_setup_for_bundling(isolated_filesystem)
    outside_dir = isolated_filesystem / "outside"
    outside_nested_dir = outside_dir / "nested"
    outside_nested_dir.mkdir(parents=True)
    output_dir = isolated_filesystem / "output"
    output_dir.symlink_to(outside_dir)

    result = cli_runner.invoke(app, ["bundle", "--output", str(output_dir / "nested")])

    assert result.exit_code == 1
    assert "Refusing to write bundle through symlinked directory" in result.output
    assert not (outside_nested_dir / "test-extension-1.0.0.supx").exists()


@pytest.mark.cli
@patch("superset_extensions_cli.cli.build")
def test_bundle_rejects_non_file_output_path(
    mock_build, cli_runner, isolated_filesystem, extension_setup_for_bundling
):
    """Test bundle refuses existing output paths that are not regular files."""
    mock_build.return_value = None
    extension_setup_for_bundling(isolated_filesystem)
    output_dir = isolated_filesystem / "output"
    output_dir.mkdir()
    output_path = output_dir / "test-extension-1.0.0.supx"
    output_path.mkdir()

    result = cli_runner.invoke(app, ["bundle", "--output", str(output_dir)])

    assert result.exit_code == 1
    assert "exists but is not a file" in result.output


@pytest.mark.cli
@patch("superset_extensions_cli.cli.build")
def test_bundle_rejects_non_directory_output_parent(
    mock_build, cli_runner, isolated_filesystem, extension_setup_for_bundling
):
    """Test bundle refuses output paths below a file parent."""
    mock_build.return_value = None
    extension_setup_for_bundling(isolated_filesystem)
    output_parent = isolated_filesystem / "output"
    output_parent.write_text("not a directory")

    result = cli_runner.invoke(
        app,
        ["bundle", "--output", str(output_parent / "bundle.supx")],
    )

    assert result.exit_code == 1
    assert "parent exists but is not a directory" in result.output
    assert output_parent.read_text() == "not a directory"


@pytest.mark.cli
@patch("superset_extensions_cli.cli.build")
def test_bundle_rejects_non_directory_output_ancestor(
    mock_build, cli_runner, isolated_filesystem, extension_setup_for_bundling
):
    """Test bundle refuses nested output paths below a file ancestor."""
    mock_build.return_value = None
    extension_setup_for_bundling(isolated_filesystem)
    output_parent = isolated_filesystem / "output"
    output_parent.write_text("not a directory")

    result = cli_runner.invoke(
        app,
        ["bundle", "--output", str(output_parent / "nested" / "bundle.supx")],
    )

    assert result.exit_code == 1
    assert "parent exists but is not a directory" in result.output
    assert output_parent.read_text() == "not a directory"


@pytest.mark.cli
@patch("superset_extensions_cli.cli.build")
def test_bundle_rejects_missing_output_parent(
    mock_build, cli_runner, isolated_filesystem, extension_setup_for_bundling
):
    """Test bundle refuses output paths below missing directories."""
    mock_build.return_value = None
    extension_setup_for_bundling(isolated_filesystem)
    missing_parent = isolated_filesystem / "missing"

    result = cli_runner.invoke(
        app,
        ["bundle", "--output", str(missing_parent / "bundle.supx")],
    )

    assert result.exit_code == 1
    assert "parent directory does not exist" in result.output
    assert not missing_parent.exists()


@pytest.mark.cli
@patch("superset_extensions_cli.cli.build")
def test_bundle_command_short_option(
    mock_build, cli_runner, isolated_filesystem, extension_setup_for_bundling
):
    """Test bundle command with short -o option."""
    # Mock the build command
    mock_build.return_value = None

    extension_setup_for_bundling(isolated_filesystem)

    result = cli_runner.invoke(app, ["bundle", "-o", "short_option.supx"])

    assert result.exit_code == 0
    assert "✅ Bundle created: short_option.supx" in result.output
    assert_file_exists(isolated_filesystem / "short_option.supx")


@pytest.mark.cli
@pytest.mark.parametrize("output_option", ["--output", "-o"])
@patch("superset_extensions_cli.cli.build")
def test_bundle_command_output_options(
    mock_build,
    output_option,
    cli_runner,
    isolated_filesystem,
    extension_setup_for_bundling,
):
    """Test bundle command with both long and short output options."""
    # Mock the build command
    mock_build.return_value = None

    extension_setup_for_bundling(isolated_filesystem)

    filename = f"test_{output_option.replace('-', '')}.supx"
    result = cli_runner.invoke(app, ["bundle", output_option, filename])

    assert result.exit_code == 0
    assert f"✅ Bundle created: {filename}" in result.output
    assert_file_exists(isolated_filesystem / filename)

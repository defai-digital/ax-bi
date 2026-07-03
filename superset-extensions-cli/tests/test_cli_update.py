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
from pathlib import Path

import pytest
import superset_extensions_cli.cli as cli
from superset_extensions_cli.cli import app
from superset_extensions_cli.utils import read_json, read_toml


@pytest.mark.cli
def test_update_syncs_versions(
    cli_runner, isolated_filesystem, extension_with_versions
):
    """Test update syncs frontend and backend versions from extension.json."""
    extension_with_versions(
        isolated_filesystem,
        ext_version="2.0.0",
        frontend_version="1.0.0",
        backend_version="1.0.0",
    )

    result = cli_runner.invoke(app, ["update"])

    assert result.exit_code == 0
    assert "Updated frontend/package.json" in result.output
    assert "Updated backend/pyproject.toml" in result.output

    frontend_pkg = read_json(isolated_filesystem / "frontend" / "package.json")
    assert frontend_pkg["version"] == "2.0.0"

    backend_pyproject = read_toml(isolated_filesystem / "backend" / "pyproject.toml")
    assert backend_pyproject["project"]["version"] == "2.0.0"


@pytest.mark.cli
def test_update_noop_when_all_match(
    cli_runner, isolated_filesystem, extension_with_versions
):
    """Test update reports no changes when everything already matches."""
    extension_with_versions(
        isolated_filesystem,
        ext_version="1.0.0",
        frontend_version="1.0.0",
        backend_version="1.0.0",
    )

    result = cli_runner.invoke(app, ["update"])

    assert result.exit_code == 0
    assert "All files already up to date" in result.output


@pytest.mark.cli
def test_update_fails_without_extension_json(cli_runner, isolated_filesystem):
    """Test update fails when extension.json is missing."""
    result = cli_runner.invoke(app, ["update"])

    assert result.exit_code != 0
    assert "extension.json not found" in result.output


@pytest.mark.cli
@pytest.mark.parametrize("extension_json", ["{ invalid json", "[]"])
def test_update_fails_with_invalid_extension_json(
    cli_runner, isolated_filesystem, extension_json
):
    """Test update reports malformed extension.json cleanly."""
    (isolated_filesystem / "extension.json").write_text(extension_json)

    result = cli_runner.invoke(app, ["update"])

    assert result.exit_code == 1
    assert "Invalid extension.json" in result.output


@pytest.mark.cli
@pytest.mark.parametrize("package_json", ["{ invalid json", "[]"])
def test_update_fails_with_invalid_frontend_package_json(
    cli_runner, isolated_filesystem, extension_with_versions, package_json
):
    """Test update reports malformed frontend/package.json cleanly."""
    extension_with_versions(
        isolated_filesystem,
        ext_version="1.0.0",
        frontend_version="1.0.0",
    )
    (isolated_filesystem / "frontend" / "package.json").write_text(package_json)

    result = cli_runner.invoke(app, ["update", "--version", "2.0.0"])

    assert result.exit_code == 1
    assert "Invalid frontend/package.json" in result.output
    ext = read_json(isolated_filesystem / "extension.json")
    assert ext["version"] == "1.0.0"


@pytest.mark.cli
def test_update_fails_with_malformed_backend_pyproject_toml(
    cli_runner, isolated_filesystem, extension_with_versions
):
    """Test update reports malformed backend/pyproject.toml cleanly."""
    extension_with_versions(
        isolated_filesystem,
        ext_version="1.0.0",
        backend_version="1.0.0",
    )
    (isolated_filesystem / "backend" / "pyproject.toml").write_text("[ invalid toml")

    result = cli_runner.invoke(app, ["update", "--version", "2.0.0"])

    assert result.exit_code == 1
    assert "Invalid backend/pyproject.toml" in result.output
    ext = read_json(isolated_filesystem / "extension.json")
    assert ext["version"] == "1.0.0"


@pytest.mark.cli
def test_update_fails_with_non_table_backend_project_before_writing(
    cli_runner, isolated_filesystem, extension_with_versions
):
    """Test update rejects invalid backend [project] shape before writes."""
    extension_with_versions(
        isolated_filesystem,
        ext_version="1.0.0",
        backend_version="1.0.0",
    )
    (isolated_filesystem / "backend" / "pyproject.toml").write_text(
        """
project = "invalid"

[tool.apache_superset_extensions.build]
include = ["src/**/*.py"]
exclude = []
"""
    )

    result = cli_runner.invoke(app, ["update", "--version", "2.0.0"])

    assert result.exit_code == 1
    assert "Invalid backend/pyproject.toml: [project] must be a table" in result.output
    ext = read_json(isolated_filesystem / "extension.json")
    assert ext["version"] == "1.0.0"


@pytest.mark.cli
def test_update_rejects_symlinked_extension_json(
    cli_runner, isolated_filesystem, extension_with_versions
):
    """Test update refuses to overwrite symlinked extension metadata."""
    extension_with_versions(isolated_filesystem, ext_version="1.0.0")
    extension_json_path = isolated_filesystem / "extension.json"
    outside_extension_json = isolated_filesystem / "outside-extension.json"
    outside_extension_json.write_text(extension_json_path.read_text())
    extension_json_path.unlink()
    extension_json_path.symlink_to(outside_extension_json)

    result = cli_runner.invoke(app, ["update", "--version", "2.0.0"])

    assert result.exit_code == 1
    assert "extension.json" in result.output
    assert "path is a symlink" in result.output
    assert read_json(outside_extension_json)["version"] == "1.0.0"


@pytest.mark.cli
def test_update_rejects_symlinked_frontend_package_before_writing(
    cli_runner, isolated_filesystem, extension_with_versions
):
    """Test update validates all output paths before writing extension metadata."""
    extension_with_versions(
        isolated_filesystem,
        ext_version="1.0.0",
        frontend_version="1.0.0",
    )
    package_json_path = isolated_filesystem / "frontend" / "package.json"
    outside_package_json = isolated_filesystem / "outside-package.json"
    outside_package_json.write_text(package_json_path.read_text())
    package_json_path.unlink()
    package_json_path.symlink_to(outside_package_json)

    result = cli_runner.invoke(app, ["update", "--version", "2.0.0"])

    assert result.exit_code == 1
    assert "frontend/package.json" in result.output
    assert "path is a symlink" in result.output
    assert read_json(isolated_filesystem / "extension.json")["version"] == "1.0.0"
    assert read_json(outside_package_json)["version"] == "1.0.0"


@pytest.mark.cli
def test_update_rejects_symlinked_frontend_directory_before_writing(
    cli_runner, isolated_filesystem, extension_with_versions
):
    """Test update refuses metadata inside a symlinked frontend directory."""
    extension_with_versions(
        isolated_filesystem,
        ext_version="1.0.0",
        frontend_version="1.0.0",
    )
    frontend_dir = isolated_filesystem / "frontend"
    outside_frontend = isolated_filesystem / "outside-frontend"
    frontend_dir.rename(outside_frontend)
    frontend_dir.symlink_to(outside_frontend)

    result = cli_runner.invoke(app, ["update", "--version", "2.0.0"])

    assert result.exit_code == 1
    assert "frontend path is a symlink" in result.output
    assert read_json(isolated_filesystem / "extension.json")["version"] == "1.0.0"
    assert read_json(outside_frontend / "package.json")["version"] == "1.0.0"


@pytest.mark.cli
def test_update_rejects_symlinked_backend_pyproject_before_writing(
    cli_runner, isolated_filesystem, extension_with_versions
):
    """Test update refuses symlinked TOML outputs before writing JSON outputs."""
    extension_with_versions(
        isolated_filesystem,
        ext_version="1.0.0",
        backend_version="1.0.0",
    )
    pyproject_path = isolated_filesystem / "backend" / "pyproject.toml"
    outside_pyproject = isolated_filesystem / "outside-pyproject.toml"
    outside_pyproject.write_text(pyproject_path.read_text())
    pyproject_path.unlink()
    pyproject_path.symlink_to(outside_pyproject)

    result = cli_runner.invoke(app, ["update", "--version", "2.0.0"])

    assert result.exit_code == 1
    assert "backend/pyproject.toml" in result.output
    assert "path is a symlink" in result.output
    assert read_json(isolated_filesystem / "extension.json")["version"] == "1.0.0"
    assert read_toml(outside_pyproject)["project"]["version"] == "1.0.0"


@pytest.mark.cli
def test_update_rejects_symlinked_backend_directory_before_writing(
    cli_runner, isolated_filesystem, extension_with_versions
):
    """Test update refuses metadata inside a symlinked backend directory."""
    extension_with_versions(
        isolated_filesystem,
        ext_version="1.0.0",
        backend_version="1.0.0",
    )
    backend_dir = isolated_filesystem / "backend"
    outside_backend = isolated_filesystem / "outside-backend"
    backend_dir.rename(outside_backend)
    backend_dir.symlink_to(outside_backend)

    result = cli_runner.invoke(app, ["update", "--version", "2.0.0"])

    assert result.exit_code == 1
    assert "backend path is a symlink" in result.output
    assert read_json(isolated_filesystem / "extension.json")["version"] == "1.0.0"
    assert (
        read_toml(outside_backend / "pyproject.toml")["project"]["version"] == "1.0.0"
    )


@pytest.mark.cli
def test_update_rejects_frontend_package_directory_before_writing(
    cli_runner, isolated_filesystem, extension_with_versions
):
    """Test update refuses frontend metadata paths that are directories."""
    extension_with_versions(
        isolated_filesystem,
        ext_version="1.0.0",
        frontend_version="1.0.0",
    )
    package_json_path = isolated_filesystem / "frontend" / "package.json"
    package_json_path.unlink()
    package_json_path.mkdir()

    result = cli_runner.invoke(app, ["update", "--version", "2.0.0"])

    assert result.exit_code == 1
    assert "frontend/package.json path exists but is not a file" in result.output
    assert read_json(isolated_filesystem / "extension.json")["version"] == "1.0.0"


@pytest.mark.cli
def test_update_rejects_backend_pyproject_directory_before_writing(
    cli_runner, isolated_filesystem, extension_with_versions
):
    """Test update refuses backend metadata paths that are directories."""
    extension_with_versions(
        isolated_filesystem,
        ext_version="1.0.0",
        backend_version="1.0.0",
    )
    pyproject_path = isolated_filesystem / "backend" / "pyproject.toml"
    pyproject_path.unlink()
    pyproject_path.mkdir()

    result = cli_runner.invoke(app, ["update", "--version", "2.0.0"])

    assert result.exit_code == 1
    assert "backend/pyproject.toml path exists but is not a file" in result.output
    assert read_json(isolated_filesystem / "extension.json")["version"] == "1.0.0"


@pytest.mark.cli
def test_update_reports_json_write_failures(
    cli_runner, isolated_filesystem, extension_with_versions, monkeypatch
):
    """Test update reports write failures after output validation."""
    extension_with_versions(
        isolated_filesystem,
        ext_version="1.0.0",
        frontend_version="1.0.0",
    )
    extension_json_path = isolated_filesystem / "extension.json"
    original_replace = Path.replace

    def fail_extension_json_replace(path, target):
        if target == extension_json_path:
            raise OSError("disk full")
        return original_replace(path, target)

    monkeypatch.setattr(Path, "replace", fail_extension_json_replace)

    result = cli_runner.invoke(app, ["update", "--version", "2.0.0"])

    assert result.exit_code == 1
    assert "Failed to write JSON file" in result.output
    assert "disk full" in result.output
    assert "Updated extension.json" not in result.output
    assert read_json(extension_json_path)["version"] == "1.0.0"


@pytest.mark.cli
def test_update_rejects_changed_frontend_directory_before_metadata_write(
    cli_runner, isolated_filesystem, extension_with_versions, monkeypatch
):
    """Test update refuses metadata writes after a source directory swap."""
    extension_with_versions(
        isolated_filesystem,
        ext_version="1.0.0",
        frontend_version="1.0.0",
    )
    frontend_dir = isolated_filesystem / "frontend"
    frontend_pkg_path = frontend_dir / "package.json"
    saved_frontend_dir = isolated_filesystem / "saved-frontend"
    replacement_frontend_dir = isolated_filesystem / "replacement-frontend"
    replacement_frontend_dir.mkdir()
    (replacement_frontend_dir / "package.json").write_text(
        json.dumps(
            {
                "name": "@replacement/replacement",
                "version": "9.9.9",
                "license": "Apache-2.0",
            }
        )
    )
    original_validate_output_file = cli.validate_output_file
    swapped = False

    def replace_frontend_after_package_validation(path, label):
        nonlocal swapped
        original_validate_output_file(path, label)
        if path == frontend_pkg_path and not swapped:
            frontend_dir.rename(saved_frontend_dir)
            replacement_frontend_dir.rename(frontend_dir)
            swapped = True

    monkeypatch.setattr(
        "superset_extensions_cli.cli.validate_output_file",
        replace_frontend_after_package_validation,
    )

    result = cli_runner.invoke(app, ["update", "--version", "2.0.0"])

    assert result.exit_code == 1
    assert "frontend path changed before metadata update" in result.output
    assert read_json(isolated_filesystem / "extension.json")["version"] == "1.0.0"
    assert read_json(saved_frontend_dir / "package.json")["version"] == "1.0.0"
    assert read_json(frontend_dir / "package.json")["version"] == "9.9.9"


@pytest.mark.cli
def test_update_rejects_frontend_directory_content_change_before_metadata_write(
    cli_runner,
    isolated_filesystem,
    extension_with_versions,
    monkeypatch,
):
    """Test update refuses metadata writes after source directory content changes."""
    extension_with_versions(
        isolated_filesystem,
        ext_version="1.0.0",
        frontend_version="1.0.0",
    )
    frontend_dir = isolated_filesystem / "frontend"
    frontend_pkg_path = frontend_dir / "package.json"
    original_validate_output_file = cli.validate_output_file
    changed = False

    def change_frontend_after_package_validation(path, label):
        nonlocal changed
        original_validate_output_file(path, label)
        if path == frontend_pkg_path and not changed:
            (frontend_dir / "added.txt").write_text("new entry")
            changed = True

    monkeypatch.setattr(
        "superset_extensions_cli.cli.validate_output_file",
        change_frontend_after_package_validation,
    )

    result = cli_runner.invoke(app, ["update", "--version", "2.0.0"])

    assert result.exit_code == 1
    assert "frontend path changed before metadata update" in result.output
    assert read_json(isolated_filesystem / "extension.json")["version"] == "1.0.0"
    assert read_json(frontend_pkg_path)["version"] == "1.0.0"
    assert (frontend_dir / "added.txt").read_text() == "new entry"


@pytest.mark.cli
def test_update_fails_when_original_metadata_becomes_unsafe_before_write(
    cli_runner, isolated_filesystem, extension_with_versions, monkeypatch
):
    """Test update aborts when rollback snapshot metadata becomes unsafe."""
    extension_with_versions(isolated_filesystem, ext_version="1.0.0")
    extension_json_path = isolated_filesystem / "extension.json"
    original_extension_json = extension_json_path.read_text()
    outside_extension_json = isolated_filesystem / "outside-extension.json"
    outside_extension_json.write_text(
        json.dumps(
            {
                "publisher": "outside-org",
                "name": "outside-extension",
                "displayName": "Outside Extension",
                "version": "9.9.9",
                "license": "Apache-2.0",
                "permissions": [],
            }
        )
    )
    original_read_text = Path.read_text
    extension_json_reads = 0

    def replace_extension_json_during_snapshot(path, *args, **kwargs):
        nonlocal extension_json_reads
        if path == extension_json_path:
            extension_json_reads += 1
            if extension_json_reads == 2:
                extension_json_path.unlink()
                extension_json_path.symlink_to(outside_extension_json)
                return original_extension_json
        return original_read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", replace_extension_json_during_snapshot)

    result = cli_runner.invoke(app, ["update", "--version", "2.0.0"])

    assert result.exit_code == 1
    assert "Failed to read original metadata before update" in result.output
    assert "path is a symlink" in result.output
    assert "Updated extension.json" not in result.output
    assert extension_json_path.is_symlink()
    assert read_json(outside_extension_json)["version"] == "9.9.9"


@pytest.mark.cli
def test_update_rejects_metadata_changed_after_snapshot(
    cli_runner,
    isolated_filesystem,
    extension_with_versions,
    monkeypatch,
):
    """Test update refuses to overwrite metadata changed after snapshot."""
    extension_with_versions(isolated_filesystem, ext_version="1.0.0")
    extension_json_path = isolated_filesystem / "extension.json"
    saved_extension_json = isolated_filesystem / "saved-extension.json"
    replacement_extension_json = isolated_filesystem / "replacement-extension.json"
    replacement_extension_json.write_text(
        json.dumps(
            {
                "publisher": "replacement-org",
                "name": "replacement-extension",
                "displayName": "Replacement Extension",
                "version": "9.9.9",
                "license": "Apache-2.0",
                "permissions": [],
            }
        )
    )
    original_read_input_text = cli.read_input_text
    original_get_read_path_identity = cli.get_read_path_identity
    snapshot_read = False
    swapped = False

    def read_snapshot(path, label):
        nonlocal snapshot_read
        content = original_read_input_text(path, label)
        if path == extension_json_path:
            snapshot_read = True
        return content

    def swap_after_snapshot_identity(path):
        nonlocal swapped
        identity = original_get_read_path_identity(path)
        if path == extension_json_path and snapshot_read and not swapped:
            extension_json_path.rename(saved_extension_json)
            replacement_extension_json.rename(extension_json_path)
            swapped = True
        return identity

    monkeypatch.setattr(cli, "read_input_text", read_snapshot)
    monkeypatch.setattr(cli, "get_read_path_identity", swap_after_snapshot_identity)

    result = cli_runner.invoke(app, ["update", "--version", "2.0.0"])

    assert result.exit_code == 1
    assert (
        "Refusing to update extension.json: path changed after snapshot"
        in result.output
    )
    assert "Updated extension.json" not in result.output
    assert read_json(saved_extension_json)["version"] == "1.0.0"
    assert read_json(extension_json_path)["version"] == "9.9.9"


@pytest.mark.cli
def test_update_binds_metadata_write_to_snapshot_identity(
    cli_runner,
    isolated_filesystem,
    extension_with_versions,
    monkeypatch,
):
    """Test update passes the metadata snapshot identity into writes."""
    extension_with_versions(isolated_filesystem, ext_version="1.0.0")
    extension_json_path = isolated_filesystem / "extension.json"
    expected_identity = cli.get_read_path_identity(extension_json_path)
    assert expected_identity is not None
    original_write_json = cli.write_json
    seen_identities: list[tuple[int, int, int, int] | None] = []

    def capture_write_identity(path, data, *, expected_existing_identity=None):
        if path == extension_json_path:
            seen_identities.append(expected_existing_identity)
        return original_write_json(
            path,
            data,
            expected_existing_identity=expected_existing_identity,
        )

    monkeypatch.setattr(cli, "write_json", capture_write_identity)

    result = cli_runner.invoke(app, ["update", "--version", "2.0.0"])

    assert result.exit_code == 0
    assert seen_identities == [expected_identity]
    assert read_json(extension_json_path)["version"] == "2.0.0"


@pytest.mark.cli
def test_update_rolls_back_completed_writes_on_later_failure(
    cli_runner, isolated_filesystem, extension_with_versions, monkeypatch
):
    """Test update restores earlier files when a later metadata write fails."""
    extension_with_versions(
        isolated_filesystem,
        ext_version="1.0.0",
        frontend_version="1.0.0",
        backend_version="1.0.0",
    )
    backend_pyproject_path = isolated_filesystem / "backend" / "pyproject.toml"
    original_replace = Path.replace

    def fail_backend_pyproject_replace(path, target):
        if target == backend_pyproject_path:
            raise OSError("disk full")
        return original_replace(path, target)

    monkeypatch.setattr(Path, "replace", fail_backend_pyproject_replace)

    result = cli_runner.invoke(app, ["update", "--version", "2.0.0"])

    assert result.exit_code == 1
    assert "Failed to write TOML file" in result.output
    assert "disk full" in result.output
    assert "Updated extension.json" not in result.output
    assert read_json(isolated_filesystem / "extension.json")["version"] == "1.0.0"
    assert (
        read_json(isolated_filesystem / "frontend" / "package.json")["version"]
        == "1.0.0"
    )
    assert read_toml(backend_pyproject_path)["project"]["version"] == "1.0.0"


@pytest.mark.cli
def test_update_refuses_rollback_when_written_metadata_changes(
    cli_runner, isolated_filesystem, extension_with_versions, monkeypatch
):
    """Test update does not roll back a metadata file changed after writing."""
    extension_with_versions(
        isolated_filesystem,
        ext_version="1.0.0",
        backend_version="1.0.0",
    )
    extension_json_path = isolated_filesystem / "extension.json"
    backend_pyproject_path = isolated_filesystem / "backend" / "pyproject.toml"
    replacement_json_path = isolated_filesystem / "replacement-extension.json"
    replacement_json_path.write_text(
        json.dumps(
            {
                "publisher": "replacement-org",
                "name": "replacement-extension",
                "displayName": "Replacement Extension",
                "version": "9.9.9",
                "license": "Apache-2.0",
                "permissions": [],
            }
        )
    )
    original_replace = Path.replace

    def fail_backend_write_after_extension_swap(path, target):
        if target == backend_pyproject_path:
            extension_json_path.unlink()
            original_replace(replacement_json_path, extension_json_path)
            raise OSError("disk full")
        return original_replace(path, target)

    monkeypatch.setattr(Path, "replace", fail_backend_write_after_extension_swap)

    result = cli_runner.invoke(app, ["update", "--version", "2.0.0"])

    assert result.exit_code == 1
    assert "Failed to roll back extension.json" in result.output
    assert "Refusing to roll back extension.json: path changed" in result.output
    assert read_json(extension_json_path)["version"] == "9.9.9"
    assert read_toml(backend_pyproject_path)["project"]["version"] == "1.0.0"


@pytest.mark.cli
def test_update_refuses_rollback_when_metadata_directory_changes(
    cli_runner, isolated_filesystem, extension_with_versions, monkeypatch
):
    """Test update verifies metadata directories after rollback writes."""
    extension_with_versions(
        isolated_filesystem,
        ext_version="1.0.0",
        frontend_version="1.0.0",
        backend_version="1.0.0",
    )
    frontend_dir = isolated_filesystem / "frontend"
    frontend_pkg_path = frontend_dir / "package.json"
    backend_pyproject_path = isolated_filesystem / "backend" / "pyproject.toml"
    saved_frontend_dir = isolated_filesystem / "saved-frontend"
    replacement_frontend_dir = isolated_filesystem / "replacement-frontend"
    replacement_frontend_dir.mkdir()
    (replacement_frontend_dir / "package.json").write_text(
        json.dumps({"version": "9.9.9", "license": "Apache-2.0"})
    )
    original_replace = Path.replace
    original_write_text_atomic = cli.write_text_atomic

    def fail_backend_pyproject_replace(path, target):
        if target == backend_pyproject_path:
            raise OSError("disk full")
        return original_replace(path, target)

    def swap_frontend_after_rollback(path, content, **kwargs):
        result = original_write_text_atomic(path, content, **kwargs)
        if path == frontend_pkg_path:
            frontend_dir.rename(saved_frontend_dir)
            replacement_frontend_dir.rename(frontend_dir)
        return result

    monkeypatch.setattr(Path, "replace", fail_backend_pyproject_replace)
    monkeypatch.setattr(cli, "write_text_atomic", swap_frontend_after_rollback)

    result = cli_runner.invoke(app, ["update", "--version", "2.0.0"])

    assert result.exit_code == 1
    assert "Failed to roll back frontend/package.json" in result.output
    assert "directory path changed" in result.output
    assert read_json(saved_frontend_dir / "package.json")["version"] == "1.0.0"
    assert read_json(frontend_pkg_path)["version"] == "9.9.9"
    assert read_toml(backend_pyproject_path)["project"]["version"] == "1.0.0"


@pytest.mark.cli
def test_update_with_version_flag(
    cli_runner, isolated_filesystem, extension_with_versions
):
    """Test --version updates extension.json first, then syncs all files."""
    extension_with_versions(
        isolated_filesystem,
        ext_version="1.0.0",
        frontend_version="1.0.0",
        backend_version="1.0.0",
    )

    result = cli_runner.invoke(app, ["update", "--version", "3.0.0"])

    assert result.exit_code == 0
    assert "Updated extension.json" in result.output
    assert "Updated frontend/package.json" in result.output
    assert "Updated backend/pyproject.toml" in result.output

    ext = read_json(isolated_filesystem / "extension.json")
    assert ext["version"] == "3.0.0"

    frontend_pkg = read_json(isolated_filesystem / "frontend" / "package.json")
    assert frontend_pkg["version"] == "3.0.0"

    backend_pyproject = read_toml(isolated_filesystem / "backend" / "pyproject.toml")
    assert backend_pyproject["project"]["version"] == "3.0.0"


@pytest.mark.cli
def test_update_with_license_flag(
    cli_runner, isolated_filesystem, extension_with_versions
):
    """Test --license updates license across all files."""
    extension_with_versions(
        isolated_filesystem,
        ext_version="1.0.0",
        frontend_version="1.0.0",
        backend_version="1.0.0",
        ext_license="Apache-2.0",
    )

    result = cli_runner.invoke(app, ["update", "--license", "MIT"])

    assert result.exit_code == 0
    assert "Updated extension.json" in result.output
    assert "Updated frontend/package.json" in result.output
    assert "Updated backend/pyproject.toml" in result.output

    ext = read_json(isolated_filesystem / "extension.json")
    assert ext["license"] == "MIT"

    frontend_pkg = read_json(isolated_filesystem / "frontend" / "package.json")
    assert frontend_pkg["license"] == "MIT"

    backend_pyproject = read_toml(isolated_filesystem / "backend" / "pyproject.toml")
    assert backend_pyproject["project"]["license"] == "MIT"


@pytest.mark.cli
def test_update_version_prompt_default(
    cli_runner, isolated_filesystem, extension_with_versions
):
    """Test --version without value prompts with current version as default."""
    extension_with_versions(
        isolated_filesystem,
        ext_version="1.0.0",
        frontend_version="1.0.0",
        backend_version="1.0.0",
    )

    # Hit enter to accept default — nothing should change
    result = cli_runner.invoke(app, ["update", "--version"], input="\n")

    assert result.exit_code == 0
    assert "All files already up to date" in result.output


@pytest.mark.cli
def test_update_rejects_invalid_version(
    cli_runner, isolated_filesystem, extension_with_versions
):
    """Test --version with an invalid semver string exits with error."""
    extension_with_versions(
        isolated_filesystem,
        ext_version="1.0.0",
    )

    result = cli_runner.invoke(app, ["update", "--version", "not-a-version"])

    assert result.exit_code != 0
    assert "Invalid value" in result.output

    # Verify extension.json was not modified
    ext = read_json(isolated_filesystem / "extension.json")
    assert ext["version"] == "1.0.0"

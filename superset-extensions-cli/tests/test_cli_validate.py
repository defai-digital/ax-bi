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
from unittest.mock import Mock, patch

import pytest
import click
import superset_extensions_cli.cli as cli
from superset_extensions_cli.cli import (
    app,
    load_json_object,
    load_toml_object,
    optional_directory_exists,
    optional_file_exists,
    require_optional_directory,
    validate_npm,
)


def create_file_path(path: Path) -> None:
    """Create a regular file at the project source path."""
    path.write_text("not a directory")


def create_broken_symlink(path: Path) -> None:
    """Create a broken symlink at the project source path."""
    path.symlink_to(path.parent / f"missing-{path.name}")


def create_directory_symlink(path: Path) -> None:
    """Create a symlink to a real directory at the project source path."""
    target = path.parent / f"outside-{path.name}"
    target.mkdir()
    path.symlink_to(target)


@pytest.mark.unit
def test_optional_directory_exists_validates_project_paths(isolated_filesystem):
    """Test optional source directory helper accepts only safe directories."""
    missing_path = isolated_filesystem / "missing"
    assert optional_directory_exists(missing_path, "missing") is False

    source_dir = isolated_filesystem / "frontend"
    source_dir.mkdir()
    assert optional_directory_exists(source_dir, "frontend") is True

    source_file = isolated_filesystem / "backend"
    source_file.write_text("not a directory")
    with pytest.raises(click.ClickException, match="not a directory"):
        optional_directory_exists(source_file, "backend")

    target_dir = isolated_filesystem / "outside"
    target_dir.mkdir()
    source_link = isolated_filesystem / "linked"
    source_link.symlink_to(target_dir)
    with pytest.raises(click.ClickException, match="path is a symlink"):
        optional_directory_exists(source_link, "linked")

    nested_target_dir = isolated_filesystem / "outside-nested"
    nested_target_dir.mkdir()
    parent_link = isolated_filesystem / "linked-parent"
    parent_link.symlink_to(nested_target_dir)
    with pytest.raises(click.ClickException, match="parent directory is a symlink"):
        optional_directory_exists(parent_link / "frontend", "linked/frontend")


@pytest.mark.unit
def test_optional_directory_exists_rejects_changed_path(
    isolated_filesystem,
    monkeypatch,
):
    """Test optional directory helper refuses a path changed during validation."""
    source_dir = isolated_filesystem / "frontend"
    source_dir.mkdir()
    saved_dir = isolated_filesystem / "saved-frontend"
    replacement_dir = isolated_filesystem / "replacement-frontend"
    replacement_dir.mkdir()
    original_get_directory_path_identity = cli.get_directory_path_identity
    identity_reads = 0

    def swap_directory_after_first_identity(path):
        nonlocal identity_reads
        identity = original_get_directory_path_identity(path)
        if path == source_dir:
            identity_reads += 1
            if identity_reads == 1:
                source_dir.rename(saved_dir)
                replacement_dir.rename(source_dir)
        return identity

    monkeypatch.setattr(
        cli,
        "get_directory_path_identity",
        swap_directory_after_first_identity,
    )

    with pytest.raises(click.ClickException, match="frontend path changed"):
        optional_directory_exists(source_dir, "frontend")

    assert saved_dir.is_dir()
    assert source_dir.is_dir()


@pytest.mark.unit
def test_require_optional_directory_rejects_changed_path(
    isolated_filesystem,
    monkeypatch,
):
    """Test optional directory validation refuses a changed path."""
    source_dir = isolated_filesystem / "backend"
    source_dir.mkdir()
    saved_dir = isolated_filesystem / "saved-backend"
    replacement_dir = isolated_filesystem / "replacement-backend"
    replacement_dir.mkdir()
    original_get_directory_path_identity = cli.get_directory_path_identity
    identity_reads = 0

    def swap_directory_after_first_identity(path):
        nonlocal identity_reads
        identity = original_get_directory_path_identity(path)
        if path == source_dir:
            identity_reads += 1
            if identity_reads == 1:
                source_dir.rename(saved_dir)
                replacement_dir.rename(source_dir)
        return identity

    monkeypatch.setattr(
        cli,
        "get_directory_path_identity",
        swap_directory_after_first_identity,
    )

    with pytest.raises(click.ClickException, match="backend path changed"):
        require_optional_directory(source_dir, "backend")

    assert saved_dir.is_dir()
    assert source_dir.is_dir()


@pytest.mark.unit
def test_optional_file_exists_validates_project_paths(isolated_filesystem):
    """Test optional file helper accepts only regular files or missing paths."""
    missing_path = isolated_filesystem / "missing.json"
    assert optional_file_exists(missing_path, "missing.json") is False

    metadata_file = isolated_filesystem / "extension.json"
    metadata_file.write_text("{}")
    assert optional_file_exists(metadata_file, "extension.json") is True

    metadata_dir = isolated_filesystem / "package.json"
    metadata_dir.mkdir()
    with pytest.raises(click.ClickException, match="not a file"):
        optional_file_exists(metadata_dir, "package.json")

    target_file = isolated_filesystem / "outside-package.json"
    target_file.write_text("{}")
    metadata_link = isolated_filesystem / "linked-package.json"
    metadata_link.symlink_to(target_file)
    with pytest.raises(click.ClickException, match="path is a symlink"):
        optional_file_exists(metadata_link, "linked-package.json")

    broken_link = isolated_filesystem / "pyproject.toml"
    broken_link.symlink_to(isolated_filesystem / "missing-target")
    with pytest.raises(click.ClickException, match="path is a symlink"):
        optional_file_exists(broken_link, "pyproject.toml")

    nested_target_dir = isolated_filesystem / "outside-metadata"
    nested_target_dir.mkdir()
    (nested_target_dir / "package.json").write_text("{}")
    parent_link = isolated_filesystem / "linked-parent"
    parent_link.symlink_to(nested_target_dir)
    with pytest.raises(click.ClickException, match="parent directory is a symlink"):
        optional_file_exists(parent_link / "package.json", "frontend/package.json")


@pytest.mark.unit
def test_optional_file_exists_rejects_changed_path(
    isolated_filesystem,
    monkeypatch,
):
    """Test optional file helper refuses a path changed during validation."""
    metadata_file = isolated_filesystem / "extension.json"
    metadata_file.write_text("{}")
    saved_file = isolated_filesystem / "saved-extension.json"
    replacement_file = isolated_filesystem / "replacement-extension.json"
    replacement_file.write_text('{"version": "9.9.9"}')
    original_get_read_path_identity = cli.get_read_path_identity
    identity_reads = 0

    def swap_file_after_first_identity(path):
        nonlocal identity_reads
        identity = original_get_read_path_identity(path)
        if path == metadata_file:
            identity_reads += 1
            if identity_reads == 1:
                metadata_file.rename(saved_file)
                replacement_file.rename(metadata_file)
        return identity

    monkeypatch.setattr(cli, "get_read_path_identity", swap_file_after_first_identity)

    with pytest.raises(click.ClickException, match="extension.json path changed"):
        optional_file_exists(metadata_file, "extension.json")

    assert saved_file.read_text() == "{}"
    assert metadata_file.read_text() == '{"version": "9.9.9"}'


@pytest.mark.unit
def test_metadata_loader_rejects_changed_input_during_existence_check(
    isolated_filesystem,
    monkeypatch,
):
    """Test metadata loaders refuse an input changed during existence validation."""
    metadata_file = isolated_filesystem / "metadata.json"
    metadata_file.write_text("{}")
    saved_file = isolated_filesystem / "saved-metadata.json"
    replacement_file = isolated_filesystem / "replacement-metadata.json"
    replacement_file.write_text('{"version": "9.9.9"}')
    original_get_read_path_identity = cli.get_read_path_identity
    identity_reads = 0

    def swap_file_after_first_identity(path):
        nonlocal identity_reads
        identity = original_get_read_path_identity(path)
        if path == metadata_file:
            identity_reads += 1
            if identity_reads == 1:
                metadata_file.rename(saved_file)
                replacement_file.rename(metadata_file)
        return identity

    monkeypatch.setattr(cli, "get_read_path_identity", swap_file_after_first_identity)

    with pytest.raises(click.ClickException, match="Failed to read metadata.json"):
        load_json_object(metadata_file, "metadata.json")

    assert saved_file.read_text() == "{}"
    assert metadata_file.read_text() == '{"version": "9.9.9"}'


@pytest.mark.unit
@pytest.mark.parametrize(
    ("loader", "filename", "content"),
    [
        (load_json_object, "metadata.json", "{}"),
        (load_toml_object, "pyproject.toml", "[project]\n"),
    ],
)
def test_metadata_loaders_refuse_symlinked_inputs(
    isolated_filesystem, loader, filename, content
):
    """Test metadata loaders enforce the input file boundary directly."""
    outside_file = isolated_filesystem / f"outside-{filename}"
    outside_file.write_text(content)
    metadata_link = isolated_filesystem / filename
    metadata_link.symlink_to(outside_file)

    with pytest.raises(click.ClickException, match="Refusing to read"):
        loader(metadata_link, filename)


@pytest.mark.unit
@pytest.mark.parametrize(
    ("loader", "filename", "content"),
    [
        (load_json_object, "metadata.json", "{}"),
        (load_toml_object, "pyproject.toml", "[project]\n"),
    ],
)
def test_metadata_loaders_refuse_symlinked_input_parents(
    isolated_filesystem, loader, filename, content
):
    """Test metadata loaders reject files reached through symlinked parents."""
    outside_dir = isolated_filesystem / "outside"
    outside_dir.mkdir()
    (outside_dir / filename).write_text(content)
    metadata_parent = isolated_filesystem / "linked-parent"
    metadata_parent.symlink_to(outside_dir)

    with pytest.raises(click.ClickException, match="parent directory is a symlink"):
        loader(metadata_parent / filename, filename)


@pytest.mark.unit
@pytest.mark.parametrize(
    ("loader", "reader_name", "filename", "content"),
    [
        (load_json_object, "read_json", "metadata.json", "{}"),
        (load_toml_object, "read_toml", "pyproject.toml", "[project]\n"),
    ],
)
def test_metadata_loaders_fail_when_read_boundary_changes_after_validation(
    isolated_filesystem, monkeypatch, loader, reader_name, filename, content
):
    """Test metadata loaders fail when reads become unsafe after validation."""
    metadata_file = isolated_filesystem / filename
    metadata_file.write_text(content)

    monkeypatch.setattr(f"superset_extensions_cli.cli.{reader_name}", lambda _: None)

    with pytest.raises(
        click.ClickException,
        match=f"Failed to read {filename}: path is no longer safe",
    ):
        loader(metadata_file, filename)


@pytest.mark.unit
@pytest.mark.parametrize(
    ("loader", "filename", "content"),
    [
        (load_json_object, "metadata.json", "{}"),
        (load_toml_object, "pyproject.toml", "[project]\n"),
    ],
)
def test_metadata_loaders_report_read_errors(
    isolated_filesystem, loader, filename, content, monkeypatch
):
    """Test metadata loaders distinguish filesystem read errors from invalid data."""
    metadata_file = isolated_filesystem / filename
    metadata_file.write_text(content)

    def fail_metadata_read(path, *args, **kwargs):
        if path == metadata_file:
            raise OSError("permission denied")
        raise AssertionError(f"unexpected path: {path}")

    if filename.endswith(".json"):
        monkeypatch.setattr(Path, "read_text", fail_metadata_read)
    else:
        monkeypatch.setattr(Path, "open", fail_metadata_read)

    with pytest.raises(click.ClickException, match="Failed to read"):
        loader(metadata_file, filename)


# Validate Command Tests
@pytest.mark.cli
def test_validate_command_success(cli_runner, isolated_filesystem):
    """Test validate command succeeds when npm is available and valid."""
    # Create minimal extension.json for validation
    extension_json = {
        "publisher": "test-org",
        "name": "test-extension",
        "displayName": "Test Extension",
        "version": "1.0.0",
        "permissions": [],
    }

    (isolated_filesystem / "extension.json").write_text(json.dumps(extension_json))

    with patch("superset_extensions_cli.cli.validate_npm") as mock_validate:
        result = cli_runner.invoke(app, ["validate"])

        assert result.exit_code == 0
        assert "✅ Validation successful" in result.output
        mock_validate.assert_called_once()


@pytest.mark.cli
def test_validate_command_calls_npm_validation(cli_runner):
    """Test that validate command calls the npm validation function."""
    with patch("superset_extensions_cli.cli.validate_npm") as mock_validate:
        cli_runner.invoke(app, ["validate"])
        mock_validate.assert_called_once()


@pytest.mark.cli
@pytest.mark.parametrize("extension_json", ["{ invalid json", "[]"])
def test_validate_fails_with_invalid_extension_json(
    cli_runner, isolated_filesystem, extension_json
):
    """Test validate reports malformed extension.json cleanly."""
    (isolated_filesystem / "extension.json").write_text(extension_json)

    with patch("superset_extensions_cli.cli.validate_npm"):
        result = cli_runner.invoke(app, ["validate"])

    assert result.exit_code == 1
    assert "Invalid extension.json" in result.output


@pytest.mark.cli
def test_validate_rejects_symlinked_extension_json(cli_runner, isolated_filesystem):
    """Test validate refuses to read symlinked extension metadata."""
    outside_extension_json = isolated_filesystem / "outside-extension.json"
    outside_extension_json.write_text(
        json.dumps(
            {
                "publisher": "test-org",
                "name": "test-extension",
                "displayName": "Test Extension",
                "version": "1.0.0",
                "permissions": [],
            }
        )
    )
    (isolated_filesystem / "extension.json").symlink_to(outside_extension_json)

    with patch("superset_extensions_cli.cli.validate_npm"):
        result = cli_runner.invoke(app, ["validate"])

    assert result.exit_code == 1
    assert "Refusing to read extension.json: path is a symlink" in result.output


@pytest.mark.cli
def test_validate_rejects_symlinked_frontend_package_json(
    cli_runner,
    isolated_filesystem,
):
    """Test validate refuses to read symlinked frontend package metadata."""
    extension_json = {
        "publisher": "test-org",
        "name": "test-extension",
        "displayName": "Test Extension",
        "version": "1.0.0",
        "permissions": [],
    }
    (isolated_filesystem / "extension.json").write_text(json.dumps(extension_json))
    frontend_dir = isolated_filesystem / "frontend"
    frontend_dir.mkdir()
    frontend_src = frontend_dir / "src"
    frontend_src.mkdir()
    (frontend_src / "index.tsx").write_text("export default {}")
    outside_package = isolated_filesystem / "outside-package.json"
    outside_package.write_text("{}")
    (frontend_dir / "package.json").symlink_to(outside_package)

    with patch("superset_extensions_cli.cli.validate_npm"):
        result = cli_runner.invoke(app, ["validate"])

    assert result.exit_code == 1
    assert "frontend/package.json path is a symlink" in result.output


@pytest.mark.cli
def test_validate_rejects_symlinked_backend_pyproject_toml(
    cli_runner,
    isolated_filesystem,
):
    """Test validate refuses to read symlinked backend project metadata."""
    extension_json = {
        "publisher": "test-org",
        "name": "test-extension",
        "displayName": "Test Extension",
        "version": "1.0.0",
        "permissions": [],
    }
    (isolated_filesystem / "extension.json").write_text(json.dumps(extension_json))
    backend_dir = isolated_filesystem / "backend"
    backend_dir.mkdir()
    outside_pyproject = isolated_filesystem / "outside-pyproject.toml"
    outside_pyproject.write_text('[project]\nname = "test"\n')
    (backend_dir / "pyproject.toml").symlink_to(outside_pyproject)

    with patch("superset_extensions_cli.cli.validate_npm"):
        result = cli_runner.invoke(app, ["validate"])

    assert result.exit_code == 1
    assert "backend/pyproject.toml path is a symlink" in result.output


@pytest.mark.cli
def test_validate_fails_with_invalid_backend_build_config(
    cli_runner, isolated_filesystem
):
    """Test validate reports malformed backend build config cleanly."""
    extension_json = {
        "publisher": "test-org",
        "name": "test-extension",
        "displayName": "Test Extension",
        "version": "1.0.0",
        "permissions": [],
    }
    (isolated_filesystem / "extension.json").write_text(json.dumps(extension_json))

    backend_dir = isolated_filesystem / "backend"
    entrypoint_dir = backend_dir / "src" / "test_org" / "test_extension"
    entrypoint_dir.mkdir(parents=True)
    (entrypoint_dir / "entrypoint.py").write_text("# entry")
    (backend_dir / "pyproject.toml").write_text(
        """[project]
name = "test-org-test-extension"
version = "1.0.0"

[tool.apache_superset_extensions.build]
include = "src/**/*.py"
"""
    )

    with patch("superset_extensions_cli.cli.validate_npm"):
        result = cli_runner.invoke(app, ["validate"])

    assert result.exit_code == 1
    assert "Invalid backend build config" in result.output


@pytest.mark.cli
@pytest.mark.parametrize(
    ("build_config", "expected_message"),
    [
        (
            """include = ["../secret.py"]
exclude = []
""",
            "Invalid include pattern",
        ),
        (
            """include = ["src/**/*.py"]
exclude = ["/tmp/*.py"]
""",
            "Invalid exclude pattern",
        ),
    ],
)
def test_validate_rejects_backend_build_patterns_outside_backend(
    cli_runner, isolated_filesystem, build_config, expected_message
):
    """Test validate refuses backend build patterns that escape backend."""
    extension_json = {
        "publisher": "test-org",
        "name": "test-extension",
        "displayName": "Test Extension",
        "version": "1.0.0",
        "permissions": [],
    }
    (isolated_filesystem / "extension.json").write_text(json.dumps(extension_json))

    backend_dir = isolated_filesystem / "backend"
    backend_dir.mkdir()
    (backend_dir / "pyproject.toml").write_text(
        f"""[project]
name = "test-org-test-extension"
version = "1.0.0"

[tool.apache_superset_extensions.build]
{build_config}
"""
    )

    with patch("superset_extensions_cli.cli.validate_npm"):
        result = cli_runner.invoke(app, ["validate"])

    assert result.exit_code == 1
    assert expected_message in result.output


@pytest.mark.cli
def test_validate_fails_when_backend_entrypoint_is_directory(
    cli_runner, isolated_filesystem, extension_with_versions
):
    """Test validate requires backend entrypoint.py to be a file."""
    extension_with_versions(
        isolated_filesystem,
        ext_version="1.0.0",
        backend_version="1.0.0",
    )
    entrypoint_path = (
        isolated_filesystem
        / "backend"
        / "src"
        / "test_org"
        / "test_extension"
        / "entrypoint.py"
    )
    entrypoint_path.unlink()
    entrypoint_path.mkdir()

    with patch("superset_extensions_cli.cli.validate_npm"):
        result = cli_runner.invoke(app, ["validate"])

    assert result.exit_code == 1
    assert "Backend entry point not found" in result.output


@pytest.mark.cli
def test_validate_rejects_symlinked_backend_entrypoint(
    cli_runner, isolated_filesystem, extension_with_versions
):
    """Test validate refuses a symlinked backend entrypoint."""
    extension_with_versions(
        isolated_filesystem,
        ext_version="1.0.0",
        backend_version="1.0.0",
    )
    entrypoint_path = (
        isolated_filesystem
        / "backend"
        / "src"
        / "test_org"
        / "test_extension"
        / "entrypoint.py"
    )
    outside_entrypoint = isolated_filesystem / "outside-entrypoint.py"
    outside_entrypoint.write_text("# outside")
    entrypoint_path.unlink()
    entrypoint_path.symlink_to(outside_entrypoint)

    with patch("superset_extensions_cli.cli.validate_npm"):
        result = cli_runner.invoke(app, ["validate"])

    assert result.exit_code == 1
    assert "Backend entry point path is a symlink" in result.output


@pytest.mark.cli
def test_validate_rejects_symlinked_backend_entrypoint_parent(
    cli_runner, isolated_filesystem, extension_with_versions
):
    """Test validate refuses backend entrypoints below symlinked parents."""
    extension_with_versions(
        isolated_filesystem,
        ext_version="1.0.0",
        backend_version="1.0.0",
    )
    entrypoint_dir = (
        isolated_filesystem / "backend" / "src" / "test_org" / "test_extension"
    )
    (entrypoint_dir / "entrypoint.py").unlink()
    entrypoint_dir.rmdir()
    outside_entrypoint_dir = isolated_filesystem / "outside-entrypoint-package"
    outside_entrypoint_dir.mkdir()
    (outside_entrypoint_dir / "entrypoint.py").write_text("# outside")
    entrypoint_dir.symlink_to(outside_entrypoint_dir)

    with patch("superset_extensions_cli.cli.validate_npm"):
        result = cli_runner.invoke(app, ["validate"])

    assert result.exit_code == 1
    assert "Backend entry point parent directory is a symlink" in result.output


@pytest.mark.cli
def test_validate_rejects_backend_entrypoint_changed_during_validation(
    cli_runner, isolated_filesystem, extension_with_versions, monkeypatch
):
    """Test validate refuses a backend entrypoint changed during validation."""
    extension_with_versions(
        isolated_filesystem,
        ext_version="1.0.0",
        backend_version="1.0.0",
    )
    entrypoint_path = (
        isolated_filesystem
        / "backend"
        / "src"
        / "test_org"
        / "test_extension"
        / "entrypoint.py"
    )
    replacement_entrypoint = isolated_filesystem / "replacement-entrypoint.py"
    replacement_entrypoint.write_text("# replacement")

    from superset_extensions_cli import cli

    original_get_read_path_identity = cli.get_read_path_identity
    identity_reads = 0

    def replace_entrypoint_after_first_identity(path):
        nonlocal identity_reads
        identity = original_get_read_path_identity(path)
        if path == entrypoint_path:
            identity_reads += 1
            if identity_reads == 1:
                entrypoint_path.unlink()
                replacement_entrypoint.replace(entrypoint_path)
        return identity

    monkeypatch.setattr(
        cli,
        "get_read_path_identity",
        replace_entrypoint_after_first_identity,
    )

    with patch("superset_extensions_cli.cli.validate_npm"):
        result = cli_runner.invoke(app, ["validate"])

    assert result.exit_code == 1
    assert "Backend entry point path changed during validation" in result.output


@pytest.mark.cli
def test_validate_fails_when_frontend_entrypoint_is_directory(
    cli_runner, isolated_filesystem, extension_with_versions
):
    """Test validate requires frontend src/index.tsx to be a file."""
    extension_with_versions(
        isolated_filesystem,
        ext_version="1.0.0",
        frontend_version="1.0.0",
    )
    entrypoint_path = isolated_filesystem / "frontend" / "src" / "index.tsx"
    entrypoint_path.unlink()
    entrypoint_path.mkdir()

    with patch("superset_extensions_cli.cli.validate_npm"):
        result = cli_runner.invoke(app, ["validate"])

    assert result.exit_code == 1
    assert "Frontend entry point not found" in result.output


@pytest.mark.cli
def test_validate_rejects_symlinked_frontend_entrypoint(
    cli_runner, isolated_filesystem, extension_with_versions
):
    """Test validate refuses a symlinked frontend entrypoint."""
    extension_with_versions(
        isolated_filesystem,
        ext_version="1.0.0",
        frontend_version="1.0.0",
    )
    entrypoint_path = isolated_filesystem / "frontend" / "src" / "index.tsx"
    outside_entrypoint = isolated_filesystem / "outside-index.tsx"
    outside_entrypoint.write_text("export default {}")
    entrypoint_path.unlink()
    entrypoint_path.symlink_to(outside_entrypoint)

    with patch("superset_extensions_cli.cli.validate_npm"):
        result = cli_runner.invoke(app, ["validate"])

    assert result.exit_code == 1
    assert "Frontend entry point path is a symlink" in result.output


@pytest.mark.cli
def test_validate_rejects_symlinked_frontend_entrypoint_parent(
    cli_runner, isolated_filesystem, extension_with_versions
):
    """Test validate refuses frontend entrypoints below symlinked parents."""
    extension_with_versions(
        isolated_filesystem,
        ext_version="1.0.0",
        frontend_version="1.0.0",
    )
    frontend_src = isolated_filesystem / "frontend" / "src"
    (frontend_src / "index.tsx").unlink()
    frontend_src.rmdir()
    outside_frontend_src = isolated_filesystem / "outside-frontend-src"
    outside_frontend_src.mkdir()
    (outside_frontend_src / "index.tsx").write_text("export default {}")
    frontend_src.symlink_to(outside_frontend_src)

    with patch("superset_extensions_cli.cli.validate_npm"):
        result = cli_runner.invoke(app, ["validate"])

    assert result.exit_code == 1
    assert "Frontend entry point parent directory is a symlink" in result.output


@pytest.mark.cli
@pytest.mark.parametrize(
    ("path_name", "path_factory", "expected_message"),
    [
        (
            "frontend",
            create_file_path,
            "frontend path exists but is not a directory",
        ),
        (
            "backend",
            create_broken_symlink,
            "backend path is a symlink",
        ),
        (
            "frontend",
            create_directory_symlink,
            "frontend path is a symlink",
        ),
        (
            "backend",
            create_directory_symlink,
            "backend path is a symlink",
        ),
    ],
)
def test_validate_fails_when_source_path_is_not_directory(
    cli_runner,
    isolated_filesystem,
    path_name,
    path_factory,
    expected_message,
):
    """Test validate rejects source paths that are not real directories."""
    extension_json = {
        "publisher": "test-org",
        "name": "test-extension",
        "displayName": "Test Extension",
        "version": "1.0.0",
        "permissions": [],
    }
    (isolated_filesystem / "extension.json").write_text(json.dumps(extension_json))
    path_factory(isolated_filesystem / path_name)

    with patch("superset_extensions_cli.cli.validate_npm"):
        result = cli_runner.invoke(app, ["validate"])

    assert result.exit_code == 1
    assert expected_message in result.output


@pytest.mark.cli
def test_validate_rejects_source_directory_changed_during_validation(
    cli_runner, isolated_filesystem, monkeypatch
):
    """Test validate refuses a source directory changed during validation."""
    extension_json = {
        "publisher": "test-org",
        "name": "test-extension",
        "displayName": "Test Extension",
        "version": "1.0.0",
        "permissions": [],
    }
    (isolated_filesystem / "extension.json").write_text(json.dumps(extension_json))
    backend_dir = isolated_filesystem / "backend"
    backend_dir.mkdir()
    saved_backend_dir = isolated_filesystem / "saved-backend"
    replacement_backend_dir = isolated_filesystem / "replacement-backend"
    replacement_backend_dir.mkdir()

    from superset_extensions_cli import cli

    original_get_directory_path_identity = cli.get_directory_path_identity
    identity_reads = 0

    def replace_backend_after_first_identity(path):
        nonlocal identity_reads
        identity = original_get_directory_path_identity(path)
        if path == backend_dir:
            identity_reads += 1
            if identity_reads == 1:
                backend_dir.rename(saved_backend_dir)
                replacement_backend_dir.rename(backend_dir)
        return identity

    monkeypatch.setattr(
        cli,
        "get_directory_path_identity",
        replace_backend_after_first_identity,
    )

    with patch("superset_extensions_cli.cli.validate_npm"):
        result = cli_runner.invoke(app, ["validate"])

    assert result.exit_code == 1
    assert "backend path changed during validation" in result.output


@pytest.mark.cli
@pytest.mark.parametrize("package_json", ["{ invalid json", "[]"])
def test_validate_fails_with_invalid_frontend_package_json(
    cli_runner, isolated_filesystem, extension_with_versions, package_json
):
    """Test validate reports malformed frontend/package.json cleanly."""
    extension_with_versions(
        isolated_filesystem,
        ext_version="1.0.0",
        frontend_version="1.0.0",
    )
    (isolated_filesystem / "frontend" / "package.json").write_text(package_json)

    with patch("superset_extensions_cli.cli.validate_npm"):
        result = cli_runner.invoke(app, ["validate"])

    assert result.exit_code == 1
    assert "Invalid frontend/package.json" in result.output


@pytest.mark.cli
def test_validate_fails_when_frontend_package_json_is_directory(
    cli_runner, isolated_filesystem, extension_with_versions
):
    """Test validate reports frontend package metadata paths that are directories."""
    extension_with_versions(
        isolated_filesystem,
        ext_version="1.0.0",
        frontend_version="1.0.0",
    )
    package_json_path = isolated_filesystem / "frontend" / "package.json"
    package_json_path.unlink()
    package_json_path.mkdir()

    with patch("superset_extensions_cli.cli.validate_npm"):
        result = cli_runner.invoke(app, ["validate"])

    assert result.exit_code == 1
    assert "frontend/package.json path exists but is not a file" in result.output


@pytest.mark.cli
def test_validate_fails_with_malformed_backend_pyproject_toml(
    cli_runner, isolated_filesystem, extension_with_versions
):
    """Test validate reports malformed backend pyproject.toml cleanly."""
    extension_with_versions(
        isolated_filesystem,
        ext_version="1.0.0",
        backend_version="1.0.0",
    )
    (isolated_filesystem / "backend" / "pyproject.toml").write_text("[ invalid toml")

    with patch("superset_extensions_cli.cli.validate_npm"):
        result = cli_runner.invoke(app, ["validate"])

    assert result.exit_code == 1
    assert "Invalid backend pyproject.toml" in result.output


@pytest.mark.cli
def test_validate_fails_when_backend_pyproject_is_directory(
    cli_runner, isolated_filesystem, extension_with_versions
):
    """Test validate reports backend TOML metadata paths that are directories."""
    extension_with_versions(
        isolated_filesystem,
        ext_version="1.0.0",
        backend_version="1.0.0",
    )
    pyproject_path = isolated_filesystem / "backend" / "pyproject.toml"
    pyproject_path.unlink()
    pyproject_path.mkdir()

    with patch("superset_extensions_cli.cli.validate_npm"):
        result = cli_runner.invoke(app, ["validate"])

    assert result.exit_code == 1
    assert "backend/pyproject.toml path exists but is not a file" in result.output


@pytest.mark.cli
def test_validate_fails_with_non_table_backend_project(
    cli_runner, isolated_filesystem, extension_with_versions
):
    """Test validate reports invalid backend [project] shape cleanly."""
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

    with patch("superset_extensions_cli.cli.validate_npm"):
        result = cli_runner.invoke(app, ["validate"])

    assert result.exit_code == 1
    assert "Invalid backend/pyproject.toml: [project] must be a table" in result.output


# Validate NPM Function Tests
@pytest.mark.unit
@patch("shutil.which")
def test_validate_npm_fails_when_npm_not_on_path(mock_which):
    """Test validate_npm fails when npm is not on PATH."""
    mock_which.return_value = None

    with pytest.raises(SystemExit) as exc_info:
        validate_npm()

    assert exc_info.value.code == 1
    mock_which.assert_called_once_with("npm")


@pytest.mark.unit
@patch("shutil.which")
@patch("subprocess.run")
def test_validate_npm_fails_when_npm_command_fails(mock_run, mock_which):
    """Test validate_npm fails when npm -v command fails."""
    mock_which.return_value = "/usr/bin/npm"
    mock_run.return_value = Mock(returncode=1, stderr="Command failed")

    with pytest.raises(SystemExit) as exc_info:
        validate_npm()

    assert exc_info.value.code == 1


@pytest.mark.unit
@patch("shutil.which")
@patch("subprocess.run")
def test_validate_npm_fails_when_version_too_low(mock_run, mock_which):
    """Test validate_npm fails when npm version is below minimum."""
    mock_which.return_value = "/usr/bin/npm"
    mock_run.return_value = Mock(returncode=0, stdout="9.0.0\n", stderr="")

    with pytest.raises(SystemExit) as exc_info:
        validate_npm()

    assert exc_info.value.code == 1


@pytest.mark.unit
@pytest.mark.parametrize(
    "npm_version",
    [
        "10.8.2",  # Exact minimum version
        "11.0.0",  # Higher version
        "10.9.0-alpha.1",  # Pre-release version higher than minimum
    ],
)
@patch("shutil.which")
@patch("subprocess.run")
def test_validate_npm_succeeds_with_valid_versions(mock_run, mock_which, npm_version):
    """Test validate_npm succeeds when npm version is valid."""
    mock_which.return_value = "/usr/bin/npm"
    mock_run.return_value = Mock(returncode=0, stdout=f"{npm_version}\n", stderr="")

    # Should not raise SystemExit
    validate_npm()


@pytest.mark.unit
@pytest.mark.parametrize(
    "npm_version,should_pass",
    [
        ("10.8.2", True),  # Exact minimum version
        ("10.8.1", False),  # Slightly lower version
        ("10.9.0-alpha.1", True),  # Pre-release version higher than minimum
        ("9.9.9", False),  # Much lower version
        ("11.0.0", True),  # Much higher version
    ],
)
@patch("shutil.which")
@patch("subprocess.run")
def test_validate_npm_version_comparison_edge_cases(
    mock_run, mock_which, npm_version, should_pass
):
    """Test npm version comparison with edge cases."""
    mock_which.return_value = "/usr/bin/npm"
    mock_run.return_value = Mock(returncode=0, stdout=f"{npm_version}\n", stderr="")

    if should_pass:
        # Should not raise SystemExit
        validate_npm()
    else:
        with pytest.raises(SystemExit):
            validate_npm()


@pytest.mark.unit
@patch("shutil.which")
@patch("subprocess.run")
@pytest.mark.parametrize(
    "exception_type",
    [
        FileNotFoundError,
        OSError,
        PermissionError,
    ],
)
def test_validate_npm_handles_subprocess_launch_errors(
    mock_run, mock_which, capsys, exception_type
):
    """Test validate_npm handles npm launch errors gracefully."""
    mock_which.return_value = "/usr/bin/npm"
    mock_run.side_effect = exception_type("Test error")

    with pytest.raises(SystemExit) as exc_info:
        validate_npm()

    assert exc_info.value.code == 1
    assert "Failed to run `npm -v`: Test error" in capsys.readouterr().err


@pytest.mark.unit
@patch("shutil.which")
@patch("subprocess.run")
def test_validate_npm_with_malformed_version_output_exits_cleanly(
    mock_run, mock_which, capsys
):
    """Test validate_npm exits cleanly with malformed version output."""
    mock_which.return_value = "/usr/bin/npm"
    mock_run.return_value = Mock(returncode=0, stdout="not-a-version\n", stderr="")

    with pytest.raises(SystemExit) as exc_info:
        validate_npm()

    assert exc_info.value.code == 1
    assert "Failed to parse npm version" in capsys.readouterr().err


@pytest.mark.unit
@patch("shutil.which")
@patch("subprocess.run")
def test_validate_npm_with_empty_version_output_exits_cleanly(
    mock_run, mock_which, capsys
):
    """Test validate_npm exits cleanly with empty version output."""
    mock_which.return_value = "/usr/bin/npm"
    mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

    with pytest.raises(SystemExit) as exc_info:
        validate_npm()

    assert exc_info.value.code == 1
    assert "Failed to parse npm version" in capsys.readouterr().err


# Version Consistency Tests
@pytest.mark.cli
def test_validate_fails_on_version_mismatch(
    cli_runner, isolated_filesystem, extension_with_versions
):
    """Test validate fails when frontend/backend versions differ from extension.json."""
    extension_with_versions(
        isolated_filesystem,
        ext_version="2.0.0",
        frontend_version="1.0.0",
        backend_version="1.0.0",
    )

    with patch("superset_extensions_cli.cli.validate_npm"):
        result = cli_runner.invoke(app, ["validate"])

    assert result.exit_code != 0
    assert "Metadata mismatch" in result.output
    assert "superset-extensions update" in result.output


@pytest.mark.cli
def test_validate_passes_with_matching_versions(
    cli_runner, isolated_filesystem, extension_with_versions
):
    """Test validate passes when all versions match extension.json."""
    extension_with_versions(
        isolated_filesystem,
        ext_version="1.0.0",
        frontend_version="1.0.0",
        backend_version="1.0.0",
    )

    with patch("superset_extensions_cli.cli.validate_npm"):
        result = cli_runner.invoke(app, ["validate"])

    assert result.exit_code == 0
    assert "Validation successful" in result.output


@pytest.mark.cli
def test_validate_fails_on_license_mismatch(
    cli_runner, isolated_filesystem, extension_with_versions
):
    """Test validate fails when frontend/backend licenses differ from extension.json."""
    extension_with_versions(
        isolated_filesystem,
        ext_version="1.0.0",
        frontend_version="1.0.0",
        backend_version="1.0.0",
        ext_license="Apache-2.0",
        frontend_license="MIT",
        backend_license="MIT",
    )

    with patch("superset_extensions_cli.cli.validate_npm"):
        result = cli_runner.invoke(app, ["validate"])

    assert result.exit_code != 0
    assert "Metadata mismatch" in result.output
    assert "license" in result.output

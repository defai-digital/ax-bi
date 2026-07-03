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

from pathlib import Path

import click
import pytest
import superset_extensions_cli.cli as cli
from superset_extensions_cli.cli import (
    app,
    cleanup_scaffold_directory,
    create_scaffold_directory,
)

from tests.utils import (
    assert_directory_exists,
    assert_directory_structure,
    assert_file_exists,
    assert_file_structure,
    assert_json_content,
    create_test_extension_structure,
    load_json_file,
)


# Init Command Tests
@pytest.mark.cli
def test_init_creates_extension_with_both_frontend_and_backend(
    cli_runner, isolated_filesystem, cli_input_both
):
    """Test that init creates a complete extension with both frontend and backend."""
    result = cli_runner.invoke(app, ["init"], input=cli_input_both)

    assert result.exit_code == 0, f"Command failed with output: {result.output}"
    assert (
        "🎉 Extension Test Extension (ID: test-org.test-extension) initialized"
        in result.output
    )

    # Verify directory structure
    extension_path = isolated_filesystem / "test-extension"
    assert_directory_exists(extension_path, "main extension directory")

    expected_structure = create_test_extension_structure(
        isolated_filesystem,
        "test-extension",
        include_frontend=True,
        include_backend=True,
    )

    # Check directories
    assert_directory_structure(extension_path, expected_structure["expected_dirs"])

    # Check files
    assert_file_structure(extension_path, expected_structure["expected_files"])


@pytest.mark.cli
def test_init_creates_extension_with_frontend_only(
    cli_runner, isolated_filesystem, cli_input_frontend_only
):
    """Test that init creates extension with only frontend components."""
    result = cli_runner.invoke(app, ["init"], input=cli_input_frontend_only)

    assert result.exit_code == 0, f"Command failed with output: {result.output}"

    extension_path = isolated_filesystem / "test-extension"
    assert_directory_exists(extension_path)

    # Should have frontend directory and package.json
    assert_directory_exists(extension_path / "frontend")
    assert_file_exists(extension_path / "frontend" / "package.json")

    # Should NOT have backend directory
    backend_path = extension_path / "backend"
    assert not backend_path.exists(), (
        "Backend directory should not exist for frontend-only extension"
    )


@pytest.mark.cli
def test_init_creates_extension_with_backend_only(
    cli_runner, isolated_filesystem, cli_input_backend_only
):
    """Test that init creates extension with only backend components."""
    result = cli_runner.invoke(app, ["init"], input=cli_input_backend_only)

    assert result.exit_code == 0, f"Command failed with output: {result.output}"

    extension_path = isolated_filesystem / "test-extension"
    assert_directory_exists(extension_path)

    # Should have backend directory and pyproject.toml
    assert_directory_exists(extension_path / "backend")
    assert_file_exists(extension_path / "backend" / "pyproject.toml")

    # Should NOT have frontend directory
    frontend_path = extension_path / "frontend"
    assert not frontend_path.exists(), (
        "Frontend directory should not exist for backend-only extension"
    )


@pytest.mark.cli
def test_init_creates_extension_with_neither_frontend_nor_backend(
    cli_runner, isolated_filesystem, cli_input_neither
):
    """Test that init creates minimal extension with neither frontend nor backend."""
    result = cli_runner.invoke(app, ["init"], input=cli_input_neither)

    assert result.exit_code == 0, f"Command failed with output: {result.output}"

    extension_path = isolated_filesystem / "test-extension"
    assert_directory_exists(extension_path)

    # Should only have extension.json
    assert_file_exists(extension_path / "extension.json")

    # Should NOT have frontend or backend directories
    assert not (extension_path / "frontend").exists()
    assert not (extension_path / "backend").exists()


@pytest.mark.cli
def test_init_accepts_valid_display_name(cli_runner, isolated_filesystem):
    """Test that init accepts valid display names and generates proper ID."""
    cli_input = "My Awesome Extension\n\ntest-org\n0.1.0\nApache-2.0\ny\ny\n"
    result = cli_runner.invoke(app, ["init"], input=cli_input)

    assert result.exit_code == 0, f"Should accept display name: {result.output}"
    assert Path("my-awesome-extension").exists(), (
        "Directory with extension name should be created"
    )


@pytest.mark.cli
def test_init_accepts_mixed_alphanumeric_name(cli_runner, isolated_filesystem):
    """Test that init accepts mixed alphanumeric display names."""
    cli_input = "Tool 123\n\ntest-org\n0.1.0\nApache-2.0\ny\ny\n"
    result = cli_runner.invoke(app, ["init"], input=cli_input)

    assert result.exit_code == 0, (
        f"Mixed alphanumeric display name should be valid: {result.output}"
    )
    assert Path("tool-123").exists(), "Directory for 'tool-123' should be created"


@pytest.mark.cli
@pytest.mark.parametrize(
    "display_name,expected_dir",
    [
        ("Test Extension", "test-extension"),
        ("My Tool v2", "my-tool-v2"),
        ("Dashboard Helper", "dashboard-helper"),
        ("Chart Builder Pro", "chart-builder-pro"),
    ],
)
def test_init_with_various_display_names(cli_runner, display_name, expected_dir):
    """Test that init accepts various display names and creates directory named after extension."""
    with cli_runner.isolated_filesystem():
        cli_input = f"{display_name}\n\ntest-org\n0.1.0\nApache-2.0\ny\ny\n"
        result = cli_runner.invoke(app, ["init"], input=cli_input)

        assert result.exit_code == 0, (
            f"Valid display name '{display_name}' was rejected: {result.output}"
        )
        assert Path(expected_dir).exists(), (
            f"Directory '{expected_dir}' was not created"
        )


@pytest.mark.cli
def test_init_fails_when_directory_already_exists(
    cli_runner, isolated_filesystem, cli_input_both
):
    """Test that init fails gracefully when target directory already exists."""
    # Create the directory first
    existing_dir = isolated_filesystem / "test-extension"
    existing_dir.mkdir()

    result = cli_runner.invoke(app, ["init"], input=cli_input_both)

    assert result.exit_code == 1, "Command should fail when directory already exists"
    assert "already exists" in result.output


@pytest.mark.cli
def test_init_fails_when_target_is_broken_symlink(
    cli_runner, isolated_filesystem, cli_input_both
):
    """Test that init fails gracefully when target path is a broken symlink."""
    existing_link = isolated_filesystem / "test-extension"
    existing_link.symlink_to(isolated_filesystem / "missing-target")

    result = cli_runner.invoke(app, ["init"], input=cli_input_both)

    assert result.exit_code == 1
    assert "already exists" in result.output
    assert existing_link.is_symlink()


@pytest.mark.unit
def test_cleanup_scaffold_directory_rejects_broken_symlink_target(
    isolated_filesystem,
):
    """Test scaffold cleanup refuses a broken symlink target."""
    target_link = isolated_filesystem / "test-extension"
    target_link.symlink_to(isolated_filesystem / "missing-target")

    with pytest.raises(
        click.ClickException,
        match="Refusing to clean extension directory: path is a symlink",
    ):
        cleanup_scaffold_directory(target_link, "extension directory")

    assert target_link.is_symlink()


@pytest.mark.unit
def test_cleanup_scaffold_directory_rejects_changed_target(
    isolated_filesystem,
    monkeypatch,
):
    """Test scaffold cleanup refuses a directory changed before deletion."""
    target_dir = isolated_filesystem / "test-extension"
    target_dir.mkdir()
    (target_dir / "extension.json").write_text("{}")
    replacement_dir = isolated_filesystem / "replacement-extension"
    replacement_dir.mkdir()
    (replacement_dir / "replacement.json").write_text("{}")
    saved_original = isolated_filesystem / "saved-original-extension"
    original_get_directory_path_identity = cli.get_directory_path_identity
    identity_reads = 0

    def replace_target_after_initial_identity(path):
        nonlocal identity_reads
        identity = original_get_directory_path_identity(path)
        if path == target_dir:
            identity_reads += 1
            if identity_reads == 1:
                target_dir.rename(saved_original)
                replacement_dir.rename(target_dir)
        return identity

    monkeypatch.setattr(
        "superset_extensions_cli.cli.get_directory_path_identity",
        replace_target_after_initial_identity,
    )

    with pytest.raises(
        click.ClickException,
        match="Refusing to clean extension directory: path changed",
    ):
        cleanup_scaffold_directory(target_dir, "extension directory")

    assert_file_exists(saved_original / "extension.json")
    assert_file_exists(target_dir / "replacement.json")


@pytest.mark.unit
def test_create_scaffold_directory_rejects_changed_parent(
    isolated_filesystem,
    monkeypatch,
):
    """Test scaffold directory creation refuses a changed parent directory."""
    parent_dir = isolated_filesystem / "workspace"
    parent_dir.mkdir()
    target_dir = parent_dir / "test-extension"
    saved_parent = isolated_filesystem / "saved-workspace"
    replacement_parent = isolated_filesystem / "replacement-workspace"
    replacement_parent.mkdir()
    original_mkdir = Path.mkdir
    swapped = False

    def swap_parent_before_mkdir(path, *args, **kwargs):
        nonlocal swapped
        if path == target_dir and not swapped:
            parent_dir.rename(saved_parent)
            replacement_parent.rename(parent_dir)
            swapped = True
        return original_mkdir(path, *args, **kwargs)

    monkeypatch.setattr(Path, "mkdir", swap_parent_before_mkdir)

    with pytest.raises(
        click.ClickException,
        match="Refusing to create extension directory: parent path changed",
    ):
        create_scaffold_directory(target_dir, "extension directory")

    assert_directory_exists(saved_parent)
    assert not target_dir.exists()


@pytest.mark.unit
def test_create_scaffold_directory_rejects_changed_created_path(
    isolated_filesystem,
    monkeypatch,
):
    """Test scaffold directory creation refuses a replaced created path."""
    target_dir = isolated_filesystem / "test-extension"
    saved_target_dir = isolated_filesystem / "saved-test-extension"
    replacement_dir = isolated_filesystem / "replacement-test-extension"
    replacement_dir.mkdir()
    (replacement_dir / "replacement.txt").write_text("replacement")
    original_get_directory_path_identity = cli.get_directory_path_identity
    target_identity_reads = 0

    def replace_target_after_created_identity(path):
        nonlocal target_identity_reads
        identity = original_get_directory_path_identity(path)
        if path == target_dir and identity is not None:
            target_identity_reads += 1
            if target_identity_reads == 1:
                target_dir.rename(saved_target_dir)
                replacement_dir.rename(target_dir)
        return identity

    monkeypatch.setattr(
        "superset_extensions_cli.cli.get_directory_path_identity",
        replace_target_after_created_identity,
    )

    with pytest.raises(
        click.ClickException,
        match="Refusing to create extension directory: path changed",
    ):
        create_scaffold_directory(target_dir, "extension directory")

    assert_directory_exists(saved_target_dir)
    assert_file_exists(target_dir / "replacement.txt")


@pytest.mark.cli
def test_init_reports_scaffold_directory_create_errors(
    cli_runner, isolated_filesystem, monkeypatch
):
    """Test init reports target directory creation failures cleanly."""
    original_mkdir = Path.mkdir

    def fail_target_mkdir(path, *args, **kwargs):
        if path == isolated_filesystem / "test-extension":
            raise OSError("permission denied")
        return original_mkdir(path, *args, **kwargs)

    monkeypatch.setattr(Path, "mkdir", fail_target_mkdir)

    result = cli_runner.invoke(
        app,
        [
            "init",
            "--publisher",
            "test-org",
            "--name",
            "test-extension",
            "--display-name",
            "Test Extension",
            "--version",
            "1.0.0",
            "--license",
            "Apache-2.0",
            "--frontend",
            "--backend",
        ],
    )

    assert result.exit_code == 1
    assert "Failed to create extension directory: permission denied" in result.output


@pytest.mark.cli
def test_init_reports_scaffold_file_write_errors(
    cli_runner, isolated_filesystem, monkeypatch
):
    """Test init reports scaffold file write failures cleanly."""
    extension_json_path = isolated_filesystem / "test-extension" / "extension.json"
    original_replace = Path.replace

    def fail_extension_json_replace(path, target):
        if target == extension_json_path:
            raise OSError("disk full")
        return original_replace(path, target)

    monkeypatch.setattr(Path, "replace", fail_extension_json_replace)

    result = cli_runner.invoke(
        app,
        [
            "init",
            "--publisher",
            "test-org",
            "--name",
            "test-extension",
            "--display-name",
            "Test Extension",
            "--version",
            "1.0.0",
            "--license",
            "Apache-2.0",
            "--frontend",
            "--backend",
        ],
    )

    assert result.exit_code == 1
    assert "Failed to create extension.json: disk full" in result.output
    assert not extension_json_path.exists()
    assert not (isolated_filesystem / "test-extension").exists()
    assert (
        list((isolated_filesystem / "test-extension").glob(".extension.json.*.tmp"))
        == []
    )


@pytest.mark.unit
def test_write_scaffold_file_requires_missing_target(
    isolated_filesystem,
    monkeypatch,
):
    """Test scaffold file creation binds the final write to a missing target."""
    target_path = isolated_filesystem / "extension.json"
    seen_require_missing: list[bool] = []
    original_write_text_atomic = cli.write_text_atomic

    def capture_require_missing(path, content, **kwargs):
        seen_require_missing.append(kwargs.get("require_missing", False))
        return original_write_text_atomic(path, content, **kwargs)

    monkeypatch.setattr(cli, "write_text_atomic", capture_require_missing)

    cli.write_scaffold_file(target_path, "extension.json", "{}")

    assert seen_require_missing == [True]
    assert target_path.read_text() == "{}"


@pytest.mark.cli
def test_init_cleans_partial_scaffold_on_nested_directory_error(
    cli_runner, isolated_filesystem, monkeypatch
):
    """Test init removes the target directory when nested scaffolding fails."""
    frontend_src_path = isolated_filesystem / "test-extension" / "frontend" / "src"
    original_mkdir = Path.mkdir

    def fail_frontend_src_mkdir(path, *args, **kwargs):
        if path == frontend_src_path:
            raise OSError("cannot create src")
        return original_mkdir(path, *args, **kwargs)

    monkeypatch.setattr(Path, "mkdir", fail_frontend_src_mkdir)

    result = cli_runner.invoke(
        app,
        [
            "init",
            "--publisher",
            "test-org",
            "--name",
            "test-extension",
            "--display-name",
            "Test Extension",
            "--version",
            "1.0.0",
            "--license",
            "Apache-2.0",
            "--frontend",
            "--no-backend",
        ],
    )

    assert result.exit_code == 1
    assert "Failed to create frontend src directory: cannot create src" in result.output
    assert not (isolated_filesystem / "test-extension").exists()


@pytest.mark.cli
def test_init_refuses_cleanup_when_scaffold_root_changes(
    cli_runner, isolated_filesystem, monkeypatch
):
    """Test init does not clean a replacement scaffold root on rollback."""
    target_dir = isolated_filesystem / "test-extension"
    saved_target_dir = isolated_filesystem / "saved-test-extension"
    replacement_dir = isolated_filesystem / "replacement-test-extension"
    replacement_dir.mkdir()
    (replacement_dir / "replacement.txt").write_text("replacement")
    original_write_scaffold_file = cli.write_scaffold_file

    def swap_target_before_scaffold_failure(path, label, content):
        if label == ".gitignore":
            target_dir.rename(saved_target_dir)
            replacement_dir.rename(target_dir)
            raise click.ClickException("scaffold failed")
        original_write_scaffold_file(path, label, content)

    monkeypatch.setattr(
        "superset_extensions_cli.cli.write_scaffold_file",
        swap_target_before_scaffold_failure,
    )

    result = cli_runner.invoke(
        app,
        [
            "init",
            "--publisher",
            "test-org",
            "--name",
            "test-extension",
            "--display-name",
            "Test Extension",
            "--version",
            "1.0.0",
            "--license",
            "Apache-2.0",
            "--frontend",
            "--backend",
        ],
    )

    assert result.exit_code == 1
    assert "Refusing to clean extension directory: path changed" in result.output
    assert "scaffold failed" in result.output
    assert_file_exists(saved_target_dir / "extension.json")
    assert_file_exists(target_dir / "replacement.txt")


@pytest.mark.cli
def test_init_refuses_cleanup_when_scaffold_root_content_changes(
    cli_runner,
    isolated_filesystem,
    monkeypatch,
):
    """Test init does not clean scaffold root after unexpected root content changes."""
    target_dir = isolated_filesystem / "test-extension"
    original_write_scaffold_file = cli.write_scaffold_file

    def change_target_before_scaffold_failure(path, label, content):
        if label == ".gitignore":
            (target_dir / "external.txt").write_text("external")
            raise click.ClickException("scaffold failed")
        original_write_scaffold_file(path, label, content)

    monkeypatch.setattr(
        "superset_extensions_cli.cli.write_scaffold_file",
        change_target_before_scaffold_failure,
    )

    result = cli_runner.invoke(
        app,
        [
            "init",
            "--publisher",
            "test-org",
            "--name",
            "test-extension",
            "--display-name",
            "Test Extension",
            "--version",
            "1.0.0",
            "--license",
            "Apache-2.0",
            "--frontend",
            "--backend",
        ],
    )

    assert result.exit_code == 1
    assert "Refusing to clean extension directory: path changed" in result.output
    assert "scaffold failed" in result.output
    assert_file_exists(target_dir / "extension.json")
    assert_file_exists(target_dir / "external.txt")


@pytest.mark.cli
def test_init_refuses_cleanup_when_nested_scaffold_content_changes(
    cli_runner,
    isolated_filesystem,
    monkeypatch,
):
    """Test init does not clean scaffold root after unexpected nested changes."""
    target_dir = isolated_filesystem / "test-extension"
    nested_external_file = target_dir / "frontend" / "src" / "external.tsx"
    original_write_scaffold_file = cli.write_scaffold_file

    def change_nested_before_scaffold_failure(path, label, content):
        if label == "backend/pyproject.toml":
            raise click.ClickException("scaffold failed")
        original_write_scaffold_file(path, label, content)
        if label == "frontend/src/index.tsx":
            nested_external_file.write_text("external")

    monkeypatch.setattr(
        "superset_extensions_cli.cli.write_scaffold_file",
        change_nested_before_scaffold_failure,
    )

    result = cli_runner.invoke(
        app,
        [
            "init",
            "--publisher",
            "test-org",
            "--name",
            "test-extension",
            "--display-name",
            "Test Extension",
            "--version",
            "1.0.0",
            "--license",
            "Apache-2.0",
            "--frontend",
            "--backend",
        ],
    )

    assert result.exit_code == 1
    assert "Refusing to clean extension directory: path changed" in result.output
    assert "scaffold failed" in result.output
    assert_file_exists(target_dir / "frontend" / "src" / "index.tsx")
    assert nested_external_file.read_text() == "external"


@pytest.mark.cli
def test_init_refuses_cleanup_when_nested_scaffold_directory_changes(
    cli_runner,
    isolated_filesystem,
    monkeypatch,
):
    """Test init does not clean scaffold root after nested directory replacement."""
    target_dir = isolated_filesystem / "test-extension"
    frontend_src_dir = target_dir / "frontend" / "src"
    saved_src_dir = isolated_filesystem / "saved-src"
    replacement_src_dir = isolated_filesystem / "replacement-src"
    replacement_src_dir.mkdir()
    (replacement_src_dir / "index.tsx").write_text("replacement")
    original_write_scaffold_file = cli.write_scaffold_file

    def replace_nested_before_scaffold_failure(path, label, content):
        original_write_scaffold_file(path, label, content)
        if label == "frontend/src/index.tsx":
            frontend_src_dir.rename(saved_src_dir)
            replacement_src_dir.rename(frontend_src_dir)
        if label == "backend/pyproject.toml":
            raise click.ClickException("scaffold failed")

    monkeypatch.setattr(
        "superset_extensions_cli.cli.write_scaffold_file",
        replace_nested_before_scaffold_failure,
    )

    result = cli_runner.invoke(
        app,
        [
            "init",
            "--publisher",
            "test-org",
            "--name",
            "test-extension",
            "--display-name",
            "Test Extension",
            "--version",
            "1.0.0",
            "--license",
            "Apache-2.0",
            "--frontend",
            "--backend",
        ],
    )

    assert result.exit_code == 1
    assert "Refusing to clean extension directory: path changed" in result.output
    assert "scaffold failed" in result.output
    assert_file_exists(saved_src_dir / "index.tsx")
    assert (frontend_src_dir / "index.tsx").read_text() == "replacement"


@pytest.mark.cli
def test_extension_json_content_is_correct(
    cli_runner, isolated_filesystem, cli_input_both
):
    """Test that the generated extension.json has the correct content."""
    result = cli_runner.invoke(app, ["init"], input=cli_input_both)
    assert result.exit_code == 0

    extension_path = isolated_filesystem / "test-extension"
    extension_json_path = extension_path / "extension.json"

    # Verify the JSON structure and values
    assert_json_content(
        extension_json_path,
        {
            "publisher": "test-org",
            "name": "test-extension",
            "displayName": "Test Extension",
            "version": "0.1.0",
            "license": "Apache-2.0",
            "permissions": [],
        },
    )

    # Load and verify more complex nested structures
    content = load_json_file(extension_json_path)

    # Verify frontend section is not present (contributions are code-first)
    assert "frontend" not in content

    # Verify no backend section in extension.json (moved to pyproject.toml)
    assert "backend" not in content


@pytest.mark.cli
def test_frontend_package_json_content_is_correct(
    cli_runner, isolated_filesystem, cli_input_both
):
    """Test that the generated frontend/package.json has the correct content."""
    result = cli_runner.invoke(app, ["init"], input=cli_input_both)
    assert result.exit_code == 0

    extension_path = isolated_filesystem / "test-extension"
    package_json_path = extension_path / "frontend" / "package.json"

    # Verify the package.json structure and values
    assert_json_content(
        package_json_path,
        {
            "name": "@test-org/test-extension",
            "version": "0.1.0",
            "license": "Apache-2.0",
        },
    )

    # Verify more complex structures
    content = load_json_file(package_json_path)
    assert "scripts" in content
    assert "build" in content["scripts"]
    assert "peerDependencies" in content
    assert "@apache-superset/core" in content["peerDependencies"]


@pytest.mark.cli
def test_backend_pyproject_toml_is_created(
    cli_runner, isolated_filesystem, cli_input_both
):
    """Test that the generated backend/pyproject.toml file is created."""
    result = cli_runner.invoke(app, ["init"], input=cli_input_both)
    assert result.exit_code == 0

    extension_path = isolated_filesystem / "test-extension"
    pyproject_path = extension_path / "backend" / "pyproject.toml"

    assert_file_exists(pyproject_path, "backend pyproject.toml")

    # Basic content verification (without parsing TOML for now)
    content = pyproject_path.read_text()
    assert (
        "test_org-test_extension" in content
    )  # Package name uses collision-safe naming
    assert "0.1.0" in content
    assert "Apache-2.0" in content


@pytest.mark.cli
def test_init_command_output_messages(cli_runner, isolated_filesystem, cli_input_both):
    """Test that init command produces expected output messages."""
    result = cli_runner.invoke(app, ["init"], input=cli_input_both)

    assert result.exit_code == 0
    output = result.output

    # Check for expected success messages
    assert "Created extension.json" in output
    assert "Created .gitignore" in output
    assert "Created frontend folder structure" in output
    assert "Created backend folder structure" in output
    assert (
        "Extension Test Extension (ID: test-org.test-extension) initialized" in output
    )


@pytest.mark.cli
def test_gitignore_content_is_correct(cli_runner, isolated_filesystem, cli_input_both):
    """Test that the generated .gitignore has the correct content."""
    result = cli_runner.invoke(app, ["init"], input=cli_input_both)
    assert result.exit_code == 0

    extension_path = isolated_filesystem / "test-extension"
    gitignore_path = extension_path / ".gitignore"

    assert_file_exists(gitignore_path, ".gitignore")

    content = gitignore_path.read_text()

    # Verify key patterns are present
    assert "node_modules/" in content
    assert "dist/" in content
    assert "*.supx" in content
    assert "__pycache__" in content
    assert ".venv/" in content
    assert ".DS_Store" in content
    assert ".env" in content


@pytest.mark.cli
def test_init_with_custom_version_and_license(cli_runner, isolated_filesystem):
    """Test init with custom version and license parameters."""
    cli_input = "My Extension\n\ntest-org\n2.1.0\nMIT\ny\nn\n"
    result = cli_runner.invoke(app, ["init"], input=cli_input)

    assert result.exit_code == 0

    extension_path = isolated_filesystem / "my-extension"
    extension_json_path = extension_path / "extension.json"

    assert_json_content(
        extension_json_path,
        {
            "publisher": "test-org",
            "name": "my-extension",
            "displayName": "My Extension",
            "version": "2.1.0",
            "license": "MIT",
        },
    )


@pytest.mark.integration
@pytest.mark.cli
def test_full_init_workflow_integration(cli_runner, isolated_filesystem):
    """Integration test for the complete init workflow."""
    # Test the complete flow with realistic user input
    cli_input = "Awesome Charts\n\nawesome-org\n1.0.0\nApache-2.0\ny\ny\n"
    result = cli_runner.invoke(app, ["init"], input=cli_input)

    # Verify success
    assert result.exit_code == 0

    # Verify complete directory structure
    extension_path = isolated_filesystem / "awesome-charts"
    expected_structure = create_test_extension_structure(
        isolated_filesystem,
        "awesome-charts",
        include_frontend=True,
        include_backend=True,
    )

    # Comprehensive structure verification
    assert_directory_structure(extension_path, expected_structure["expected_dirs"])
    assert_file_structure(extension_path, expected_structure["expected_files"])

    # Verify all generated files have correct content
    extension_json = load_json_file(extension_path / "extension.json")
    assert extension_json["publisher"] == "awesome-org"
    assert extension_json["name"] == "awesome-charts"
    assert extension_json["displayName"] == "Awesome Charts"
    assert extension_json["version"] == "1.0.0"
    assert extension_json["license"] == "Apache-2.0"

    package_json = load_json_file(extension_path / "frontend" / "package.json")
    assert package_json["name"] == "@awesome-org/awesome-charts"

    pyproject_content = (extension_path / "backend" / "pyproject.toml").read_text()
    assert (
        "awesome_org-awesome_charts" in pyproject_content
    )  # Package name uses collision-safe naming


# Non-interactive mode tests
@pytest.mark.cli
def test_init_non_interactive_with_all_options(cli_runner, isolated_filesystem):
    """Test that init works in non-interactive mode with all CLI options."""
    result = cli_runner.invoke(
        app,
        [
            "init",
            "--publisher",
            "my-org",
            "--name",
            "my-ext",
            "--display-name",
            "My Extension",
            "--version",
            "1.0.0",
            "--license",
            "MIT",
            "--frontend",
            "--backend",
        ],
    )

    assert result.exit_code == 0, f"Command failed with output: {result.output}"
    assert "🎉 Extension My Extension (ID: my-org.my-ext) initialized" in result.output

    extension_path = isolated_filesystem / "my-ext"
    assert_directory_exists(extension_path)
    assert_directory_exists(extension_path / "frontend")
    assert_directory_exists(extension_path / "backend")

    extension_json = load_json_file(extension_path / "extension.json")
    assert extension_json["publisher"] == "my-org"
    assert extension_json["name"] == "my-ext"
    assert extension_json["displayName"] == "My Extension"
    assert extension_json["version"] == "1.0.0"
    assert extension_json["license"] == "MIT"


@pytest.mark.cli
def test_init_frontend_only_with_cli_options(cli_runner, isolated_filesystem):
    """Test init with frontend only using CLI options."""
    result = cli_runner.invoke(
        app,
        [
            "init",
            "--publisher",
            "frontend-org",
            "--name",
            "frontend-ext",
            "--display-name",
            "Frontend Extension",
            "--version",
            "1.0.0",
            "--license",
            "MIT",
            "--frontend",
            "--no-backend",
        ],
    )

    assert result.exit_code == 0, f"Command failed with output: {result.output}"

    extension_path = isolated_filesystem / "frontend-ext"
    assert_directory_exists(extension_path / "frontend")
    assert not (extension_path / "backend").exists()


@pytest.mark.cli
def test_init_backend_only_with_cli_options(cli_runner, isolated_filesystem):
    """Test init with backend only using CLI options."""
    result = cli_runner.invoke(
        app,
        [
            "init",
            "--publisher",
            "backend-org",
            "--name",
            "backend-ext",
            "--display-name",
            "Backend Extension",
            "--version",
            "1.0.0",
            "--license",
            "MIT",
            "--no-frontend",
            "--backend",
        ],
    )

    assert result.exit_code == 0, f"Command failed with output: {result.output}"

    extension_path = isolated_filesystem / "backend-ext"
    assert not (extension_path / "frontend").exists()
    assert_directory_exists(extension_path / "backend")


@pytest.mark.cli
def test_init_prompts_for_missing_options(cli_runner, isolated_filesystem):
    """Test that init prompts for options not provided via CLI and uses defaults."""
    # Provide publisher, name, and display-name via CLI, but version/license will be prompted (accept defaults)
    result = cli_runner.invoke(
        app,
        [
            "init",
            "--publisher",
            "default-org",
            "--name",
            "default-ext",
            "--display-name",
            "Default Extension",
            "--frontend",
            "--backend",
        ],
        input="\n\n",  # Accept defaults for version and license prompts
    )

    assert result.exit_code == 0, f"Command failed with output: {result.output}"

    extension_path = isolated_filesystem / "default-ext"
    extension_json = load_json_file(extension_path / "extension.json")
    assert extension_json["version"] == "0.1.0"
    assert extension_json["license"] == "Apache-2.0"


@pytest.mark.cli
def test_init_non_interactive_validates_technical_name(cli_runner, isolated_filesystem):
    """Test that non-interactive mode validates technical name."""
    result = cli_runner.invoke(
        app,
        [
            "init",
            "--publisher",
            "test-org",
            "--name",
            "invalid_name",
            "--display-name",
            "Invalid Extension",
            "--frontend",
            "--backend",
        ],
    )

    assert result.exit_code == 1
    assert "must start with a letter" in result.output.lower()


@pytest.mark.cli
def test_init_non_interactive_validates_initial_version(
    cli_runner, isolated_filesystem
):
    """Test that init validates generated extension metadata before writing files."""
    result = cli_runner.invoke(
        app,
        [
            "init",
            "--publisher",
            "test-org",
            "--name",
            "test-extension",
            "--display-name",
            "Test Extension",
            "--version",
            "not-a-version",
            "--license",
            "Apache-2.0",
            "--frontend",
            "--backend",
        ],
    )

    assert result.exit_code == 1
    assert "invalid initial extension metadata" in result.output.lower()
    assert "version" in result.output.lower()
    assert not (isolated_filesystem / "test-extension").exists()

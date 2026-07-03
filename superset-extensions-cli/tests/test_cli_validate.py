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
from superset_extensions_cli.cli import app, validate_npm


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

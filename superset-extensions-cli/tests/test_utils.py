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
from superset_extensions_cli.utils import (
    read_json,
    read_toml,
    write_json,
    write_text_atomic,
    write_toml,
)


# Read JSON Tests
@pytest.mark.unit
def test_read_json_with_valid_file(isolated_filesystem):
    """Test read_json with valid JSON file."""
    json_data = {"name": "test", "version": "1.0.0"}
    json_file = isolated_filesystem / "test.json"
    json_file.write_text(json.dumps(json_data))

    result = read_json(json_file)

    assert result == json_data


@pytest.mark.unit
def test_read_json_with_nonexistent_file(isolated_filesystem):
    """Test read_json returns None when file doesn't exist."""
    nonexistent_file = isolated_filesystem / "nonexistent.json"

    result = read_json(nonexistent_file)

    assert result is None


@pytest.mark.unit
def test_read_json_with_invalid_json(isolated_filesystem):
    """Test read_json with invalid JSON content."""
    invalid_json_file = isolated_filesystem / "invalid.json"
    invalid_json_file.write_text("{ invalid json content")

    with pytest.raises(json.JSONDecodeError):
        read_json(invalid_json_file)


@pytest.mark.unit
def test_read_json_with_directory_instead_of_file(isolated_filesystem):
    """Test read_json returns None when path is a directory."""
    directory = isolated_filesystem / "test_dir"
    directory.mkdir()

    result = read_json(directory)

    assert result is None


@pytest.mark.unit
def test_read_json_with_symlinked_file(isolated_filesystem):
    """Test read_json returns None when path is a symlink."""
    outside_file = isolated_filesystem / "outside.json"
    outside_file.write_text('{"name": "outside"}')
    json_link = isolated_filesystem / "test.json"
    json_link.symlink_to(outside_file)

    result = read_json(json_link)

    assert result is None


@pytest.mark.unit
def test_read_json_with_symlinked_parent(isolated_filesystem):
    """Test read_json returns None when a parent directory is a symlink."""
    outside_dir = isolated_filesystem / "outside"
    outside_dir.mkdir()
    (outside_dir / "metadata.json").write_text('{"name": "outside"}')
    output_dir = isolated_filesystem / "output"
    output_dir.symlink_to(outside_dir)

    result = read_json(output_dir / "metadata.json")

    assert result is None


@pytest.mark.unit
def test_read_json_with_symlinked_ancestor(isolated_filesystem):
    """Test read_json returns None below a symlinked ancestor directory."""
    outside_dir = isolated_filesystem / "outside"
    outside_nested = outside_dir / "nested"
    outside_nested.mkdir(parents=True)
    (outside_nested / "metadata.json").write_text('{"name": "outside"}')
    output_dir = isolated_filesystem / "output"
    output_dir.symlink_to(outside_dir)

    result = read_json(output_dir / "nested" / "metadata.json")

    assert result is None


@pytest.mark.unit
def test_read_json_returns_none_when_path_becomes_symlink_during_read(
    isolated_filesystem, monkeypatch
):
    """Test read_json refuses content if the path becomes unsafe during read."""
    json_file = isolated_filesystem / "metadata.json"
    json_file.write_text('{"name": "original"}')
    outside_file = isolated_filesystem / "outside.json"
    outside_file.write_text('{"name": "outside"}')
    original_read_text = Path.read_text

    def replace_json_during_read(path, *args, **kwargs):
        if path == json_file:
            json_file.unlink()
            json_file.symlink_to(outside_file)
            return original_read_text(outside_file, *args, **kwargs)
        return original_read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", replace_json_during_read)

    result = read_json(json_file)

    assert result is None
    assert json_file.is_symlink()


@pytest.mark.unit
def test_read_json_returns_none_when_path_is_replaced_during_read(
    isolated_filesystem, monkeypatch
):
    """Test read_json refuses content if the file identity changes during read."""
    json_file = isolated_filesystem / "metadata.json"
    json_file.write_text('{"name": "original"}')
    replacement_file = isolated_filesystem / "replacement.json"
    replacement_file.write_text('{"name": "replacement"}')
    original_read_text = Path.read_text

    def replace_json_during_read(path, *args, **kwargs):
        if path == json_file:
            content = original_read_text(replacement_file, *args, **kwargs)
            json_file.unlink()
            json_file.write_text(content)
            return content
        return original_read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", replace_json_during_read)

    result = read_json(json_file)

    assert result is None
    assert not json_file.is_symlink()
    assert json.loads(original_read_text(json_file)) == {"name": "replacement"}


@pytest.mark.unit
@pytest.mark.parametrize(
    "json_content,expected",
    [
        ({"simple": "value"}, {"simple": "value"}),
        ({"nested": {"key": "value"}}, {"nested": {"key": "value"}}),
        ({"array": [1, 2, 3]}, {"array": [1, 2, 3]}),
        ({}, {}),  # Empty JSON object
    ],
)
def test_read_json_with_various_valid_content(
    isolated_filesystem, json_content, expected
):
    """Test read_json with various valid JSON content types."""
    json_file = isolated_filesystem / "test.json"
    json_file.write_text(json.dumps(json_content))

    result = read_json(json_file)

    assert result == expected


@pytest.mark.unit
def test_read_json_reports_read_errors(isolated_filesystem, monkeypatch):
    """Test read_json reports filesystem read failures with path context."""
    json_file = isolated_filesystem / "test.json"
    json_file.write_text("{}")
    original_read_text = Path.read_text

    def fail_json_read(path, *args, **kwargs):
        if path == json_file:
            raise OSError("permission denied")
        return original_read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", fail_json_read)

    with pytest.raises(OSError, match="Failed to read JSON file .*permission denied"):
        read_json(json_file)


# Read TOML Tests
@pytest.mark.unit
def test_read_toml_with_valid_file(isolated_filesystem):
    """Test read_toml with valid TOML file."""
    toml_content = '[project]\nname = "test"\nversion = "1.0.0"'
    toml_file = isolated_filesystem / "pyproject.toml"
    toml_file.write_text(toml_content)

    result = read_toml(toml_file)

    assert result is not None
    assert result["project"]["name"] == "test"
    assert result["project"]["version"] == "1.0.0"


@pytest.mark.unit
def test_read_toml_with_nonexistent_file(isolated_filesystem):
    """Test read_toml returns None when file doesn't exist."""
    nonexistent_file = isolated_filesystem / "nonexistent.toml"

    result = read_toml(nonexistent_file)

    assert result is None


@pytest.mark.unit
def test_read_toml_with_directory_instead_of_file(isolated_filesystem):
    """Test read_toml returns None when path is a directory."""
    directory = isolated_filesystem / "test_dir"
    directory.mkdir()

    result = read_toml(directory)

    assert result is None


@pytest.mark.unit
def test_read_toml_with_symlinked_file(isolated_filesystem):
    """Test read_toml returns None when path is a symlink."""
    outside_file = isolated_filesystem / "outside.toml"
    outside_file.write_text('[project]\nname = "outside"')
    toml_link = isolated_filesystem / "pyproject.toml"
    toml_link.symlink_to(outside_file)

    result = read_toml(toml_link)

    assert result is None


@pytest.mark.unit
def test_read_toml_with_symlinked_parent(isolated_filesystem):
    """Test read_toml returns None when a parent directory is a symlink."""
    outside_dir = isolated_filesystem / "outside"
    outside_dir.mkdir()
    (outside_dir / "pyproject.toml").write_text('[project]\nname = "outside"')
    output_dir = isolated_filesystem / "output"
    output_dir.symlink_to(outside_dir)

    result = read_toml(output_dir / "pyproject.toml")

    assert result is None


@pytest.mark.unit
def test_read_toml_with_symlinked_ancestor(isolated_filesystem):
    """Test read_toml returns None below a symlinked ancestor directory."""
    outside_dir = isolated_filesystem / "outside"
    outside_nested = outside_dir / "nested"
    outside_nested.mkdir(parents=True)
    (outside_nested / "pyproject.toml").write_text('[project]\nname = "outside"')
    output_dir = isolated_filesystem / "output"
    output_dir.symlink_to(outside_dir)

    result = read_toml(output_dir / "nested" / "pyproject.toml")

    assert result is None


@pytest.mark.unit
def test_read_toml_returns_none_when_path_becomes_symlink_during_read(
    isolated_filesystem, monkeypatch
):
    """Test read_toml refuses content if the path becomes unsafe during read."""
    toml_file = isolated_filesystem / "pyproject.toml"
    toml_file.write_text('[project]\nname = "original"')
    outside_file = isolated_filesystem / "outside.toml"
    outside_file.write_text('[project]\nname = "outside"')
    original_open = Path.open

    def replace_toml_during_read(path, *args, **kwargs):
        if path == toml_file:
            toml_file.unlink()
            toml_file.symlink_to(outside_file)
            return original_open(outside_file, *args, **kwargs)
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", replace_toml_during_read)

    result = read_toml(toml_file)

    assert result is None
    assert toml_file.is_symlink()


@pytest.mark.unit
def test_read_toml_returns_none_when_path_is_replaced_during_read(
    isolated_filesystem, monkeypatch
):
    """Test read_toml refuses content if the file identity changes during read."""
    toml_file = isolated_filesystem / "pyproject.toml"
    toml_file.write_text('[project]\nname = "original"')
    replacement_file = isolated_filesystem / "replacement.toml"
    replacement_file.write_text('[project]\nname = "replacement"')
    original_open = Path.open

    def replace_toml_during_read(path, *args, **kwargs):
        if path == toml_file:
            content = replacement_file.read_text()
            toml_file.unlink()
            with original_open(toml_file, "w", encoding="utf-8") as replacement:
                replacement.write(content)
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", replace_toml_during_read)

    result = read_toml(toml_file)

    assert result is None
    assert not toml_file.is_symlink()
    assert 'name = "replacement"' in toml_file.read_text()


@pytest.mark.unit
def test_read_toml_with_invalid_toml(isolated_filesystem):
    """Test read_toml with invalid TOML content."""
    invalid_toml_file = isolated_filesystem / "invalid.toml"
    invalid_toml_file.write_text("[ invalid toml content")

    with pytest.raises(Exception):  # tomli raises various exceptions for invalid TOML
        read_toml(invalid_toml_file)


@pytest.mark.unit
def test_read_toml_reports_read_errors(isolated_filesystem, monkeypatch):
    """Test read_toml reports filesystem read failures with path context."""
    toml_file = isolated_filesystem / "pyproject.toml"
    toml_file.write_text("[project]\nname = 'test'\n")
    original_open = Path.open

    def fail_toml_open(path, *args, **kwargs):
        if path == toml_file:
            raise OSError("permission denied")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", fail_toml_open)

    with pytest.raises(OSError, match="Failed to read TOML file .*permission denied"):
        read_toml(toml_file)


@pytest.mark.unit
@pytest.mark.parametrize(
    "toml_content,expected_keys",
    [
        ('[project]\nname = "test"', ["project"]),
        ('[build-system]\nrequires = ["setuptools"]', ["build-system"]),
        (
            '[project]\nname = "test"\n[build-system]\nrequires = ["setuptools"]',
            ["project", "build-system"],
        ),
    ],
)
def test_read_toml_with_various_valid_content(
    isolated_filesystem, toml_content, expected_keys
):
    """Test read_toml with various valid TOML content types."""
    toml_file = isolated_filesystem / "test.toml"
    toml_file.write_text(toml_content)

    result = read_toml(toml_file)

    assert result is not None
    for key in expected_keys:
        assert key in result


@pytest.mark.unit
def test_read_toml_with_complex_structure(isolated_filesystem):
    """Test read_toml with complex TOML structure."""
    complex_toml = """
[project]
name = "my-package"
version = "1.0.0"
authors = [
    {name = "Author Name", email = "author@example.com"}
]

[project.dependencies]
requests = "^2.25.0"

[build-system]
requires = ["setuptools", "wheel"]
build-backend = "setuptools.build_meta"
"""
    toml_file = isolated_filesystem / "complex.toml"
    toml_file.write_text(complex_toml)

    result = read_toml(toml_file)

    assert result is not None
    assert result["project"]["name"] == "my-package"
    assert result["project"]["version"] == "1.0.0"
    assert len(result["project"]["authors"]) == 1
    assert result["project"]["authors"][0]["name"] == "Author Name"
    assert result["build-system"]["requires"] == ["setuptools", "wheel"]


@pytest.mark.unit
def test_read_toml_with_empty_file(isolated_filesystem):
    """Test read_toml with empty TOML file."""
    toml_file = isolated_filesystem / "empty.toml"
    toml_file.write_text("")

    result = read_toml(toml_file)

    assert result == {}


@pytest.mark.unit
@pytest.mark.parametrize(
    "invalid_content",
    [
        "[ invalid section",
        "key = ",
        "key = unquoted string",
        "[section\nkey = value",
    ],
)
def test_read_toml_with_various_invalid_content(isolated_filesystem, invalid_content):
    """Test read_toml with various types of invalid TOML content."""
    toml_file = isolated_filesystem / "invalid.toml"
    toml_file.write_text(invalid_content)

    with pytest.raises(Exception):  # Various TOML parsing exceptions
        read_toml(toml_file)


# File System Edge Cases
@pytest.mark.unit
def test_read_json_with_permission_denied(isolated_filesystem):
    """Test read_json behavior when file permissions are denied."""
    json_file = isolated_filesystem / "restricted.json"
    json_file.write_text('{"test": "value"}')

    # This test may not work on all systems, so we'll skip it if chmod doesn't work
    try:
        json_file.chmod(0o000)  # No permissions
        result = read_json(json_file)
        # If we get here without exception, the file was still readable
        # This is system-dependent behavior
        assert result is None or result == {"test": "value"}
    except (OSError, PermissionError):
        # Expected on some systems
        pass
    finally:
        # Restore permissions for cleanup
        try:
            json_file.chmod(0o644)
        except (OSError, PermissionError):
            pass


@pytest.mark.unit
def test_read_toml_with_permission_denied(isolated_filesystem):
    """Test read_toml behavior when file permissions are denied."""
    toml_file = isolated_filesystem / "restricted.toml"
    toml_file.write_text('[test]\nkey = "value"')

    # This test may not work on all systems, so we'll skip it if chmod doesn't work
    try:
        toml_file.chmod(0o000)  # No permissions
        result = read_toml(toml_file)
        # If we get here without exception, the file was still readable
        # This is system-dependent behavior
        assert result is None or "test" in result
    except (OSError, PermissionError):
        # Expected on some systems
        pass
    finally:
        # Restore permissions for cleanup
        try:
            toml_file.chmod(0o644)
        except (OSError, PermissionError):
            pass


# Atomic Write Tests
@pytest.mark.unit
def test_write_text_atomic_round_trip(isolated_filesystem):
    """Test atomic text writes replace file contents."""
    output_path = isolated_filesystem / "output.txt"
    output_path.write_text("old")

    write_text_atomic(output_path, "new")

    assert output_path.read_text() == "new"
    assert list(isolated_filesystem.glob(".output.txt.*.tmp")) == []


@pytest.mark.unit
def test_write_text_atomic_rejects_symlinked_output(isolated_filesystem):
    """Test atomic text writes refuse symlinked output paths."""
    outside_file = isolated_filesystem / "outside.txt"
    outside_file.write_text("original")
    output_path = isolated_filesystem / "output.txt"
    output_path.symlink_to(outside_file)

    with pytest.raises(OSError, match="Refusing to write through symlink"):
        write_text_atomic(output_path, "updated")

    assert outside_file.read_text() == "original"


@pytest.mark.unit
def test_write_text_atomic_rejects_symlinked_parent(isolated_filesystem):
    """Test atomic text writes refuse symlinked parent directories."""
    outside_dir = isolated_filesystem / "outside"
    outside_dir.mkdir()
    output_dir = isolated_filesystem / "output"
    output_dir.symlink_to(outside_dir)

    with pytest.raises(OSError, match="Refusing to write through symlinked directory"):
        write_text_atomic(output_dir / "metadata.txt", "updated")

    assert not (outside_dir / "metadata.txt").exists()


# Write JSON Tests
@pytest.mark.unit
def test_write_json_round_trip(isolated_filesystem):
    """Test write_json then read_json round-trip preserves content."""
    data = {"name": "test-extension", "version": "2.0.0", "nested": {"key": "value"}}
    json_file = isolated_filesystem / "output.json"

    write_json(json_file, data)
    result = read_json(json_file)

    assert result == data


@pytest.mark.unit
def test_write_json_rejects_symlinked_output(isolated_filesystem):
    """Test write_json refuses to write through a symlink."""
    outside_file = isolated_filesystem / "outside.json"
    outside_file.write_text('{"name": "original"}')
    json_link = isolated_filesystem / "output.json"
    json_link.symlink_to(outside_file)

    with pytest.raises(OSError, match="Refusing to write through symlink"):
        write_json(json_link, {"name": "updated"})

    assert outside_file.read_text() == '{"name": "original"}'


@pytest.mark.unit
def test_write_json_rejects_symlinked_parent(isolated_filesystem):
    """Test write_json refuses to write through a symlinked parent directory."""
    outside_dir = isolated_filesystem / "outside"
    outside_dir.mkdir()
    output_dir = isolated_filesystem / "output"
    output_dir.symlink_to(outside_dir)

    with pytest.raises(OSError, match="Refusing to write through symlinked directory"):
        write_json(output_dir / "metadata.json", {"name": "updated"})

    assert not (outside_dir / "metadata.json").exists()


@pytest.mark.unit
def test_write_json_rejects_symlinked_ancestor(isolated_filesystem):
    """Test write_json refuses to write below a symlinked ancestor directory."""
    outside_dir = isolated_filesystem / "outside"
    outside_nested = outside_dir / "nested"
    outside_nested.mkdir(parents=True)
    output_dir = isolated_filesystem / "output"
    output_dir.symlink_to(outside_dir)

    with pytest.raises(OSError, match="Refusing to write through symlinked directory"):
        write_json(output_dir / "nested" / "metadata.json", {"name": "updated"})

    assert not (outside_nested / "metadata.json").exists()


@pytest.mark.unit
def test_write_json_rejects_directory_output(isolated_filesystem):
    """Test write_json refuses output paths that are directories."""
    output_dir = isolated_filesystem / "metadata.json"
    output_dir.mkdir()

    with pytest.raises(OSError, match="Refusing to write non-file path"):
        write_json(output_dir, {"name": "updated"})


@pytest.mark.unit
def test_write_json_rejects_non_directory_parent(isolated_filesystem):
    """Test write_json refuses output paths below a file parent."""
    output_parent = isolated_filesystem / "output"
    output_parent.write_text("not a directory")

    with pytest.raises(OSError, match="Refusing to write through non-directory parent"):
        write_json(output_parent / "metadata.json", {"name": "updated"})

    assert output_parent.read_text() == "not a directory"


@pytest.mark.unit
def test_write_json_rejects_non_directory_ancestor(isolated_filesystem):
    """Test write_json refuses nested output paths below a file ancestor."""
    output_parent = isolated_filesystem / "output"
    output_parent.write_text("not a directory")

    with pytest.raises(OSError, match="Refusing to write through non-directory parent"):
        write_json(output_parent / "nested" / "metadata.json", {"name": "updated"})

    assert output_parent.read_text() == "not a directory"


@pytest.mark.unit
def test_write_json_reports_write_errors(isolated_filesystem, monkeypatch):
    """Test write_json reports filesystem write failures with path context."""
    output_path = isolated_filesystem / "output.json"
    output_path.write_text('{"name": "original"}')
    original_replace = Path.replace

    def fail_json_replace(path, target):
        if target == output_path:
            raise OSError("disk full")
        return original_replace(path, target)

    monkeypatch.setattr(Path, "replace", fail_json_replace)

    with pytest.raises(OSError, match="Failed to write JSON file .*disk full"):
        write_json(output_path, {"name": "updated"})

    assert output_path.read_text() == '{"name": "original"}'
    assert list(isolated_filesystem.glob(".output.json.*.tmp")) == []


# Write TOML Tests
@pytest.mark.unit
def test_write_toml_round_trip(isolated_filesystem):
    """Test write_toml then read_toml round-trip preserves content."""
    data = {
        "project": {"name": "test-package", "version": "1.0.0"},
        "tool": {"apache_superset_extensions": {"build": {"include": ["src/**/*.py"]}}},
    }
    toml_file = isolated_filesystem / "output.toml"

    write_toml(toml_file, data)
    result = read_toml(toml_file)

    assert result == data


@pytest.mark.unit
def test_write_toml_rejects_symlinked_output(isolated_filesystem):
    """Test write_toml refuses to write through a symlink."""
    outside_file = isolated_filesystem / "outside.toml"
    outside_file.write_text('[project]\nname = "original"\n')
    toml_link = isolated_filesystem / "output.toml"
    toml_link.symlink_to(outside_file)

    with pytest.raises(OSError, match="Refusing to write through symlink"):
        write_toml(toml_link, {"project": {"name": "updated"}})

    assert outside_file.read_text() == '[project]\nname = "original"\n'


@pytest.mark.unit
def test_write_toml_rejects_symlinked_parent(isolated_filesystem):
    """Test write_toml refuses to write through a symlinked parent directory."""
    outside_dir = isolated_filesystem / "outside"
    outside_dir.mkdir()
    output_dir = isolated_filesystem / "output"
    output_dir.symlink_to(outside_dir)

    with pytest.raises(OSError, match="Refusing to write through symlinked directory"):
        write_toml(output_dir / "pyproject.toml", {"project": {"name": "updated"}})

    assert not (outside_dir / "pyproject.toml").exists()


@pytest.mark.unit
def test_write_toml_rejects_symlinked_ancestor(isolated_filesystem):
    """Test write_toml refuses to write below a symlinked ancestor directory."""
    outside_dir = isolated_filesystem / "outside"
    outside_nested = outside_dir / "nested"
    outside_nested.mkdir(parents=True)
    output_dir = isolated_filesystem / "output"
    output_dir.symlink_to(outside_dir)

    with pytest.raises(OSError, match="Refusing to write through symlinked directory"):
        write_toml(
            output_dir / "nested" / "pyproject.toml",
            {"project": {"name": "x"}},
        )

    assert not (outside_nested / "pyproject.toml").exists()


@pytest.mark.unit
def test_write_toml_rejects_directory_output(isolated_filesystem):
    """Test write_toml refuses output paths that are directories."""
    output_dir = isolated_filesystem / "pyproject.toml"
    output_dir.mkdir()

    with pytest.raises(OSError, match="Refusing to write non-file path"):
        write_toml(output_dir, {"project": {"name": "updated"}})


@pytest.mark.unit
def test_write_toml_rejects_non_directory_parent(isolated_filesystem):
    """Test write_toml refuses output paths below a file parent."""
    output_parent = isolated_filesystem / "output"
    output_parent.write_text("not a directory")

    with pytest.raises(OSError, match="Refusing to write through non-directory parent"):
        write_toml(output_parent / "pyproject.toml", {"project": {"name": "updated"}})

    assert output_parent.read_text() == "not a directory"


@pytest.mark.unit
def test_write_toml_reports_write_errors(isolated_filesystem, monkeypatch):
    """Test write_toml reports filesystem write failures with path context."""
    output_path = isolated_filesystem / "pyproject.toml"
    output_path.write_text('[project]\nname = "original"\n')
    original_replace = Path.replace

    def fail_toml_replace(path, target):
        if target == output_path:
            raise OSError("disk full")
        return original_replace(path, target)

    monkeypatch.setattr(Path, "replace", fail_toml_replace)

    with pytest.raises(OSError, match="Failed to write TOML file .*disk full"):
        write_toml(output_path, {"project": {"name": "updated"}})

    assert output_path.read_text() == '[project]\nname = "original"\n'
    assert list(isolated_filesystem.glob(".pyproject.toml.*.tmp")) == []


@pytest.mark.unit
def test_write_toml_rejects_non_directory_ancestor(isolated_filesystem):
    """Test write_toml refuses nested output paths below a file ancestor."""
    output_parent = isolated_filesystem / "output"
    output_parent.write_text("not a directory")

    with pytest.raises(OSError, match="Refusing to write through non-directory parent"):
        write_toml(
            output_parent / "nested" / "pyproject.toml",
            {"project": {"name": "updated"}},
        )

    assert output_parent.read_text() == "not a directory"

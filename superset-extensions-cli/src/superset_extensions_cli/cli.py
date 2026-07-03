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

import filecmp
import re
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from dataclasses import dataclass
from pathlib import Path, PureWindowsPath
from typing import Any, Callable

import click
import semver
from jinja2 import Environment, FileSystemLoader
from superset_core.extensions.types import (
    ExtensionConfig,
    Manifest,
    ManifestBackend,
    ManifestFrontend,
)
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from superset_extensions_cli.constants import MIN_NPM_VERSION
from superset_extensions_cli.exceptions import ExtensionNameError
from superset_extensions_cli.types import ExtensionNames
from superset_extensions_cli.utils import (
    generate_extension_names,
    get_module_federation_name,
    get_read_path_identity,
    kebab_to_snake_case,
    read_json,
    read_toml,
    suggest_technical_name,
    validate_display_name,
    validate_publisher,
    validate_technical_name,
    write_json,
    write_text_atomic,
    write_toml,
)

REMOTE_ENTRY_REGEX = re.compile(r"^remoteEntry\..+\.js$")
CLI_TEMPORARY_DIST_DIRECTORY_PREFIXES = (
    ".backend.",
    ".backend-backup.",
    ".frontend.",
    ".frontend-backup.",
)


@dataclass(frozen=True)
class ValidatedNpmExecutable:
    """Npm executable path and identity validated before command launch."""

    path: str
    identity: tuple[int, int, int, int]


def split_path_parts(path: str) -> list[str]:
    """Split path components regardless of platform path separators."""
    return [part for part in re.split(r"[\\/]+", path) if part]


def validate_backend_build_pattern(pattern: str, pattern_type: str) -> None:
    """Require backend build globs to stay relative to the backend directory."""
    windows_pattern = PureWindowsPath(pattern)
    if (
        Path(pattern).is_absolute()
        or bool(windows_pattern.drive)
        or bool(windows_pattern.root)
        or ".." in split_path_parts(pattern)
    ):
        raise click.ClickException(
            f"Invalid {pattern_type} pattern {pattern!r}: patterns must be "
            "relative to the backend directory and may not contain '..'."
        )


def is_cli_temporary_dist_artifact(relative_path: Path) -> bool:
    """Return whether a dist-relative path belongs to CLI temporary state."""
    if not relative_path.parts:
        return False

    root_name = relative_path.parts[0]
    if root_name.startswith(
        CLI_TEMPORARY_DIST_DIRECTORY_PREFIXES
    ) and root_name.endswith(".tmp"):
        return True

    file_name = relative_path.name
    return file_name.startswith(".") and file_name.endswith(".tmp")


def validate_npm() -> ValidatedNpmExecutable:
    """Return the resolved npm executable path after validating it."""
    npm_path = shutil.which("npm")
    if npm_path is None:
        click.secho(
            "❌ npm is not installed or not on your PATH.",
            err=True,
            fg="red",
        )
        sys.exit(1)
    npm_command = str(Path(npm_path).resolve())
    npm_identity = get_output_copy_source_identity(Path(npm_command))
    if npm_identity is None:
        click.secho(
            f"❌ npm executable path is unsafe: {npm_command}",
            err=True,
            fg="red",
        )
        sys.exit(1)

    try:
        result = subprocess.run(  # noqa: S603
            [npm_command, "-v"],  # noqa: S607
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if result.returncode != 0:
            click.secho(
                f"❌ Failed to run `npm -v`: {result.stderr.strip()}",
                err=True,
                fg="red",
            )
            sys.exit(1)

        npm_version = result.stdout.strip()
        try:
            parsed_npm_version = semver.Version.parse(npm_version)
        except ValueError:
            click.secho(
                f"❌ Failed to parse npm version from `npm -v`: {npm_version!r}",
                err=True,
                fg="red",
            )
            sys.exit(1)

        if parsed_npm_version.compare(MIN_NPM_VERSION) < 0:
            click.secho(
                f"❌ npm version {npm_version} is lower than the required {MIN_NPM_VERSION}.",  # noqa: E501
                err=True,
                fg="red",
            )
            sys.exit(1)
        if get_output_copy_source_identity(Path(npm_command)) != npm_identity:
            click.secho(
                "❌ npm executable changed during validation.",
                err=True,
                fg="red",
            )
            sys.exit(1)
        return ValidatedNpmExecutable(npm_command, npm_identity)

    except OSError as ex:
        click.secho(
            f"❌ Failed to run `npm -v`: {ex}",
            err=True,
            fg="red",
        )
        sys.exit(1)


def get_npm_executable_path(npm_executable: Any) -> str:
    """Return a launchable npm path after checking validated identity."""
    if isinstance(npm_executable, ValidatedNpmExecutable):
        if (
            get_output_copy_source_identity(Path(npm_executable.path))
            != npm_executable.identity
        ):
            raise click.ClickException("npm executable changed before launch.")
        return npm_executable.path
    if isinstance(npm_executable, str):
        return npm_executable
    return "npm"


def validate_node_modules_path(node_modules: Path) -> None:
    """Validate frontend/node_modules before dependency install decisions."""
    if node_modules.is_symlink():
        raise click.ClickException("frontend/node_modules path is a symlink.")
    if node_modules.exists() and not node_modules.is_dir():
        raise click.ClickException(
            "frontend/node_modules path exists but is not a directory."
        )


def init_frontend_deps(frontend_dir: Path) -> None:
    """
    If node_modules is missing under `frontend_dir`, run `npm ci` if package-lock.json
    exists, otherwise run `npm i`.
    """
    require_optional_directory(frontend_dir, "frontend")
    frontend_identity = get_directory_path_identity(frontend_dir)
    if frontend_identity is None:
        raise click.ClickException("frontend path is no longer safe.")
    node_modules = frontend_dir / "node_modules"
    validate_node_modules_path(node_modules)

    if not node_modules.exists():
        package_lock = frontend_dir / "package-lock.json"
        if optional_file_exists(package_lock, "frontend/package-lock.json"):
            click.secho("⚙️  node_modules not found, running `npm ci`…", fg="cyan")
            npm_command = ["npm", "ci"]
            error_msg = "❌ `npm ci` failed. Aborting."
        else:
            click.secho("⚙️  node_modules not found, running `npm i`…", fg="cyan")
            npm_command = ["npm", "i"]
            error_msg = "❌ `npm i` failed. Aborting."

        npm_executable = validate_npm()
        validate_node_modules_path(node_modules)
        current_frontend_identity = get_directory_path_identity(frontend_dir)
        if current_frontend_identity != frontend_identity:
            raise click.ClickException(
                "frontend path changed before dependency install."
            )
        npm_command = [get_npm_executable_path(npm_executable), *npm_command[1:]]
        try:
            res = subprocess.run(  # noqa: S603
                npm_command,  # noqa: S607
                cwd=frontend_dir,
                text=True,
            )
        except OSError as ex:
            click.secho(f"{error_msg} {ex}", err=True, fg="red")
            sys.exit(1)
        if res.returncode != 0:
            click.secho(error_msg, err=True, fg="red")
            sys.exit(1)
        click.secho("✅ Dependencies installed", fg="green")


def clean_dist(cwd: Path) -> None:
    dist_dir = cwd / "dist"
    remove_output_directory(dist_dir, "dist directory")
    ensure_output_directory(dist_dir, "dist directory")


def start_dist_replacement(
    cwd: Path,
) -> tuple[
    Path | None,
    Path | None,
    tuple[int, int, int, int] | None,
    tuple[int, int, int, int] | None,
    tuple[int, int, int, int],
]:
    """Move existing dist aside before a full build writes replacement output."""
    dist_dir = cwd / "dist"
    if not dist_dir.exists():
        ensure_output_directory(dist_dir, "dist directory")
        replacement_identity = get_directory_path_identity(dist_dir)
        if replacement_identity is None:
            raise click.ClickException("Refusing to build dist directory: unsafe path.")
        return None, None, None, None, replacement_identity

    validate_output_directory(dist_dir, "dist directory")
    dist_identity = get_directory_path_identity(dist_dir)
    if dist_identity is None:
        raise click.ClickException("Refusing to back up dist directory: unsafe path.")
    backup_root = create_temporary_output_directory(
        cwd,
        ".dist-backup.",
        "temporary dist backup directory",
    )
    backup_path = backup_root / "dist"
    backup_root_identity = get_directory_path_identity(backup_root)
    if backup_root_identity is None:
        raise click.ClickException(
            "Refusing to back up dist directory: backup root path is unsafe."
        )
    if get_directory_path_identity(dist_dir) != dist_identity:
        try:
            remove_output_directory(
                backup_root,
                "temporary dist backup directory",
                backup_root_identity,
            )
        except click.ClickException:
            pass
        raise click.ClickException("Failed to back up dist directory: path changed.")
    try:
        dist_dir.replace(backup_path)
    except OSError as ex:
        try:
            remove_output_directory(
                backup_root,
                "temporary dist backup directory",
                backup_root_identity,
            )
        except click.ClickException:
            pass
        raise click.ClickException(f"Failed to back up dist directory: {ex}") from ex

    backup_identity = get_directory_path_identity(backup_path)
    if backup_identity != dist_identity:
        try:
            remove_output_directory(
                backup_root,
                "temporary dist backup directory",
                backup_root_identity,
            )
        except click.ClickException:
            pass
        raise click.ClickException("Failed to back up dist directory: path changed.")

    try:
        ensure_output_directory(dist_dir, "dist directory")
    except click.ClickException as ex:
        try:
            if get_directory_path_identity(backup_path) != backup_identity:
                raise OSError("backup path changed")
            backup_path.replace(dist_dir)
            if get_directory_path_identity(dist_dir) != backup_identity:
                raise OSError("restored backup path changed")
        except OSError as restore_ex:
            raise click.ClickException(
                f"{ex.message}; also failed to restore previous dist directory: "
                f"{restore_ex}"
            ) from ex
        try:
            remove_output_directory(
                backup_root,
                "temporary dist backup directory",
                backup_root_identity,
            )
        except click.ClickException:
            pass
        raise
    replacement_identity = get_directory_path_identity(dist_dir)
    if replacement_identity is None:
        raise click.ClickException("Refusing to build dist directory: unsafe path.")
    return (
        backup_root,
        backup_path,
        backup_identity,
        backup_root_identity,
        replacement_identity,
    )


def rollback_dist_replacement(
    cwd: Path,
    backup_root: Path | None,
    backup_path: Path | None,
    backup_identity: tuple[int, int, int, int] | None,
    backup_root_identity: tuple[int, int, int, int] | None,
    replacement_identity: tuple[int, int, int, int],
) -> None:
    """Restore the previous dist directory after a failed full build."""
    dist_dir = cwd / "dist"
    try:
        ensure_directory_identity_unchanged(
            dist_dir,
            "dist directory",
            replacement_identity,
            "rollback cleanup",
        )
        remove_output_directory(dist_dir, "dist directory", replacement_identity)
    except click.ClickException as ex:
        raise click.ClickException(
            f"Failed to clean failed dist directory before restore: {ex.message}"
        ) from ex

    if backup_root is None or backup_path is None or backup_identity is None:
        return

    try:
        if get_directory_path_identity(backup_path) != backup_identity:
            raise OSError("backup path changed")
        backup_path.replace(dist_dir)
        if get_directory_path_identity(dist_dir) != backup_identity:
            raise OSError("restored backup path changed")
    except OSError as ex:
        raise click.ClickException(
            f"Failed to restore previous dist directory: {ex}"
        ) from ex
    try:
        remove_output_directory(
            backup_root,
            "temporary dist backup directory",
            backup_root_identity,
        )
    except click.ClickException:
        pass


def cleanup_dist_replacement_backup(
    backup_root: Path | None,
    backup_root_identity: tuple[int, int, int, int] | None,
) -> None:
    """Remove a full-build dist backup after a successful publish."""
    if backup_root is None:
        return
    try:
        remove_output_directory(
            backup_root,
            "temporary dist backup directory",
            backup_root_identity,
        )
    except click.ClickException:
        pass


def ensure_output_directory(path: Path, label: str) -> None:
    """Create an output directory after validating the path is safe to write."""
    validate_output_directory(path, label)
    anchor = get_existing_output_directory_anchor(path)
    anchor_identity = get_directory_path_identity(anchor)
    if anchor_identity is None:
        raise click.ClickException(
            f"Refusing to create {label}: parent path is unsafe."
        )

    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError as ex:
        raise click.ClickException(f"Failed to create {label}: {ex}") from ex
    current_anchor_identity = get_directory_path_identity(anchor)
    if (
        current_anchor_identity is None
        or current_anchor_identity[:2] != anchor_identity[:2]
    ):
        raise click.ClickException(f"Refusing to create {label}: parent path changed.")
    validate_output_directory(path, label)


def validate_output_directory(path: Path, label: str) -> None:
    """Validate that an output directory path is safe to write."""
    if path.is_symlink():
        raise click.ClickException(f"Refusing to write {label}: path is a symlink.")
    if path.exists() and not path.is_dir():
        raise click.ClickException(
            f"Refusing to write {label}: path exists but is not a directory."
        )

    if (symlinked_parent := find_symlinked_parent(path)) is not None:
        raise click.ClickException(
            f"Refusing to write {label}: parent directory is a symlink: "
            f"{symlinked_parent}."
        )

    invalid_parent = next(
        (parent for parent in path.parents if parent.exists() and not parent.is_dir()),
        None,
    )
    if invalid_parent is not None:
        raise click.ClickException(
            f"Refusing to write {label}: parent exists but is not a directory: "
            f"{invalid_parent}."
        )


def get_existing_output_directory_anchor(path: Path) -> Path:
    """Return the nearest existing directory boundary for output creation."""
    return next(parent for parent in (path, *path.parents) if parent.exists())


def validate_output_file_parent(path: Path, root: Path, label: str) -> None:
    """Validate an output file parent without creating missing directories."""
    if not path.is_relative_to(root):
        raise click.ClickException(
            f"Refusing to write {label}: path is outside {root}."
        )
    symlinked_root = next(
        (parent for parent in (root, *root.parents) if parent.is_symlink()),
        None,
    )
    if symlinked_root is not None:
        raise click.ClickException(
            f"Refusing to write {label}: parent directory is a symlink: "
            f"{symlinked_root}."
        )
    invalid_root_parent = next(
        (
            parent
            for parent in (root, *root.parents)
            if parent.exists() and not parent.is_dir()
        ),
        None,
    )
    if invalid_root_parent is not None:
        raise click.ClickException(
            f"Refusing to write {label}: parent exists but is not a directory: "
            f"{invalid_root_parent}."
        )
    if path.is_symlink():
        raise click.ClickException(f"Refusing to write {label}: path is a symlink.")
    if path.exists() and not path.is_file():
        raise click.ClickException(
            f"Refusing to write {label}: path exists but is not a file."
        )

    parent = path.parent
    current = parent
    while current != root:
        if current.is_symlink():
            raise click.ClickException(
                f"Refusing to write {label}: parent directory is a symlink: {current}."
            )
        if current.exists() and not current.is_dir():
            raise click.ClickException(
                f"Refusing to write {label}: parent exists but is not a directory: "
                f"{current}."
            )
        current = current.parent


def ensure_output_file_parent(path: Path, root: Path, label: str) -> None:
    """Create an output file parent after validating existing ancestors."""
    validate_output_file_parent(path, root, label)
    anchor = get_existing_output_directory_anchor(root)
    anchor_identity = get_directory_path_identity(anchor)
    if anchor_identity is None:
        raise click.ClickException(
            f"Refusing to create parent for {label}: parent path is unsafe."
        )
    parent = path.parent
    try:
        parent.mkdir(parents=True, exist_ok=True)
    except OSError as ex:
        raise click.ClickException(f"Failed to create parent for {label}: {ex}") from ex
    current_anchor_identity = get_directory_path_identity(anchor)
    if (
        current_anchor_identity is None
        or current_anchor_identity[:2] != anchor_identity[:2]
    ):
        raise click.ClickException(
            f"Refusing to create parent for {label}: parent path changed."
        )
    validate_output_file_parent(path, root, label)


def copy_output_file(source: Path, target: Path, label: str) -> None:
    """Copy a validated output file while preserving command-level error context."""
    source_identity = get_output_copy_source_identity(source)
    if source_identity is None:
        raise click.ClickException(f"Refusing to copy {label}: source path is unsafe.")
    validate_output_file(target, label)
    target_parent_identity = get_directory_path_identity(target.parent)
    if target_parent_identity is None:
        raise click.ClickException(
            f"Refusing to copy {label}: target parent path is unsafe."
        )
    try:
        current_parent_identity = get_directory_path_identity(target.parent)
        if (
            current_parent_identity is None
            or current_parent_identity[:2] != target_parent_identity[:2]
        ):
            raise click.ClickException(
                f"Refusing to copy {label}: target parent path changed."
            )
        shutil.copy2(source, target)
    except (OSError, shutil.Error) as ex:
        raise click.ClickException(f"Failed to copy {label}: {ex}") from ex
    current_parent_identity = get_directory_path_identity(target.parent)
    if (
        current_parent_identity is None
        or current_parent_identity[:2] != target_parent_identity[:2]
    ):
        raise click.ClickException(
            f"Refusing to copy {label}: target parent path changed during copy."
        )
    if get_output_copy_source_identity(source) != source_identity:
        raise click.ClickException(
            f"Refusing to copy {label}: source path changed during copy."
        )
    target_identity = get_read_path_identity(target)
    if target_identity is None:
        raise click.ClickException(
            f"Refusing to copy {label}: target path changed during copy."
        )
    try:
        target_matches_source = filecmp.cmp(source, target, shallow=False)
    except OSError as ex:
        raise click.ClickException(f"Failed to verify copied {label}: {ex}") from ex
    if not target_matches_source:
        raise click.ClickException(
            f"Refusing to copy {label}: target content changed during copy."
        )
    if get_output_copy_source_identity(source) != source_identity:
        raise click.ClickException(
            f"Refusing to copy {label}: source path changed during copy."
        )
    if get_read_path_identity(target) != target_identity:
        raise click.ClickException(
            f"Refusing to copy {label}: target path changed during copy."
        )


def get_output_copy_source_identity(
    source: Path,
) -> tuple[int, int, int, int] | None:
    """Return source identity for output copy, following file symlinks."""
    if not source.is_file():
        return None
    try:
        stat = source.stat()
    except OSError:
        return None
    return (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns)


def get_copy_source_identity(
    source: Path, root: Path
) -> tuple[int, int, int, int] | None:
    """Return source file identity after confirming it resolves inside root."""
    try:
        resolved = source.resolve()
    except OSError:
        return None
    if not resolved.is_relative_to(root):
        return None
    if not source.is_file():
        return None
    try:
        stat = source.stat()
    except OSError:
        return None
    return (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns)


def ensure_copy_source_unchanged(
    source: Path,
    root: Path,
    identity: tuple[int, int, int, int],
    label: str,
) -> None:
    """Fail if a source file changes after copy target planning."""
    if get_copy_source_identity(source, root) != identity:
        raise click.ClickException(
            f"Refusing to copy {label}: source path changed before copy."
        )


def validate_output_file(path: Path, label: str) -> None:
    """Validate that an output file path is safe to write."""
    if path.is_symlink():
        raise click.ClickException(f"Refusing to write {label}: path is a symlink.")
    if path.exists() and not path.is_file():
        raise click.ClickException(
            f"Refusing to write {label}: path exists but is not a file."
        )
    symlinked_parent = next(
        (
            parent
            for parent in (path.parent, *path.parent.parents)
            if parent.is_symlink()
        ),
        None,
    )
    if symlinked_parent is not None:
        raise click.ClickException(
            f"Refusing to write {label}: parent directory is a symlink: "
            f"{symlinked_parent}."
        )
    invalid_parent = next(
        (
            parent
            for parent in (path.parent, *path.parent.parents)
            if parent.exists() and not parent.is_dir()
        ),
        None,
    )
    if invalid_parent is not None:
        raise click.ClickException(
            f"Refusing to write {label}: parent exists but is not a directory: "
            f"{invalid_parent}."
        )


def clean_dist_frontend(cwd: Path) -> None:
    frontend_dist = cwd / "dist" / "frontend"
    remove_output_directory(frontend_dist, "dist/frontend directory")


def remove_output_directory(
    path: Path,
    label: str,
    expected_identity: tuple[int, int, int, int] | None = None,
    *,
    allow_content_changes: bool = True,
) -> None:
    """Remove an output directory after validating the path is safe to clean."""
    if path.is_symlink():
        raise click.ClickException(f"Refusing to clean {label}: path is a symlink.")
    symlinked_parent = next(
        (
            parent
            for parent in (path.parent, *path.parent.parents)
            if parent.is_symlink()
        ),
        None,
    )
    if symlinked_parent is not None:
        raise click.ClickException(
            f"Refusing to clean {label}: parent directory is a symlink: "
            f"{symlinked_parent}."
        )
    invalid_parent = next(
        (parent for parent in path.parents if parent.exists() and not parent.is_dir()),
        None,
    )
    if invalid_parent is not None:
        raise click.ClickException(
            f"Refusing to clean {label}: parent exists but is not a directory: "
            f"{invalid_parent}."
        )
    if not path.exists():
        return
    if not path.is_dir():
        raise click.ClickException(
            f"Refusing to clean {label}: path exists but is not a directory."
        )
    directory_identity = get_directory_path_identity(path)
    if directory_identity is None:
        raise click.ClickException(f"Refusing to clean {label}: path is unsafe.")
    if (
        expected_identity is not None
        and directory_identity != expected_identity
        and not (
            allow_content_changes and directory_identity[:2] == expected_identity[:2]
        )
    ):
        raise click.ClickException(f"Refusing to clean {label}: path changed.")
    try:
        if get_directory_path_identity(path) != directory_identity:
            raise click.ClickException(f"Refusing to clean {label}: path changed.")
        shutil.rmtree(path)
    except click.ClickException:
        raise
    except OSError as ex:
        raise click.ClickException(f"Failed to clean {label}: {ex}") from ex


def remove_output_file(
    path: Path,
    label: str,
    expected_identity: tuple[int, int, int, int],
    *,
    allow_content_changes: bool = False,
) -> None:
    """Remove an output file only if it still matches the expected identity."""
    current_identity = get_read_path_identity(path)
    if current_identity is None or (
        current_identity != expected_identity
        and not (
            allow_content_changes and current_identity[:2] == expected_identity[:2]
        )
    ):
        raise click.ClickException(f"Refusing to clean {label}: path changed.")
    try:
        if get_read_path_identity(path) != current_identity:
            raise click.ClickException(f"Refusing to clean {label}: path changed.")
        path.unlink()
    except click.ClickException:
        raise
    except OSError as ex:
        raise click.ClickException(f"Failed to clean {label}: {ex}") from ex


def create_temporary_output_directory(parent: Path, prefix: str, label: str) -> Path:
    """Create a temporary output directory inside an already-validated parent."""
    validate_output_directory(parent, f"parent for {label}")
    parent_identity = get_directory_path_identity(parent)
    if parent_identity is None:
        raise click.ClickException(
            f"Refusing to create {label}: parent path is unsafe."
        )
    try:
        temp_path = Path(tempfile.mkdtemp(prefix=prefix, suffix=".tmp", dir=parent))
    except OSError as ex:
        raise click.ClickException(f"Failed to create {label}: {ex}") from ex
    temp_identity = get_directory_path_identity(temp_path)
    if temp_identity is None:
        raise click.ClickException(f"Refusing to create {label}: temp path is unsafe.")
    current_parent_identity = get_directory_path_identity(parent)
    if (
        current_parent_identity is None
        or current_parent_identity[:2] != parent_identity[:2]
    ):
        try:
            remove_output_directory(temp_path, label, temp_identity)
        except click.ClickException:
            pass
        raise click.ClickException(f"Refusing to create {label}: parent path changed.")
    return temp_path


def get_directory_path_identity(path: Path) -> tuple[int, int, int, int] | None:
    """Return directory identity unless the path crosses a symlink boundary."""
    if path.is_symlink() or not path.is_dir():
        return None
    if any(parent.is_symlink() for parent in (path.parent, *path.parent.parents)):
        return None
    try:
        stat = path.stat()
    except OSError:
        return None
    return (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns)


def publish_staged_output_directory(
    staged_path: Path, target_path: Path, label: str
) -> None:
    """Replace an output directory with a staged directory, restoring on failure."""
    if staged_path.is_symlink():
        raise click.ClickException(
            f"Refusing to publish {label}: staged path is a symlink."
        )
    if not staged_path.is_dir():
        raise click.ClickException(
            f"Refusing to publish {label}: staged path is not a directory."
        )
    staged_identity = get_directory_path_identity(staged_path)
    if staged_identity is None:
        raise click.ClickException(
            f"Refusing to publish {label}: staged path is not safe to publish."
        )
    validate_output_directory(target_path, label)
    target_parent_identity = get_directory_path_identity(target_path.parent)
    if target_parent_identity is None:
        raise click.ClickException(
            f"Refusing to publish {label}: target parent path is unsafe."
        )

    backup_root: Path | None = None
    backup_path: Path | None = None
    backup_identity: tuple[int, int, int, int] | None = None
    backup_root_identity: tuple[int, int, int, int] | None = None
    if target_path.exists():
        target_identity = get_directory_path_identity(target_path)
        if target_identity is None:
            raise click.ClickException(
                f"Refusing to back up {label}: target path is unsafe."
            )
        backup_root = create_temporary_output_directory(
            target_path.parent,
            f".{target_path.name}-backup.",
            f"temporary {label} backup directory",
        )
        backup_path = backup_root / target_path.name
        backup_root_identity = get_directory_path_identity(backup_root)
        if backup_root_identity is None:
            raise click.ClickException(
                f"Refusing to back up {label}: backup root path is unsafe."
            )
        if get_directory_path_identity(target_path) != target_identity:
            try:
                remove_output_directory(
                    backup_root,
                    f"temporary {label} backup directory",
                    backup_root_identity,
                )
            except click.ClickException:
                pass
            raise click.ClickException(f"Failed to back up {label}: path changed.")
        try:
            target_path.replace(backup_path)
        except OSError as ex:
            try:
                remove_output_directory(
                    backup_root,
                    f"temporary {label} backup directory",
                    backup_root_identity,
                )
            except click.ClickException:
                pass
            raise click.ClickException(f"Failed to back up {label}: {ex}") from ex
        backup_identity = get_directory_path_identity(backup_path)
        if backup_identity != target_identity:
            try:
                remove_output_directory(
                    backup_root,
                    f"temporary {label} backup directory",
                    backup_root_identity,
                )
            except click.ClickException:
                pass
            raise click.ClickException(f"Failed to back up {label}: path changed.")

    target_replaced = False
    published_target_identity: tuple[int, int, int, int] | None = None
    try:
        current_parent_identity = get_directory_path_identity(target_path.parent)
        if (
            current_parent_identity is None
            or current_parent_identity[:2] != target_parent_identity[:2]
        ):
            raise click.ClickException(
                f"Refusing to publish {label}: target parent path changed."
            )
        staged_path.replace(target_path)
        target_replaced = True
        current_parent_identity = get_directory_path_identity(target_path.parent)
        if (
            current_parent_identity is None
            or current_parent_identity[:2] != target_parent_identity[:2]
        ):
            raise click.ClickException(
                f"Failed to publish {label}: target parent path changed."
            )
        published_target_identity = get_directory_path_identity(target_path)
        validate_output_directory(target_path, label)
        if get_directory_path_identity(target_path) != staged_identity:
            raise click.ClickException(
                f"Failed to publish {label}: staged path changed during publish."
            )
    except OSError as ex:
        publish_error = click.ClickException(f"Failed to publish {label}: {ex}")
    except click.ClickException as ex:
        publish_error = ex
    else:
        if backup_root is not None:
            try:
                remove_output_directory(
                    backup_root,
                    f"temporary {label} backup directory",
                    backup_root_identity,
                )
            except click.ClickException:
                pass
        return

    if target_replaced:
        if target_path.is_symlink() or target_path.is_file():
            try:
                if (
                    published_target_identity is not None
                    and get_directory_path_identity(target_path)
                    != published_target_identity
                ):
                    raise click.ClickException(
                        f"Refusing to clean {label}: path changed."
                    )
                target_path.unlink()
            except click.ClickException as cleanup_ex:
                raise click.ClickException(
                    f"{publish_error.message}; also failed to clean failed "
                    f"{label}: {cleanup_ex.message}"
                ) from cleanup_ex
        elif target_path.exists():
            try:
                remove_output_directory(
                    target_path,
                    label,
                    published_target_identity,
                    allow_content_changes=False,
                )
            except click.ClickException as cleanup_ex:
                raise click.ClickException(
                    f"{publish_error.message}; also failed to clean failed "
                    f"{label}: {cleanup_ex.message}"
                ) from cleanup_ex

    if backup_root is not None and backup_path is not None:
        try:
            if get_directory_path_identity(backup_path) != backup_identity:
                raise OSError("backup path changed")
            backup_path.replace(target_path)
            if get_directory_path_identity(target_path) != backup_identity:
                raise OSError("restored backup path changed")
        except OSError as restore_ex:
            raise click.ClickException(
                f"{publish_error.message}; also failed to restore previous "
                f"{label}: {restore_ex}"
            ) from restore_ex
        try:
            remove_output_directory(
                backup_root,
                f"temporary {label} backup directory",
                backup_root_identity,
            )
        except click.ClickException:
            pass

    raise publish_error


def publish_output_file(
    staged_path: Path,
    target_path: Path,
    label: str,
    expected_staged_identity: tuple[int, int, int, int] | None = None,
) -> None:
    """Replace an output file with a staged file."""
    if staged_path.is_symlink():
        raise click.ClickException(
            f"Refusing to publish {label}: staged path is a symlink."
        )
    if not staged_path.is_file():
        raise click.ClickException(
            f"Refusing to publish {label}: staged path is not a file."
        )
    staged_identity = get_read_path_identity(staged_path)
    if staged_identity is None:
        raise click.ClickException(
            f"Refusing to publish {label}: staged path is not safe to read."
        )
    if (
        expected_staged_identity is not None
        and staged_identity != expected_staged_identity
    ):
        raise click.ClickException(
            f"Refusing to publish {label}: staged path changed before publish."
        )
    validate_output_file(target_path, label)
    target_parent_identity = get_directory_path_identity(target_path.parent)
    if target_parent_identity is None:
        raise click.ClickException(
            f"Refusing to publish {label}: target parent path is unsafe."
        )

    backup_root: Path | None = None
    backup_path: Path | None = None
    backup_identity: tuple[int, int, int, int] | None = None
    backup_root_identity: tuple[int, int, int, int] | None = None
    if target_path.exists():
        target_identity = get_read_path_identity(target_path)
        if target_identity is None:
            raise click.ClickException(
                f"Refusing to back up {label}: target path is unsafe."
            )
        backup_root = create_temporary_output_directory(
            target_path.parent,
            f".{target_path.name}-backup.",
            f"temporary {label} backup directory",
        )
        backup_path = backup_root / target_path.name
        backup_root_identity = get_directory_path_identity(backup_root)
        if backup_root_identity is None:
            raise click.ClickException(
                f"Refusing to back up {label}: backup root path is unsafe."
            )
        if get_read_path_identity(target_path) != target_identity:
            try:
                remove_output_directory(
                    backup_root,
                    f"temporary {label} backup",
                    backup_root_identity,
                )
            except click.ClickException:
                pass
            raise click.ClickException(f"Failed to back up {label}: path changed.")
        try:
            copy_output_file(target_path, backup_path, f"temporary {label} backup")
        except click.ClickException as ex:
            try:
                remove_output_directory(
                    backup_root,
                    f"temporary {label} backup",
                    backup_root_identity,
                )
            except click.ClickException:
                pass
            raise click.ClickException(
                f"Failed to back up {label}: {ex.message}"
            ) from ex
        if get_read_path_identity(target_path) != target_identity:
            try:
                remove_output_directory(
                    backup_root,
                    f"temporary {label} backup",
                    backup_root_identity,
                )
            except click.ClickException:
                pass
            raise click.ClickException(f"Failed to back up {label}: path changed.")
        backup_identity = get_output_copy_source_identity(backup_path)
        if backup_identity is None:
            try:
                remove_output_directory(
                    backup_root,
                    f"temporary {label} backup",
                    backup_root_identity,
                )
            except click.ClickException:
                pass
            raise click.ClickException(f"Failed to back up {label}: backup is unsafe.")

    target_replaced = False
    published_target_identity: tuple[int, int, int, int] | None = None
    published_target_directory_identity: tuple[int, int, int, int] | None = None
    try:
        current_parent_identity = get_directory_path_identity(target_path.parent)
        if (
            current_parent_identity is None
            or current_parent_identity[:2] != target_parent_identity[:2]
        ):
            raise click.ClickException(
                f"Refusing to publish {label}: target parent path changed."
            )
        staged_path.replace(target_path)
        target_replaced = True
        current_parent_identity = get_directory_path_identity(target_path.parent)
        if (
            current_parent_identity is None
            or current_parent_identity[:2] != target_parent_identity[:2]
        ):
            raise click.ClickException(
                f"Failed to publish {label}: target parent path changed."
            )
        published_target_identity = get_read_path_identity(target_path)
        if published_target_identity is None:
            published_target_directory_identity = get_directory_path_identity(
                target_path
            )
            raise click.ClickException(
                f"Failed to publish {label}: target path changed during publish."
            )
        validate_output_file(target_path, label)
        if get_read_path_identity(target_path) != staged_identity:
            raise click.ClickException(
                f"Failed to publish {label}: staged path changed during publish."
            )
    except OSError as ex:
        publish_error = click.ClickException(f"Failed to publish {label}: {ex}")
    except click.ClickException as ex:
        publish_error = ex
    else:
        if backup_root is not None:
            try:
                remove_output_directory(
                    backup_root,
                    f"temporary {label} backup",
                    backup_root_identity,
                )
            except click.ClickException:
                pass
        return

    if not target_replaced:
        if backup_root is not None:
            try:
                remove_output_directory(
                    backup_root,
                    f"temporary {label} backup",
                    backup_root_identity,
                )
            except click.ClickException:
                pass
        raise publish_error

    if target_path.is_symlink() or target_path.is_file():
        try:
            if published_target_identity is None:
                raise click.ClickException(f"Refusing to clean {label}: path changed.")
            remove_output_file(target_path, label, published_target_identity)
        except click.ClickException as cleanup_ex:
            raise click.ClickException(
                f"{publish_error.message}; also failed to clean failed {label}: "
                f"{cleanup_ex.message}"
            ) from cleanup_ex
    elif target_path.exists():
        try:
            if published_target_directory_identity is None:
                raise click.ClickException(f"Refusing to clean {label}: path changed.")
            remove_output_directory(
                target_path,
                label,
                published_target_directory_identity,
            )
        except click.ClickException as cleanup_ex:
            raise click.ClickException(
                f"{publish_error.message}; also failed to clean failed {label}: "
                f"{cleanup_ex.message}"
            ) from cleanup_ex

    if backup_root is not None and backup_path is not None:
        try:
            if get_output_copy_source_identity(backup_path) != backup_identity:
                raise OSError("backup path changed")
            backup_path.replace(target_path)
            if get_read_path_identity(target_path) != backup_identity:
                raise OSError("restored backup path changed")
        except OSError as restore_ex:
            raise click.ClickException(
                f"{publish_error.message}; also failed to restore previous "
                f"{label}: {restore_ex}"
            ) from restore_ex
        try:
            remove_output_directory(
                backup_root,
                f"temporary {label} backup",
                backup_root_identity,
            )
        except click.ClickException:
            pass

    raise publish_error


def load_json_object(path: Path, label: str) -> dict[str, Any] | None:
    """Load an optional JSON metadata file and require an object when present."""
    try:
        if not input_file_exists(path, label):
            return None
        data = read_json(path)
    except click.ClickException:
        raise
    except OSError as ex:
        raise click.ClickException(f"Failed to read {label}: {ex}") from ex
    except Exception as ex:
        raise click.ClickException(f"Invalid {label}: {ex}") from ex

    if data is not None and not isinstance(data, dict):
        raise click.ClickException(f"Invalid {label}: expected a JSON object.")
    if data is None:
        raise click.ClickException(f"Failed to read {label}: path is no longer safe.")

    return data


def load_toml_object(path: Path, label: str) -> dict[str, Any] | None:
    """Load an optional TOML metadata file and wrap parser errors for the CLI."""
    try:
        if not input_file_exists(path, label):
            return None
        data = read_toml(path)
    except click.ClickException:
        raise
    except OSError as ex:
        raise click.ClickException(f"Failed to read {label}: {ex}") from ex
    except Exception as ex:
        raise click.ClickException(f"Invalid {label}: {ex}") from ex

    if data is None:
        raise click.ClickException(f"Failed to read {label}: path is no longer safe.")
    return data


def get_pyproject_project_table(
    pyproject: dict[str, Any],
    label: str,
    *,
    create: bool = False,
) -> dict[str, Any]:
    """Return the optional [project] table from a pyproject mapping."""
    if "project" not in pyproject:
        if create:
            project: dict[str, Any] = {}
            pyproject["project"] = project
            return project
        return {}

    project = pyproject["project"]
    if not isinstance(project, dict):
        raise click.ClickException(f"Invalid {label}: [project] must be a table.")

    return project


def load_extension_config(path: Path) -> tuple[dict[str, Any], ExtensionConfig]:
    """Load and validate an extension.json file for CLI commands."""
    if not input_file_exists(path, "extension.json"):
        raise click.ClickException("extension.json not found.")

    extension_data = load_json_object(path, "extension.json")
    if extension_data is None:
        raise click.ClickException("extension.json not found.")

    try:
        extension = ExtensionConfig.model_validate(extension_data)
    except Exception as ex:
        raise click.ClickException(f"Invalid extension.json: {ex}") from ex

    return extension_data, extension


def find_symlinked_parent(path: Path) -> Path | None:
    """Return the first symlinked parent directory in a path."""
    return next(
        (
            parent
            for parent in (path.parent, *path.parent.parents)
            if parent.is_symlink()
        ),
        None,
    )


def require_optional_directory(path: Path, label: str) -> None:
    """Require an optional project path to be a directory when present."""
    if path.is_symlink():
        raise click.ClickException(f"{label} path is a symlink.")
    if (symlinked_parent := find_symlinked_parent(path)) is not None:
        raise click.ClickException(
            f"{label} parent directory is a symlink: {symlinked_parent}."
        )
    if (path.exists() or path.is_symlink()) and not path.is_dir():
        raise click.ClickException(f"{label} path exists but is not a directory.")
    if path.exists():
        directory_identity = get_directory_path_identity(path)
        if directory_identity is None:
            raise click.ClickException(f"{label} path is no longer safe.")
        current_identity = get_directory_path_identity(path)
        if current_identity != directory_identity:
            raise click.ClickException(f"{label} path changed during validation.")


def optional_directory_exists(path: Path, label: str) -> bool:
    """Return whether an optional project directory exists after validation."""
    require_optional_directory(path, label)
    if not path.exists():
        return False
    directory_identity = get_directory_path_identity(path)
    if directory_identity is None:
        raise click.ClickException(f"{label} path is no longer safe.")
    current_identity = get_directory_path_identity(path)
    if current_identity != directory_identity:
        raise click.ClickException(f"{label} path changed during validation.")
    return True


def get_optional_directory_identity(
    path: Path,
    label: str,
) -> tuple[int, int, int, int] | None:
    """Return the identity of an optional project directory when present."""
    if not optional_directory_exists(path, label):
        return None
    directory_identity = get_directory_path_identity(path)
    if directory_identity is None:
        raise click.ClickException(f"{label} path is no longer safe.")
    return directory_identity


def ensure_directory_identity_unchanged(
    path: Path,
    label: str,
    identity: tuple[int, int, int, int] | None,
    operation: str = "metadata update",
    *,
    allow_content_changes: bool = True,
) -> None:
    """Fail if an optional project directory changed after validation."""
    if identity is None:
        return
    current_identity = get_directory_path_identity(path)
    if current_identity is None or (
        current_identity != identity
        and not (allow_content_changes and current_identity[:2] == identity[:2])
    ):
        raise click.ClickException(f"{label} path changed before {operation}.")


def optional_file_exists(path: Path, label: str) -> bool:
    """Return whether an optional project file exists after validation."""
    if path.is_symlink():
        raise click.ClickException(f"{label} path is a symlink.")
    if (symlinked_parent := find_symlinked_parent(path)) is not None:
        raise click.ClickException(
            f"{label} parent directory is a symlink: {symlinked_parent}."
        )
    if path.exists() and not path.is_file():
        raise click.ClickException(f"{label} path exists but is not a file.")
    if not path.exists():
        return False
    file_identity = get_read_path_identity(path)
    if file_identity is None:
        raise click.ClickException(f"{label} path is no longer safe.")
    current_identity = get_read_path_identity(path)
    if current_identity != file_identity:
        raise click.ClickException(f"{label} path changed during validation.")
    return True


def input_file_exists(path: Path, label: str) -> bool:
    """Return whether an input file exists after validating it is safe to read."""
    if path.is_symlink():
        raise click.ClickException(f"Refusing to read {label}: path is a symlink.")
    if (symlinked_parent := find_symlinked_parent(path)) is not None:
        raise click.ClickException(
            f"Refusing to read {label}: parent directory is a symlink: "
            f"{symlinked_parent}."
        )
    if path.exists() and not path.is_file():
        raise click.ClickException(f"Invalid {label}: path exists but is not a file.")
    if not path.exists():
        return False
    file_identity = get_read_path_identity(path)
    if file_identity is None:
        raise click.ClickException(f"Failed to read {label}: path is no longer safe.")
    current_identity = get_read_path_identity(path)
    if current_identity != file_identity:
        raise click.ClickException(f"Failed to read {label}: path changed.")
    return True


def read_input_text(path: Path, label: str) -> str | None:
    """Read an optional input file after validating the input boundary."""
    if not input_file_exists(path, label):
        return None
    initial_identity = get_read_path_identity(path)
    if initial_identity is None:
        raise click.ClickException(f"Failed to read {label}: path is no longer safe.")

    try:
        content = path.read_text()
    except OSError as ex:
        raise click.ClickException(f"Failed to read {label}: {ex}") from ex

    try:
        still_exists = input_file_exists(path, label)
    except click.ClickException as ex:
        raise click.ClickException(f"Failed to read {label}: {ex.message}") from ex
    if not still_exists:
        raise click.ClickException(f"Failed to read {label}: path is no longer safe.")
    if get_read_path_identity(path) != initial_identity:
        raise click.ClickException(f"Failed to read {label}: path changed during read.")

    return content


def validate_initial_extension_config(
    names: ExtensionNames, version: str, license_: str
) -> None:
    """Validate the metadata that init writes to extension.json."""
    try:
        ExtensionConfig.model_validate(
            {
                "publisher": names["publisher"],
                "name": names["name"],
                "displayName": names["display_name"],
                "version": version,
                "license": license_,
                "permissions": [],
            }
        )
    except Exception as ex:
        raise click.ClickException(f"Invalid initial extension metadata: {ex}") from ex


def create_scaffold_directory(path: Path, label: str) -> None:
    """Create a new scaffold directory without following unsafe boundaries."""
    if path.exists() or path.is_symlink():
        raise click.ClickException(f"Refusing to create {label}: path already exists.")
    if (symlinked_parent := find_symlinked_parent(path)) is not None:
        raise click.ClickException(
            f"Refusing to create {label}: parent directory is a symlink: "
            f"{symlinked_parent}."
        )
    invalid_parent = next(
        (parent for parent in path.parents if parent.exists() and not parent.is_dir()),
        None,
    )
    if invalid_parent is not None:
        raise click.ClickException(
            f"Refusing to create {label}: parent exists but is not a directory: "
            f"{invalid_parent}."
        )
    anchor = get_existing_output_directory_anchor(path)
    anchor_identity = get_directory_path_identity(anchor)
    if anchor_identity is None:
        raise click.ClickException(
            f"Refusing to create {label}: parent path is unsafe."
        )

    try:
        path.mkdir()
    except FileExistsError as ex:
        raise click.ClickException(
            f"Refusing to create {label}: path already exists."
        ) from ex
    except OSError as ex:
        raise click.ClickException(f"Failed to create {label}: {ex}") from ex
    created_identity = get_directory_path_identity(path)
    if created_identity is None:
        raise click.ClickException(f"Refusing to create {label}: path changed.")
    current_anchor_identity = get_directory_path_identity(anchor)
    if (
        current_anchor_identity is None
        or current_anchor_identity[:2] != anchor_identity[:2]
    ):
        try:
            cleanup_scaffold_directory(
                path,
                label,
                created_identity,
                allow_content_changes=False,
            )
        except click.ClickException:
            pass
        raise click.ClickException(f"Refusing to create {label}: parent path changed.")
    if get_directory_path_identity(path) != created_identity:
        raise click.ClickException(f"Refusing to create {label}: path changed.")


def write_scaffold_file(path: Path, label: str, content: str) -> None:
    """Create a scaffold file after validating the output boundary."""
    if path.exists() or path.is_symlink():
        raise click.ClickException(f"Refusing to create {label}: path already exists.")
    validate_output_file(path, label)
    try:
        write_text_atomic(path, content, require_missing=True)
    except OSError as ex:
        raise click.ClickException(f"Failed to create {label}: {ex}") from ex


def cleanup_scaffold_directory(
    path: Path,
    label: str,
    expected_identity: tuple[int, int, int, int] | None = None,
    *,
    allow_content_changes: bool = True,
) -> None:
    """Remove a scaffold directory created during a failed init run."""
    if path.is_symlink():
        raise click.ClickException(f"Refusing to clean {label}: path is a symlink.")
    if not path.exists():
        return
    if not path.is_dir():
        raise click.ClickException(
            f"Refusing to clean {label}: path exists but is not a directory."
        )
    if (symlinked_parent := find_symlinked_parent(path)) is not None:
        raise click.ClickException(
            f"Refusing to clean {label}: parent directory is a symlink: "
            f"{symlinked_parent}."
        )
    directory_identity = get_directory_path_identity(path)
    if directory_identity is None:
        raise click.ClickException(f"Refusing to clean {label}: path is unsafe.")
    if (
        expected_identity is not None
        and directory_identity != expected_identity
        and not (
            allow_content_changes and directory_identity[:2] == expected_identity[:2]
        )
    ):
        raise click.ClickException(f"Refusing to clean {label}: path changed.")
    try:
        if get_directory_path_identity(path) != directory_identity:
            raise click.ClickException(f"Refusing to clean {label}: path changed.")
        shutil.rmtree(path)
    except click.ClickException:
        raise
    except OSError as ex:
        raise click.ClickException(f"Failed to clean {label}: {ex}") from ex


def build_manifest(cwd: Path, remote_entry: str | None) -> Manifest:
    _, extension = load_extension_config(cwd / "extension.json")

    # Generate composite ID from publisher and name
    composite_id = f"{extension.publisher}.{extension.name}"

    frontend: ManifestFrontend | None = None
    if remote_entry:
        frontend = ManifestFrontend(
            remoteEntry=remote_entry,
            moduleFederationName=get_module_federation_name(
                extension.publisher, extension.name
            ),
        )

    backend: ManifestBackend | None = None
    backend_dir = cwd / "backend"
    if optional_directory_exists(backend_dir, "backend"):
        # Generate conventional entry point
        publisher_snake = kebab_to_snake_case(extension.publisher)
        name_snake = kebab_to_snake_case(extension.name)
        entrypoint = f"{publisher_snake}.{name_snake}.entrypoint"
        backend = ManifestBackend(entrypoint=entrypoint)

    return Manifest(
        id=composite_id,
        publisher=extension.publisher,
        name=extension.name,
        displayName=extension.displayName,
        version=extension.version,
        permissions=extension.permissions,
        dependencies=extension.dependencies,
        frontend=frontend,
        backend=backend,
    )


def write_manifest(cwd: Path, manifest: Manifest) -> None:
    dist_dir = cwd / "dist"
    ensure_output_directory(dist_dir, "dist directory")
    manifest_path = dist_dir / "manifest.json"
    validate_output_file(manifest_path, "dist/manifest.json")
    manifest_identity = get_read_path_identity(manifest_path)
    if manifest_identity is None and (
        manifest_path.exists() or manifest_path.is_symlink()
    ):
        raise click.ClickException(
            "Refusing to write dist/manifest.json: path changed."
        )
    try:
        write_text_atomic(
            manifest_path,
            manifest.model_dump_json(indent=2, exclude_none=True, by_alias=True),
            expected_existing_identity=manifest_identity,
            require_missing=manifest_identity is None,
        )
    except OSError as ex:
        raise click.ClickException(f"Failed to write dist/manifest.json: {ex}") from ex
    click.secho("✅ Manifest updated", fg="green")


def run_frontend_build(frontend_dir: Path) -> subprocess.CompletedProcess[str]:
    require_optional_directory(frontend_dir, "frontend")
    frontend_identity = get_directory_path_identity(frontend_dir)
    if frontend_identity is None:
        raise click.ClickException("frontend path is no longer safe.")

    click.echo()
    click.secho("⚙️  Building frontend assets…", fg="cyan")
    npm_executable = validate_npm()
    current_frontend_identity = get_directory_path_identity(frontend_dir)
    if current_frontend_identity != frontend_identity:
        raise click.ClickException("frontend path changed before frontend build.")
    command = [get_npm_executable_path(npm_executable), "run", "build"]
    try:
        return subprocess.run(  # noqa: S603
            command,  # noqa: S607
            cwd=frontend_dir,
            text=True,
        )
    except OSError as ex:
        click.secho(f"❌ Failed to run `npm run build`: {ex}", err=True, fg="red")
        return subprocess.CompletedProcess(command, returncode=1)


def copy_frontend_dist(cwd: Path) -> str:
    dist_dir = cwd / "dist"
    frontend_output_dir = dist_dir / "frontend"
    frontend_dist_output_dir = frontend_output_dir / "dist"
    frontend_dir_path = cwd / "frontend"
    require_optional_directory(frontend_dir_path, "frontend")
    frontend_dist_path = frontend_dir_path / "dist"
    require_optional_directory(frontend_dist_path, "frontend/dist")
    frontend_dist = frontend_dist_path.resolve()
    frontend_files: list[tuple[Path, tuple[int, int, int, int]]] = []
    remote_entries: list[str] = []

    for f in sorted(frontend_dist.rglob("*")):
        if not f.is_file():
            continue
        identity = get_copy_source_identity(f, frontend_dist)
        if identity is None:
            raise click.ClickException(
                f"Refusing to copy {f}: resolved path is outside the "
                f"frontend dist directory {frontend_dist}."
            )
        if REMOTE_ENTRY_REGEX.match(f.name):
            if f.parent != frontend_dist:
                raise click.ClickException(
                    f"Remote entry file must be in frontend/dist: "
                    f"{f.relative_to(frontend_dist)}."
                )
            remote_entries.append(f.name)
        frontend_files.append((f, identity))

    if not remote_entries:
        raise click.ClickException("No remote entry file found.")
    if len(remote_entries) > 1:
        raise click.ClickException(
            f"Multiple remote entry files found: {', '.join(sorted(remote_entries))}."
        )

    copy_targets = [
        (f, identity, frontend_dist_output_dir / f.relative_to(frontend_dist))
        for f, identity in frontend_files
    ]
    for _, _, tgt in copy_targets:
        validate_output_file_parent(
            tgt,
            frontend_dist_output_dir,
            f"frontend asset {tgt.relative_to(frontend_dist_output_dir)}",
        )

    ensure_output_directory(dist_dir, "dist directory")
    staged_frontend_output_dir = create_temporary_output_directory(
        dist_dir,
        ".frontend.",
        "temporary frontend output directory",
    )
    staged_frontend_identity = get_directory_path_identity(staged_frontend_output_dir)
    if staged_frontend_identity is None:
        raise click.ClickException(
            "Refusing to stage frontend assets: temporary output path is unsafe."
        )
    staged_frontend_dist_output_dir = staged_frontend_output_dir / "dist"

    try:
        for f, identity, tgt in copy_targets:
            relative_target = tgt.relative_to(frontend_dist_output_dir)
            ensure_copy_source_unchanged(
                f,
                frontend_dist,
                identity,
                f"frontend asset {relative_target}",
            )
            staged_target = staged_frontend_dist_output_dir / relative_target
            ensure_output_file_parent(
                staged_target,
                staged_frontend_dist_output_dir,
                f"frontend asset {relative_target}",
            )
            copy_output_file(
                f,
                staged_target,
                f"frontend asset {relative_target}",
            )

        publish_staged_output_directory(
            staged_frontend_output_dir,
            frontend_output_dir,
            "dist/frontend directory",
        )
    except click.ClickException:
        try:
            remove_output_directory(
                staged_frontend_output_dir,
                "temporary frontend output directory",
                staged_frontend_identity,
            )
        except click.ClickException:
            pass
        raise

    return remote_entries[0]


def get_backend_build_patterns(
    pyproject: dict[str, Any],
) -> tuple[list[str], list[str]]:
    """Return validated backend build include and exclude patterns."""
    tool_config = pyproject.get("tool", {})
    if not isinstance(tool_config, dict):
        raise click.ClickException(
            "Invalid backend build config: [tool] must be a table."
        )

    extension_config = tool_config.get("apache_superset_extensions", {})
    if not isinstance(extension_config, dict):
        raise click.ClickException(
            "Invalid backend build config: "
            "[tool.apache_superset_extensions] must be a table."
        )

    build_config = extension_config.get("build", {})
    if not isinstance(build_config, dict):
        raise click.ClickException(
            "Invalid backend build config: "
            "[tool.apache_superset_extensions.build] must be a table."
        )

    include_patterns = build_config.get("include")
    if (
        not isinstance(include_patterns, list)
        or not include_patterns
        or not all(isinstance(pattern, str) and pattern for pattern in include_patterns)
    ):
        raise click.ClickException(
            "Invalid backend build config: 'include' must be a non-empty "
            "list of string patterns."
        )

    exclude_patterns = build_config.get("exclude", [])
    if not isinstance(exclude_patterns, list) or not all(
        isinstance(pattern, str) and pattern for pattern in exclude_patterns
    ):
        raise click.ClickException(
            "Invalid backend build config: 'exclude' must be a list of "
            "string patterns when provided."
        )

    for pattern in include_patterns:
        validate_backend_build_pattern(pattern, "include")
    for pattern in exclude_patterns:
        validate_backend_build_pattern(pattern, "exclude")

    return include_patterns, exclude_patterns


def copy_backend_files(cwd: Path) -> None:
    """Copy backend files based on pyproject.toml build configuration (validation already passed)."""
    dist_dir = cwd / "dist"
    backend_output_dir = dist_dir / "backend"
    backend_dir_path = cwd / "backend"
    require_optional_directory(backend_dir_path, "backend")
    backend_dir = backend_dir_path.resolve()

    # Read build config from pyproject.toml
    pyproject_path = backend_dir / "pyproject.toml"
    if not input_file_exists(pyproject_path, "backend/pyproject.toml"):
        raise click.ClickException("backend pyproject.toml not found.")
    pyproject = load_toml_object(pyproject_path, "backend pyproject.toml")
    if pyproject is None:
        raise click.ClickException("backend pyproject.toml not found.")
    include_patterns, exclude_patterns = get_backend_build_patterns(pyproject)

    copy_targets: dict[Path, tuple[Path, Path, tuple[int, int, int, int]]] = {}

    # Process include patterns
    for pattern in include_patterns:
        for f in sorted(backend_dir.glob(pattern)):
            if not f.is_file():
                continue

            # Defense in depth: confirm the matched file resolves to a location
            # inside the backend directory before copying it into the bundle.
            identity = get_copy_source_identity(f, backend_dir)
            if identity is None:
                raise click.ClickException(
                    f"Refusing to copy {f}: resolved path is outside the "
                    f"backend directory {backend_dir}."
                )

            # Use the matched path (not the resolved target) for the bundle
            # layout and exclude evaluation so symlinked files are staged at
            # their configured path rather than their symlink target.
            relative_path = f.relative_to(backend_dir)
            should_exclude = any(
                relative_path.match(excl_pattern) for excl_pattern in exclude_patterns
            )
            if should_exclude:
                continue

            target_path = backend_output_dir / relative_path
            copy_targets.setdefault(target_path, (f, target_path, identity))

    for _, tgt, _ in copy_targets.values():
        validate_output_file_parent(
            tgt,
            backend_output_dir,
            f"backend file {tgt.relative_to(backend_output_dir)}",
        )

    ensure_output_directory(dist_dir, "dist directory")
    staged_backend_output_dir = create_temporary_output_directory(
        dist_dir,
        ".backend.",
        "temporary backend output directory",
    )
    staged_backend_identity = get_directory_path_identity(staged_backend_output_dir)
    if staged_backend_identity is None:
        raise click.ClickException(
            "Refusing to stage backend files: temporary output path is unsafe."
        )

    try:
        for f, tgt, identity in copy_targets.values():
            relative_target = tgt.relative_to(backend_output_dir)
            ensure_copy_source_unchanged(
                f,
                backend_dir,
                identity,
                f"backend file {relative_target}",
            )
            staged_target = staged_backend_output_dir / relative_target
            ensure_output_file_parent(
                staged_target,
                staged_backend_output_dir,
                f"backend file {relative_target}",
            )
            copy_output_file(
                f,
                staged_target,
                f"backend file {relative_target}",
            )

        publish_staged_output_directory(
            staged_backend_output_dir,
            backend_output_dir,
            "dist/backend directory",
        )
    except click.ClickException:
        try:
            remove_output_directory(
                staged_backend_output_dir,
                "temporary backend output directory",
                staged_backend_identity,
            )
        except click.ClickException:
            pass
        raise


def rebuild_frontend(cwd: Path, frontend_dir: Path) -> str | None:
    """Clean and rebuild frontend, return the remoteEntry filename."""
    res = run_frontend_build(frontend_dir)
    if res.returncode != 0:
        click.secho("❌ Frontend build failed", fg="red")
        return None

    remote_entry = copy_frontend_dist(cwd)
    click.secho("✅ Frontend rebuilt", fg="green")
    return remote_entry


def rebuild_backend(cwd: Path) -> None:
    """Copy backend files (no manifest update)."""
    copy_backend_files(cwd)
    click.secho("✅ Backend files synced", fg="green")


def require_conventional_entrypoint(
    path: Path,
    cwd: Path,
    label: str,
    convention: str,
) -> None:
    """Validate a conventional entrypoint file and report a convention hint."""
    try:
        exists = optional_file_exists(path, label)
    except click.ClickException as ex:
        if "exists but is not a file" not in ex.message:
            click.secho(f"❌ {ex.message}", err=True, fg="red")
            sys.exit(1)
        exists = False

    if not exists:
        click.secho(
            f"❌ {label} not found at expected location: {path.relative_to(cwd)}",
            err=True,
            fg="red",
        )
        click.secho(f"   Convention requires: {convention}", fg="yellow")
        sys.exit(1)


def validate_bundle_output_path(path: Path) -> None:
    """Validate that a bundle output path can be safely opened for writing."""
    if path.is_symlink():
        raise click.ClickException(f"Refusing to write bundle to symlink: {path}.")

    symlinked_parent = next(
        (
            parent
            for parent in (path.parent, *path.parent.parents)
            if parent.is_symlink()
        ),
        None,
    )
    if symlinked_parent is not None:
        raise click.ClickException(
            f"Refusing to write bundle through symlinked directory: {symlinked_parent}."
        )
    if path.exists() and not path.is_file():
        raise click.ClickException(
            f"Refusing to write bundle: {path} exists but is not a file."
        )
    invalid_parent = next(
        (
            parent
            for parent in (path.parent, *path.parent.parents)
            if parent.exists() and not parent.is_dir()
        ),
        None,
    )
    if invalid_parent is not None:
        raise click.ClickException(
            f"Refusing to write bundle: parent exists but is not a directory: "
            f"{invalid_parent}."
        )
    if not path.parent.is_dir():
        raise click.ClickException(
            f"Refusing to write bundle: parent directory does not exist: {path.parent}."
        )


def get_bundle_default_filename(extension_name: str, extension_version: str) -> str:
    """Return the default bundle filename from manifest metadata."""
    filename = f"{extension_name}-{extension_version}.supx"
    windows_filename = PureWindowsPath(filename)
    if (
        split_path_parts(filename) != [filename]
        or Path(filename).name != filename
        or bool(windows_filename.drive)
        or bool(windows_filename.root)
        or windows_filename.name != filename
    ):
        raise click.ClickException(
            "Invalid bundle default filename from manifest metadata."
        )
    return filename


def verify_bundle_archive_contents(
    archive_path: Path,
    bundle_entries: list[tuple[Path, Path, tuple[int, int, int, int]]],
    resolved_dist_dir: Path,
) -> None:
    """Verify a temporary bundle archive still matches planned dist entries."""
    expected_names = {arcname.as_posix() for _, arcname, _ in bundle_entries}
    try:
        with zipfile.ZipFile(archive_path, "r") as zipf:
            archive_names = zipf.namelist()
            actual_names = set(archive_names)
            if (
                len(archive_names) != len(expected_names)
                or actual_names != expected_names
            ):
                raise click.ClickException(
                    "Refusing to publish bundle: temporary archive content changed."
                )
            for file, arcname, identity in bundle_entries:
                ensure_copy_source_unchanged(
                    file,
                    resolved_dist_dir,
                    identity,
                    f"bundle entry {arcname}",
                )
                archived_bytes = zipf.read(arcname.as_posix())
                ensure_copy_source_unchanged(
                    file,
                    resolved_dist_dir,
                    identity,
                    f"bundle entry {arcname}",
                )
                source_bytes = file.read_bytes()
                ensure_copy_source_unchanged(
                    file,
                    resolved_dist_dir,
                    identity,
                    f"bundle entry {arcname}",
                )
                if archived_bytes != source_bytes:
                    raise click.ClickException(
                        "Refusing to publish bundle: temporary archive content "
                        f"changed for {arcname}."
                    )
    except zipfile.BadZipFile as ex:
        raise click.ClickException(
            "Refusing to publish bundle: temporary archive is not a valid zip."
        ) from ex
    except OSError as ex:
        raise click.ClickException(
            f"Failed to verify temporary bundle archive: {ex}"
        ) from ex


class FrontendChangeHandler(FileSystemEventHandler):
    def __init__(self, trigger_build: Callable[[], None]):
        self.trigger_build = trigger_build

    def on_any_event(self, event: Any) -> None:
        if is_frontend_dist_path(event.src_path):
            return
        click.secho(f"🔁 Frontend change detected: {event.src_path}", fg="yellow")
        self.trigger_build()


def is_frontend_dist_path(path: str) -> bool:
    """Return whether a watched frontend path is inside frontend/dist."""
    parts = split_path_parts(path)
    return any(
        part == "frontend" and index + 1 < len(parts) and parts[index + 1] == "dist"
        for index, part in enumerate(parts)
    )


@click.group(help="CLI for validating and bundling Superset extensions.")
def app() -> None:
    pass


@app.command()
def validate() -> None:
    """Validate the extension structure and metadata consistency."""
    validate_npm()

    cwd = Path.cwd()

    # Validate extension.json exists and is valid
    try:
        extension_data, extension = load_extension_config(cwd / "extension.json")
    except click.ClickException as ex:
        click.secho(f"❌ {ex.message}", err=True, fg="red")
        sys.exit(1)

    # Validate conventional backend structure if backend directory exists
    backend_dir = cwd / "backend"
    try:
        has_backend_dir = optional_directory_exists(backend_dir, "backend")
    except click.ClickException as ex:
        click.secho(f"❌ {ex.message}", err=True, fg="red")
        sys.exit(1)
    if has_backend_dir:
        # Check for pyproject.toml
        pyproject_path = backend_dir / "pyproject.toml"
        try:
            has_pyproject = optional_file_exists(
                pyproject_path, "backend/pyproject.toml"
            )
        except click.ClickException as ex:
            click.secho(f"❌ {ex.message}", err=True, fg="red")
            sys.exit(1)
        if not has_pyproject:
            click.secho(
                "❌ Backend directory exists but pyproject.toml not found",
                err=True,
                fg="red",
            )
            sys.exit(1)

        # Validate pyproject.toml has build configuration
        try:
            pyproject = load_toml_object(pyproject_path, "backend pyproject.toml")
        except click.ClickException as ex:
            click.secho(f"❌ {ex.message}", err=True, fg="red")
            sys.exit(1)
        if not pyproject:
            click.secho("❌ Failed to read backend pyproject.toml", err=True, fg="red")
            sys.exit(1)

        try:
            get_backend_build_patterns(pyproject)
        except click.ClickException as ex:
            click.secho(
                f"❌ {ex.message}",
                err=True,
                fg="red",
            )
            sys.exit(1)

        # Check conventional backend entry point
        publisher_snake = kebab_to_snake_case(extension.publisher)
        name_snake = kebab_to_snake_case(extension.name)
        expected_entry_file = (
            backend_dir / "src" / publisher_snake / name_snake / "entrypoint.py"
        )

        require_conventional_entrypoint(
            expected_entry_file,
            cwd,
            "Backend entry point",
            f"backend/src/{publisher_snake}/{name_snake}/entrypoint.py",
        )

    # Validate conventional frontend entry point if frontend directory exists
    frontend_dir = cwd / "frontend"
    try:
        has_frontend_dir = optional_directory_exists(frontend_dir, "frontend")
    except click.ClickException as ex:
        click.secho(f"❌ {ex.message}", err=True, fg="red")
        sys.exit(1)
    if has_frontend_dir:
        expected_frontend_entry = frontend_dir / "src" / "index.tsx"
        require_conventional_entrypoint(
            expected_frontend_entry,
            cwd,
            "Frontend entry point",
            "frontend/src/index.tsx",
        )

    # Validate version and license consistency across extension.json, frontend, and backend
    mismatches: list[str] = []
    frontend_pkg_path = frontend_dir / "package.json"
    frontend_pkg = None
    try:
        has_frontend_pkg = optional_file_exists(
            frontend_pkg_path, "frontend/package.json"
        )
    except click.ClickException as ex:
        click.secho(f"❌ {ex.message}", err=True, fg="red")
        sys.exit(1)
    if has_frontend_pkg:
        try:
            frontend_pkg = load_json_object(frontend_pkg_path, "frontend/package.json")
        except click.ClickException as ex:
            click.secho(f"❌ {ex.message}", err=True, fg="red")
            sys.exit(1)
        if frontend_pkg:
            if frontend_pkg.get("version") != extension.version:
                mismatches.append(
                    f"  frontend/package.json version: {frontend_pkg.get('version')} "
                    f"(expected {extension.version})"
                )
            if extension.license and frontend_pkg.get("license") != extension.license:
                mismatches.append(
                    f"  frontend/package.json license: {frontend_pkg.get('license')} "
                    f"(expected {extension.license})"
                )

    backend_pyproject_path = cwd / "backend" / "pyproject.toml"
    try:
        has_backend_pyproject = optional_file_exists(
            backend_pyproject_path, "backend/pyproject.toml"
        )
    except click.ClickException as ex:
        click.secho(f"❌ {ex.message}", err=True, fg="red")
        sys.exit(1)
    if has_backend_pyproject:
        try:
            backend_pyproject = load_toml_object(
                backend_pyproject_path, "backend/pyproject.toml"
            )
        except click.ClickException as ex:
            click.secho(f"❌ {ex.message}", err=True, fg="red")
            sys.exit(1)
        if backend_pyproject:
            try:
                project = get_pyproject_project_table(
                    backend_pyproject, "backend/pyproject.toml"
                )
            except click.ClickException as ex:
                click.secho(f"❌ {ex.message}", err=True, fg="red")
                sys.exit(1)
            if project.get("version") != extension.version:
                mismatches.append(
                    f"  backend/pyproject.toml version: {project.get('version')} "
                    f"(expected {extension.version})"
                )
            if extension.license and project.get("license") != extension.license:
                mismatches.append(
                    f"  backend/pyproject.toml license: {project.get('license')} "
                    f"(expected {extension.license})"
                )

    if mismatches:
        click.secho("❌ Metadata mismatch detected:", err=True, fg="red")
        for mismatch in mismatches:
            click.secho(mismatch, err=True, fg="red")
        click.secho(
            "Run `superset-extensions update` to sync from extension.json.",
            fg="yellow",
        )
        sys.exit(1)

    click.secho("✅ Validation successful", fg="green")


@app.command()
@click.option(
    "--version",
    "version_opt",
    is_flag=False,
    flag_value="__prompt__",
    default=None,
    help="Set a new version. Prompts for value if none given.",
)
@click.option(
    "--license",
    "license_opt",
    is_flag=False,
    flag_value="__prompt__",
    default=None,
    help="Set a new license. Prompts for value if none given.",
)
def update(version_opt: str | None, license_opt: str | None) -> None:
    """Update derived and generated files in the extension project."""
    cwd = Path.cwd()

    extension_json_path = cwd / "extension.json"
    try:
        extension_data, extension = load_extension_config(extension_json_path)
    except click.ClickException as ex:
        click.secho(f"❌ {ex.message}", err=True, fg="red")
        sys.exit(1)

    # Resolve version: prompt if flag used without value
    if version_opt == "__prompt__":
        version_opt = click.prompt("Version", default=extension.version)
    target_version = (
        version_opt
        if version_opt and version_opt != extension.version
        else extension.version
    )

    # Resolve license: prompt if flag used without value
    if license_opt == "__prompt__":
        license_opt = click.prompt("License", default=extension.license or "")
    target_license = (
        license_opt
        if license_opt and license_opt != extension.license
        else extension.license
    )

    frontend_dir = cwd / "frontend"
    try:
        frontend_identity = get_optional_directory_identity(frontend_dir, "frontend")
    except click.ClickException as ex:
        click.secho(f"❌ {ex.message}", err=True, fg="red")
        sys.exit(1)

    frontend_pkg_path = frontend_dir / "package.json"
    frontend_pkg = None
    try:
        has_frontend_pkg = optional_file_exists(
            frontend_pkg_path, "frontend/package.json"
        )
    except click.ClickException as ex:
        click.secho(f"❌ {ex.message}", err=True, fg="red")
        sys.exit(1)
    if has_frontend_pkg:
        try:
            frontend_pkg = load_json_object(frontend_pkg_path, "frontend/package.json")
        except click.ClickException as ex:
            click.secho(f"❌ {ex.message}", err=True, fg="red")
            sys.exit(1)

    backend_dir = cwd / "backend"
    try:
        backend_identity = get_optional_directory_identity(backend_dir, "backend")
    except click.ClickException as ex:
        click.secho(f"❌ {ex.message}", err=True, fg="red")
        sys.exit(1)

    backend_pyproject_path = backend_dir / "pyproject.toml"
    backend_pyproject = None
    backend_project = None
    try:
        has_backend_pyproject = optional_file_exists(
            backend_pyproject_path, "backend/pyproject.toml"
        )
    except click.ClickException as ex:
        click.secho(f"❌ {ex.message}", err=True, fg="red")
        sys.exit(1)
    if has_backend_pyproject:
        try:
            backend_pyproject = load_toml_object(
                backend_pyproject_path, "backend/pyproject.toml"
            )
            if backend_pyproject:
                backend_project = get_pyproject_project_table(
                    backend_pyproject,
                    "backend/pyproject.toml",
                    create=True,
                )
        except click.ClickException as ex:
            click.secho(f"❌ {ex.message}", err=True, fg="red")
            sys.exit(1)

    updated: list[str] = []
    pending_json_writes: list[tuple[Path, str, dict[str, Any]]] = []
    pending_toml_writes: list[tuple[Path, str, dict[str, Any]]] = []

    # Update extension.json if version or license changed
    ext_changed = False
    if version_opt and version_opt != extension.version:
        extension_data["version"] = target_version
        ext_changed = True
    if license_opt and license_opt != extension.license:
        extension_data["license"] = target_license
        ext_changed = True
    if ext_changed:
        try:
            ExtensionConfig.model_validate(extension_data)
        except Exception as e:
            click.secho(f"❌ Invalid value: {e}", err=True, fg="red")
            sys.exit(1)
        pending_json_writes.append(
            (extension_json_path, "extension.json", extension_data)
        )

    # Update frontend/package.json
    if frontend_pkg is not None:
        if frontend_pkg:
            pkg_changed = False
            if frontend_pkg.get("version") != target_version:
                frontend_pkg["version"] = target_version
                pkg_changed = True
            if target_license and frontend_pkg.get("license") != target_license:
                frontend_pkg["license"] = target_license
                pkg_changed = True
            if pkg_changed:
                pending_json_writes.append(
                    (frontend_pkg_path, "frontend/package.json", frontend_pkg)
                )

    # Update backend/pyproject.toml
    if backend_pyproject is not None:
        if backend_pyproject:
            project = backend_project
            toml_changed = False
            if project is not None and project.get("version") != target_version:
                project["version"] = target_version
                toml_changed = True
            if (
                project is not None
                and target_license
                and project.get("license") != target_license
            ):
                project["license"] = target_license
                toml_changed = True
            if toml_changed:
                pending_toml_writes.append(
                    (
                        backend_pyproject_path,
                        "backend/pyproject.toml",
                        backend_pyproject,
                    )
                )

    try:
        for path, label, _ in [*pending_json_writes, *pending_toml_writes]:
            validate_output_file(path, label)
    except click.ClickException as ex:
        click.secho(f"❌ {ex.message}", err=True, fg="red")
        sys.exit(1)

    def ensure_metadata_directories_unchanged() -> None:
        ensure_directory_identity_unchanged(
            frontend_dir,
            "frontend",
            frontend_identity,
            allow_content_changes=False,
        )
        ensure_directory_identity_unchanged(
            backend_dir,
            "backend",
            backend_identity,
            allow_content_changes=False,
        )

    def refresh_metadata_directory_identity(path: Path) -> None:
        nonlocal backend_identity, frontend_identity
        if frontend_identity is not None and path.is_relative_to(frontend_dir):
            frontend_identity = get_directory_path_identity(frontend_dir)
            if frontend_identity is None:
                raise OSError("Failed to verify frontend directory: unsafe path.")
        if backend_identity is not None and path.is_relative_to(backend_dir):
            backend_identity = get_directory_path_identity(backend_dir)
            if backend_identity is None:
                raise OSError("Failed to verify backend directory: unsafe path.")

    pending_writes = [*pending_json_writes, *pending_toml_writes]
    try:
        original_contents: dict[Path, str] = {}
        original_identities: dict[Path, tuple[int, int, int, int]] = {}
        for path, label, _ in pending_writes:
            ensure_metadata_directories_unchanged()
            original_content = read_input_text(path, label)
            if original_content is None:
                raise click.ClickException(f"Failed to read {label}: file not found.")
            original_identity = get_read_path_identity(path)
            if original_identity is None:
                raise click.ClickException(f"Failed to read {label}: unsafe path.")
            original_contents[path] = original_content
            original_identities[path] = original_identity
    except click.ClickException as ex:
        click.secho(
            f"❌ Failed to read original metadata before update: {ex.message}",
            err=True,
            fg="red",
        )
        sys.exit(1)

    written_paths: list[tuple[Path, str, tuple[int, int, int, int]]] = []
    try:
        for path, label, data in pending_json_writes:
            ensure_metadata_directories_unchanged()
            if get_read_path_identity(path) != original_identities[path]:
                raise click.ClickException(
                    f"Refusing to update {label}: path changed after snapshot."
                )
            write_json(
                path,
                data,
                expected_existing_identity=original_identities[path],
            )
            written_identity = get_read_path_identity(path)
            if written_identity is None:
                raise OSError(f"Failed to verify written {label}: unsafe path.")
            refresh_metadata_directory_identity(path)
            written_paths.append((path, label, written_identity))
            updated.append(label)

        for path, label, data in pending_toml_writes:
            ensure_metadata_directories_unchanged()
            if get_read_path_identity(path) != original_identities[path]:
                raise click.ClickException(
                    f"Refusing to update {label}: path changed after snapshot."
                )
            write_toml(
                path,
                data,
                expected_existing_identity=original_identities[path],
            )
            written_identity = get_read_path_identity(path)
            if written_identity is None:
                raise OSError(f"Failed to verify written {label}: unsafe path.")
            refresh_metadata_directory_identity(path)
            written_paths.append((path, label, written_identity))
            updated.append(label)
    except (OSError, click.ClickException) as ex:
        for path, label, written_identity in reversed(written_paths):
            try:
                if get_read_path_identity(path) != written_identity:
                    raise OSError(f"Refusing to roll back {label}: path changed.")
                rollback_directory_identity: tuple[int, int, int, int] | None = None
                rollback_directory: Path | None = None
                if frontend_identity is not None and path.is_relative_to(frontend_dir):
                    rollback_directory = frontend_dir
                    rollback_directory_identity = get_directory_path_identity(
                        frontend_dir
                    )
                if backend_identity is not None and path.is_relative_to(backend_dir):
                    rollback_directory = backend_dir
                    rollback_directory_identity = get_directory_path_identity(
                        backend_dir
                    )
                if (
                    rollback_directory is not None
                    and rollback_directory_identity is None
                ):
                    raise OSError(
                        f"Refusing to roll back {label}: directory path changed."
                    )
                write_text_atomic(
                    path,
                    original_contents[path],
                    expected_existing_identity=written_identity,
                )
                if (
                    rollback_directory is not None
                    and rollback_directory_identity is not None
                ):
                    current_directory_identity = get_directory_path_identity(
                        rollback_directory
                    )
                    if (
                        current_directory_identity is None
                        or current_directory_identity[:2]
                        != rollback_directory_identity[:2]
                    ):
                        raise OSError(
                            f"Refusing to roll back {label}: directory path changed."
                        )
                    refresh_metadata_directory_identity(path)
            except OSError as rollback_ex:
                click.secho(
                    f"❌ Failed to roll back {label}: {rollback_ex}",
                    err=True,
                    fg="red",
                )
        message = ex.message if isinstance(ex, click.ClickException) else str(ex)
        click.secho(f"❌ {message}", err=True, fg="red")
        sys.exit(1)

    if updated:
        for updated_path in updated:
            click.secho(f"✅ Updated {updated_path}", fg="green")
    else:
        click.secho("✅ All files already up to date.", fg="green")


@app.command()
@click.pass_context
def build(ctx: click.Context) -> None:
    """Build extension assets."""
    ctx.invoke(validate)
    cwd = Path.cwd()
    frontend_dir = cwd / "frontend"
    backend_dir = cwd / "backend"

    frontend_identity = get_optional_directory_identity(frontend_dir, "frontend")
    backend_identity = get_optional_directory_identity(backend_dir, "backend")
    has_frontend = frontend_identity is not None
    has_backend = backend_identity is not None
    remote_entry = None
    if has_frontend:
        ensure_directory_identity_unchanged(
            frontend_dir,
            "frontend",
            frontend_identity,
            "build",
        )
        init_frontend_deps(frontend_dir)
        ensure_directory_identity_unchanged(
            frontend_dir,
            "frontend",
            frontend_identity,
            "build",
        )
        frontend_result = run_frontend_build(frontend_dir)
        if frontend_result.returncode != 0:
            click.secho(
                "❌ Frontend build failed; aborting full build.",
                err=True,
                fg="red",
            )
            sys.exit(1)

    (
        dist_backup_root,
        dist_backup_path,
        dist_backup_identity,
        dist_backup_root_identity,
        dist_replacement_identity,
    ) = start_dist_replacement(cwd)
    try:
        if has_frontend:
            ensure_directory_identity_unchanged(
                frontend_dir,
                "frontend",
                frontend_identity,
                "build",
            )
            remote_entry = copy_frontend_dist(cwd)
            click.secho("✅ Frontend rebuilt", fg="green")

        # Build backend independently if it exists
        if has_backend:
            ensure_directory_identity_unchanged(
                backend_dir,
                "backend",
                backend_identity,
                "build",
            )
            pyproject = load_toml_object(
                backend_dir / "pyproject.toml", "backend pyproject.toml"
            )
            if pyproject:
                ensure_directory_identity_unchanged(
                    backend_dir,
                    "backend",
                    backend_identity,
                    "build",
                )
                rebuild_backend(cwd)

        # Build manifest and write it
        manifest = build_manifest(cwd, remote_entry)
        write_manifest(cwd, manifest)
    except Exception as ex:
        try:
            rollback_dist_replacement(
                cwd,
                dist_backup_root,
                dist_backup_path,
                dist_backup_identity,
                dist_backup_root_identity,
                dist_replacement_identity,
            )
        except click.ClickException as rollback_ex:
            if isinstance(ex, click.ClickException):
                raise click.ClickException(
                    f"{ex.message}; {rollback_ex.message}"
                ) from ex
            raise click.ClickException(f"{ex}; {rollback_ex.message}") from ex
        raise

    cleanup_dist_replacement_backup(dist_backup_root, dist_backup_root_identity)

    click.secho("✅ Full build completed in dist/", fg="green")


@app.command()
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path, dir_okay=True, file_okay=True, writable=True),
    help="Optional output path or filename for the bundle.",
)
@click.pass_context
def bundle(ctx: click.Context, output: Path | None) -> None:
    """Package the extension into a .supx file."""
    ctx.invoke(build)

    cwd = Path.cwd()
    dist_dir = cwd / "dist"
    try:
        require_optional_directory(dist_dir, "dist")
    except click.ClickException as ex:
        click.secho(f"❌ {ex.message}", err=True, fg="red")
        sys.exit(1)

    manifest_path = dist_dir / "manifest.json"

    try:
        manifest_json = read_input_text(manifest_path, "dist/manifest.json")
    except click.ClickException as ex:
        click.secho(f"❌ {ex.message}", err=True, fg="red")
        sys.exit(1)

    if manifest_json is None:
        click.secho(
            "❌ dist/manifest.json not found. Run `build` first.", err=True, fg="red"
        )
        sys.exit(1)

    try:
        manifest = Manifest.model_validate_json(manifest_json)
    except Exception as ex:
        click.secho(f"❌ Invalid dist/manifest.json: {ex}", err=True, fg="red")
        sys.exit(1)

    try:
        default_filename = get_bundle_default_filename(manifest.name, manifest.version)
    except click.ClickException as ex:
        click.secho(f"❌ {ex.message}", err=True, fg="red")
        sys.exit(1)

    output_directory_identity: tuple[int, int, int, int] | None = None
    if output is None:
        zip_path = Path(default_filename)
    elif output.is_dir():
        output_directory_identity = get_directory_path_identity(output)
        zip_path = output / default_filename
    else:
        zip_path = output

    temp_path: Path | None = None
    temp_identity: tuple[int, int, int, int] | None = None
    try:
        resolved_dist_dir = dist_dir.resolve()
        resolved_zip_path = zip_path.resolve()
        validate_bundle_output_path(zip_path)
        if (
            output is not None
            and output_directory_identity is not None
            and get_directory_path_identity(output) != output_directory_identity
        ):
            raise click.ClickException(
                f"Refusing to write bundle: output directory changed: {output}."
            )
        output_parent_identity = get_directory_path_identity(zip_path.parent)
        if output_parent_identity is None:
            raise click.ClickException(
                f"Refusing to write bundle: parent directory is unsafe: "
                f"{zip_path.parent}."
            )

        bundle_entries: list[tuple[Path, Path, tuple[int, int, int, int]]] = []
        for file in dist_dir.rglob("*"):
            if not file.is_file():
                continue
            relative_file = file.relative_to(dist_dir)
            if is_cli_temporary_dist_artifact(relative_file):
                continue
            identity = get_copy_source_identity(file, resolved_dist_dir)
            if identity is None:
                raise click.ClickException(
                    f"Refusing to bundle {file}: resolved path is outside "
                    f"the dist directory {resolved_dist_dir}."
                )
            resolved_file = file.resolve()
            if not resolved_file.is_relative_to(resolved_dist_dir):
                raise click.ClickException(
                    f"Refusing to bundle {file}: resolved path is outside "
                    f"the dist directory {resolved_dist_dir}."
                )
            if resolved_file == resolved_zip_path:
                continue
            bundle_entries.append((file, relative_file, identity))

        if get_directory_path_identity(zip_path.parent) != output_parent_identity:
            raise click.ClickException(
                f"Refusing to write bundle: parent directory changed: "
                f"{zip_path.parent}."
            )

        with tempfile.NamedTemporaryFile(
            delete=False,
            dir=zip_path.parent,
            prefix=f".{zip_path.name}.",
            suffix=".tmp",
        ) as temp_file:
            temp_path = Path(temp_file.name)
        temp_identity = get_read_path_identity(temp_path)
        if temp_identity is None:
            raise click.ClickException(
                "Refusing to write bundle: temporary archive path is unsafe."
            )

        with zipfile.ZipFile(temp_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for file, arcname, identity in bundle_entries:
                ensure_copy_source_unchanged(
                    file,
                    resolved_dist_dir,
                    identity,
                    f"bundle entry {arcname}",
                )
                zipf.write(file, arcname)

        verify_bundle_archive_contents(temp_path, bundle_entries, resolved_dist_dir)
        current_temp_identity = get_read_path_identity(temp_path)
        if (
            current_temp_identity is None
            or current_temp_identity[:2] != temp_identity[:2]
        ):
            raise click.ClickException(
                "Refusing to publish bundle: temporary archive path changed."
            )
        temp_identity = current_temp_identity
        validate_bundle_output_path(zip_path)
        publish_output_file(temp_path, zip_path, "bundle", temp_identity)
        temp_path = None
    except Exception as ex:
        if temp_path is not None and temp_identity is not None:
            try:
                remove_output_file(
                    temp_path,
                    "temporary bundle",
                    temp_identity,
                    allow_content_changes=True,
                )
            except click.ClickException:
                pass
        click.secho(f"❌ Failed to create bundle: {ex}", err=True, fg="red")
        sys.exit(1)

    click.secho(f"✅ Bundle created: {zip_path}", fg="green")


@app.command()
@click.pass_context
def dev(ctx: click.Context) -> None:
    """Automatically rebuild the extension as files change."""
    ctx.invoke(validate)

    cwd = Path.cwd()
    frontend_dir = cwd / "frontend"
    backend_dir = cwd / "backend"

    clean_dist(cwd)

    # Build frontend if it exists
    remote_entry = None
    if optional_directory_exists(frontend_dir, "frontend"):
        init_frontend_deps(frontend_dir)
        remote_entry = rebuild_frontend(cwd, frontend_dir)
        if remote_entry is None:
            click.secho(
                "❌ Frontend build failed; aborting watch mode.",
                err=True,
                fg="red",
            )
            sys.exit(1)

    # Build backend if it exists
    if optional_directory_exists(backend_dir, "backend"):
        rebuild_backend(cwd)

    manifest = build_manifest(cwd, remote_entry)
    write_manifest(cwd, manifest)

    def frontend_watcher() -> None:
        if optional_directory_exists(frontend_dir, "frontend"):
            if (remote_entry := rebuild_frontend(cwd, frontend_dir)) is not None:
                manifest = build_manifest(cwd, remote_entry)
                write_manifest(cwd, manifest)

    def backend_watcher() -> None:
        if optional_directory_exists(backend_dir, "backend"):
            rebuild_backend(cwd)

    # Build watch message based on existing directories
    watch_targets: list[tuple[str, Path, tuple[int, int, int, int]]] = []
    for label, directory in (("frontend", frontend_dir), ("backend", backend_dir)):
        if optional_directory_exists(directory, label):
            directory_identity = get_directory_path_identity(directory)
            if directory_identity is None:
                raise click.ClickException(f"{label} path is no longer safe.")
            watch_targets.append((label, directory, directory_identity))
    watch_dirs = [str(directory) for _, directory, _ in watch_targets]

    if watch_dirs:
        click.secho(f"👀 Watching for changes in: {', '.join(watch_dirs)}", fg="green")
    else:
        click.secho("⚠️  No frontend or backend directories found to watch", fg="yellow")

    observer = Observer()

    # Only set up watchers for directories that exist
    for label, directory, directory_identity in watch_targets:
        current_identity = get_directory_path_identity(directory)
        if current_identity != directory_identity:
            raise click.ClickException(f"{label} path changed before watch setup.")
        if label == "frontend":
            frontend_handler = FrontendChangeHandler(trigger_build=frontend_watcher)
            observer.schedule(frontend_handler, str(directory), recursive=True)
        else:
            backend_handler = FileSystemEventHandler()
            backend_handler.on_any_event = lambda event: backend_watcher()
            observer.schedule(backend_handler, str(directory), recursive=True)

    if watch_dirs:
        observer.start()

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            click.secho("\n🛑 Stopping watch mode", fg="blue")
            observer.stop()

        observer.join()
    else:
        click.secho("❌ No directories to watch. Exiting.", fg="red")


def prompt_for_extension_info(
    display_name_opt: str | None,
    publisher_opt: str | None,
    technical_name_opt: str | None,
) -> ExtensionNames:
    """
    Prompt for extension info with graceful validation and re-prompting.

    Args:
        display_name_opt: Display name provided via CLI option (if any)
        publisher_opt: Publisher provided via CLI option (if any)
        technical_name_opt: Technical name provided via CLI option (if any)

    Returns:
        ExtensionNames: Validated extension name variants
    """

    # Step 1: Get display name
    if display_name_opt:
        display_name = display_name_opt
        try:
            display_name = validate_display_name(display_name)
        except ExtensionNameError as e:
            click.secho(f"❌ {e}", fg="red")
            sys.exit(1)
    else:
        while True:
            display_name = click.prompt("Extension display name", type=str)
            try:
                display_name = validate_display_name(display_name)
                break
            except ExtensionNameError as e:
                click.secho(f"❌ {e}", fg="red")

    # Step 2: Get technical name (with suggestion from display name)
    if technical_name_opt:
        technical_name = technical_name_opt
        try:
            validate_technical_name(technical_name)
        except ExtensionNameError as e:
            click.secho(f"❌ {e}", fg="red")
            sys.exit(1)
    else:
        # Suggest technical name from display name
        try:
            suggested_technical = suggest_technical_name(display_name)
        except ExtensionNameError:
            suggested_technical = "extension"

        while True:
            technical_name = click.prompt(
                f"Extension name ({suggested_technical})",
                default=suggested_technical,
                type=str,
            )
            try:
                validate_technical_name(technical_name)
                break
            except ExtensionNameError as e:
                click.secho(f"❌ {e}", fg="red")

    # Step 3: Get publisher
    if publisher_opt:
        publisher = publisher_opt
        try:
            validate_publisher(publisher)
        except ExtensionNameError as e:
            click.secho(f"❌ {e}", fg="red")
            sys.exit(1)
    else:
        while True:
            publisher = click.prompt("Publisher (e.g., my-org)", type=str)
            try:
                validate_publisher(publisher)
                break
            except ExtensionNameError as e:
                click.secho(f"❌ {e}", fg="red")

    # Generate all name variants
    try:
        return generate_extension_names(display_name, publisher, technical_name)
    except ExtensionNameError as e:
        click.secho(f"❌ {e}", fg="red")
        sys.exit(1)


@app.command()
@click.option(
    "--publisher",
    "publisher_opt",
    default=None,
    help="Publisher namespace (kebab-case, e.g. my-org)",
)
@click.option(
    "--name",
    "name_opt",
    default=None,
    help="Technical extension name (kebab-case, e.g. dashboard-widgets)",
)
@click.option(
    "--display-name",
    "display_name_opt",
    default=None,
    help="Extension display name (e.g. Dashboard Widgets)",
)
@click.option(
    "--version", "version_opt", default=None, help="Initial version (default: 0.1.0)"
)
@click.option(
    "--license", "license_opt", default=None, help="License (default: Apache-2.0)"
)
@click.option(
    "--frontend/--no-frontend", "frontend_opt", default=None, help="Include frontend"
)
@click.option(
    "--backend/--no-backend", "backend_opt", default=None, help="Include backend"
)
def init(
    publisher_opt: str | None,
    name_opt: str | None,
    display_name_opt: str | None,
    version_opt: str | None,
    license_opt: str | None,
    frontend_opt: bool | None,
    backend_opt: bool | None,
) -> None:
    """Scaffold a new extension project."""
    # Get extension names with graceful validation
    names = prompt_for_extension_info(display_name_opt, publisher_opt, name_opt)

    version = version_opt or click.prompt("Initial version", default="0.1.0")
    license_ = license_opt or click.prompt("License", default="Apache-2.0")
    include_frontend = (
        frontend_opt
        if frontend_opt is not None
        else click.confirm("Include frontend?", default=True)
    )
    include_backend = (
        backend_opt
        if backend_opt is not None
        else click.confirm("Include backend?", default=True)
    )

    try:
        validate_initial_extension_config(names, version, license_)
    except click.ClickException as ex:
        click.secho(f"❌ {ex.message}", err=True, fg="red")
        sys.exit(1)

    target_dir = Path.cwd() / names["name"]
    if target_dir.exists() or target_dir.is_symlink():
        click.secho(f"❌ Directory {target_dir} already exists.", fg="red")
        sys.exit(1)

    # Set up Jinja environment
    templates_dir = Path(__file__).parent / "templates"
    env = Environment(loader=FileSystemLoader(templates_dir))  # noqa: S701
    ctx = {
        **names,  # Include all name variants
        "include_frontend": include_frontend,
        "include_backend": include_backend,
        "license": license_,
        "version": version,
    }

    created_target_dir = False
    target_dir_identity: tuple[int, int, int, int] | None = None
    expected_scaffold_entries: dict[Path, set[str]] = {}
    expected_scaffold_identities: dict[Path, tuple[int, int, int, int]] = {}

    def refresh_target_dir_identity() -> None:
        nonlocal target_dir_identity
        target_dir_identity = get_directory_path_identity(target_dir)
        if target_dir_identity is None:
            raise click.ClickException(
                "Refusing to create extension directory: path changed."
            )

    def track_scaffold_directory(path: Path) -> None:
        expected_scaffold_entries.setdefault(path, set())
        directory_identity = get_directory_path_identity(path)
        if directory_identity is None:
            raise click.ClickException(
                "Refusing to create extension directory: path changed."
            )
        expected_scaffold_identities[path] = directory_identity
        if path != target_dir:
            expected_scaffold_entries.setdefault(path.parent, set()).add(path.name)

    def track_scaffold_file(path: Path) -> None:
        expected_scaffold_entries.setdefault(path.parent, set()).add(path.name)

    def ensure_target_entries_unchanged() -> None:
        if (
            not target_dir.exists()
            or target_dir.is_symlink()
            or not target_dir.is_dir()
        ):
            return
        for directory, expected_entries in expected_scaffold_entries.items():
            if not directory.is_dir() or directory.is_symlink():
                raise click.ClickException(
                    "Refusing to clean extension directory: path changed."
                )
            directory_identity = get_directory_path_identity(directory)
            expected_identity = expected_scaffold_identities.get(directory)
            if (
                directory_identity is None
                or expected_identity is None
                or directory_identity[:2] != expected_identity[:2]
            ):
                raise click.ClickException(
                    "Refusing to clean extension directory: path changed."
                )
            current_entries = {entry.name for entry in directory.iterdir()}
            if current_entries != expected_entries:
                raise click.ClickException(
                    "Refusing to clean extension directory: path changed."
                )

    try:
        # Create base directory
        create_scaffold_directory(target_dir, "extension directory")
        created_target_dir = True
        track_scaffold_directory(target_dir)
        refresh_target_dir_identity()
        extension_json = env.get_template("extension.json.j2").render(ctx)
        write_scaffold_file(
            target_dir / "extension.json",
            "extension.json",
            extension_json,
        )
        track_scaffold_file(target_dir / "extension.json")
        refresh_target_dir_identity()
        click.secho("✅ Created extension.json", fg="green")

        # Create .gitignore
        gitignore = env.get_template("gitignore.j2").render(ctx)
        write_scaffold_file(target_dir / ".gitignore", ".gitignore", gitignore)
        track_scaffold_file(target_dir / ".gitignore")
        refresh_target_dir_identity()
        click.secho("✅ Created .gitignore", fg="green")

        # Initialize frontend files
        if include_frontend:
            frontend_dir = target_dir / "frontend"
            create_scaffold_directory(frontend_dir, "frontend directory")
            track_scaffold_directory(frontend_dir)
            refresh_target_dir_identity()
            frontend_src_dir = frontend_dir / "src"
            create_scaffold_directory(frontend_src_dir, "frontend src directory")
            track_scaffold_directory(frontend_src_dir)

            # frontend files
            package_json = env.get_template("frontend/package.json.j2").render(ctx)
            write_scaffold_file(
                frontend_dir / "package.json",
                "frontend/package.json",
                package_json,
            )
            track_scaffold_file(frontend_dir / "package.json")
            webpack_config = env.get_template("frontend/webpack.config.js.j2").render(
                ctx
            )
            write_scaffold_file(
                frontend_dir / "webpack.config.js",
                "frontend/webpack.config.js",
                webpack_config,
            )
            track_scaffold_file(frontend_dir / "webpack.config.js")
            tsconfig_json = env.get_template("frontend/tsconfig.json.j2").render(ctx)
            write_scaffold_file(
                frontend_dir / "tsconfig.json",
                "frontend/tsconfig.json",
                tsconfig_json,
            )
            track_scaffold_file(frontend_dir / "tsconfig.json")
            index_tsx = env.get_template("frontend/src/index.tsx.j2").render(ctx)
            write_scaffold_file(
                frontend_src_dir / "index.tsx",
                "frontend/src/index.tsx",
                index_tsx,
            )
            track_scaffold_file(frontend_src_dir / "index.tsx")
            click.secho("✅ Created frontend folder structure", fg="green")

        # Initialize backend files with publisher.name structure
        if include_backend:
            backend_dir = target_dir / "backend"
            create_scaffold_directory(backend_dir, "backend directory")
            track_scaffold_directory(backend_dir)
            refresh_target_dir_identity()
            backend_src_dir = backend_dir / "src"
            create_scaffold_directory(backend_src_dir, "backend src directory")
            track_scaffold_directory(backend_src_dir)

            # Create publisher directory (e.g., my_org)
            publisher_snake = kebab_to_snake_case(names["publisher"])
            publisher_dir = backend_src_dir / publisher_snake
            create_scaffold_directory(publisher_dir, "backend publisher directory")
            track_scaffold_directory(publisher_dir)

            # Create extension package directory (e.g., my_org/dashboard_widgets)
            name_snake = kebab_to_snake_case(names["name"])
            extension_package_dir = publisher_dir / name_snake
            create_scaffold_directory(
                extension_package_dir,
                "backend extension package directory",
            )
            track_scaffold_directory(extension_package_dir)

            # backend files
            pyproject_toml = env.get_template("backend/pyproject.toml.j2").render(ctx)
            write_scaffold_file(
                backend_dir / "pyproject.toml",
                "backend/pyproject.toml",
                pyproject_toml,
            )
            track_scaffold_file(backend_dir / "pyproject.toml")

            # Extension package files
            entrypoint_py = env.get_template(
                "backend/src/package/entrypoint.py.j2"
            ).render(ctx)
            write_scaffold_file(
                extension_package_dir / "entrypoint.py",
                "backend entrypoint.py",
                entrypoint_py,
            )
            track_scaffold_file(extension_package_dir / "entrypoint.py")

            click.secho("✅ Created backend folder structure", fg="green")
    except click.ClickException as ex:
        if created_target_dir:
            try:
                ensure_target_entries_unchanged()
                cleanup_scaffold_directory(
                    target_dir,
                    "extension directory",
                    target_dir_identity,
                )
            except click.ClickException as cleanup_ex:
                click.secho(f"❌ {cleanup_ex.message}", err=True, fg="red")
        click.secho(f"❌ {ex.message}", err=True, fg="red")
        sys.exit(1)

    click.secho(
        f"🎉 Extension {names['display_name']} (ID: {names['id']}) initialized at {target_dir}",
        fg="cyan",
    )


if __name__ == "__main__":
    app()

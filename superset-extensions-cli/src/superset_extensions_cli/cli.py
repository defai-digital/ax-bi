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

import re
import shutil
import subprocess
import sys
import time
import zipfile
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
    kebab_to_snake_case,
    read_json,
    read_toml,
    suggest_technical_name,
    validate_display_name,
    validate_publisher,
    validate_technical_name,
    write_json,
    write_toml,
)

REMOTE_ENTRY_REGEX = re.compile(r"^remoteEntry\..+\.js$")


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


def validate_npm() -> None:
    """Abort if `npm` is not on PATH."""
    if shutil.which("npm") is None:
        click.secho(
            "❌ npm is not installed or not on your PATH.",
            err=True,
            fg="red",
        )
        sys.exit(1)

    try:
        result = subprocess.run(  # noqa: S603
            ["npm", "-v"],  # noqa: S607
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

    except OSError as ex:
        click.secho(
            f"❌ Failed to run `npm -v`: {ex}",
            err=True,
            fg="red",
        )
        sys.exit(1)


def init_frontend_deps(frontend_dir: Path) -> None:
    """
    If node_modules is missing under `frontend_dir`, run `npm ci` if package-lock.json
    exists, otherwise run `npm i`.
    """
    node_modules = frontend_dir / "node_modules"
    if node_modules.is_symlink():
        raise click.ClickException("frontend/node_modules path is a symlink.")
    if node_modules.exists() and not node_modules.is_dir():
        raise click.ClickException(
            "frontend/node_modules path exists but is not a directory."
        )

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

        validate_npm()
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


def ensure_output_directory(path: Path, label: str) -> None:
    """Create an output directory after validating the path is safe to write."""
    if path.is_symlink():
        raise click.ClickException(f"Refusing to write {label}: path is a symlink.")
    if path.exists() and not path.is_dir():
        raise click.ClickException(
            f"Refusing to write {label}: path exists but is not a directory."
        )

    symlinked_parent = next(
        (parent for parent in path.parents if parent.exists() and parent.is_symlink()),
        None,
    )
    if symlinked_parent is not None:
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

    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError as ex:
        raise click.ClickException(f"Failed to create {label}: {ex}") from ex


def ensure_output_file_parent(path: Path, root: Path, label: str) -> None:
    """Create an output file parent after validating existing ancestors."""
    if not path.is_relative_to(root):
        raise click.ClickException(
            f"Refusing to write {label}: path is outside {root}."
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

    try:
        parent.mkdir(parents=True, exist_ok=True)
    except OSError as ex:
        raise click.ClickException(f"Failed to create parent for {label}: {ex}") from ex


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
    if path.parent.exists() and not path.parent.is_dir():
        raise click.ClickException(
            f"Refusing to write {label}: parent exists but is not a directory: "
            f"{path.parent}."
        )


def clean_dist_frontend(cwd: Path) -> None:
    frontend_dist = cwd / "dist" / "frontend"
    remove_output_directory(frontend_dist, "dist/frontend directory")


def remove_output_directory(path: Path, label: str) -> None:
    """Remove an output directory after validating the path is safe to clean."""
    if path.is_symlink():
        raise click.ClickException(f"Refusing to clean {label}: path is a symlink.")
    if not path.exists():
        return
    if not path.is_dir():
        raise click.ClickException(
            f"Refusing to clean {label}: path exists but is not a directory."
        )
    try:
        shutil.rmtree(path)
    except OSError as ex:
        raise click.ClickException(f"Failed to clean {label}: {ex}") from ex


def load_json_object(path: Path, label: str) -> dict[str, Any] | None:
    """Load an optional JSON metadata file and require an object when present."""
    try:
        if not input_file_exists(path, label):
            return None
        data = read_json(path)
    except click.ClickException:
        raise
    except Exception as ex:
        raise click.ClickException(f"Invalid {label}: {ex}") from ex

    if data is not None and not isinstance(data, dict):
        raise click.ClickException(f"Invalid {label}: expected a JSON object.")

    return data


def load_toml_object(path: Path, label: str) -> dict[str, Any] | None:
    """Load an optional TOML metadata file and wrap parser errors for the CLI."""
    try:
        if not input_file_exists(path, label):
            return None
        return read_toml(path)
    except click.ClickException:
        raise
    except Exception as ex:
        raise click.ClickException(f"Invalid {label}: {ex}") from ex


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


def require_optional_directory(path: Path, label: str) -> None:
    """Require an optional project path to be a directory when present."""
    if path.is_symlink():
        raise click.ClickException(f"{label} path is a symlink.")
    if (path.exists() or path.is_symlink()) and not path.is_dir():
        raise click.ClickException(f"{label} path exists but is not a directory.")


def optional_directory_exists(path: Path, label: str) -> bool:
    """Return whether an optional project directory exists after validation."""
    require_optional_directory(path, label)
    return path.exists()


def optional_file_exists(path: Path, label: str) -> bool:
    """Return whether an optional project file exists after validation."""
    if path.is_symlink():
        raise click.ClickException(f"{label} path is a symlink.")
    if path.exists() and not path.is_file():
        raise click.ClickException(f"{label} path exists but is not a file.")
    return path.exists()


def input_file_exists(path: Path, label: str) -> bool:
    """Return whether an input file exists after validating it is safe to read."""
    if path.is_symlink():
        raise click.ClickException(f"Refusing to read {label}: path is a symlink.")
    if path.exists() and not path.is_file():
        raise click.ClickException(f"Invalid {label}: path exists but is not a file.")
    return path.exists()


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
    manifest_path.write_text(
        manifest.model_dump_json(indent=2, exclude_none=True, by_alias=True)
    )
    click.secho("✅ Manifest updated", fg="green")


def run_frontend_build(frontend_dir: Path) -> subprocess.CompletedProcess[str]:
    click.echo()
    click.secho("⚙️  Building frontend assets…", fg="cyan")
    command = ["npm", "run", "build"]
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
    frontend_files: list[Path] = []
    remote_entries: list[str] = []

    for f in sorted(frontend_dist.rglob("*")):
        if not f.is_file():
            continue
        resolved = f.resolve()
        if not resolved.is_relative_to(frontend_dist):
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
        frontend_files.append(f)

    if not remote_entries:
        click.secho("❌ No remote entry file found.", err=True, fg="red")
        sys.exit(1)
    if len(remote_entries) > 1:
        raise click.ClickException(
            f"Multiple remote entry files found: {', '.join(sorted(remote_entries))}."
        )

    ensure_output_directory(dist_dir, "dist directory")
    ensure_output_directory(frontend_output_dir, "dist/frontend directory")
    ensure_output_directory(frontend_dist_output_dir, "dist/frontend/dist directory")

    copy_targets = [
        (f, frontend_dist_output_dir / f.relative_to(frontend_dist))
        for f in frontend_files
    ]
    for _, tgt in copy_targets:
        ensure_output_file_parent(
            tgt,
            frontend_dist_output_dir,
            f"frontend asset {tgt.relative_to(frontend_dist_output_dir)}",
        )

    for f, tgt in copy_targets:
        shutil.copy2(f, tgt)

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

    ensure_output_directory(dist_dir, "dist directory")
    ensure_output_directory(backend_output_dir, "dist/backend directory")

    # Read build config from pyproject.toml
    pyproject_path = backend_dir / "pyproject.toml"
    if not input_file_exists(pyproject_path, "backend/pyproject.toml"):
        raise click.ClickException("backend pyproject.toml not found.")
    pyproject = load_toml_object(pyproject_path, "backend pyproject.toml")
    if pyproject is None:
        raise click.ClickException("backend pyproject.toml not found.")
    include_patterns, exclude_patterns = get_backend_build_patterns(pyproject)

    copy_targets: list[tuple[Path, Path]] = []

    # Process include patterns
    for pattern in include_patterns:
        for f in backend_dir.glob(pattern):
            if not f.is_file():
                continue

            # Defense in depth: confirm the matched file resolves to a location
            # inside the backend directory before copying it into the bundle.
            resolved = f.resolve()
            if not resolved.is_relative_to(backend_dir):
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

            copy_targets.append((f, backend_output_dir / relative_path))

    for _, tgt in copy_targets:
        ensure_output_file_parent(
            tgt,
            backend_output_dir,
            f"backend file {tgt.relative_to(backend_output_dir)}",
        )

    for f, tgt in copy_targets:
        shutil.copy2(f, tgt)


def rebuild_frontend(cwd: Path, frontend_dir: Path) -> str | None:
    """Clean and rebuild frontend, return the remoteEntry filename."""
    clean_dist_frontend(cwd)

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
    if path.parent.exists() and not path.parent.is_dir():
        raise click.ClickException(
            f"Refusing to write bundle: parent exists but is not a directory: "
            f"{path.parent}."
        )


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
        require_optional_directory(backend_dir, "backend")
    except click.ClickException as ex:
        click.secho(f"❌ {ex.message}", err=True, fg="red")
        sys.exit(1)
    if backend_dir.exists():
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

        if expected_entry_file.is_symlink():
            click.secho(
                f"❌ Backend entry point path is a symlink: {expected_entry_file.relative_to(cwd)}",
                err=True,
                fg="red",
            )
            sys.exit(1)
        if not expected_entry_file.is_file():
            click.secho(
                f"❌ Backend entry point not found at expected location: {expected_entry_file.relative_to(cwd)}",
                err=True,
                fg="red",
            )
            click.secho(
                f"   Convention requires: backend/src/{publisher_snake}/{name_snake}/entrypoint.py",
                fg="yellow",
            )
            sys.exit(1)

    # Validate conventional frontend entry point if frontend directory exists
    frontend_dir = cwd / "frontend"
    try:
        require_optional_directory(frontend_dir, "frontend")
    except click.ClickException as ex:
        click.secho(f"❌ {ex.message}", err=True, fg="red")
        sys.exit(1)
    if frontend_dir.exists():
        expected_frontend_entry = frontend_dir / "src" / "index.tsx"
        if expected_frontend_entry.is_symlink():
            click.secho(
                f"❌ Frontend entry point path is a symlink: {expected_frontend_entry.relative_to(cwd)}",
                err=True,
                fg="red",
            )
            sys.exit(1)
        if not expected_frontend_entry.is_file():
            click.secho(
                f"❌ Frontend entry point not found at expected location: {expected_frontend_entry.relative_to(cwd)}",
                err=True,
                fg="red",
            )
            click.secho("   Convention requires: frontend/src/index.tsx", fg="yellow")
            sys.exit(1)

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
        require_optional_directory(frontend_dir, "frontend")
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
        require_optional_directory(backend_dir, "backend")
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

    for path, label, data in pending_json_writes:
        write_json(path, data)
        updated.append(label)

    for path, label, data in pending_toml_writes:
        write_toml(path, data)
        updated.append(label)

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

    clean_dist(cwd)

    # Build frontend if it exists
    remote_entry = None
    if optional_directory_exists(frontend_dir, "frontend"):
        init_frontend_deps(frontend_dir)
        remote_entry = rebuild_frontend(cwd, frontend_dir)

    # Build backend independently if it exists
    if optional_directory_exists(backend_dir, "backend"):
        pyproject = load_toml_object(
            backend_dir / "pyproject.toml", "backend pyproject.toml"
        )
        if pyproject:
            rebuild_backend(cwd)

    # Build manifest and write it
    manifest = build_manifest(cwd, remote_entry)
    write_manifest(cwd, manifest)

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
        has_manifest = input_file_exists(manifest_path, "dist/manifest.json")
    except click.ClickException as ex:
        click.secho(f"❌ {ex.message}", err=True, fg="red")
        sys.exit(1)

    if not has_manifest:
        click.secho(
            "❌ dist/manifest.json not found. Run `build` first.", err=True, fg="red"
        )
        sys.exit(1)

    try:
        manifest = Manifest.model_validate_json(manifest_path.read_text())
    except Exception as ex:
        click.secho(f"❌ Invalid dist/manifest.json: {ex}", err=True, fg="red")
        sys.exit(1)

    default_filename = f"{manifest.name}-{manifest.version}.supx"

    if output is None:
        zip_path = Path(default_filename)
    elif output.is_dir():
        zip_path = output / default_filename
    else:
        zip_path = output

    try:
        resolved_dist_dir = dist_dir.resolve()
        resolved_zip_path = zip_path.resolve()
        validate_bundle_output_path(zip_path)
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for file in dist_dir.rglob("*"):
                if not file.is_file():
                    continue
                resolved_file = file.resolve()
                if resolved_file == resolved_zip_path:
                    continue
                if not resolved_file.is_relative_to(resolved_dist_dir):
                    raise click.ClickException(
                        f"Refusing to bundle {file}: resolved path is outside "
                        f"the dist directory {resolved_dist_dir}."
                    )
                arcname = file.relative_to(dist_dir)
                zipf.write(file, arcname)
    except Exception as ex:
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
    watch_dirs = []
    if optional_directory_exists(frontend_dir, "frontend"):
        watch_dirs.append(str(frontend_dir))
    if optional_directory_exists(backend_dir, "backend"):
        watch_dirs.append(str(backend_dir))

    if watch_dirs:
        click.secho(f"👀 Watching for changes in: {', '.join(watch_dirs)}", fg="green")
    else:
        click.secho("⚠️  No frontend or backend directories found to watch", fg="yellow")

    observer = Observer()

    # Only set up watchers for directories that exist
    if optional_directory_exists(frontend_dir, "frontend"):
        frontend_handler = FrontendChangeHandler(trigger_build=frontend_watcher)
        observer.schedule(frontend_handler, str(frontend_dir), recursive=True)

    if optional_directory_exists(backend_dir, "backend"):
        backend_handler = FileSystemEventHandler()
        backend_handler.on_any_event = lambda event: backend_watcher()
        observer.schedule(backend_handler, str(backend_dir), recursive=True)

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

    # Create base directory
    target_dir.mkdir()
    extension_json = env.get_template("extension.json.j2").render(ctx)
    (target_dir / "extension.json").write_text(extension_json)
    click.secho("✅ Created extension.json", fg="green")

    # Create .gitignore
    gitignore = env.get_template("gitignore.j2").render(ctx)
    (target_dir / ".gitignore").write_text(gitignore)
    click.secho("✅ Created .gitignore", fg="green")

    # Initialize frontend files
    if include_frontend:
        frontend_dir = target_dir / "frontend"
        frontend_dir.mkdir()
        frontend_src_dir = frontend_dir / "src"
        frontend_src_dir.mkdir()

        # frontend files
        package_json = env.get_template("frontend/package.json.j2").render(ctx)
        (frontend_dir / "package.json").write_text(package_json)
        webpack_config = env.get_template("frontend/webpack.config.js.j2").render(ctx)
        (frontend_dir / "webpack.config.js").write_text(webpack_config)
        tsconfig_json = env.get_template("frontend/tsconfig.json.j2").render(ctx)
        (frontend_dir / "tsconfig.json").write_text(tsconfig_json)
        index_tsx = env.get_template("frontend/src/index.tsx.j2").render(ctx)
        (frontend_src_dir / "index.tsx").write_text(index_tsx)
        click.secho("✅ Created frontend folder structure", fg="green")

    # Initialize backend files with publisher.name structure
    if include_backend:
        backend_dir = target_dir / "backend"
        backend_dir.mkdir()
        backend_src_dir = backend_dir / "src"
        backend_src_dir.mkdir()

        # Create publisher directory (e.g., my_org)
        publisher_snake = kebab_to_snake_case(names["publisher"])
        publisher_dir = backend_src_dir / publisher_snake
        publisher_dir.mkdir()

        # Create extension package directory (e.g., my_org/dashboard_widgets)
        name_snake = kebab_to_snake_case(names["name"])
        extension_package_dir = publisher_dir / name_snake
        extension_package_dir.mkdir()

        # backend files
        pyproject_toml = env.get_template("backend/pyproject.toml.j2").render(ctx)
        (backend_dir / "pyproject.toml").write_text(pyproject_toml)

        # Extension package files
        entrypoint_py = env.get_template("backend/src/package/entrypoint.py.j2").render(
            ctx
        )
        (extension_package_dir / "entrypoint.py").write_text(entrypoint_py)

        click.secho("✅ Created backend folder structure", fg="green")

    click.secho(
        f"🎉 Extension {names['display_name']} (ID: {names['id']}) initialized at {target_dir}",
        fg="cyan",
    )


if __name__ == "__main__":
    app()

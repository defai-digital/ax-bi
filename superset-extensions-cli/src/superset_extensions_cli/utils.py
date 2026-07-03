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

import json  # noqa: TID251
import re
import sys
import tempfile
from pathlib import Path
from typing import Any

import tomli_w

from superset_core.extensions.constants import (
    DISPLAY_NAME_PATTERN,
    PUBLISHER_PATTERN,
    TECHNICAL_NAME_PATTERN,
)
from superset_extensions_cli.exceptions import ExtensionNameError
from superset_extensions_cli.types import ExtensionNames

PathIdentity = tuple[int, int, int, int]
NodeIdentity = tuple[int, int]

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

# Python reserved keywords to avoid in package names
PYTHON_KEYWORDS = {
    "and",
    "as",
    "assert",
    "break",
    "class",
    "continue",
    "def",
    "del",
    "elif",
    "else",
    "except",
    "exec",
    "finally",
    "for",
    "from",
    "global",
    "if",
    "import",
    "in",
    "is",
    "lambda",
    "not",
    "or",
    "pass",
    "print",
    "raise",
    "return",
    "try",
    "while",
    "with",
    "yield",
    "False",
    "None",
    "True",
}

# npm reserved names to avoid
NPM_RESERVED = {
    "node_modules",
    "favicon.ico",
    "www",
    "http",
    "https",
    "ftp",
    "localhost",
    "package.json",
    "npm",
    "yarn",
    "bower_components",
}

MAX_PUBLISHER_LENGTH = 64
MAX_TECHNICAL_NAME_LENGTH = 64
MAX_DISPLAY_NAME_LENGTH = 128

# Compiled patterns for publisher/name validation
PUBLISHER_REGEX = re.compile(PUBLISHER_PATTERN)
TECHNICAL_NAME_REGEX = re.compile(TECHNICAL_NAME_PATTERN)
DISPLAY_NAME_REGEX = re.compile(DISPLAY_NAME_PATTERN)


def validate_read_path(path: Path) -> Path | None:
    """Return a normalized input path unless it crosses a symlink boundary."""
    path = Path(path)
    if not path.is_file() or find_symlinked_path_or_parent(path) is not None:
        return None
    return path


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


def find_symlinked_path_or_parent(path: Path) -> Path | None:
    """Return a symlinked path or the first symlinked parent directory."""
    if path.is_symlink():
        return path
    return find_symlinked_parent(path)


def find_non_directory_parent(path: Path) -> Path | None:
    """Return the first existing parent path that is not a directory."""
    return next(
        (
            parent
            for parent in (path.parent, *path.parent.parents)
            if parent.exists() and not parent.is_dir()
        ),
        None,
    )


def find_non_directory_path_or_parent(path: Path) -> Path | None:
    """Return a non-directory path or the first non-directory parent."""
    if path.exists() and not path.is_dir():
        return path
    return find_non_directory_parent(path)


def get_read_path_identity(path: Path) -> PathIdentity | None:
    """Return file identity for a safe input path."""
    read_path = validate_read_path(path)
    if read_path is None:
        return None
    try:
        stat = read_path.stat()
    except OSError:
        return None
    return (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns)


def get_directory_path_identity(path: Path) -> PathIdentity | None:
    """Return directory identity unless the path crosses a symlink boundary."""
    if not path.is_dir() or find_symlinked_path_or_parent(path) is not None:
        return None
    try:
        stat = path.stat()
    except OSError:
        return None
    return (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns)


def get_directory_node_identity(path: Path) -> NodeIdentity | None:
    """Return stable directory node identity without content metadata."""
    identity = get_directory_path_identity(path)
    if identity is None:
        return None
    return identity[:2]


def _get_parent_directory_identity(path: Path) -> NodeIdentity | None:
    """Return parent identity unless it crosses a symlink boundary."""
    return get_directory_node_identity(Path(path).parent)


def get_read_parent_identity(path: Path) -> NodeIdentity | None:
    """Return read parent identity unless it crosses a symlink boundary."""
    return _get_parent_directory_identity(path)


def get_write_parent_identity(path: Path) -> NodeIdentity | None:
    """Return output parent identity unless it crosses a symlink boundary."""
    return _get_parent_directory_identity(path)


def read_toml(path: Path) -> dict[str, Any] | None:
    read_path = validate_read_path(path)
    if read_path is None:
        return None
    initial_identity = get_read_path_identity(path)
    if initial_identity is None:
        return None
    parent_identity = get_read_parent_identity(path)
    if parent_identity is None:
        return None

    try:
        with read_path.open("rb") as f:
            content = f.read()
    except OSError as ex:
        raise OSError(f"Failed to read TOML file {read_path}: {ex}") from ex

    if (
        get_read_parent_identity(path) != parent_identity
        or get_read_path_identity(path) != initial_identity
    ):
        return None
    return tomllib.loads(content.decode("utf-8"))


def read_json(path: Path) -> object | None:
    read_path = validate_read_path(path)
    if read_path is None:
        return None
    initial_identity = get_read_path_identity(path)
    if initial_identity is None:
        return None
    parent_identity = get_read_parent_identity(path)
    if parent_identity is None:
        return None

    try:
        content = read_path.read_text()
    except OSError as ex:
        raise OSError(f"Failed to read JSON file {read_path}: {ex}") from ex

    if (
        get_read_parent_identity(path) != parent_identity
        or get_read_path_identity(path) != initial_identity
    ):
        return None
    return json.loads(content)


def validate_write_path(path: Path) -> Path:
    """Return a normalized output path after rejecting symlink boundaries."""
    path = Path(path)
    if path.is_symlink():
        raise OSError(f"Refusing to write through symlink: {path}")
    if path.exists() and not path.is_file():
        raise OSError(f"Refusing to write non-file path: {path}")
    if (symlinked_parent := find_symlinked_parent(path)) is not None:
        raise OSError(
            f"Refusing to write through symlinked directory: {symlinked_parent}"
        )
    if (invalid_parent := find_non_directory_parent(path)) is not None:
        raise OSError(
            f"Refusing to write through non-directory parent: {invalid_parent}"
        )
    return path


def write_text_atomic(
    path: Path,
    content: str,
    *,
    expected_existing_identity: PathIdentity | None = None,
    require_missing: bool = False,
) -> None:
    """Write text via a same-directory temporary file before replacing the target."""
    path = validate_write_path(path)
    parent_identity = get_write_parent_identity(path)
    if parent_identity is None:
        raise OSError(f"Refusing to write through unsafe parent: {path.parent}")
    temp_path: Path | None = None
    temp_identity: PathIdentity | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            delete=False,
            dir=path.parent,
            encoding="utf-8",
            prefix=f".{path.name}.",
            suffix=".tmp",
        ) as temp_file:
            temp_path = Path(temp_file.name)
            temp_file.write(content)
        temp_identity = get_read_path_identity(temp_path)
        if temp_identity is None:
            raise OSError(f"Refusing to promote unsafe temporary file: {temp_path}")
        if get_write_parent_identity(path) != parent_identity:
            raise OSError(f"Refusing to promote through changed parent: {path.parent}")
        validate_write_path(path)
        if (
            expected_existing_identity is not None
            and get_read_path_identity(path) != expected_existing_identity
        ):
            raise OSError(f"Refusing to promote through changed target: {path}")
        if require_missing and (path.exists() or path.is_symlink()):
            raise OSError(f"Refusing to promote over existing target: {path}")
        if get_read_path_identity(temp_path) != temp_identity:
            raise OSError(f"Refusing to promote changed temporary file: {temp_path}")
        temp_path.replace(path)
        if get_write_parent_identity(path) != parent_identity:
            raise OSError(f"Refusing to promote through changed parent: {path.parent}")
        if get_read_path_identity(path) != temp_identity:
            raise OSError(f"Failed to verify promoted temporary file: {path}")
        temp_path = None
    except OSError:
        if temp_path is not None and temp_identity is not None:
            try:
                current_temp_identity = get_read_path_identity(temp_path)
                if (
                    current_temp_identity is not None
                    and current_temp_identity == temp_identity
                    and get_read_path_identity(temp_path) == current_temp_identity
                ):
                    temp_path.unlink()
            except OSError:
                pass
        raise


def write_json(
    path: Path,
    data: dict[str, Any],
    *,
    expected_existing_identity: PathIdentity | None = None,
) -> None:
    path = validate_write_path(path)
    try:
        write_text_atomic(
            path,
            json.dumps(data, indent=2) + "\n",
            expected_existing_identity=expected_existing_identity,
        )
    except OSError as ex:
        raise OSError(f"Failed to write JSON file {path}: {ex}") from ex


def write_toml(
    path: Path,
    data: dict[str, Any],
    *,
    expected_existing_identity: PathIdentity | None = None,
) -> None:
    path = validate_write_path(path)
    try:
        write_text_atomic(
            path,
            tomli_w.dumps(data),
            expected_existing_identity=expected_existing_identity,
        )
    except OSError as ex:
        raise OSError(f"Failed to write TOML file {path}: {ex}") from ex


def _normalize_for_identifiers(name: str) -> str:
    """
    Normalize display name to clean lowercase words.

    Args:
        name: Raw display name (e.g., "Hello World!")

    Returns:
        Normalized string (e.g., "hello world")
    """
    # Convert to lowercase
    normalized = name.lower().strip()

    # Convert underscores and existing hyphens to spaces for consistent processing
    normalized = normalized.replace("_", " ").replace("-", " ")

    # Remove any non-alphanumeric characters except spaces
    normalized = re.sub(r"[^a-z0-9\s]", "", normalized)

    # Normalize whitespace (collapse multiple spaces, strip)
    normalized = " ".join(normalized.split())

    return normalized


def _normalized_to_kebab(normalized: str) -> str:
    """Convert normalized string to kebab-case."""
    return normalized.replace(" ", "-")


def _normalized_to_snake(normalized: str) -> str:
    """Convert normalized string to snake_case."""
    return normalized.replace(" ", "_")


def _normalized_to_camel(normalized: str) -> str:
    """Convert normalized string to camelCase."""
    parts = normalized.split()
    if not parts:
        return ""
    # First part lowercase, subsequent parts capitalized
    return parts[0] + "".join(word.capitalize() for word in parts[1:])


def kebab_to_camel_case(kebab_name: str) -> str:
    """Convert kebab-case to camelCase (e.g., 'hello-world' -> 'helloWorld')."""
    parts = kebab_name.split("-")
    if not parts:
        return ""
    # First part lowercase, subsequent parts capitalized
    return parts[0] + "".join(word.capitalize() for word in parts[1:])


def kebab_to_snake_case(kebab_name: str) -> str:
    """Convert kebab-case to snake_case (e.g., 'hello-world' -> 'hello_world')."""
    return kebab_name.replace("-", "_")


def name_to_kebab_case(name: str) -> str:
    """Convert display name directly to kebab-case (e.g., 'Hello World' -> 'hello-world')."""
    normalized = _normalize_for_identifiers(name)
    return _normalized_to_kebab(normalized)


def validate_python_package_name(name: str) -> None:
    """
    Validate Python package name (snake_case format).

    Raises:
        ExtensionNameError: If name is invalid
    """
    if not name:
        raise ExtensionNameError("Package name cannot be empty")

    # Check if it starts with a number (invalid for Python identifiers)
    if name[0].isdigit():
        raise ExtensionNameError(f"Package name '{name}' cannot start with a number")

    # Check if the first part (before any underscore) is a Python keyword
    if (first_part := name.split("_")[0]) in PYTHON_KEYWORDS:
        raise ExtensionNameError(
            f"Package name cannot start with Python keyword '{first_part}'"
        )

    # Check if it's a valid Python identifier
    if not name.replace("_", "a").isalnum():
        raise ExtensionNameError(f"'{name}' is not a valid Python package name")


def validate_npm_package_name(name: str) -> None:
    """
    Validate npm package name (kebab-case format).

    Raises:
        ExtensionNameError: If name is invalid
    """
    if not name:
        raise ExtensionNameError("NPM package name cannot be empty")

    if name.lower() in NPM_RESERVED:
        raise ExtensionNameError(f"'{name}' is a reserved npm package name")


def validate_publisher(publisher: str) -> None:
    """
    Validate publisher namespace format.

    Args:
        publisher: Publisher namespace (e.g., 'my-org')

    Raises:
        ExtensionNameError: If publisher is invalid
    """
    if not publisher:
        raise ExtensionNameError("Publisher cannot be empty")

    if len(publisher) > MAX_PUBLISHER_LENGTH:
        raise ExtensionNameError(
            f"Publisher must be at most {MAX_PUBLISHER_LENGTH} characters"
        )

    if not PUBLISHER_REGEX.match(publisher):
        raise ExtensionNameError(
            "Publisher must start with a letter and contain only lowercase letters, numbers, and hyphens (e.g., 'my-org')"
        )


def validate_technical_name(name: str) -> None:
    """
    Validate technical extension name format.

    Args:
        name: Technical extension name (e.g., 'dashboard-widgets')

    Raises:
        ExtensionNameError: If name is invalid
    """
    if not name:
        raise ExtensionNameError("Extension name cannot be empty")

    if len(name) > MAX_TECHNICAL_NAME_LENGTH:
        raise ExtensionNameError(
            f"Extension name must be at most {MAX_TECHNICAL_NAME_LENGTH} characters"
        )

    if not TECHNICAL_NAME_REGEX.match(name):
        raise ExtensionNameError(
            "Extension name must start with a letter and contain only lowercase letters, numbers, and hyphens (e.g., 'dashboard-widgets')"
        )


def validate_display_name(display_name: str) -> str:
    """
    Validate and normalize display name format.

    Args:
        display_name: Human-readable extension name

    Returns:
        Cleaned display name

    Raises:
        ExtensionNameError: If display name is invalid
    """
    if not display_name or not display_name.strip():
        raise ExtensionNameError("Display name cannot be empty")

    # Normalize whitespace: strip and collapse multiple spaces
    normalized = " ".join(display_name.strip().split())

    if len(normalized) > MAX_DISPLAY_NAME_LENGTH:
        raise ExtensionNameError(
            f"Display name must be at most {MAX_DISPLAY_NAME_LENGTH} characters"
        )

    if not DISPLAY_NAME_REGEX.match(normalized):
        raise ExtensionNameError(
            "Display name must start with a letter and can contain letters, numbers, spaces, hyphens, underscores, and dots (e.g., 'Dashboard Widgets')"
        )

    # Check for only whitespace/special chars after normalization
    if not any(c.isalnum() for c in normalized):
        raise ExtensionNameError(
            "Display name must contain at least one letter or number"
        )

    return normalized


def suggest_technical_name(display_name: str) -> str:
    """
    Suggest technical name from display name.

    Args:
        display_name: Human-readable name (e.g., "Dashboard Widgets!")

    Returns:
        Technical name suggestion (e.g., "dashboard-widgets")
    """
    # Normalize for identifiers
    normalized = _normalize_for_identifiers(display_name)

    # Convert to kebab-case
    technical_name = _normalized_to_kebab(normalized)

    # Remove any leading/trailing hyphens that might result from edge cases
    technical_name = technical_name.strip("-")

    # Ensure we have something left
    if not technical_name:
        raise ExtensionNameError(
            "Display name must contain at least one letter or number"
        )

    return technical_name


def get_module_federation_name(publisher: str, name: str) -> str:
    """
    Generate Module Federation container name.

    Args:
        publisher: Publisher namespace (e.g., 'my-org')
        name: Technical name (e.g., 'dashboard-widgets')

    Returns:
        Module Federation name (e.g., 'myOrg_dashboardWidgets')
    """
    publisher_camel = kebab_to_camel_case(publisher)
    name_camel = kebab_to_camel_case(name)
    return f"{publisher_camel}_{name_camel}"


def generate_extension_names(
    display_name: str, publisher: str, technical_name: str | None = None
) -> ExtensionNames:
    """
    Generate all extension name variants from input.

    Args:
        display_name: Human-readable name (e.g., "Dashboard Widgets")
        publisher: Publisher namespace (e.g., "my-org")
        technical_name: Technical name override, or None to auto-generate

    Returns:
        ExtensionNames: Dictionary with all name variants

    Raises:
        ExtensionNameError: If any name is invalid
    """
    # Validate and normalize inputs
    display_name = validate_display_name(display_name)
    validate_publisher(publisher)

    # Use provided technical name or generate from display name
    if technical_name is None:
        technical_name = suggest_technical_name(display_name)
    validate_technical_name(technical_name)

    # Generate composite ID
    composite_id = f"{publisher}.{technical_name}"

    # Generate NPM package name
    npm_name = f"@{publisher}/{technical_name}"

    # Generate Module Federation name
    mf_name = get_module_federation_name(publisher, technical_name)

    # Generate backend names with collision protection
    publisher_snake = kebab_to_snake_case(publisher)
    name_snake = kebab_to_snake_case(technical_name)
    backend_package = f"{publisher_snake}-{name_snake}"
    backend_path = f"{publisher_snake}.{name_snake}"
    backend_entry = f"{backend_path}.entrypoint"

    # Validate the generated names
    validate_python_package_name(publisher_snake)
    validate_python_package_name(name_snake)
    validate_npm_package_name(technical_name)

    return ExtensionNames(
        publisher=publisher,
        name=technical_name,
        display_name=display_name,
        id=composite_id,
        npm_name=npm_name,
        mf_name=mf_name,
        backend_package=backend_package,
        backend_path=backend_path,
        backend_entry=backend_entry,
    )

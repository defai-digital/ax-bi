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
"""Tests for examples/utils.py - YAML config loading and content assembly."""

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

import pandas as pd
import yaml


def _create_example_tree(base_dir: Path) -> Path:
    """Create a minimal example directory tree under base_dir/superset/examples/.

    Returns the 'superset' directory (what files("superset") would return).
    """
    superset_dir = base_dir / "superset"
    examples_dir = superset_dir / "examples"

    # _shared configs
    shared_dir = examples_dir / "_shared"
    shared_dir.mkdir(parents=True)
    (shared_dir / "database.yaml").write_text(
        "database_name: examples\n"
        "sqlalchemy_uri: __SQLALCHEMY_EXAMPLES_URI__\n"
        "uuid: a2dc77af-e654-49bb-b321-40f6b559a1ee\n"
        "version: '1.0.0'\n"
    )
    (shared_dir / "metadata.yaml").write_text(
        "version: '1.0.0'\ntimestamp: '2020-12-11T22:52:56.534241+00:00'\n"
    )

    # An example with dataset, dashboard, and chart
    example_dir = examples_dir / "test_example"
    example_dir.mkdir()
    (example_dir / "dataset.yaml").write_text(
        yaml.dump(
            {
                "table_name": "test_table",
                "schema": "main",
                "uuid": "14f48794-ebfa-4f60-a26a-582c49132f1b",
                "database_uuid": "a2dc77af-e654-49bb-b321-40f6b559a1ee",
                "version": "1.0.0",
            }
        )
    )
    (example_dir / "dashboard.yaml").write_text(
        yaml.dump(
            {
                "dashboard_title": "Test Dashboard",
                "uuid": "dddddddd-dddd-dddd-dddd-dddddddddddd",
                "version": "1.0.0",
            }
        )
    )
    charts_dir = example_dir / "charts"
    charts_dir.mkdir()
    (charts_dir / "test_chart.yaml").write_text(
        yaml.dump(
            {
                "slice_name": "Test Chart",
                "uuid": "cccccccc-cccc-cccc-cccc-cccccccccccc",
                "dataset_uuid": "14f48794-ebfa-4f60-a26a-582c49132f1b",
                "version": "1.0.0",
            }
        )
    )

    return superset_dir


def test_load_contents_builds_correct_import_structure():
    """load_contents() must produce the key structure ImportExamplesCommand expects.

    This tests the orchestration entry point: YAML files are discovered from
    the examples directory, the shared database config has its URI placeholder
    replaced, and the result has the correct key prefixes (databases/, datasets/,
    metadata.yaml).
    """
    from superset.examples.utils import load_contents

    with TemporaryDirectory() as tmpdir:
        superset_dir = _create_example_tree(Path(tmpdir))

        test_examples_uri = "sqlite:///path/to/examples.db"
        mock_app = MagicMock()
        mock_app.config = {"SQLALCHEMY_EXAMPLES_URI": test_examples_uri}

        with patch("superset.examples.utils.files", return_value=superset_dir):
            with patch("flask.current_app", mock_app):
                contents = load_contents()

        # Verify database config is present with placeholder replaced
        assert "databases/examples.yaml" in contents
        db_content = contents["databases/examples.yaml"]
        assert "__SQLALCHEMY_EXAMPLES_URI__" not in db_content
        assert test_examples_uri in db_content

        # Verify metadata is present
        assert "metadata.yaml" in contents

        # Verify dataset is discovered with correct key prefix
        assert "datasets/examples/test_example.yaml" in contents

        # Verify dashboard is discovered with correct key prefix
        assert "dashboards/test_example.yaml" in contents

        # Verify chart is discovered with correct key prefix
        assert "charts/test_example/test_chart.yaml" in contents

        # Verify schema normalization happened (main -> null)
        dataset_content = contents["datasets/examples/test_example.yaml"]
        assert "schema: main" not in dataset_content
        assert "schema: null" in dataset_content


def test_load_contents_resolves_data_file_uris():
    """data_file entries should point the importer at the bundled Parquet file."""
    from superset.examples.utils import load_contents

    with TemporaryDirectory() as tmpdir:
        superset_dir = _create_example_tree(Path(tmpdir))
        examples_dir = superset_dir / "examples"
        example_dir = examples_dir / "test_example"

        single_data = example_dir / "data.parquet"
        single_data.write_bytes(b"")
        single_config = yaml.safe_load((example_dir / "dataset.yaml").read_text())
        single_config["data_file"] = "data.parquet"
        (example_dir / "dataset.yaml").write_text(yaml.safe_dump(single_config))

        nested_dir = examples_dir / "multi_example"
        nested_data_dir = nested_dir / "data"
        nested_datasets_dir = nested_dir / "datasets"
        nested_data_dir.mkdir(parents=True)
        nested_datasets_dir.mkdir()
        nested_data = nested_data_dir / "nested_dataset.parquet"
        nested_data.write_bytes(b"")
        (nested_datasets_dir / "nested_dataset.yaml").write_text(
            yaml.safe_dump(
                {
                    "table_name": "nested_dataset",
                    "data_file": "nested_dataset.parquet",
                    "schema": None,
                    "uuid": "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee",
                    "database_uuid": "a2dc77af-e654-49bb-b321-40f6b559a1ee",
                    "version": "1.0.0",
                }
            )
        )

        mock_app = MagicMock()
        mock_app.config = {"SQLALCHEMY_EXAMPLES_URI": "sqlite:///examples.db"}

        with patch("superset.examples.utils.files", return_value=superset_dir):
            with patch("flask.current_app", mock_app):
                contents = load_contents()

        single_content = yaml.safe_load(contents["datasets/examples/test_example.yaml"])
        nested_content = yaml.safe_load(
            contents["datasets/examples/nested_dataset.yaml"]
        )

        assert single_content["data_file_uri"] == single_data.resolve().as_uri()
        assert nested_content["data_file_uri"] == nested_data.resolve().as_uri()


def _read_example_data_file(path: Path) -> pd.DataFrame:
    """Read a bundled example data file."""
    if path.suffix == ".parquet":
        return pd.read_parquet(path)
    if path.suffix == ".gz":
        return pd.read_csv(path, compression="gzip")
    if path.suffix == ".csv":
        return pd.read_csv(path)

    raise AssertionError(f"Unsupported data file type: {path}")


def test_bundled_data_file_varchar_columns_fit_default_length():
    """Bundled example data should not exceed default VARCHAR storage."""
    issues: list[str] = []

    for yaml_path in sorted(Path("superset/examples").glob("**/datasets/*.yaml")):
        config = yaml.safe_load(yaml_path.read_text())
        if not isinstance(config, dict) or not config.get("data_file"):
            continue

        data_path = yaml_path.parents[1] / "data" / config["data_file"]
        if not data_path.exists():
            data_path = yaml_path.parent / config["data_file"]

        assert data_path.exists(), f"Missing data file for {yaml_path}"
        df = _read_example_data_file(data_path)
        for column in config.get("columns", []):
            if not isinstance(column, dict):
                continue

            column_name = column.get("column_name")
            if not isinstance(column_name, str):
                continue

            column_type = str(column.get("type") or "").upper()
            if column_type != "VARCHAR" or column_name not in df.columns:
                continue

            series = df[column_name].dropna().astype(str)
            if series.empty:
                continue

            max_length = int(series.str.len().max())
            if max_length > 255:
                issues.append(f"{yaml_path}:{column_name} has max length {max_length}")

    assert issues == []


def test_load_contents_replaces_sqlalchemy_examples_uri_placeholder():
    """The __SQLALCHEMY_EXAMPLES_URI__ placeholder must be replaced with the real URI.

    If this placeholder is not replaced, the database import will fail with an
    invalid connection string, preventing all examples from loading.
    """
    from superset.examples.utils import _load_shared_configs

    with TemporaryDirectory() as tmpdir:
        superset_dir = _create_example_tree(Path(tmpdir))
        examples_root = Path("examples")

        test_uri = "postgresql://user:pass@host/db"
        mock_app = MagicMock()
        mock_app.config = {"SQLALCHEMY_EXAMPLES_URI": test_uri}

        with patch("superset.examples.utils.files", return_value=superset_dir):
            with patch("flask.current_app", mock_app):
                contents = _load_shared_configs(examples_root)

        assert "databases/examples.yaml" in contents
        assert test_uri in contents["databases/examples.yaml"]
        assert "__SQLALCHEMY_EXAMPLES_URI__" not in contents["databases/examples.yaml"]


@patch("superset.examples.utils.ImportExamplesCommand")
@patch("superset.examples.utils.load_contents")
def test_load_examples_from_configs_wires_command_correctly(
    mock_load_contents,
    mock_command_cls,
):
    """load_examples_from_configs() must construct ImportExamplesCommand
    with overwrite=True and thread force_data through.

    A wiring regression here would silently skip overwriting existing
    examples or ignore the force_data flag.
    """
    from superset.examples.utils import load_examples_from_configs

    mock_load_contents.return_value = {"databases/examples.yaml": "content"}
    mock_command = MagicMock()
    mock_command_cls.return_value = mock_command

    load_examples_from_configs(force_data=True)

    mock_load_contents.assert_called_once_with(False)
    mock_command_cls.assert_called_once_with(
        {"databases/examples.yaml": "content"},
        overwrite=True,
        force_data=True,
    )
    mock_command.run.assert_called_once()


@patch("superset.examples.utils.ImportExamplesCommand")
@patch("superset.examples.utils.load_contents")
def test_load_examples_from_configs_defaults(
    mock_load_contents,
    mock_command_cls,
):
    """Default call should pass force_data=False and load_test_data=False."""
    from superset.examples.utils import load_examples_from_configs

    mock_load_contents.return_value = {}
    mock_command = MagicMock()
    mock_command_cls.return_value = mock_command

    load_examples_from_configs()

    mock_load_contents.assert_called_once_with(False)
    mock_command_cls.assert_called_once_with(
        {},
        overwrite=True,
        force_data=False,
    )
    mock_command.run.assert_called_once()

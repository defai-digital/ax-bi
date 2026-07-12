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
"""Tests for axbi/commands/dataset/importers/v1/utils.py temporal helpers."""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from marshmallow import fields, Schema, ValidationError
from pytest_mock import MockerFixture


class RequiredNameSchema(Schema):
    name = fields.String(required=True)


class MaskedEncryptedExtraSchema(Schema):
    name = fields.String(required=True)
    masked_encrypted_extra = fields.String(required=False)


class SshTunnelSchema(Schema):
    name = fields.String(required=True)
    ssh_tunnel = fields.Dict(required=False)


def _mock_empty_import_queries(mocker: MockerFixture) -> None:
    query = mocker.patch("axbi.commands.importers.v1.utils.db").session.query
    query.return_value.all.return_value = []


def test_load_yaml_wraps_scanner_errors() -> None:
    from axbi.commands.importers.v1.utils import load_yaml

    with pytest.raises(ValidationError) as excinfo:
        load_yaml("databases/bad.yaml", "name: [")

    assert excinfo.value.messages == {
        "databases/bad.yaml": "Not a valid YAML file",
    }


def test_load_configs_rejects_non_object_yaml(mocker: MockerFixture) -> None:
    from axbi.commands.importers.v1.utils import load_configs

    _mock_empty_import_queries(mocker)
    exceptions: list[ValidationError] = []

    configs = load_configs(
        {"databases/bad.yaml": "- item"},
        {"databases/": RequiredNameSchema()},
        {},
        exceptions,
        {},
        {},
        {},
        {},
    )

    assert configs == {}
    assert len(exceptions) == 1
    assert exceptions[0].messages == {
        "databases/bad.yaml": {"_schema": ["Invalid config file"]},
    }


def test_load_configs_schema_error_does_not_require_config_assignment(
    mocker: MockerFixture,
) -> None:
    from axbi.commands.importers.v1.utils import load_configs

    _mock_empty_import_queries(mocker)
    exceptions: list[ValidationError] = []

    configs = load_configs(
        {"databases/bad.yaml": "{}"},
        {"databases/": RequiredNameSchema()},
        {},
        exceptions,
        {},
        {},
        {},
        {},
    )

    assert configs == {}
    assert len(exceptions) == 1
    assert exceptions[0].messages == {
        "databases/bad.yaml": {"name": ["Missing data for required field."]},
    }


@pytest.mark.parametrize(
    ("masked_encrypted_extra", "expected_message"),
    [
        ("{bad json", "Invalid JSON"),
        ("[]", "Invalid JSON object"),
    ],
)
def test_load_configs_rejects_bad_masked_encrypted_extra_when_applying_secrets(
    mocker: MockerFixture,
    masked_encrypted_extra: str,
    expected_message: str,
) -> None:
    from axbi.commands.importers.v1.utils import load_configs
    from axbi.utils import json

    _mock_empty_import_queries(mocker)
    exceptions: list[ValidationError] = []

    configs = load_configs(
        {
            "databases/database.yaml": (
                "name: test_db\n"
                f"masked_encrypted_extra: {json.dumps(masked_encrypted_extra)}\n"
            )
        },
        {"databases/": MaskedEncryptedExtraSchema()},
        {},
        exceptions,
        {},
        {},
        {},
        {"databases/database.yaml": {"$.secret": "secret-value"}},
    )

    assert configs == {}
    assert len(exceptions) == 1
    assert exceptions[0].messages == {
        "databases/database.yaml": {
            "masked_encrypted_extra": [expected_message],
        },
    }


def test_load_configs_rejects_non_object_ssh_tunnel_without_crashing(
    mocker: MockerFixture,
) -> None:
    from axbi.commands.importers.v1.utils import load_configs

    _mock_empty_import_queries(mocker)
    exceptions: list[ValidationError] = []

    configs = load_configs(
        {"databases/database.yaml": "name: test_db\nssh_tunnel: []\n"},
        {"databases/": SshTunnelSchema()},
        {},
        exceptions,
        {},
        {},
        {},
        {},
    )

    assert configs == {}
    assert len(exceptions) == 1
    assert exceptions[0].messages == {
        "databases/database.yaml": {
            "ssh_tunnel": ["Not a valid mapping type."],
        },
    }


def test_read_dataframe_from_uri_supports_file_parquet(tmp_path) -> None:
    """Bundled example imports use local Parquet files."""
    from axbi.commands.dataset.importers.v1.utils import _read_dataframe_from_uri

    expected = pd.DataFrame({"name": ["alpha", "beta"], "value": [1, 2]})
    parquet_path = tmp_path / "example.parquet"
    expected.to_parquet(parquet_path)

    result = _read_dataframe_from_uri(parquet_path.resolve().as_uri())

    pd.testing.assert_frame_equal(result, expected)


def test_get_dtype_skips_columns_without_supported_native_type() -> None:
    """Columns without supported imported types should let pandas infer SQL types."""
    from sqlalchemy import Text

    from axbi.commands.dataset.importers.v1.utils import get_dtype

    dataset = MagicMock()
    dataset.columns = [
        MagicMock(column_name="name", type=None),
        MagicMock(column_name="category", type="VAR_STRING"),
        MagicMock(column_name="description", type="TEXT"),
        MagicMock(column_name="value", type="BIGINT"),
    ]
    df = pd.DataFrame(
        {
            "name": ["alpha"],
            "category": ["a"],
            "description": ["long text"],
            "value": [1],
        }
    )

    dtype = get_dtype(df, dataset)

    assert "name" not in dtype
    assert "category" not in dtype
    assert isinstance(dtype["description"], Text)
    assert str(dtype["value"]) == "BIGINT"


class TestConvertTemporalColumns:
    def test_normal_dates_converted(self) -> None:
        """Valid in-range dates are converted to datetime64 normally."""
        from sqlalchemy import DateTime

        from axbi.commands.dataset.importers.v1.utils import (
            _convert_temporal_columns,
        )

        df = pd.DataFrame({"ts": ["2023-01-01", "2024-06-15"]})
        _convert_temporal_columns(df, {"ts": DateTime()})
        assert pd.api.types.is_datetime64_any_dtype(df["ts"])

    def test_out_of_bounds_coerced_to_nat(self) -> None:
        """
        Dates beyond the ns range (~2262) used to overflow int64 nanoseconds.

        Under pandas 3.0+, ``to_datetime`` may keep microsecond resolution so
        far-future dates remain valid. The importer must not raise; if pandas
        still raises OutOfBoundsDatetime, values are coerced to NaT with a
        warning.
        """
        from sqlalchemy import DateTime

        from axbi.commands.dataset.importers.v1.utils import (
            _convert_temporal_columns,
        )

        df = pd.DataFrame({"ts": ["3118-01-01"]})
        with patch("axbi.commands.dataset.importers.v1.utils.logger") as mock_logger:
            _convert_temporal_columns(df, {"ts": DateTime()})

        value = df["ts"].iloc[0]
        if pd.isna(value):
            mock_logger.warning.assert_called_once()
            warning_msg = mock_logger.warning.call_args[0][0]
            assert "out-of-bounds" in warning_msg
        else:
            assert pd.Timestamp(value).year == 3118

    def test_malformed_dates_still_raise(self) -> None:
        """
        Completely malformed date strings are NOT silently coerced — only
        out-of-bounds timestamps are. This preserves the original import-fail
        behavior for bad data.
        """
        from sqlalchemy import DateTime

        from axbi.commands.dataset.importers.v1.utils import (
            _convert_temporal_columns,
        )

        df = pd.DataFrame({"ts": ["not-a-date"]})
        with pytest.raises((ValueError, pd.errors.ParserError)):
            _convert_temporal_columns(df, {"ts": DateTime()})

    @pytest.mark.parametrize(
        "values",
        [
            ["3118-01-01", "not-a-date"],
            ["not-a-date", "3118-01-01"],
        ],
    )
    def test_mixed_out_of_bounds_and_malformed_still_raises(
        self, values: list[str]
    ) -> None:
        """
        A column mixing out-of-bounds and malformed dates must raise, not silently
        coerce the malformed value to NaT. Both orderings are tested to ensure the
        invariant holds regardless of which error pandas encounters first.
        """
        from sqlalchemy import DateTime

        from axbi.commands.dataset.importers.v1.utils import (
            _convert_temporal_columns,
        )

        df = pd.DataFrame({"ts": values})
        with pytest.raises((ValueError, pd.errors.ParserError)):
            _convert_temporal_columns(df, {"ts": DateTime()})

    def test_warning_count_excludes_preexisting_nulls(self) -> None:
        """
        When OutOfBoundsDatetime still fires, the warning count reflects only
        net-new NaTs from coercion, not nulls already in the source data.

        Under pandas 3.0+ far-future dates may parse successfully (us resolution);
        then no warning is emitted and values stay valid.
        """
        from sqlalchemy import DateTime

        from axbi.commands.dataset.importers.v1.utils import (
            _convert_temporal_columns,
        )

        df = pd.DataFrame({"ts": [None, "3118-01-01", "3119-06-01"]})
        with patch("axbi.commands.dataset.importers.v1.utils.logger") as mock_logger:
            _convert_temporal_columns(df, {"ts": DateTime()})

        if mock_logger.warning.called:
            call_args = mock_logger.warning.call_args[0]
            assert call_args[1] == 2  # 2 out-of-bounds, 1 pre-existing null
        else:
            assert pd.Timestamp(df["ts"].iloc[1]).year == 3118
            assert pd.Timestamp(df["ts"].iloc[2]).year == 3119

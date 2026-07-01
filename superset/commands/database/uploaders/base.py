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
import logging
import re
from abc import abstractmethod
from functools import partial
from typing import Any, Optional, TypedDict

import pandas as pd
from flask import current_app
from flask_babel import lazy_gettext as _
from pandas.api import types as pd_types
from werkzeug.datastructures import FileStorage

from superset import db
from superset.commands.base import BaseCommand
from superset.commands.database.exceptions import (
    DatabaseNotFoundError,
    DatabaseSchemaUploadNotAllowed,
    DatabaseUploadFailed,
    DatabaseUploadFileTooLarge,
    DatabaseUploadNotSupported,
    DatabaseUploadSaveMetadataFailed,
)
from superset.connectors.sqla.models import SqlaTable
from superset.daos.database import DatabaseDAO
from superset.models.core import Database
from superset.sql.parse import Table
from superset.utils.backports import StrEnum
from superset.utils.core import get_user
from superset.utils.decorators import on_error, transaction
from superset.views.database.validators import schema_allows_file_upload

logger = logging.getLogger(__name__)

READ_CHUNK_SIZE = 1000


class UploadFileType(StrEnum):
    CSV = "csv"
    EXCEL = "excel"
    COLUMNAR = "columnar"
    STRUCTURED = "structured"


class ReaderOptions(TypedDict, total=False):
    already_exists: str
    index_label: str
    dataframe_index: bool


class FileMetadataItem(TypedDict, total=False):
    sheet_name: Optional[str]
    column_names: list[str]
    columns: list["FileColumnMetadata"]
    sample_rows: list[dict[str, Optional[str]]]
    row_count_sampled: int


class FileMetadata(TypedDict, total=False):
    items: list[FileMetadataItem]


class FileColumnMetadata(TypedDict, total=False):
    name: str
    source_dtype: str
    semantic_type: str
    suggested_type: str
    bi_role: str
    confidence: float
    null_count: int
    row_count_sampled: int
    n_unique_sampled: int
    sample_values: list[Optional[str]]
    min: Optional[float]
    max: Optional[float]
    warnings: list[str]


_IDENTIFIER_NAME_RE = re.compile(r"(^|[_\W])(id|uuid|guid|code|key)([_\W]|$)")
_TEXT_IDENTIFIER_HINTS = ("zip", "postal", "postcode", "ssn", "tax")
_MEASURE_NAME_HINTS = (
    "amount",
    "balance",
    "cost",
    "price",
    "profit",
    "quantity",
    "revenue",
    "salary",
    "sales",
    "score",
    "total",
)


def _stringify_metadata_value(value: Any) -> Optional[str]:
    """Return a compact string representation for upload metadata previews."""
    if pd.isna(value):
        return None
    text = str(value)
    return text if len(text) <= 80 else f"{text[:77]}..."


def _non_null_text_values(series: pd.Series) -> pd.Series:
    """Return non-empty string values from a series for heuristic checks."""
    values = series.dropna().astype(str)
    return values[values.str.len() > 0]


def _looks_like_identifier(name: str) -> bool:
    """Return whether a column name looks like an identifier or code."""
    lowered = name.lower()
    return bool(_IDENTIFIER_NAME_RE.search(lowered)) or any(
        hint in lowered for hint in _TEXT_IDENTIFIER_HINTS
    )


def _looks_like_measure(name: str) -> bool:
    """Return whether a column name suggests a numeric measure."""
    lowered = name.lower()
    return any(hint in lowered for hint in _MEASURE_NAME_HINTS)


def _has_leading_zero_values(values: pd.Series) -> bool:
    """Return whether string values include numeric codes with leading zeroes."""
    return values.str.match(r"^0\d+$").any()


def _datetime_candidate_ratio(values: pd.Series) -> float:
    """Return the fraction of string values that parse as datetimes."""
    if values.empty:
        return 0.0
    date_like = values[
        values.str.contains(r"[-/:T ]", regex=True) | values.str.match(r"^\d{8}$")
    ]
    if date_like.empty:
        return 0.0
    parsed = pd.to_datetime(date_like, errors="coerce")
    return float(parsed.notna().sum()) / float(len(values))


def _numeric_parse(values: pd.Series) -> pd.Series:
    """Parse string values as numeric values using conservative cleanup."""
    cleaned = values.str.replace(",", "", regex=False)
    return pd.to_numeric(cleaned, errors="coerce")


def _infer_column_metadata(  # noqa: C901
    column_name: str, series: pd.Series
) -> FileColumnMetadata:
    """Infer BI-oriented metadata for one uploaded file column."""
    row_count = int(len(series))
    null_count = int(series.isna().sum())
    unique_count = int(series.dropna().nunique())
    sample_values = [
        _stringify_metadata_value(value) for value in series.head(5).tolist()
    ]
    values = _non_null_text_values(series)
    warnings: list[str] = []
    semantic_type = "text"
    suggested_type = "text"
    bi_role = "Dimension"
    confidence = 0.6
    min_value: Optional[float] = None
    max_value: Optional[float] = None

    identifier_name = _looks_like_identifier(column_name)
    leading_zeroes = _has_leading_zero_values(values)
    numeric_values = _numeric_parse(values)
    numeric_ratio = (
        float(numeric_values.notna().sum()) / float(len(values))
        if not values.empty
        else 0.0
    )
    datetime_ratio = _datetime_candidate_ratio(values)

    if leading_zeroes:
        warnings.append("Leading zero values detected; text preserves codes.")

    if pd_types.is_bool_dtype(series):
        semantic_type = "boolean"
        suggested_type = "boolean"
        confidence = 0.95
    elif pd_types.is_datetime64_any_dtype(series):
        semantic_type = "datetime"
        suggested_type = "datetime"
        bi_role = "Time column"
        confidence = 0.95
    elif identifier_name and (leading_zeroes or not pd_types.is_numeric_dtype(series)):
        semantic_type = "identifier"
        suggested_type = "text"
        confidence = 0.9 if leading_zeroes else 0.75
    elif datetime_ratio >= 0.9:
        semantic_type = "datetime"
        suggested_type = "datetime"
        bi_role = "Time column"
        confidence = round(datetime_ratio, 2)
    elif numeric_ratio >= 0.95 or pd_types.is_numeric_dtype(series):
        non_null_numeric = numeric_values.dropna()
        if not non_null_numeric.empty:
            min_value = float(non_null_numeric.min())
            max_value = float(non_null_numeric.max())
        if identifier_name:
            semantic_type = "identifier"
            bi_role = "Dimension"
            confidence = 0.85
            if values.str.replace(",", "", regex=False).str.len().max() >= 16:
                suggested_type = "text"
                warnings.append("Long numeric identifiers should be stored as text.")
            else:
                suggested_type = "integer"
        elif not non_null_numeric.empty and (non_null_numeric.dropna() % 1 == 0).all():
            semantic_type = "integer"
            suggested_type = "integer"
            confidence = round(numeric_ratio, 2)
            bi_role = "Measure" if _looks_like_measure(column_name) else "Dimension"
        else:
            semantic_type = "decimal"
            suggested_type = "decimal"
            bi_role = "Measure"
            confidence = round(numeric_ratio, 2)
    elif unique_count <= min(100, max(1, row_count // 20)):
        semantic_type = "category"
        suggested_type = "text"
        confidence = 0.7

    if 0 < numeric_ratio < 0.95 and suggested_type != "text":
        warnings.append("Mixed numeric and text values detected.")
        suggested_type = "text"
        semantic_type = "mixed"
        bi_role = "Dimension"
        confidence = 0.65

    metadata: FileColumnMetadata = {
        "name": column_name,
        "source_dtype": str(series.dtype),
        "semantic_type": semantic_type,
        "suggested_type": suggested_type,
        "bi_role": bi_role,
        "confidence": confidence,
        "null_count": null_count,
        "row_count_sampled": row_count,
        "n_unique_sampled": unique_count,
        "sample_values": sample_values,
        "warnings": warnings,
    }
    if min_value is not None:
        metadata["min"] = min_value
    if max_value is not None:
        metadata["max"] = max_value
    return metadata


def build_upload_metadata_item(
    df: pd.DataFrame,
    sheet_name: Optional[str],
) -> FileMetadataItem:
    """Build rich, BI-oriented metadata for an uploaded file preview."""
    columns = [_infer_column_metadata(str(column), df[column]) for column in df.columns]
    sample_rows = [
        {str(column): _stringify_metadata_value(value) for column, value in row.items()}
        for row in df.head(5).to_dict(orient="records")
    ]
    return {
        "sheet_name": sheet_name,
        "column_names": [str(column) for column in df.columns.tolist()],
        "columns": columns,
        "sample_rows": sample_rows,
        "row_count_sampled": int(len(df)),
    }


def build_type_preserving_upload_options(
    metadata: FileMetadata,
) -> dict[str, str]:
    """Build column dtype options that preserve metadata text columns."""
    items = metadata.get("items") or []
    if not items:
        return {}

    return {
        column["name"]: "string"
        for column in items[0].get("columns", [])
        if column.get("suggested_type") == "text"
    }


class BaseDataReader:
    """
    Base class for reading data from a file and uploading it to a database
    These child objects are used by the UploadCommand as a dependency injection
    to read data from multiple file types (e.g. CSV, Excel, etc.)
    """

    def __init__(self, options: Optional[dict[str, Any]] = None) -> None:
        self._options = options or {}

    @abstractmethod
    def file_to_dataframe(self, file: FileStorage) -> pd.DataFrame: ...

    @abstractmethod
    def file_metadata(self, file: FileStorage) -> FileMetadata: ...

    def read(
        self,
        file: FileStorage,
        database: Database,
        table_name: str,
        schema_name: Optional[str],
    ) -> None:
        self._dataframe_to_database(
            self.file_to_dataframe(file), database, table_name, schema_name
        )

    def _dataframe_to_database(
        self,
        df: pd.DataFrame,
        database: Database,
        table_name: str,
        schema_name: Optional[str],
    ) -> None:
        """
        Upload DataFrame to database

        :param df:
        :throws DatabaseUploadFailed: if there is an error uploading the DataFrame
        """
        try:
            data_table = Table(table=table_name, schema=schema_name)
            to_sql_kwargs = {
                "chunksize": READ_CHUNK_SIZE,
                "if_exists": self._options.get("already_exists", "fail"),
                "index": self._options.get("dataframe_index", False),
            }
            if self._options.get("index_label") and self._options.get(
                "dataframe_index"
            ):
                to_sql_kwargs["index_label"] = self._options.get("index_label")
            database.db_engine_spec.df_to_sql(
                database,
                data_table,
                df,
                to_sql_kwargs=to_sql_kwargs,
            )
        except ValueError as ex:
            raise DatabaseUploadFailed(
                message=_(
                    "Table already exists. You can change your "
                    "'if table already exists' strategy to append or "
                    "replace or provide a different Table Name to use."
                )
            ) from ex
        except Exception as ex:
            message = ex.message if hasattr(ex, "message") and ex.message else str(ex)
            raise DatabaseUploadFailed(message=message, exception=ex) from ex


class UploadCommand(BaseCommand):
    def __init__(  # pylint: disable=too-many-arguments
        self,
        model_id: int,
        table_name: str,
        file: Any,
        schema: Optional[str],
        reader: BaseDataReader,
    ) -> None:
        self._model_id = model_id
        self._model: Optional[Database] = None
        self._table_name = table_name
        self._schema = schema
        self._file = file
        self._reader = reader

    @transaction(on_error=partial(on_error, reraise=DatabaseUploadSaveMetadataFailed))
    def run(self) -> None:
        self.validate()
        if not self._model:
            return

        self._table_name, self._schema = (
            self._model.db_engine_spec.normalize_table_name_for_upload(
                self._table_name, self._schema
            )
        )

        self._reader.read(self._file, self._model, self._table_name, self._schema)

        sqla_table = (
            db.session.query(SqlaTable)
            .filter_by(
                table_name=self._table_name,
                schema=self._schema,
                database_id=self._model_id,
            )
            .one_or_none()
        )
        if not sqla_table:
            sqla_table = SqlaTable(
                table_name=self._table_name,
                database=self._model,
                database_id=self._model_id,
                owners=[get_user()],
                schema=self._schema,
            )
            db.session.add(sqla_table)

        sqla_table.fetch_metadata()

    @staticmethod
    def _file_size_bytes(file: Any) -> Optional[int]:
        """
        Return the size of an uploaded file without consuming its stream.

        Returns ``None`` when the stream is not seekable, in which case the
        size cannot be determined cheaply and the size check is skipped in
        favour of downstream guards.
        """
        stream = getattr(file, "stream", file)
        try:
            position = stream.tell()
            stream.seek(0, 2)  # seek to end
            size = stream.tell()
            stream.seek(position)  # restore the original position
        except (AttributeError, OSError):
            return None
        return size

    @classmethod
    def validate_file_size(cls, file: Any) -> None:
        """
        Reject a file whose size exceeds ``UPLOAD_MAX_FILE_SIZE_BYTES``.

        Shared by the upload command and the metadata endpoint so oversized
        files are rejected before their contents are read into memory,
        regardless of which path is used.

        :raises DatabaseUploadFileTooLarge: if the file is larger than the limit
        """
        max_file_size = current_app.config.get("UPLOAD_MAX_FILE_SIZE_BYTES")
        if max_file_size is None or file is None:
            return
        size = cls._file_size_bytes(file)
        if size is not None and size > max_file_size:
            raise DatabaseUploadFileTooLarge()

    def validate(self) -> None:
        self._model = DatabaseDAO.find_by_id(self._model_id)
        if not self._model:
            raise DatabaseNotFoundError()
        if not schema_allows_file_upload(self._model, self._schema):
            raise DatabaseSchemaUploadNotAllowed()
        if not self._model.db_engine_spec.supports_file_upload:
            raise DatabaseUploadNotSupported()

        self.validate_file_size(self._file)

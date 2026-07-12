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

from collections.abc import Callable, Generator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
import pytest
from werkzeug.datastructures import FileStorage

from axbi.commands.database.uploaders.base import BaseDataReader
from axbi.commands.database.uploaders.columnar_reader import ColumnarReader
from axbi.commands.database.uploaders.csv_reader import CSVReader, CSVReaderOptions
from axbi.commands.database.uploaders.excel_reader import (
    ExcelReader,
    ExcelReaderOptions,
)
from axbi.commands.database.uploaders.structured_reader import StructuredReader

SAMPLE_DIR = Path(__file__).parent / "sample_files"
EXPECTED_SAMPLE_FILES = {
    "customers.csv",
    "customers.tsv",
    "customers_pipe.txt",
    "customers.xls",
    "customers.xlsx",
    "customers.parquet",
    "customers.json",
    "customers.jsonl",
    "customers.ndjson",
    "customers.xml",
    "customers.sql",
    "customers.dump",
    "customers.sqlite",
    "customers.sqlite3",
    "customers.db",
}


@dataclass(frozen=True)
class ReaderCase:
    filename: str
    reader_factory: Callable[[], BaseDataReader]


CSV_READER_OPTIONS: CSVReaderOptions = {
    "column_data_types": {"customer_id": "string"},
    "column_dates": ["invoice_date"],
}
EXCEL_READER_OPTIONS: ExcelReaderOptions = {
    "column_data_types": {"customer_id": "string"},
    "column_dates": ["invoice_date"],
}

READER_CASES = [
    ReaderCase("customers.csv", lambda: CSVReader(CSV_READER_OPTIONS)),
    ReaderCase("customers.tsv", lambda: CSVReader(CSV_READER_OPTIONS)),
    ReaderCase("customers_pipe.txt", lambda: CSVReader(CSV_READER_OPTIONS)),
    ReaderCase("customers.xls", lambda: ExcelReader(EXCEL_READER_OPTIONS)),
    ReaderCase("customers.xlsx", lambda: ExcelReader(EXCEL_READER_OPTIONS)),
    ReaderCase("customers.parquet", lambda: ColumnarReader()),
    ReaderCase("customers.json", lambda: StructuredReader()),
    ReaderCase("customers.jsonl", lambda: StructuredReader()),
    ReaderCase("customers.ndjson", lambda: StructuredReader()),
    ReaderCase("customers.xml", lambda: StructuredReader()),
    ReaderCase("customers.sql", lambda: StructuredReader()),
    ReaderCase("customers.dump", lambda: StructuredReader()),
    ReaderCase("customers.sqlite", lambda: StructuredReader()),
    ReaderCase("customers.sqlite3", lambda: StructuredReader()),
    ReaderCase("customers.db", lambda: StructuredReader()),
]


@contextmanager
def upload_file(filename: str) -> Generator[FileStorage, None, None]:
    """Open a QA sample file as a Werkzeug FileStorage upload."""
    path = SAMPLE_DIR / filename
    with path.open("rb") as stream:
        yield FileStorage(stream=stream, filename=filename)


def _truthy(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes"}
    return bool(value)


def assert_customer_frame(df: pd.DataFrame) -> None:
    """Assert that a parsed sample file preserves expected customer records."""
    assert df.columns.tolist() == [
        "customer_id",
        "invoice_date",
        "amount",
        "active",
    ]
    assert [str(value) for value in df["customer_id"].tolist()] == ["00123", "00124"]
    assert [str(value)[:10] for value in df["invoice_date"].tolist()] == [
        "2024-01-15",
        "2024-02-20",
    ]
    assert [float(value) for value in df["amount"].tolist()] == pytest.approx(
        [10.5, 20.75]
    )
    assert [_truthy(value) for value in df["active"].tolist()] == [True, False]


def test_qa_sample_folder_contains_supported_file_types() -> None:
    """Ensure QA fixtures cover every supported upload sample type."""
    actual_files = {path.name for path in SAMPLE_DIR.iterdir() if path.is_file()}
    assert EXPECTED_SAMPLE_FILES <= actual_files


@pytest.mark.parametrize("case", READER_CASES, ids=lambda case: case.filename)
def test_upload_readers_load_qa_sample_files(case: ReaderCase) -> None:
    """Load each supported QA sample file into a DataFrame."""
    reader = case.reader_factory()
    with upload_file(case.filename) as file:
        df = reader.file_to_dataframe(file)

    assert_customer_frame(df)


@pytest.mark.parametrize("case", READER_CASES, ids=lambda case: case.filename)
def test_upload_metadata_suggests_bi_field_types(case: ReaderCase) -> None:
    """Verify metadata detection for BI-oriented field type suggestions."""
    reader = case.reader_factory()
    with upload_file(case.filename) as file:
        metadata = reader.file_metadata(file)

    item = metadata["items"][0]
    columns = {column["name"]: column for column in item["columns"]}

    assert item["column_names"] == [
        "customer_id",
        "invoice_date",
        "amount",
        "active",
    ]
    assert columns["customer_id"]["suggested_type"] == "text"
    assert "Leading zero values detected" in " ".join(
        columns["customer_id"]["warnings"]
    )
    assert columns["invoice_date"]["suggested_type"] == "datetime"
    assert columns["amount"]["suggested_type"] == "decimal"

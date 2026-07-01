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

import io
import sqlite3
from pathlib import Path

import pandas as pd
import pytest
from werkzeug.datastructures import FileStorage

from superset.commands.database.exceptions import DatabaseUploadFailed
from superset.commands.database.uploaders.structured_reader import StructuredReader


def make_file(content: bytes, filename: str) -> FileStorage:
    return FileStorage(io.BytesIO(content), filename=filename)


def test_structured_reader_json_metadata() -> None:
    reader = StructuredReader()
    metadata = reader.file_metadata(
        make_file(
            b'[{"customer_id":"00123","amount":10.5},{"customer_id":"00124","amount":20.0}]',
            "customers.json",
        )
    )

    item = metadata["items"][0]
    columns = {column["name"]: column for column in item["columns"]}
    assert item["column_names"] == ["customer_id", "amount"]
    assert columns["customer_id"]["suggested_type"] == "text"
    assert columns["customer_id"]["sample_values"] == ["00123", "00124"]
    assert columns["amount"]["suggested_type"] == "decimal"


def test_structured_reader_jsonl() -> None:
    reader = StructuredReader()
    df = reader.file_to_dataframe(
        make_file(
            b'{"name":"Alice","active":true}\n{"name":"Bob","active":false}\n',
            "users.jsonl",
        )
    )

    assert df.to_dict(orient="records") == [
        {"name": "Alice", "active": True},
        {"name": "Bob", "active": False},
    ]


def test_structured_reader_xml() -> None:
    reader = StructuredReader()
    df = reader.file_to_dataframe(
        make_file(
            b"""
            <rows>
              <row id="001"><name>Alice</name><amount>10.5</amount></row>
              <row id="002"><name>Bob</name><amount>20.0</amount></row>
            </rows>
            """,
            "rows.xml",
        )
    )

    assert df["id"].tolist() == ["001", "002"]
    assert df["name"].tolist() == ["Alice", "Bob"]


def test_structured_reader_sql_insert_dump() -> None:
    reader = StructuredReader()
    df = reader.file_to_dataframe(
        make_file(
            b"""
            INSERT INTO users (id, email, score) VALUES
              (1, 'a@example.com', 10.5),
              (2, 'b@example.com', NULL);
            """,
            "users.sql",
        )
    )

    assert df.columns.tolist() == ["id", "email", "score"]
    assert df["email"].tolist() == ["a@example.com", "b@example.com"]
    assert pd.isna(df["score"].tolist()[1])


def test_structured_reader_rejects_multi_table_sql_dump() -> None:
    reader = StructuredReader()
    with pytest.raises(DatabaseUploadFailed) as ex:
        reader.file_to_dataframe(
            make_file(
                b"INSERT INTO a (x) VALUES (1); INSERT INTO b (x) VALUES (2);",
                "dump.sql",
            )
        )

    assert "Multi-table SQL dumps" in str(ex.value)


def test_structured_reader_sqlite(tmp_path: Path) -> None:
    db_path = tmp_path / "users.sqlite"
    db = sqlite3.connect(db_path)
    db.execute("CREATE TABLE users (id INTEGER, name TEXT)")
    db.execute("INSERT INTO users VALUES (1, 'Alice'), (2, 'Bob')")
    db.commit()
    db.close()

    reader = StructuredReader()
    df = reader.file_to_dataframe(
        FileStorage(io.BytesIO(db_path.read_bytes()), filename="users.sqlite")
    )

    assert df.to_dict(orient="records") == [
        {"id": 1, "name": "Alice"},
        {"id": 2, "name": "Bob"},
    ]

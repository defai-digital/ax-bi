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

import gzip
import io
import sqlite3
import tarfile
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import numpy as np
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


def test_structured_reader_gzip_jsonl() -> None:
    reader = StructuredReader()
    df = reader.file_to_dataframe(
        make_file(
            gzip.compress(b'{"prompt":"A","score":0.8}\n{"prompt":"B","score":0.9}\n'),
            "eval.jsonl.gz",
        )
    )

    assert df.to_dict(orient="records") == [
        {"prompt": "A", "score": 0.8},
        {"prompt": "B", "score": 0.9},
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


def test_structured_reader_sql_dump_accepts_dialect_literals() -> None:
    reader = StructuredReader()
    df = reader.file_to_dataframe(
        make_file(
            b"""
            INSERT INTO [users] ([id], [name], [created_at]) VALUES
              (1, N'Alice', DATE '2024-01-01');
            GO
            """,
            "users.sql",
        )
    )

    assert df.to_dict(orient="records") == [
        {"id": 1, "name": "Alice", "created_at": "2024-01-01"}
    ]


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


def test_structured_reader_fixed_width() -> None:
    reader = StructuredReader()
    df = reader.file_to_dataframe(
        make_file(
            b"name  age\nAlice 030\nBob   025\n",
            "people.fwf",
        )
    )

    assert df.columns.tolist() == ["name", "age"]
    assert df["name"].tolist() == ["Alice", "Bob"]


def test_structured_reader_html_table() -> None:
    pytest.importorskip("lxml")
    reader = StructuredReader()
    df = reader.file_to_dataframe(
        make_file(
            b"<table><tr><th>name</th><th>score</th></tr>"
            b"<tr><td>Alice</td><td>10</td></tr></table>",
            "scores.html",
        )
    )

    assert df.to_dict(orient="records") == [{"name": "Alice", "score": 10}]


def test_structured_reader_numpy_embeddings() -> None:
    buffer = io.BytesIO()
    np.save(buffer, np.array([[0.1, 0.2], [0.3, 0.4]]))
    buffer.seek(0)

    reader = StructuredReader()
    df = reader.file_to_dataframe(FileStorage(buffer, filename="embeddings.npy"))

    assert df["embedding_id"].tolist() == [0, 1]
    assert df["embedding_dimensions"].tolist() == [2, 2]
    assert df["embedding"].tolist() == ["[0.1, 0.2]", "[0.3, 0.4]"]


def test_structured_reader_geojson() -> None:
    reader = StructuredReader()
    df = reader.file_to_dataframe(
        make_file(
            b"""
            {
              "type": "FeatureCollection",
              "features": [
                {
                  "type": "Feature",
                  "properties": {"name": "A"},
                  "geometry": {"type": "Point", "coordinates": [1, 2]}
                }
              ]
            }
            """,
            "places.geojson",
        )
    )

    assert df["name"].tolist() == ["A"]
    assert df["geometry_type"].tolist() == ["Point"]


def test_structured_reader_croissant_manifest() -> None:
    reader = StructuredReader()
    df = reader.file_to_dataframe(
        make_file(
            b"""
            {
              "@context": "https://schema.org/",
              "conformsTo": "https://mlcommons.org/croissant/1.0",
              "name": "Example",
              "recordSet": [{"name": "rows", "field": [{"name": "label"}]}]
            }
            """,
            "metadata.croissant.json",
        )
    )

    assert "croissant_dataset" in df["artifact_type"].tolist()
    assert "recordSet" in df["section"].tolist()


def test_structured_reader_coco_annotations() -> None:
    reader = StructuredReader()
    df = reader.file_to_dataframe(
        make_file(
            b"""
            {
              "images": [{"id": 1, "file_name": "image.jpg"}],
              "categories": [{"id": 7, "name": "defect"}],
              "annotations": [
                {"id": 10, "image_id": 1, "category_id": 7, "bbox": [1, 2, 3, 4]}
              ]
            }
            """,
            "coco.json",
        )
    )

    assert df.to_dict(orient="records")[0]["category_name"] == "defect"


def test_structured_reader_label_studio_list_export() -> None:
    reader = StructuredReader()
    df = reader.file_to_dataframe(
        make_file(
            b"""
            [
              {
                "id": 1,
                "data": {"text": "hello"},
                "annotations": [{"id": 2, "completed_by": 3, "result": []}]
              }
            ]
            """,
            "label_studio.json",
        )
    )

    row = df.to_dict(orient="records")[0]
    assert row["artifact_type"] == "label_studio_annotation"
    assert row["task_id"] == 1
    assert row["annotation_id"] == 2


def test_structured_reader_model_artifact_metadata() -> None:
    reader = StructuredReader()
    df = reader.file_to_dataframe(make_file(b"GGUF", "model.gguf"))

    row = df.to_dict(orient="records")[0]
    assert row["artifact_type"] == "model_artifact"
    assert row["size_bytes"] == 4


def test_structured_reader_tar_manifest() -> None:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w") as tar:
        payload = b"sample"
        info = tarfile.TarInfo("000001.txt")
        info.size = len(payload)
        tar.addfile(info, io.BytesIO(payload))
    buffer.seek(0)

    reader = StructuredReader()
    df = reader.file_to_dataframe(FileStorage(buffer, filename="dataset.tar"))

    assert df.to_dict(orient="records") == [
        {
            "path": "000001.txt",
            "suffix": ".txt",
            "size": 6,
            "artifact_type": "tar",
        }
    ]


def test_structured_reader_zip_manifest() -> None:
    buffer = io.BytesIO()
    with ZipFile(buffer, mode="w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("labels/000001.txt", "0 0.5 0.5 0.1 0.1")
    buffer.seek(0)

    reader = StructuredReader()
    df = reader.file_to_dataframe(FileStorage(buffer, filename="labels.yolo.zip"))

    row = df.to_dict(orient="records")[0]
    assert row["path"] == "labels/000001.txt"
    assert row["artifact_type"] == "yolo.zip"

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
import re
import sqlite3
import tarfile
import tempfile
from pathlib import Path
from typing import Any
from zipfile import is_zipfile, ZipFile

import pandas as pd
import yaml
from defusedxml import ElementTree
from flask_babel import lazy_gettext as _
from werkzeug.datastructures import FileStorage

from superset.commands.database.exceptions import DatabaseUploadFailed
from superset.commands.database.uploaders.base import (
    BaseDataReader,
    build_upload_metadata_item,
    FileMetadata,
    ReaderOptions,
)
from superset.exceptions import SupersetException
from superset.utils import json
from superset.utils.core import check_is_safe_zip

ROWS_TO_READ_METADATA = 100
MAX_ARCHIVE_ENTRIES = 500

_INSERT_RE = re.compile(
    r"INSERT\s+INTO\s+([\w.\"`\[\]]+)\s*(?:\(([^)]+)\))?\s*VALUES\s*",
    re.IGNORECASE,
)
_COMMENT_LINE = re.compile(r"--[^\n]*")
_COMMENT_BLOCK = re.compile(r"/\*.*?\*/", re.DOTALL)


class StructuredReaderOptions(ReaderOptions, total=False):
    sqlite_table: str
    sql_table: str


class StructuredReader(BaseDataReader):
    """Read structured single-table uploads into a DataFrame."""

    def __init__(self, options: StructuredReaderOptions | None = None) -> None:
        options = options or {}
        super().__init__(options=dict(options))

    def file_to_dataframe(self, file: FileStorage) -> pd.DataFrame:
        """Read a supported structured upload into a DataFrame."""
        return self._read_file(file)

    def file_metadata(self, file: FileStorage) -> FileMetadata:
        """Return rich metadata for a structured upload."""
        df = self._read_file(file, nrows=ROWS_TO_READ_METADATA)
        return {"items": [build_upload_metadata_item(df, None)]}

    def _read_file(  # noqa: C901
        self,
        file: FileStorage,
        nrows: int | None = None,
    ) -> pd.DataFrame:
        extension = self._extension(file)
        try:
            if extension in {".json", ".croissant.json"}:
                return self._normalize_dataframe(self._read_json(file, nrows))
            if extension in {".jsonl", ".ndjson", ".jsonl.gz", ".ndjson.gz"}:
                return self._read_json_lines(file, nrows)
            if extension == ".xml":
                return self._read_xml(file, nrows)
            if extension in {".sql", ".dump"}:
                return self._read_sql_dump(file, nrows)
            if extension in {".sqlite", ".sqlite3", ".db"}:
                return self._read_sqlite(file, nrows)
            if extension in {".fwf", ".dat", ".asc"}:
                return self._read_fixed_width(file, nrows)
            if extension in {".html", ".htm"}:
                return self._read_html(file, nrows)
            if extension in {".dta", ".sav", ".sas7bdat", ".xpt"}:
                return self._read_statistical(file, nrows, extension)
            if extension in {".npy", ".npz"}:
                return self._read_numpy(file, nrows, extension)
            if extension == ".geojson":
                return self._read_geojson(file, nrows)
            if extension in {".gpkg", ".shp.zip"}:
                return self._read_geospatial_metadata(file, nrows, extension)
            if extension == ".avro":
                return self._read_avro(file, nrows)
            if extension in {
                ".tar",
                ".tar.gz",
                ".tgz",
                ".lance.zip",
                ".mlflow.zip",
                ".mlruns.zip",
                ".yolo.zip",
            }:
                return self._read_archive_manifest(file, nrows, extension)
            if extension in {".yaml", ".yml", ".mlmodel"}:
                return self._read_yaml_metadata(file, nrows, extension)
            if extension == ".lance":
                return self._artifact_metadata_frame(
                    file,
                    "lance",
                    ["Lance directory uploads should be zipped before upload."],
                )
            if extension in {
                ".faiss",
                ".index",
                ".hnsw",
                ".ann",
                ".safetensors",
                ".onnx",
                ".gguf",
            }:
                return self._artifact_metadata_frame(
                    file,
                    self._artifact_category(extension),
                    [
                        "Binary AI artifacts are imported as metadata only; "
                        "the file is not executed or loaded for inference."
                    ],
                )
        except DatabaseUploadFailed:
            raise
        except Exception as ex:
            raise DatabaseUploadFailed(
                message=_("Error reading structured file: %(error)s", error=str(ex))
            ) from ex
        raise DatabaseUploadFailed(_("Unsupported structured file extension"))

    @staticmethod
    def _extension(file: FileStorage) -> str:
        """Return normalized simple or compound extension for a structured file."""
        filename = Path(file.filename or "").name.lower()
        if filename == "mlmodel":
            return ".mlmodel"
        for extension in (
            ".croissant.json",
            ".jsonl.gz",
            ".ndjson.gz",
            ".tar.gz",
            ".shp.zip",
            ".lance.zip",
            ".mlflow.zip",
            ".mlruns.zip",
            ".yolo.zip",
        ):
            if filename.endswith(extension):
                return extension
        return Path(filename).suffix.lower()

    @staticmethod
    def _decode_file(file: FileStorage) -> str:
        file.seek(0)
        raw = file.read()
        if Path(file.filename or "").name.lower().endswith(".gz"):
            raw = gzip.decompress(raw)
        if isinstance(raw, str):
            return raw
        for encoding in ("utf-8-sig", "utf-8", "latin-1", "cp1252"):
            try:
                return raw.decode(encoding)
            except UnicodeDecodeError:
                continue
        raise DatabaseUploadFailed(_("Could not decode structured text file"))

    @classmethod
    def _records_to_dataframe(cls, records: Any) -> pd.DataFrame:
        if isinstance(records, list):
            if any(
                isinstance(record, dict) and cls._looks_like_label_studio(record)
                for record in records
            ):
                return cls._label_studio_to_dataframe(records)
            return cls._normalize_dataframe(pd.json_normalize(records))
        if isinstance(records, dict):
            if cls._looks_like_croissant(records):
                return cls._croissant_to_dataframe(records)
            if {"images", "annotations", "categories"}.issubset(records.keys()):
                return cls._coco_to_dataframe(records)
            if cls._looks_like_label_studio(records):
                return cls._label_studio_to_dataframe(records)
            list_values = [
                (key, value)
                for key, value in records.items()
                if isinstance(value, list) and value
            ]
            if len(list_values) == 1:
                return cls._normalize_dataframe(pd.json_normalize(list_values[0][1]))
            return cls._normalize_dataframe(pd.json_normalize(records))
        raise DatabaseUploadFailed(_("JSON file must contain an object or an array"))

    def _read_json(self, file: FileStorage, nrows: int | None) -> pd.DataFrame:
        data = json.loads(self._decode_file(file))
        df = self._records_to_dataframe(data)
        return df.head(nrows) if nrows else df

    def _read_json_lines(
        self,
        file: FileStorage,
        nrows: int | None,
    ) -> pd.DataFrame:
        records = []
        for line_number, line in enumerate(self._decode_file(file).splitlines(), 1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                records.append(json.loads(stripped))
            except Exception as ex:
                raise DatabaseUploadFailed(
                    message=_(
                        "Invalid JSON on line %(line_number)s",
                        line_number=line_number,
                    )
                ) from ex
            if nrows and len(records) >= nrows:
                break
        if not records:
            raise DatabaseUploadFailed(_("JSON Lines file contains no records"))
        return self._normalize_dataframe(pd.json_normalize(records))

    def _read_xml(self, file: FileStorage, nrows: int | None) -> pd.DataFrame:
        text = self._decode_file(file)
        root = ElementTree.fromstring(text)
        children = list(root)
        if not children:
            raise DatabaseUploadFailed(_("XML file contains no row elements"))
        row_tag = max(
            {child.tag for child in children},
            key=lambda tag: sum(1 for child in children if child.tag == tag),
        )
        rows = []
        for element in children:
            if element.tag != row_tag:
                continue
            row: dict[str, Any] = dict(element.attrib)
            for child in list(element):
                row[child.tag] = child.text
                row.update(
                    {f"{child.tag}_{key}": value for key, value in child.attrib.items()}
                )
            if not row and element.text:
                row["value"] = element.text
            rows.append(row)
            if nrows and len(rows) >= nrows:
                break
        if not rows:
            raise DatabaseUploadFailed(_("XML file contains no tabular rows"))
        return self._normalize_dataframe(pd.DataFrame(rows))

    def _read_sqlite(self, file: FileStorage, nrows: int | None) -> pd.DataFrame:
        file.seek(0)
        suffix = Path(file.filename or "upload.sqlite").suffix or ".sqlite"
        with tempfile.NamedTemporaryFile(suffix=suffix) as tmp_file:
            tmp_file.write(file.read())
            tmp_file.flush()
            with sqlite3.connect(tmp_file.name) as connection:
                table_name = self._options.get("sqlite_table") or self._first_table(
                    connection
                )
                quoted_table_name = self._quote_sqlite_identifier(table_name)
                query = f"SELECT * FROM {quoted_table_name}"  # noqa: S608
                if nrows:
                    query = f"{query} LIMIT {int(nrows)}"
                try:
                    return self._normalize_dataframe(
                        pd.read_sql_query(query, connection)
                    )
                except Exception as ex:
                    raise DatabaseUploadFailed(
                        message=_(
                            "Could not read SQLite table %(table_name)s",
                            table_name=table_name,
                        )
                    ) from ex

    @staticmethod
    def _first_table(connection: sqlite3.Connection) -> str:
        rows = connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
              AND name NOT LIKE 'sqlite_%'
            ORDER BY name
            """
        ).fetchall()
        if not rows:
            raise DatabaseUploadFailed(_("SQLite database contains no tables"))
        return str(rows[0][0])

    @staticmethod
    def _quote_sqlite_identifier(identifier: str) -> str:
        return f'"{identifier.replace(chr(34), chr(34) * 2)}"'

    def _read_fixed_width(self, file: FileStorage, nrows: int | None) -> pd.DataFrame:
        text = io.StringIO(self._decode_file(file))
        try:
            df = pd.read_fwf(text, nrows=nrows)
        except Exception as ex:
            raise DatabaseUploadFailed(
                message=_("Could not read fixed-width file: %(error)s", error=str(ex))
            ) from ex
        return self._normalize_dataframe(df)

    def _read_html(self, file: FileStorage, nrows: int | None) -> pd.DataFrame:
        try:
            tables = pd.read_html(io.StringIO(self._decode_file(file)))
        except ValueError as ex:
            raise DatabaseUploadFailed(_("HTML file contains no tables")) from ex
        if not tables:
            raise DatabaseUploadFailed(_("HTML file contains no tables"))
        df = tables[0]
        return self._normalize_dataframe(df.head(nrows) if nrows else df)

    def _read_statistical(
        self,
        file: FileStorage,
        nrows: int | None,
        extension: str,
    ) -> pd.DataFrame:
        file.seek(0)
        try:
            if extension == ".dta":
                df = pd.read_stata(file, convert_categoricals=False)
            elif extension == ".sav":
                df = pd.read_spss(file)
            else:
                df = pd.read_sas(file, format="xport" if extension == ".xpt" else None)
        except ImportError as ex:
            raise DatabaseUploadFailed(
                message=_(
                    "Reading %(extension)s files requires an optional dependency",
                    extension=extension,
                )
            ) from ex
        except Exception as ex:
            raise DatabaseUploadFailed(
                message=_(
                    "Could not read statistical file: %(error)s",
                    error=str(ex),
                )
            ) from ex
        return self._normalize_dataframe(df.head(nrows) if nrows else df)

    def _read_numpy(
        self,
        file: FileStorage,
        nrows: int | None,
        extension: str,
    ) -> pd.DataFrame:
        import numpy as np  # pylint: disable=import-outside-toplevel

        file.seek(0)
        try:
            if extension == ".npz":
                loaded = np.load(file, allow_pickle=False)
                frames = [
                    self._numpy_array_to_dataframe(name, loaded[name])
                    for name in loaded.files
                ]
                df = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
            else:
                df = self._numpy_array_to_dataframe(
                    "array",
                    np.load(file, allow_pickle=False),
                )
        except Exception as ex:
            raise DatabaseUploadFailed(
                message=_("Could not read NumPy file: %(error)s", error=str(ex))
            ) from ex
        return self._normalize_dataframe(df.head(nrows) if nrows else df)

    @staticmethod
    def _numpy_array_to_dataframe(name: str, array: Any) -> pd.DataFrame:
        shape = tuple(int(value) for value in getattr(array, "shape", ()))
        dtype = str(getattr(array, "dtype", "unknown"))
        if len(shape) == 1:
            return pd.DataFrame(
                {
                    "array_name": name,
                    "index": list(range(shape[0])),
                    "value": array.tolist(),
                    "dtype": dtype,
                    "shape": json.dumps(shape),
                }
            )
        if len(shape) == 2:
            return pd.DataFrame(
                {
                    "array_name": name,
                    "embedding_id": list(range(shape[0])),
                    "embedding": [json.dumps(row) for row in array.tolist()],
                    "embedding_dimensions": shape[1],
                    "dtype": dtype,
                    "shape": json.dumps(shape),
                }
            )
        return pd.DataFrame(
            [
                {
                    "array_name": name,
                    "dtype": dtype,
                    "shape": json.dumps(shape),
                    "artifact_type": "numpy_array_metadata",
                    "warning": (
                        "Array has more than two dimensions; imported as metadata."
                    ),
                }
            ]
        )

    def _read_geojson(self, file: FileStorage, nrows: int | None) -> pd.DataFrame:
        data = json.loads(self._decode_file(file))
        features = data.get("features") if isinstance(data, dict) else None
        if not isinstance(features, list):
            return self._records_to_dataframe(data)
        rows = []
        for feature in features:
            properties = feature.get("properties") or {}
            geometry = feature.get("geometry")
            geometry_type = geometry.get("type") if isinstance(geometry, dict) else None
            rows.append(
                {
                    **properties,
                    "geometry": json.dumps(geometry) if geometry else None,
                    "geometry_type": geometry_type,
                }
            )
            if nrows and len(rows) >= nrows:
                break
        return self._normalize_dataframe(pd.DataFrame(rows))

    def _read_geospatial_metadata(
        self,
        file: FileStorage,
        nrows: int | None,
        extension: str,
    ) -> pd.DataFrame:
        if extension == ".shp.zip":
            return self._read_archive_manifest(file, nrows, extension)
        return self._artifact_metadata_frame(
            file,
            "geospatial",
            [
                "GeoPackage files are imported as metadata unless a geospatial "
                "reader is installed."
            ],
        )

    def _read_avro(self, file: FileStorage, nrows: int | None) -> pd.DataFrame:
        try:
            import fastavro  # pylint: disable=import-outside-toplevel
        except ImportError:
            return self._artifact_metadata_frame(
                file,
                "avro",
                ["Avro tabular import requires the optional fastavro dependency."],
            )

        file.seek(0)
        try:
            records = []
            for record in fastavro.reader(file):
                records.append(record)
                if nrows and len(records) >= nrows:
                    break
            return self._normalize_dataframe(pd.json_normalize(records))
        except Exception as ex:
            raise DatabaseUploadFailed(
                message=_("Could not read Avro file: %(error)s", error=str(ex))
            ) from ex

    def _read_archive_manifest(
        self,
        file: FileStorage,
        nrows: int | None,
        extension: str,
    ) -> pd.DataFrame:
        if extension.endswith(".zip"):
            rows = self._zip_manifest(file, extension)
        else:
            rows = self._tar_manifest(file, extension)
        df = pd.DataFrame(rows)
        return df.head(nrows) if nrows else df

    @staticmethod
    def _zip_manifest(file: FileStorage, extension: str) -> list[dict[str, Any]]:
        file.seek(0)
        if not is_zipfile(file):
            raise DatabaseUploadFailed(_("Not a valid ZIP file"))
        file.seek(0)
        rows: list[dict[str, Any]] = []
        with ZipFile(file) as zip_file:
            try:
                check_is_safe_zip(zip_file)
            except SupersetException as ex:
                raise DatabaseUploadFailed(str(ex)) from ex
            for index, info in enumerate(zip_file.infolist()):
                if index >= MAX_ARCHIVE_ENTRIES:
                    rows.append(
                        {
                            "path": None,
                            "artifact_type": "archive_manifest_limit",
                            "warning": "Archive entry listing was truncated.",
                        }
                    )
                    break
                if info.is_dir():
                    continue
                rows.append(
                    {
                        "path": info.filename,
                        "suffix": Path(info.filename).suffix.lower(),
                        "size": info.file_size,
                        "compressed_size": info.compress_size,
                        "artifact_type": extension.lstrip("."),
                    }
                )
        return rows

    @staticmethod
    def _tar_manifest(file: FileStorage, extension: str) -> list[dict[str, Any]]:
        file.seek(0)
        rows: list[dict[str, Any]] = []
        try:
            with tarfile.open(fileobj=file.stream, mode="r:*") as tar:
                for index, member in enumerate(tar):
                    if index >= MAX_ARCHIVE_ENTRIES:
                        rows.append(
                            {
                                "path": None,
                                "artifact_type": "archive_manifest_limit",
                                "warning": "Archive entry listing was truncated.",
                            }
                        )
                        break
                    if not member.isfile():
                        continue
                    rows.append(
                        {
                            "path": member.name,
                            "suffix": Path(member.name).suffix.lower(),
                            "size": member.size,
                            "artifact_type": extension.lstrip("."),
                        }
                    )
        except tarfile.TarError as ex:
            raise DatabaseUploadFailed(_("Not a valid TAR archive")) from ex
        return rows

    def _read_yaml_metadata(
        self,
        file: FileStorage,
        nrows: int | None,
        extension: str,
    ) -> pd.DataFrame:
        try:
            data = yaml.safe_load(self._decode_file(file)) or {}
        except yaml.YAMLError as ex:
            raise DatabaseUploadFailed(
                message=_("Could not read YAML metadata: %(error)s", error=str(ex))
            ) from ex
        rows = self._metadata_from_mapping(data, extension.lstrip("."))
        df = pd.DataFrame(rows)
        return df.head(nrows) if nrows else df

    @classmethod
    def _metadata_from_mapping(
        cls,
        data: Any,
        artifact_type: str,
        prefix: str = "",
    ) -> list[dict[str, Any]]:
        if not isinstance(data, dict):
            return [
                {
                    "artifact_type": artifact_type,
                    "key": prefix or "value",
                    "value": cls._serialize_cell(data),
                }
            ]
        rows = []
        for key, value in data.items():
            full_key = f"{prefix}.{key}" if prefix else str(key)
            if isinstance(value, dict):
                rows.extend(cls._metadata_from_mapping(value, artifact_type, full_key))
            else:
                rows.append(
                    {
                        "artifact_type": artifact_type,
                        "key": full_key,
                        "value": cls._serialize_cell(value),
                    }
                )
        return rows

    @staticmethod
    def _looks_like_croissant(records: dict[str, Any]) -> bool:
        """Return whether a JSON object resembles an MLCommons Croissant manifest."""
        has_croissant_sections = any(
            key in records for key in ("recordSet", "distribution", "field")
        )
        return has_croissant_sections and (
            "conformsTo" in records or "@context" in records
        )

    @classmethod
    def _croissant_to_dataframe(cls, records: dict[str, Any]) -> pd.DataFrame:
        """Flatten Croissant dataset metadata into chartable manifest rows."""
        rows: list[dict[str, Any]] = [
            {
                "artifact_type": "croissant_dataset",
                "section": "dataset",
                "name": records.get("name"),
                "description": records.get("description"),
                "value": cls._serialize_cell(records.get("url")),
            }
        ]
        for section in ("distribution", "recordSet", "field"):
            values = records.get(section) or []
            if isinstance(values, dict):
                values = [values]
            for item in values:
                if not isinstance(item, dict):
                    continue
                rows.append(
                    {
                        "artifact_type": "croissant_manifest",
                        "section": section,
                        "name": item.get("name") or item.get("@id"),
                        "description": item.get("description"),
                        "value": cls._serialize_cell(item),
                    }
                )
        return pd.DataFrame(rows)

    @staticmethod
    def _looks_like_label_studio(records: dict[str, Any]) -> bool:
        """Return whether a JSON object resembles a Label Studio export."""
        return "annotations" in records and (
            "data" in records or "predictions" in records or "id" in records
        )

    @classmethod
    def _label_studio_to_dataframe(cls, records: Any) -> pd.DataFrame:
        """Flatten Label Studio task exports into task/annotation rows."""
        tasks = records if isinstance(records, list) else [records]
        rows = []
        for task in tasks:
            if not isinstance(task, dict):
                continue
            annotations = task.get("annotations") or []
            if not annotations:
                rows.append(
                    {
                        "artifact_type": "label_studio_task",
                        "task_id": task.get("id"),
                        "data": cls._serialize_cell(task.get("data")),
                    }
                )
                continue
            for annotation in annotations:
                rows.append(
                    {
                        "artifact_type": "label_studio_annotation",
                        "task_id": task.get("id"),
                        "annotation_id": annotation.get("id"),
                        "completed_by": annotation.get("completed_by"),
                        "result_count": len(annotation.get("result") or []),
                        "data": cls._serialize_cell(task.get("data")),
                        "annotation": cls._serialize_cell(annotation),
                    }
                )
        return pd.DataFrame(rows)

    @classmethod
    def _coco_to_dataframe(cls, records: dict[str, Any]) -> pd.DataFrame:
        """Flatten COCO annotations into annotation-first rows."""
        images = {item.get("id"): item for item in records.get("images", [])}
        categories = {item.get("id"): item for item in records.get("categories", [])}
        rows = []
        for annotation in records.get("annotations", []):
            image = images.get(annotation.get("image_id"), {})
            category = categories.get(annotation.get("category_id"), {})
            rows.append(
                {
                    "artifact_type": "coco_annotation",
                    "annotation_id": annotation.get("id"),
                    "image_id": annotation.get("image_id"),
                    "image_file_name": image.get("file_name"),
                    "category_id": annotation.get("category_id"),
                    "category_name": category.get("name"),
                    "bbox": cls._serialize_cell(annotation.get("bbox")),
                    "area": annotation.get("area"),
                    "iscrowd": annotation.get("iscrowd"),
                }
            )
        if not rows:
            rows.extend(
                {
                    "artifact_type": "coco_image",
                    "image_id": image.get("id"),
                    "image_file_name": image.get("file_name"),
                    "width": image.get("width"),
                    "height": image.get("height"),
                }
                for image in records.get("images", [])
            )
        return pd.DataFrame(rows)

    @staticmethod
    def _serialize_cell(value: Any) -> Any:
        """Serialize nested values so dataframe rows can be written to SQL."""
        if isinstance(value, (dict, list, tuple)):
            return json.dumps(value)
        return value

    @classmethod
    def _normalize_dataframe(cls, df: pd.DataFrame) -> pd.DataFrame:
        """Convert nested cell values to compact JSON strings."""
        if df.empty:
            return df
        # pandas 3.0 removed DataFrame.applymap; map is the supported API.
        return df.map(cls._serialize_cell)

    @staticmethod
    def _artifact_category(extension: str) -> str:
        if extension in {".faiss", ".index", ".hnsw", ".ann"}:
            return "vector_index"
        if extension in {".safetensors", ".onnx", ".gguf"}:
            return "model_artifact"
        return "ai_artifact"

    def _artifact_metadata_frame(
        self,
        file: FileStorage,
        artifact_type: str,
        warnings: list[str],
    ) -> pd.DataFrame:
        file.stream.seek(0, io.SEEK_END)
        size = file.stream.tell()
        file.seek(0)
        return pd.DataFrame(
            [
                {
                    "filename": Path(file.filename or "").name,
                    "extension": self._extension(file),
                    "size_bytes": size,
                    "artifact_type": artifact_type,
                    "warning": " ".join(warnings),
                }
            ]
        )

    def _read_sql_dump(self, file: FileStorage, nrows: int | None) -> pd.DataFrame:
        text = self._decode_file(file)
        df = self._parse_insert_dump(text, self._options.get("sql_table"))
        return self._normalize_dataframe(df.head(nrows) if nrows else df)

    @classmethod
    def _parse_insert_dump(  # noqa: C901
        cls,
        text: str,
        selected_table: str | None = None,
    ) -> pd.DataFrame:
        text = _COMMENT_BLOCK.sub("", _COMMENT_LINE.sub("", text))
        tables: dict[tuple[str, tuple[str, ...]], list[list[Any]]] = {}
        i = 0
        found = False
        while i < len(text):
            match = _INSERT_RE.search(text, i)
            if not match:
                break
            found = True
            table = match.group(1).strip('`"[]')
            column_spec = match.group(2)
            rows, end = cls._parse_row_tuples(text, match.end())
            if not rows:
                i = end
                continue
            columns = (
                tuple(cls._parse_column_list(column_spec))
                if column_spec
                else tuple(f"col_{idx}" for idx in range(len(rows[0])))
            )
            key = (table, columns)
            if selected_table and table.lower() != selected_table.lower():
                i = end
                continue
            bucket = tables.setdefault(key, [])
            for row in rows:
                if len(row) != len(columns):
                    raise DatabaseUploadFailed(
                        message=_(
                            "SQL dump row has %(actual)s values, expected %(expected)s",
                            actual=len(row),
                            expected=len(columns),
                        )
                    )
                bucket.append(row)
            i = end

        if not found:
            raise DatabaseUploadFailed(_("SQL dump contains no INSERT statements"))
        if selected_table and not tables:
            raise DatabaseUploadFailed(
                message=_(
                    "SQL dump contains no INSERT rows for table %(table_name)s",
                    table_name=selected_table,
                )
            )
        if len(tables) != 1:
            raise DatabaseUploadFailed(
                _(
                    "Multi-table SQL dumps must be split and uploaded one table "
                    "at a time"
                )
            )
        (_table_name, columns), rows = next(iter(tables.items()))
        if not rows:
            raise DatabaseUploadFailed(_("SQL dump contains no data rows"))
        return pd.DataFrame(rows, columns=list(columns))

    @staticmethod
    def _parse_column_list(spec: str) -> list[str]:
        columns: list[str] = []
        buffer: list[str] = []
        quote: str | None = None
        for char in spec:
            if quote is None:
                if char == ",":
                    token = "".join(buffer).strip()
                    if token:
                        columns.append(token.strip('`"[] '))
                    buffer = []
                    continue
                if char in {'"', "`", "["}:
                    quote = "]" if char == "[" else char
            elif char == quote:
                quote = None
            buffer.append(char)
        if quote is not None:
            raise DatabaseUploadFailed(_("Unterminated quoted identifier in SQL dump"))
        token = "".join(buffer).strip()
        if token:
            columns.append(token.strip('`"[] '))
        return columns

    @classmethod
    def _parse_row_tuples(  # noqa: C901
        cls,
        text: str,
        start: int,
    ) -> tuple[list[list[Any]], int]:
        i = start
        rows: list[list[Any]] = []
        while i < len(text):
            while i < len(text) and text[i] in " \t\n\r":
                i += 1
            if i >= len(text):
                break
            if text[i] == ";":
                return rows, i + 1
            if text[i] == ",":
                i += 1
                continue
            if text[i] != "(":
                break
            i += 1
            row: list[Any] = []
            closed = False
            while i < len(text):
                while i < len(text) and text[i] in " \t\n\r":
                    i += 1
                if i < len(text) and text[i] == ")":
                    i += 1
                    closed = True
                    break
                value, i = cls._parse_value(text, i)
                row.append(value)
                while i < len(text) and text[i] in " \t\n\r":
                    i += 1
                if i < len(text) and text[i] == ",":
                    i += 1
            if not closed:
                raise DatabaseUploadFailed(_("Unterminated row tuple in SQL dump"))
            rows.append(row)
        return rows, i

    @classmethod
    def _parse_value(cls, text: str, i: int) -> tuple[Any, int]:  # noqa: C901
        while i < len(text) and text[i] in " \t\n\r":
            i += 1
        if i >= len(text):
            raise DatabaseUploadFailed(_("Unexpected end of SQL VALUES clause"))
        if i + 1 < len(text) and text[i] in {"N", "n"} and text[i + 1] in "'\"":
            return cls._parse_string(text, i + 1)
        if text[i] in "'\"":
            return cls._parse_string(text, i)
        start = i
        while i < len(text) and text[i] not in ",) \t\n\r":
            i += 1
        token = text[start:i]
        upper = token.upper()
        if upper in {"DATE", "DATETIME", "TIMESTAMP", "TO_DATE"}:
            while i < len(text) and text[i] in " \t\n\r":
                i += 1
            if i < len(text) and text[i] in "'\"":
                return cls._parse_string(text, i)
        if upper == "NULL":
            return None, i
        if upper in {"TRUE", "FALSE"}:
            return upper == "TRUE", i
        try:
            value = float(token) if any(char in token for char in ".eE") else int(token)
            return value, i
        except ValueError:
            return token, i

    @staticmethod
    def _parse_string(text: str, i: int) -> tuple[str, int]:
        quote = text[i]
        i += 1
        buffer: list[str] = []
        escapes = {
            "n": "\n",
            "t": "\t",
            "r": "\r",
            "\\": "\\",
            "'": "'",
            '"': '"',
            "0": "\x00",
        }
        while i < len(text):
            char = text[i]
            if char == quote:
                if i + 1 < len(text) and text[i + 1] == quote:
                    buffer.append(quote)
                    i += 2
                    continue
                return "".join(buffer), i + 1
            if char == "\\" and i + 1 < len(text):
                next_char = text[i + 1]
                if next_char in escapes:
                    buffer.append(escapes[next_char])
                    i += 2
                    continue
            buffer.append(char)
            i += 1
        raise DatabaseUploadFailed(_("Unterminated SQL string literal"))

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

import re
import sqlite3
import tempfile
from pathlib import Path
from typing import Any, Optional

import pandas as pd
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
from superset.utils import json

ROWS_TO_READ_METADATA = 100

_INSERT_RE = re.compile(
    r"INSERT\s+INTO\s+([\w.\"`\[\]]+)\s*(?:\(([^)]+)\))?\s*VALUES\s*",
    re.IGNORECASE,
)
_COMMENT_LINE = re.compile(r"--[^\n]*")
_COMMENT_BLOCK = re.compile(r"/\*.*?\*/", re.DOTALL)


class StructuredReaderOptions(ReaderOptions, total=False):
    sqlite_table: str


class StructuredReader(BaseDataReader):
    """Read structured single-table uploads into a DataFrame."""

    def __init__(self, options: Optional[StructuredReaderOptions] = None) -> None:
        options = options or {}
        super().__init__(options=dict(options))

    def file_to_dataframe(self, file: FileStorage) -> pd.DataFrame:
        """Read a supported structured upload into a DataFrame."""
        return self._read_file(file)

    def file_metadata(self, file: FileStorage) -> FileMetadata:
        """Return rich metadata for a structured upload."""
        df = self._read_file(file, nrows=ROWS_TO_READ_METADATA)
        return {"items": [build_upload_metadata_item(df, None)]}

    def _read_file(
        self,
        file: FileStorage,
        nrows: Optional[int] = None,
    ) -> pd.DataFrame:
        extension = Path(file.filename or "").suffix.lower()
        try:
            if extension in {".json"}:
                return self._read_json(file, nrows)
            if extension in {".jsonl", ".ndjson"}:
                return self._read_json_lines(file, nrows)
            if extension == ".xml":
                return self._read_xml(file, nrows)
            if extension in {".sql", ".dump"}:
                return self._read_sql_dump(file, nrows)
            if extension in {".sqlite", ".sqlite3", ".db"}:
                return self._read_sqlite(file, nrows)
        except DatabaseUploadFailed:
            raise
        except Exception as ex:
            raise DatabaseUploadFailed(
                message=_("Error reading structured file: %(error)s", error=str(ex))
            ) from ex
        raise DatabaseUploadFailed(_("Unsupported structured file extension"))

    @staticmethod
    def _decode_file(file: FileStorage) -> str:
        file.seek(0)
        raw = file.read()
        if isinstance(raw, str):
            return raw
        for encoding in ("utf-8-sig", "utf-8", "latin-1", "cp1252"):
            try:
                return raw.decode(encoding)
            except UnicodeDecodeError:
                continue
        raise DatabaseUploadFailed(_("Could not decode structured text file"))

    @staticmethod
    def _records_to_dataframe(records: Any) -> pd.DataFrame:
        if isinstance(records, list):
            return pd.json_normalize(records)
        if isinstance(records, dict):
            list_values = [
                (key, value)
                for key, value in records.items()
                if isinstance(value, list) and value
            ]
            if len(list_values) == 1:
                return pd.json_normalize(list_values[0][1])
            return pd.json_normalize(records)
        raise DatabaseUploadFailed(_("JSON file must contain an object or an array"))

    def _read_json(self, file: FileStorage, nrows: Optional[int]) -> pd.DataFrame:
        data = json.loads(self._decode_file(file))
        df = self._records_to_dataframe(data)
        return df.head(nrows) if nrows else df

    def _read_json_lines(
        self,
        file: FileStorage,
        nrows: Optional[int],
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
        return pd.json_normalize(records)

    def _read_xml(self, file: FileStorage, nrows: Optional[int]) -> pd.DataFrame:
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
        return pd.DataFrame(rows)

    def _read_sqlite(self, file: FileStorage, nrows: Optional[int]) -> pd.DataFrame:
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
                    return pd.read_sql_query(query, connection)
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

    def _read_sql_dump(self, file: FileStorage, nrows: Optional[int]) -> pd.DataFrame:
        text = self._decode_file(file)
        df = self._parse_insert_dump(text)
        return df.head(nrows) if nrows else df

    @classmethod
    def _parse_insert_dump(cls, text: str) -> pd.DataFrame:
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
    def _parse_value(cls, text: str, i: int) -> tuple[Any, int]:
        while i < len(text) and text[i] in " \t\n\r":
            i += 1
        if i >= len(text):
            raise DatabaseUploadFailed(_("Unexpected end of SQL VALUES clause"))
        if text[i] in "'\"":
            return cls._parse_string(text, i)
        start = i
        while i < len(text) and text[i] not in ",) \t\n\r":
            i += 1
        token = text[start:i]
        upper = token.upper()
        if upper == "NULL":
            return None, i
        if upper in {"TRUE", "FALSE"}:
            return upper == "TRUE", i
        try:
            value = float(token) if any(char in token for char in ".eE") else int(token)
            return value, i
        except ValueError:
            raise DatabaseUploadFailed(
                message=_("Unsupported SQL VALUES token: %(token)s", token=token)
            ) from None

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

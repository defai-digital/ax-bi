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
from collections.abc import Generator
from io import BytesIO
from pathlib import Path
from typing import Any, IO
from zipfile import BadZipfile, is_zipfile, ZipFile

import pandas as pd
import pyarrow.parquet as pq
from flask_babel import lazy_gettext as _
from pyarrow.lib import ArrowException
from werkzeug.datastructures import FileStorage

from superset.commands.database.exceptions import DatabaseUploadFailed
from superset.commands.database.uploaders.base import (
    BaseDataReader,
    build_upload_metadata_item,
    FileMetadata,
    ReaderOptions,
)
from superset.exceptions import SupersetException
from superset.utils.core import check_is_safe_zip

logger = logging.getLogger(__name__)
ROWS_TO_READ_METADATA = 100


class ColumnarReaderOptions(ReaderOptions, total=False):
    columns_read: list[str]


class ColumnarReader(BaseDataReader):
    def __init__(
        self,
        options: ColumnarReaderOptions | None = None,
    ) -> None:
        options = options or {}
        super().__init__(
            options=dict(options),
        )

    def _read_buffer_to_dataframe(
        self,
        buffer: IO[bytes],
        extension: str,
    ) -> pd.DataFrame:
        columns = self._options.get("columns_read")
        try:
            if extension == ".orc":
                kwargs: dict[str, Any] = {"path": buffer}
                if columns:
                    kwargs["columns"] = columns
                return pd.read_orc(**kwargs)
            if extension in {".feather", ".arrow", ".ipc"}:
                kwargs = {"path": buffer}
                if columns:
                    kwargs["columns"] = columns
                return pd.read_feather(**kwargs)
            kwargs = {"path": buffer}
            if columns:
                kwargs["columns"] = columns
            return pd.read_parquet(**kwargs)
        except (
            pd.errors.ParserError,
            pd.errors.EmptyDataError,
            UnicodeDecodeError,
            ValueError,
        ) as ex:
            raise DatabaseUploadFailed(
                message=_("Parsing error: %(error)s", error=str(ex))
            ) from ex
        except Exception as ex:
            raise DatabaseUploadFailed(_("Error reading Columnar file")) from ex

    @staticmethod
    def _yield_files(file: FileStorage) -> Generator[tuple[IO[bytes], str], None, None]:
        """
        Yields files from the provided file. If the file is a zip file, it yields each
        file within the zip file. If it's a single file, it yields the file itself.

        :param file: The file to yield files from.
        :return: A generator that yields files.
        """
        file_suffix = Path(file.filename).suffix.lower()
        if not file_suffix:
            raise DatabaseUploadFailed(_("Unexpected no file extension found"))
        file_suffix = file_suffix[1:]  # remove the dot
        if file_suffix == "zip":
            if not is_zipfile(file):
                raise DatabaseUploadFailed(_("Not a valid ZIP file"))
            try:
                with ZipFile(file) as zip_file:
                    # guard against decompression bombs before reading entries,
                    # mirroring the importer path
                    try:
                        check_is_safe_zip(zip_file)
                    except SupersetException as ex:
                        raise DatabaseUploadFailed(str(ex)) from ex
                    # check if all file types are of the same extension
                    filenames = [
                        name for name in zip_file.namelist() if not name.endswith("/")
                    ]
                    if not filenames:
                        raise DatabaseUploadFailed(_("ZIP file contains no files"))
                    file_suffixes = {Path(name).suffix.lower() for name in filenames}
                    if len(file_suffixes) > 1:
                        raise DatabaseUploadFailed(
                            _("ZIP file contains multiple file types")
                        )
                    for filename in filenames:
                        with zip_file.open(filename) as file_in_zip:
                            yield (
                                BytesIO(file_in_zip.read()),
                                Path(filename).suffix.lower(),
                            )
            except BadZipfile as ex:
                raise DatabaseUploadFailed(_("Not a valid ZIP file")) from ex
        else:
            yield file, f".{file_suffix}"

    def file_to_dataframe(self, file: FileStorage) -> pd.DataFrame:
        """
        Read Columnar file into a DataFrame

        :return: pandas DataFrame
        :throws DatabaseUploadFailed: if there is an error reading the file
        """
        frames = [
            self._read_buffer_to_dataframe(buffer, extension)
            for buffer, extension in self._yield_files(file)
        ]
        if not frames:
            raise DatabaseUploadFailed(_("Columnar upload contains no files"))
        return pd.concat(frames)

    def file_metadata(self, file: FileStorage) -> FileMetadata:  # noqa: C901
        column_names: list[str] = []
        sample_frames: list[pd.DataFrame] = []
        rows_remaining = ROWS_TO_READ_METADATA
        try:
            for file_item, extension in self._yield_files(file):
                if extension == ".parquet":
                    parquet_file = pq.ParquetFile(file_item)
                    for column_name in parquet_file.metadata.schema.names:  # pylint: disable=no-member
                        if column_name not in column_names:
                            column_names.append(column_name)
                    if rows_remaining <= 0:
                        continue
                    try:
                        batch = next(
                            parquet_file.iter_batches(
                                batch_size=rows_remaining,
                                columns=self._options.get("columns_read"),
                            )
                        )
                    except StopIteration:
                        continue
                    frame = batch.to_pandas()
                else:
                    frame = self._read_buffer_to_dataframe(file_item, extension).head(
                        rows_remaining
                    )
                    for column_name in frame.columns:
                        if column_name not in column_names:
                            column_names.append(str(column_name))
                sample_frames.append(frame)
                rows_remaining -= len(frame)
        except ArrowException as ex:
            raise DatabaseUploadFailed(
                message=_("Parsing error: %(error)s", error=str(ex))
            ) from ex
        if sample_frames:
            df = pd.concat(sample_frames, ignore_index=True)
        else:
            df = pd.DataFrame(columns=list(column_names))
        return {"items": [build_upload_metadata_item(df, None)]}

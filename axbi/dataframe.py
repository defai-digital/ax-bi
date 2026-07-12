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
"""AxBI utilities for pandas.DataFrame."""

import logging
from typing import Any

import numpy as np
import pandas as pd

from axbi.utils.core import JS_MAX_INTEGER

logger = logging.getLogger(__name__)


def _convert_big_integers(val: Any) -> Any:
    """
    Cast integers larger than ``JS_MAX_INTEGER`` to strings.

    :param val: the value to process
    :returns: the same value but recast as a string if it was an integer over
        ``JS_MAX_INTEGER``
    """
    return str(val) if isinstance(val, int) and abs(val) > JS_MAX_INTEGER else val


def _is_na(val: Any) -> bool:
    """
    Check if a value is NA/NaN for scalar values only.

    pd.isna() raises ValueError for arrays/lists, so we catch that case.

    :param val: the value to check
    :returns: True if the value is NA/NaN, False otherwise
    """
    try:
        return bool(pd.isna(val))
    except ValueError:
        # pd.isna raises ValueError for arrays (e.g., lists, dicts from JSON)
        return False


def _get_columns_by_dtype(
    dframe: pd.DataFrame,
) -> tuple[pd.Index, pd.Index, pd.Index]:
    """Return columns that need specialized record conversion.

    Includes pandas 3.0+ dedicated ``str`` dtype alongside classic ``object``
    columns so NA values still convert to JSON-safe ``None``.
    """
    return (
        dframe.select_dtypes(include=["floating"]).columns,
        dframe.select_dtypes(include=["integer"]).columns,
        dframe.select_dtypes(include=["object", "string"]).columns,
    )


def _get_float_conversions(
    dframe: pd.DataFrame,
    float_cols: pd.Index,
) -> dict[str, Any]:
    """Build replacements for float columns containing NaN values."""
    converted: dict[str, Any] = {}
    for col in float_cols:
        arr = dframe[col].values
        mask = np.isnan(arr)
        if mask.any():
            result = arr.astype(object)
            result[mask] = None
            converted[col] = result
    return converted


def _get_integer_conversions(
    dframe: pd.DataFrame,
    int_cols: pd.Index,
) -> dict[str, Any]:
    """Build replacements for integer columns containing JS-unsafe values."""
    converted: dict[str, Any] = {}
    for col in int_cols:
        arr = dframe[col].values
        big_mask = np.abs(arr) > JS_MAX_INTEGER
        if big_mask.any():
            result = arr.astype(object)
            result[big_mask] = arr[big_mask].astype(str)
            converted[col] = result
    return converted


def _get_object_conversions(
    dframe: pd.DataFrame,
    object_cols: pd.Index,
) -> dict[str, Any]:
    """Build replacements for object/string columns containing null values.

    Cast to a plain object ndarray before null replacement so pandas 3.0+
    Arrow-backed ``str`` dtypes do not keep NA as ``nan`` after assignment.
    """
    converted: dict[str, Any] = {}
    for col in object_cols:
        series = dframe[col]
        null_mask = series.isna()
        if null_mask.any():
            # object ndarray so we can put Python None (JSON-safe) in place of NA
            result = series.astype(object).to_numpy(copy=True)
            result[null_mask.to_numpy()] = None
            converted[col] = result
    return converted


def _convert_object_column_big_integers(
    records: list[dict[str, Any]],
    object_cols: pd.Index,
) -> None:
    """Convert JS-unsafe integers that live inside object columns."""
    # Pre-filter: skip columns whose non-null values are all strings, since
    # those cannot contain big integers.  This avoids a per-record isinstance
    # check on every text column, which is the common case.
    cols_with_non_str: set[str] = set()
    for col in object_cols:
        for record in records:
            val = record.get(col)
            if val is not None and not isinstance(val, str):
                cols_with_non_str.add(col)
                break

    if not cols_with_non_str:
        return

    for record in records:
        for key in cols_with_non_str:
            if key in record:
                record[key] = _convert_big_integers(record[key])


def df_to_records(dframe: pd.DataFrame) -> list[dict[str, Any]]:
    """
    Convert a DataFrame to a set of records.

    NaN values are converted to None for JSON compatibility.
    This handles division by zero and other operations that produce NaN.
    Big integers (> JS_MAX_INTEGER) are converted to strings.

    Uses vectorized numpy operations for float and integer columns where
    possible, falling back to per-value checks only for object columns.

    :param dframe: the DataFrame to convert
    :returns: a list of dictionaries reflecting each single row of the DataFrame
    """
    if not dframe.columns.is_unique:
        logger.warning(
            "DataFrame columns are not unique, some columns will be omitted."
        )

    float_cols, int_cols, object_cols = _get_columns_by_dtype(dframe)

    needs_processing = len(float_cols) > 0 or len(int_cols) > 0 or len(object_cols) > 0

    if not needs_processing:
        return dframe.to_dict(orient="records")

    converted = {
        **_get_float_conversions(dframe, float_cols),
        **_get_integer_conversions(dframe, int_cols),
        **_get_object_conversions(dframe, object_cols),
    }

    # Apply conversions and build records. Force object dtype for replaced
    # columns so pandas 3.0+ does not re-infer Arrow ``str`` and turn
    # Python ``None`` back into NA/nan before ``to_dict``.
    if converted:
        df_processed = dframe.copy()
        for col, values in converted.items():
            df_processed[col] = pd.Series(
                values, index=df_processed.index, dtype=object
            )
    else:
        df_processed = dframe

    records = df_processed.to_dict(orient="records")

    # Post-process: big-int check for integer columns that were NOT
    # vectorized (e.g., int values in object columns) and any remaining
    # edge cases in object columns.
    if len(object_cols) > 0:
        _convert_object_column_big_integers(records, object_cols)

    return records

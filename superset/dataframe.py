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
"""Superset utilities for pandas.DataFrame."""

import logging
from typing import Any

import numpy as np
import pandas as pd

from superset.utils.core import JS_MAX_INTEGER

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

    # Identify column types for vectorized processing
    float_cols = dframe.select_dtypes(include=["floating"]).columns
    int_cols = dframe.select_dtypes(include=["integer"]).columns
    object_cols = dframe.select_dtypes(include=["object"]).columns

    needs_processing = (
        len(float_cols) > 0 or len(int_cols) > 0 or len(object_cols) > 0
    )

    if not needs_processing:
        return dframe.to_dict(orient="records")

    # Build converted columns for vectorized NaN/big-int handling
    converted: dict[str, Any] = {}

    # Float columns: replace NaN with None (vectorized), preserve Inf
    for col in float_cols:
        arr = dframe[col].values
        mask = np.isnan(arr)
        if mask.any():
            # Create an object array with None where NaN
            result = arr.astype(object)
            result[mask] = None
            converted[col] = result

    # Integer columns: convert big ints to strings (vectorized)
    for col in int_cols:
        arr = dframe[col].values
        big_mask = np.abs(arr) > JS_MAX_INTEGER
        if big_mask.any():
            result = arr.astype(object)
            result[big_mask] = arr[big_mask].astype(str)
            converted[col] = result

    # Object columns: per-value NaN check (can't vectorize mixed-type columns)
    for col in object_cols:
        series = dframe[col]
        null_mask = series.isna()
        if null_mask.any():
            result = series.values.copy()
            result[null_mask] = None
            converted[col] = result

    # Apply conversions and build records
    if converted:
        df_processed = dframe.assign(**converted)
    else:
        df_processed = dframe

    records = df_processed.to_dict(orient="records")

    # Post-process: big-int check for integer columns that were NOT
    # vectorized (e.g., int values in object columns) and any remaining
    # edge cases in object columns.
    if len(object_cols) > 0:
        object_col_set = set(object_cols)
        for record in records:
            for key in object_col_set:
                if key in record:
                    record[key] = _convert_big_integers(record[key])

    return records

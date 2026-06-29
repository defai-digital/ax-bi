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
"""Fast JSON serialization using orjson for chart data responses.

This module provides a high-performance JSON serializer that is 5-10x faster
than simplejson for large payloads (10K+ rows). It is designed as a drop-in
replacement for the chart data API hot path where DataFrames have already
been converted to primitive Python types.

orjson serializes to bytes natively in C, so we decode to str for
Flask ``make_response()`` compatibility.  The decode step is still far
faster than simplejson's pure-Python str output for large payloads.

Usage::

    from superset.utils.json_fast import dumps_fast

    response_data = dumps_fast(payload)
"""

from __future__ import annotations

import logging
from datetime import date, datetime, time
from typing import Any

import numpy as np
import orjson
import pandas as pd

from superset.utils.dates import datetime_to_epoch, EPOCH
from superset.utils.json import base_json_conv

logger = logging.getLogger(__name__)

# orjson option flags
_ORJSON_OPTS = orjson.OPT_SERIALIZE_NUMPY


def _orjson_default(obj: Any) -> Any:
    """Default handler for orjson that matches superset.utils.json behavior.

    Handles:
    - datetime / pd.Timestamp -> epoch milliseconds (float), matching
      ``json_int_dttm_ser``
    - date -> epoch milliseconds (float)
    - time -> ISO 8601 string
    - All other types -> delegated to ``base_json_conv`` (bytes, UUID,
      Decimal, set, memoryview, timedelta, LazyString, pd.DateOffset,
      np.int64, np.bool_, np.ndarray)
    """
    if isinstance(obj, (datetime, pd.Timestamp)):
        return datetime_to_epoch(obj)

    if isinstance(obj, date):
        return (obj - EPOCH.date()).total_seconds() * 1000

    if isinstance(obj, time):
        return obj.isoformat()

    if isinstance(obj, float):
        # orjson serializes NaN/Inf by default as null, but if we get here
        # via some edge case, handle it explicitly
        if np.isnan(obj) or np.isinf(obj):
            return None
        return obj

    # Delegate to base_json_conv for numpy types, bytes, UUID, Decimal, etc.
    return base_json_conv(obj)


def dumps_fast(obj: Any) -> str:
    """Serialize ``obj`` to a JSON string using orjson.

    This is the fast-path serializer for chart data responses.
    It handles the same types as ``superset.utils.json.dumps()`` with
    ``default=json_int_dttm_ser`` but is 5-10x faster for large payloads.

    NaN and Inf float values are serialized as ``null``.
    Datetime objects are serialized as epoch milliseconds (matching
    ``json_int_dttm_ser`` behavior).

    :param obj: The object to serialize (typically a dict with "result" key
        containing a list of query result dicts)
    :returns: A JSON string
    """
    return orjson.dumps(
        obj,
        default=_orjson_default,
        option=_ORJSON_OPTS,
    ).decode("utf-8")


def dumps_fast_bytes(obj: Any) -> bytes:
    """Serialize ``obj`` to JSON bytes using orjson.

    Use this when the caller can work with bytes directly (e.g., writing
    to Redis or streaming responses), avoiding the UTF-8 decode overhead.

    :param obj: The object to serialize
    :returns: JSON-encoded bytes
    """
    return orjson.dumps(
        obj,
        default=_orjson_default,
        option=_ORJSON_OPTS,
    )

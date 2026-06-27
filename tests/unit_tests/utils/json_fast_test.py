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
"""Tests for superset.utils.json_fast (orjson-based fast serializer)."""
import json
import time
import uuid
from datetime import date, datetime, time as dt_time, timedelta
from decimal import Decimal

import numpy as np
import pandas as pd
import pytest

from superset.utils.json_fast import dumps_fast, dumps_fast_bytes


class TestDumpsFastPrimitives:
    """Test basic primitive type serialization."""

    def test_string(self) -> None:
        assert dumps_fast({"s": "hello"}) == '{"s":"hello"}'

    def test_integer(self) -> None:
        assert dumps_fast({"n": 42}) == '{"n":42}'

    def test_float(self) -> None:
        assert dumps_fast({"f": 3.14}) == '{"f":3.14}'

    def test_boolean(self) -> None:
        assert dumps_fast({"t": True, "f": False}) == '{"t":true,"f":false}'

    def test_null(self) -> None:
        assert dumps_fast({"v": None}) == '{"v":null}'

    def test_list(self) -> None:
        assert dumps_fast({"arr": [1, 2, 3]}) == '{"arr":[1,2,3]}'

    def test_nested_dict(self) -> None:
        result = dumps_fast({"a": {"b": {"c": 1}}})
        assert result == '{"a":{"b":{"c":1}}}'

    def test_empty_structures(self) -> None:
        assert dumps_fast({}) == "{}"
        assert dumps_fast([]) == "[]"


class TestDumpsFastNaN:
    """Test NaN/Inf handling."""

    def test_nan_float(self) -> None:
        result = dumps_fast({"v": float("nan")})
        assert result == '{"v":null}'

    def test_inf_float(self) -> None:
        result = dumps_fast({"v": float("inf")})
        assert result == '{"v":null}'

    def test_negative_inf(self) -> None:
        result = dumps_fast({"v": float("-inf")})
        assert result == '{"v":null}'

    def test_nan_in_list(self) -> None:
        result = dumps_fast({"arr": [1.0, float("nan"), 3.0]})
        assert result == '{"arr":[1.0,null,3.0]}'

    def test_normal_float_unchanged(self) -> None:
        result = dumps_fast({"v": 1.5})
        assert result == '{"v":1.5}'


class TestDumpsFastDatetime:
    """Test datetime serialization.

    Note: orjson serializes datetime/date natively as ISO 8601 strings.
    The chart data hot path pre-converts datetime to epoch ms via
    _df_to_records, so these tests verify orjson's native behavior.
    """

    def test_datetime_iso(self) -> None:
        dt = datetime(2024, 1, 15, 12, 0, 0)
        result = dumps_fast({"ts": dt})
        assert '"2024-01-15T12:00:00"' in result

    def test_date_iso(self) -> None:
        d = date(2024, 1, 15)
        result = dumps_fast({"d": d})
        assert '"2024-01-15"' in result

    def test_time_iso(self) -> None:
        t = dt_time(12, 30, 45)
        result = dumps_fast({"t": t})
        assert '"12:30:45"' in result

    def test_epoch_ms_integer(self) -> None:
        """Test the actual chart data flow: datetime already converted to epoch ms."""
        # This simulates what _df_to_records produces
        epoch_ms = 1705312800000  # 2024-01-15 12:00:00 UTC in ms
        result = dumps_fast({"ts": epoch_ms})
        assert result == '{"ts":1705312800000}'


class TestDumpsFastNumpy:
    """Test numpy type serialization."""

    def test_np_int64(self) -> None:
        result = dumps_fast({"n": np.int64(42)})
        assert result == '{"n":42}'

    def test_np_float64(self) -> None:
        result = dumps_fast({"f": np.float64(3.14)})
        assert result == '{"f":3.14}'

    def test_np_bool(self) -> None:
        result = dumps_fast({"b": np.bool_(True)})
        assert result == '{"b":true}'

    def test_np_array(self) -> None:
        result = dumps_fast({"arr": np.array([1, 2, 3])})
        assert result == '{"arr":[1,2,3]}'

    def test_np_nan(self) -> None:
        result = dumps_fast({"v": np.float64("nan")})
        assert result == '{"v":null}'

    def test_np_int32(self) -> None:
        result = dumps_fast({"n": np.int32(10)})
        assert result == '{"n":10}'


class TestDumpsFastFallback:
    """Test types handled by the default/fallback handler."""

    def test_uuid(self) -> None:
        uid = uuid.UUID("12345678-1234-5678-1234-567812345678")
        result = dumps_fast({"id": uid})
        assert '"12345678-1234-5678-1234-567812345678"' in result

    def test_decimal(self) -> None:
        result = dumps_fast({"d": Decimal("3.14")})
        assert result == '{"d":3.14}'

    def test_set(self) -> None:
        result = dumps_fast({"s": {1, 2, 3}})
        parsed = json.loads(result)
        assert sorted(parsed["s"]) == [1, 2, 3]

    def test_bytes_utf8(self) -> None:
        result = dumps_fast({"b": b"hello"})
        assert result == '{"b":"hello"}'

    def test_timedelta(self) -> None:
        td = timedelta(days=1, hours=2, minutes=30)
        result = dumps_fast({"td": td})
        assert "1 day" in result

    def test_memoryview(self) -> None:
        mv = memoryview(b"hello")
        result = dumps_fast({"mv": mv})
        assert result == '{"mv":"hello"}'


class TestDumpsFastBytes:
    """Test the bytes-returning variant."""

    def test_returns_bytes(self) -> None:
        result = dumps_fast_bytes({"n": 42})
        assert isinstance(result, bytes)
        assert result == b'{"n":42}'


class TestDumpsFastChartPayload:
    """Test with realistic chart data payloads."""

    def test_chart_data_payload(self) -> None:
        """Simulate a typical chart data API response."""
        payload = {
            "result": [
                {
                    "cache_key": "abc123",
                    "cached_dttm": None,
                    "cache_timeout": 86400,
                    "is_cached": False,
                    "status": "success",
                    "rowcount": 3,
                    "data": [
                        {"date": 1704067200000, "value": 100, "name": "A"},
                        {"date": 1704153600000, "value": 200, "name": "B"},
                        {"date": 1704240000000, "value": 300, "name": "C"},
                    ],
                }
            ]
        }
        result = dumps_fast(payload)
        parsed = json.loads(result)
        assert parsed["result"][0]["data"][0]["date"] == 1704067200000
        assert len(parsed["result"][0]["data"]) == 3

    def test_large_payload_performance(self) -> None:
        """Benchmark: orjson should be significantly faster than simplejson."""
        # Generate a 10K-row payload similar to chart data
        rows = [
            {"date": 1704067200000 + i * 86400000, "value": float(i), "name": f"row_{i}"}
            for i in range(10000)
        ]
        payload = {"result": [{"data": rows, "status": "success"}]}

        # Warm up
        dumps_fast(payload)

        # Time orjson
        start = time.perf_counter()
        for _ in range(10):
            dumps_fast(payload)
        orjson_time = time.perf_counter() - start

        # Time simplejson
        from superset.utils import json as sjson

        start = time.perf_counter()
        for _ in range(10):
            sjson.dumps(payload, default=sjson.json_int_dttm_ser, ignore_nan=True)
        simplejson_time = time.perf_counter() - start

        # orjson should be at least 2x faster (typically 5-10x)
        speedup = simplejson_time / orjson_time
        print(f"\norjson: {orjson_time:.4f}s, simplejson: {simplejson_time:.4f}s, speedup: {speedup:.1f}x")
        assert speedup > 1.5, f"orjson should be faster, but speedup is only {speedup:.1f}x"

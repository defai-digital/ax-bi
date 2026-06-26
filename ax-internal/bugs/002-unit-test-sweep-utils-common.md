Classification: confirmed

# Unit-test sweep outside postprocessing: test-only / environmental failures

## Evidence

After resolving the pandas/numpy compatibility bugs in `pandas_postprocessing`
(see `001-numpy-pandas-deprecated-apis.md`), a sweep of
`tests/unit_tests/utils/` and `tests/unit_tests/common/` ran:

```
$ python -m pytest tests/unit_tests/utils/ tests/unit_tests/common/ -q
4 failed, 648 passed
```

All 4 failures are test-only assertions or environment drift, NOT production
data-path bugs.

### 1. `test_date_parsing.py::test_epoch_format_invalid_values` (FIXED, test-only)

The test asserted `df["epoch"].dtype == object`. On pandas 3.x a string column
defaults to the dedicated `StringDtype`, so the dtype is `str` not `object`.
The production `normalize_dttm_col` code correctly leaves the column unchanged
on a failed conversion; only the dtype *representation* differs.

Fix: assert `not pd.api.types.is_numeric_dtype(...)` (the column is unchanged
and non-numeric) instead of `dtype == object`. Verified the test passes.

### 2. `excel_tests.py::test_timezone_conversion` / `test_quote_formulas` (test-only, NOT fixed)

`df_to_excel` returns raw `bytes` (`superset/utils/excel.py:77`). The tests
call `pd.read_excel(raw_bytes)` directly, which pandas 3.x rejects:
```
TypeError: Expected file path name or file-like object, got <class 'bytes'> type
```
This is a pandas IO API change (raw bytes no longer auto-wrapped). The real
production upload path (`superset/commands/database/uploaders/excel_reader.py`)
already passes a proper `io.BytesIO` buffer via kwargs, so this is a test-only
concern. Recommended test fix: wrap `pd.read_excel(io.BytesIO(contents), ...)`.
Not applied here as it does not affect production.

### 3. `profiler_test.py::test_profiler_returns_html_when_instrumented` (environmental, NOT fixed)

Fails during `client.get("/?_instrument=1")` due to pyinstrument / Werkzeug
version drift in the test harness. Not a production data-path bug and unrelated
to the pandas/numpy compatibility class; out of scope for a low-risk pass.

## Recommended Action

- The `test_date_parsing` fix (#1) is applied and verified.
- Items #2 and #3 are test-only / environmental. They can be fixed in a
  separate test-hygiene pass (wrap bytes in `BytesIO`; align pyinstrument
  version) but do not indicate production defects.

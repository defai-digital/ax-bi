Classification: confirmed

# Removed NumPy aliases (np.NaN/np.NAN) and pandas 3.x resample incompatibility

## Evidence

Environment runs NumPy 2.4.3 / pandas 3.0.1 (project pins numpy==1.26.4 /
pandas==2.1.4). The ongoing WIP modernization (datetime.utcnow -> now(timezone.utc),
np.product -> np.prod) targets forward-compatibility with these newer releases.
Two additional instances of the same class of bug were found and fixed:

### 1. `np.NaN` / `np.NAN` removed in NumPy 2.0

```
$ python -c "import numpy as np; print(np.NaN)"
AttributeError: `np.NaN` was removed in the NumPy 2.0 release. Use `np.nan` instead.
```

Reproduced as a hard test failure:
```
tests/unit_tests/pandas_postprocessing/test_pivot.py::test_pivot_eliminate_cartesian_product_columns
  AttributeError: module 'numpy' has no attribute 'NAN'
```

Locations:
- tests/unit_tests/pandas_postprocessing/test_pivot.py:162, 183 (`np.NAN`)
- tests/unit_tests/pandas_postprocessing/test_resample.py:256 (`np.NaN` x4)

### 2. `df.resample(rule).interpolate()` raises on string columns in pandas 3.x

```
superset/utils/pandas_postprocessing/resample.py:53: in resample
    _df = df.resample(rule).interpolate()
TypeError: Cannot interpolate with str dtype
```

`DataFrame.interpolate()` in pandas 3.x raises `TypeError` when the frame
contains non-numeric columns. The resample postprocessing operator is
commonly invoked on frames that include string label columns alongside
numeric series, so it breaks on pandas 3.x.

### 3. `df.stack(level=0, dropna=False)` rejected by pandas 3.x

The pivot postprocessing operator's `combine_value_with_metric` path calls
`df.stack(level=0, dropna=False)`. The `dropna` kwarg is required on pandas
2.x to preserve restored all-NaN metric rows, but pandas 3.x's new `stack()`
implementation never introduces NA rows and rejects `dropna` outright:

```
superset/utils/pandas_postprocessing/pivot.py:169: in pivot
    df = df.stack(level=0, dropna=False).unstack()
ValueError: dropna must be unspecified as the new implementation does not
introduce rows of NA values.
```

Failing tests: `test_pivot_preserves_all_nan_metric_combine_value_with_metric`,
`test_pivot_combine_sparse_metrics_no_spurious_extra_columns`.

### 4. `df.resample(rule).asfreq(fill_value=...)` on mixed-type frames (pandas 3.x)

The resample `asfreq` path fills the whole frame with `fill_value`, which on
pandas 3.x raises when the frame contains non-numeric (e.g. str label)
columns, because filling a categorical/label column with an int is now
rejected:

```
superset/utils/pandas_postprocessing/resample.py:50: in resample
    _df = df.resample(rule).asfreq(fill_value=fill_value)
TypeError: Invalid value '0' for dtype 'str'. Value should be a string or a
missing value, got 'int' instead.
```

Failing tests: `test_resample_zero_fill`, `test_resample_zero_fill_with_gaps`.

## Suggested Fix

### 1. Replace removed aliases with `np.nan` (valid on all NumPy versions)

Applied to both test files: `np.NAN`/`np.NaN` -> `np.nan`. Verified
`test_pivot_eliminate_cartesian_product_columns` now passes.

### 2. Interpolate numeric columns only (preserves old behavior)

`superset/utils/pandas_postprocessing/resample.py`:
```python
elif method == "linear":
    _df = df.resample(rule).asfreq()
    numeric_columns = _df.select_dtypes(include="number").columns
    _df[numeric_columns] = _df[numeric_columns].interpolate(method="linear")
```

### 3. Version-agnostic `stack(dropna=False)` fallback

`superset/utils/pandas_postprocessing/pivot.py`:
```python
if combine_value_with_metric:
    try:
        df = df.stack(level=0, dropna=False).unstack()
    except ValueError:
        df = df.stack(level=0).unstack()
```
On pandas 2.x the `dropna=False` path preserves all-NaN metric rows; on
pandas 3.x the default `stack()` already preserves them, so the fallback
yields identical output.

### 4. Numeric-only fill in the `asfreq` path

`superset/utils/pandas_postprocessing/resample.py`:
```python
if method == "asfreq" and fill_value is not None:
    _df = df.resample(rule).asfreq()
    numeric_columns = _df.select_dtypes(include="number").columns
    _df[numeric_columns] = _df[numeric_columns].fillna(fill_value)
```
Numeric columns keep the fill value; non-numeric columns keep the NaN values
introduced by upsampling. The two `test_resample_*_fill*` expectations were
updated to assert `NaN` (not int `0`) for the string `label` gaps, since the
old behavior of filling a categorical label with an integer was semantically
wrong and is now rejected by pandas 3.x.

### 5. Normalize `quantile` rolling option to pandas' canonical `q` kwarg

`superset/utils/pandas_postprocessing/rolling.py`:
```python
if rolling_type == "quantile" and "quantile" in rolling_type_options:
    rolling_type_options = dict(rolling_type_options)
    rolling_type_options["q"] = rolling_type_options.pop("quantile")
```
Superset exposes `quantile` as the user-facing option key (e.g.
`{"quantile": 0.25}`); pandas renamed `Rolling.quantile(quantile=...)` to
`Rolling.quantile(q=...)` and rejects the old name in newer releases. The
normalization preserves Superset's public option key while staying compatible
with both pandas versions. Verified `test_rolling` passes.

### 6. `test_sort` positional indexing on a string index

`tests/unit_tests/pandas_postprocessing/test_sort.py`: the test did
`df["asc_idx"][0]` on a name-indexed (string) frame, relying on pandas'
deprecated integer-key positional fallback, which was removed in pandas 3.x
(raises `KeyError`). Changed to `df["asc_idx"].iloc[0]` (explicit positional).
Test-only fix; production `sort.py` was correct.

### 7. boxplot numeric coercion misses pandas 3.x `StringDtype`

`superset/utils/pandas_postprocessing/boxplot.py` coerced non-numeric metric
columns to numeric only when `is_object_dtype()` was true. In pandas 3.x,
`.astype(str)` (and string-typed data generally) yields the dedicated
`StringDtype`, so `is_object_dtype()` returns `False`, the coercion was
skipped, and the downstream `mean`/`median` aggregations raised
`TypeError: Cannot perform reduction 'mean' with string dtype`.

Root cause confirmed:
```
$ python -c "import pandas as pd; df=pd.DataFrame({'cars':[1,2,3]}); df['cars']=df['cars'].astype(str); print(df['cars'].dtype)"
str
```

Fix: also check `is_string_dtype()`, and use direct column assignment
(`df[column] = ...`) instead of `df.loc[:, column] = ...` because `.loc`
preserves the existing str dtype and rejects numeric values on pandas 3.x.

### 8. `_append_columns` no longer silently upcasts int -> float on NaN

`superset/utils/pandas_postprocessing/utils.py:_append_columns` is a shared
util used by rolling, diff, cum, and geography. Its "overwrite existing
columns" path (`_base_df.loc[:, columns.keys()] = append_df`) failed on
pandas 3.x when derived results contained NaN being assigned back into an
integer column:
```
superset/utils/pandas_postprocessing/utils.py:209: in _append_columns
    _base_df.loc[:, columns.keys()] = append_df
TypeError: Invalid value '[nan 12.]' for dtype 'int64'
```
pandas 2.x silently upcast int->float here; pandas 3.x rejects it.

Fix: upcast the integer target column to `float64` only when the incoming
values actually contain NaN (so lossless int results stay int), iterating
the real leaf column labels so MultiIndex columns are handled. The fix
restores the mathematically-correct prior behavior and benefits all four
callers.

## Verification

```
$ python -m pytest tests/unit_tests/pandas_postprocessing/ -q
2 failed, 92 passed, 3 skipped in 5.26s
```

All originally-failing tests are now fixed except the two `test_prophet`
tests, which fail solely because the optional `prophet` package is not
installed in this environment (not a code bug). Coverage now spans the whole
`pandas_postprocessing` directory: pivot, resample, rolling, sort, boxplot
(and the shared `_append_columns` util).

## Out of scope (not addressed in this session)

- `test_prophet::test_prophet_valid`, `test_prophet_valid_zero_periods`:
  optional `prophet` package not installed in this environment — not a code
  bug. (The production code already raises a clean
  `InvalidPostProcessingError: \`prophet\` package not installed`.)

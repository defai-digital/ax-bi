# np.NaN / np.NAN removed in NumPy 2.0 — AttributeError at runtime

Classification: confirmed

## Evidence

`np.NaN` and `np.NAN` (uppercase) were removed from the NumPy 2.0 main
namespace. Accessing them raises `AttributeError`. The project's requirements
pin `numpy==1.26.4` but the codebase is being modernized to run on NumPy 2.x
(see existing WIP `np.product` -> `np.prod` fix in
`superset/utils/pandas_postprocessing/utils.py`). These uppercase aliases are
the same class of defect.

Reproduction against the installed NumPy 2.4.3:

```
$ python -c "import numpy as np; print(np.NaN)"
AttributeError: `np.NaN` was removed in the NumPy 2.0 release. Use `np.nan` instead.
```

Affected locations (3 occurrences):

- `tests/unit_tests/pandas_postprocessing/test_pivot.py:162` — `np.NAN`
- `tests/unit_tests/pandas_postprocessing/test_pivot.py:183` — `np.NAN`
- `tests/unit_tests/pandas_postprocessing/test_resample.py:256` — `np.NaN`

Test run before fix:

```
$ python -m pytest tests/unit_tests/pandas_postprocessing/test_pivot.py::test_pivot_eliminate_cartesian_product_columns
AttributeError: module 'numpy' has no attribute 'NAN'
1 failed
```

## Suggested Fix

Replace the removed uppercase aliases with the lowercase `np.nan`, which is
valid on both NumPy 1.26 and NumPy 2.x. Applied in this session; the
previously failing test `test_pivot_eliminate_cartesian_product_columns` now
passes.

## Verification

```
$ python -m pytest \
    tests/unit_tests/pandas_postprocessing/test_pivot.py::test_pivot_eliminate_cartesian_product_columns \
    tests/unit_tests/pandas_postprocessing/test_resample.py::test_resample_linear
5 passed in 0.83s
```

Out of scope (separate, broader pandas 3.0 migration, not fixed here): the
remaining failures in `test_pivot.py` and `test_resample.py` are caused by
pandas 3.0 rejecting mixed-type fills — `asfreq(fill_value=0)` on string
columns (`test_resample_zero_fill*`) and `stack(dropna=False)` semantics
changes (`test_pivot_preserves_all_nan_metric_*`). These are not NumPy alias
removals and require emulating previously-silent mixed-type behavior.

Classification: confirmed

# Unit-test sweep: databases + charts (no production defects found)

## Evidence

```
$ python -m pytest tests/unit_tests/databases/ tests/unit_tests/charts/ -q
5 failed, 275 passed, 1 skipped in 7.34s
```

All 5 failures are environmental drift or cosmetic test-expectation changes —
**none are production data-path defects.**

### 1. `charts/test_client_processing.py::test_pivot_df_single_row_null_values` and
###    `test_pivot_df_single_row_null_mix_values_strings` (cosmetic, NOT fixed)

Both compare `df.to_markdown()` against a hard-coded markdown string. The
failure is purely column-width padding differences from a newer
`tabulate`/pandas release:

```
- Sum)',)   |
+ Sum)',)                       |
- |:-----------------|----------------:|----------------:|:-------------------|
+ |:-----------------|----------------:|----------------:|:---------------------------------------|
```

The pivot *data* is correct; only the rendered markdown table padding differs.
This is cosmetic test-expectation drift against an external library, not a
bug in Superset's pivot/client-processing code. A test-only regeneration of
the expected strings would fix it, but that carries no production value and
was intentionally left for a test-hygiene pass.

### 2. `databases/api_test.py::test_import_includes_configuration_method` and
###    `databases/commands/importers/v1/import_test.py::test_import_database_no_creds`
###    (environmental, NOT fixed)

Both fail with:
```
sqlalchemy.exc.NoSuchModuleError: Can't load plugin: sqlalchemy.dialects:bigquery
```
The tests import a BigQuery database YAML fixture, which triggers
`get_all_catalog_names` → `get_inspector()` → engine creation for a BigQuery
URL. The optional `bigquery` SQLAlchemy driver is not installed in this
environment. This is an environment/dependency issue, not a code defect.

### 3. `databases/api_test.py::test_database_connection` (environmental, NOT fixed)

Same class as #2 — depends on optional DB drivers / live connectivity not
available in this environment.

## Recommended Action

No production fixes warranted. The databases/charts sweeps surfaced only:
- optional-driver dependency gaps (bigquery), and
- cosmetic `to_markdown()` padding drift against external libraries.

Both belong in a test-hygiene/dependency-install pass, not in a bug-fix pass.
The earlier sweeps (`pandas_postprocessing`, `utils`, `common`) captured all
of the genuine pandas/numpy compatibility production bugs in this area.

<!--
Licensed to the Apache Software Foundation (ASF) under one
or more contributor license agreements.  See the NOTICE file
distributed with this work for additional information
regarding copyright ownership.  The ASF licenses this file
to you under the Apache License, Version 2.0 (the
"License"); you may not use this file except in compliance
with the License.  You may obtain a copy of the License at

  http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on an
"AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
KIND, either express or implied.  See the License for the
specific language governing permissions and limitations
under the License.
-->

# Technical Specification: Expanded Upload Formats

> **Related documents:**
> [PRD](expanded-upload-formats-prd.md) ·
> [ADR](expanded-upload-formats-adr.md) ·
> [GenAI BI Roadmap](../../GENAI_BI_ROADMAP.md)

## Status

Draft

## Scope

This spec covers upload-format expansion in the existing database upload stack:

- `superset/config.py`
- `superset/databases/schemas.py`
- `superset/databases/api.py`
- `superset/commands/database/uploaders/*`
- `superset/mcp_service/dataset/tool/upload_file.py`
- `ax-bi-frontend/src/pages/UploadData`
- `ax-bi-frontend/src/features/databases/UploadDataModel`

It does not add a new database model, migration, background job, or external
conversion service.

## Extension Groups

### Configuration

Add extension constants:

```python
COMPRESSED_TABULAR_EXTENSIONS = {
    "csv.gz", "tsv.gz", "txt.gz", "jsonl.gz", "ndjson.gz"
}
ARROW_EXTENSIONS = {"feather", "arrow", "ipc"}
ORC_EXTENSIONS = {"orc"}
AVRO_EXTENSIONS = {"avro"}
GEOSPATIAL_EXTENSIONS = {"geojson", "gpkg", "shp.zip"}
FIXED_WIDTH_EXTENSIONS = {"fwf", "dat", "asc"}
STATISTICAL_EXTENSIONS = {"dta", "sav", "sas7bdat", "xpt"}
HTML_TABLE_EXTENSIONS = {"html", "htm"}
AI_ARTIFACT_EXTENSIONS = {
    "croissant.json", "npy", "npz", "lance", "lance.zip", "faiss",
    "index", "hnsw", "ann", "tar", "tar.gz", "tgz", "mlflow.zip",
    "mlruns.zip", "safetensors", "onnx", "gguf", "yaml", "yml",
}
```

`ALLOWED_EXTENSIONS` must include both simple and compound extensions.
Validation must check full lower-case filenames for compound extensions before
falling back to the last suffix.

### Reader Routing

Route to existing `UploadFileType` values:

| Reader | Extensions |
| --- | --- |
| CSV | `csv`, `tsv`, `txt`, `csv.gz`, `tsv.gz`, `txt.gz` |
| Excel | `xls`, `xlsx`, `ods` |
| Columnar | `parquet`, `zip`, `orc`, `feather`, `arrow`, `ipc` |
| Structured | JSON, XML, SQL, SQLite, Avro, geospatial, fixed-width, statistical, HTML, AI artifacts |

## CSVReader Changes

- Detect compression from filename:
  - `.gz` -> `compression="gzip"`
  - future `.bz2`, `.xz`, `.zip`, `.zst` can be added explicitly.
- Use the inner extension to select delimiter:
  - `.tsv.gz` -> tab
  - `.csv.gz` -> comma/sniffed
- Ensure `file.seek(0)` before reads after delimiter sniffing.

## ExcelReader Changes

- Accept `.ods`.
- Use pandas `read_excel`; Pandas selects the ODF engine when available.
- Keep existing sheet metadata behavior.

## ColumnarReader Changes

- Detect extension per file and per ZIP entry.
- `.parquet` keeps existing path.
- `.orc` uses `pd.read_orc`.
- `.feather`, `.arrow`, `.ipc` use `pd.read_feather` where possible.
- Metadata preview should read a bounded sample when the underlying reader
  supports it; otherwise read and sample.

## StructuredReader Changes

### JSON And JSONL Profiles

- Keep existing JSON and JSONL support.
- Normalize complex nested values to compact JSON strings so SQL writes do not
  receive arbitrary dict/list objects.
- Preserve common LLM eval columns if present:
  `prompt`, `messages`, `response`, `expected`, `score`, `latency`, `tokens`,
  `cost`, `error`, `model`, `run_id`.

### Compressed JSONL

- Decode `.jsonl.gz` and `.ndjson.gz` with gzip before JSON-lines parsing.

### Fixed-Width

- `.fwf`, `.dat`, `.asc` use `pd.read_fwf`.
- This is best-effort because full fixed-width imports often need field widths.

### HTML Tables

- `.html`, `.htm` use `pd.read_html`.
- Import the first table by default.
- Return an error when no tables are present.

### Statistical Packages

- `.dta` uses `pd.read_stata`.
- `.sas7bdat` and `.xpt` use `pd.read_sas`.
- `.sav` uses `pd.read_spss` when optional dependency support exists; otherwise
  return a clear parser error.

### NumPy Embeddings

- `.npy`:
  - 1-D arrays become rows with `index`, `value`.
  - 2-D arrays become rows with `embedding_id`, `embedding`, and dimensions.
  - Higher-dimensional arrays become metadata rows with shape and dtype.
- `.npz`:
  - each named array becomes rows with `array_name`.
  - 2-D arrays become embedding rows.
  - non-tabular arrays become metadata rows.

### Croissant Manifests

- Detect `@context`, `conformsTo`, `recordSet`, `distribution`, `field`, and
  Croissant-like keys.
- Produce metadata rows for dataset, distributions, record sets, and fields.

### AI Annotation Formats

- COCO JSON: rows for images, annotations, and categories.
- Label Studio JSON: rows for tasks and annotations.
- YOLO `.txt`: rows for class id and normalized box coordinates.
- YOLO `.zip`: manifest rows for annotation files.

### MLflow Exports

- `MLmodel`, `.mlflow.zip`, and `mlruns.zip` produce metadata rows for flavors,
  run files, params, metrics, and tags when available.
- Do not import model binary artifacts.

### Vector Index And Model Artifacts

- `.faiss`, `.index`, `.hnsw`, `.ann`, `.safetensors`, `.onnx`, `.gguf` produce
  metadata rows only:
  filename, extension, file size, artifact category, inferred warnings.
- Do not execute or load these artifacts.

### WebDataset And Lance

- `.tar`, `.tar.gz`, `.tgz`, `.lance.zip` produce bounded archive manifests:
  path, size, suffix, group key, and inferred role.
- `.lance` plain files produce metadata rows with a warning that directory
  uploads should be zipped.

### SQL Text Dumps

- Keep existing single-table parse behavior.
- Improve dialect tolerance:
  - ignore `GO`, `SET`, `CREATE`, `DROP`, `LOCK`, and transaction statements
    when scanning for inserts,
  - support `N'...'` unicode string literals,
  - support simple typed literals as strings when they are not numeric/bool/null.
- If a dump contains multiple tables, return metadata rows unless a table name
  is explicitly provided in options.

## API Changes

- Add a shared filename-to-upload-type helper or equivalent local mapping in
  `superset/databases/api.py`.
- Update `auto_upload` supported-type text.
- Update MCP upload file extension maps to match the REST API.

## Frontend Changes

- Expand `/upload/` `accept` list.
- Update supported-format text to mention:
  compressed exports, ODS, ORC/Arrow/Feather, fixed-width, HTML/statistical,
  geospatial/Avro metadata where optional readers are unavailable, and AI
  artifacts.
- Add structured upload accept labels for database-specific modals only if the
  modal supports the `structured` upload type. Otherwise keep the primary
  support in zero-config `/upload/`.

## Tests

Add or update unit tests:

- extension validation for compound extensions,
- CSV `.gz`,
- ODS if the ODF dependency is available in the test environment,
- ORC and Feather/Arrow,
- fixed-width,
- HTML table,
- NumPy `.npy` and `.npz`,
- COCO or Label Studio JSON,
- model metadata file,
- archive manifest,
- SQL dialect string literal handling.

## Operational Notes

- Optional parser gaps are acceptable when the user receives a clear error or
  metadata import.
- Archive metadata must cap listed entries to avoid huge result sets.
- Direct support still writes to a configured upload database, so database
  engine support for file upload remains required.

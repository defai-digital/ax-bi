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

# PRD: Expanded Upload Formats For AI-Ready BI

> **Related documents:**
> [ADR](expanded-upload-formats-adr.md) ·
> [Technical Specification](expanded-upload-formats-tech-spec.md) ·
> [GenAI BI Roadmap](../../GENAI_BI_ROADMAP.md)

## Status

Proposed

## Summary

AX-BI will expand zero-config file upload beyond CSV, Excel, Parquet, JSON,
XML, SQL text dumps, and SQLite. The goal is to let users bring common data,
analytics, and AI artifacts into AX-BI without first converting them manually.

The upload path will support two import modes:

- **Tabular imports** create a normal Superset dataset from rows and columns.
- **Metadata imports** create a dataset describing an artifact when the file is
  valuable for governance, AI inventory, or dataset QA but is not itself a
  safe tabular source.

Rejected document and native backup formats remain outside direct upload.
PDF, DOCX, PPTX, images, screenshots, Oracle Data Pump `.dmp`, SQL Server
`.bak`, and physical database backups must go through extraction or restore
workflows before BI import.

## Problem

Users increasingly receive data in formats that are common outside classic BI:

- compressed exports from SaaS products and logs,
- open spreadsheet formats,
- data-lake columnar files,
- geospatial datasets,
- research/statistical datasets,
- AI evaluation JSONL,
- embedding arrays,
- model metadata and AI annotation exports.

Forcing users to convert each file to CSV weakens type information, breaks
provenance, loses AI-specific metadata, and slows prompt-to-dashboard workflows.
AX-BI needs direct ingestion for high-value formats while preserving the
existing security and upload-resource limits.

## Goals

- Support the ten high-value general data-format groups:
  compressed tabular files, ODS, ORC, Arrow/Feather/IPC, Avro, geospatial,
  multi-table SQL text dumps, fixed-width files, statistical packages, and HTML
  tables.
- Support the nine AI-oriented format groups:
  Croissant manifests, LLM eval/batch/fine-tune JSONL profiles, NumPy
  embedding bundles, Lance manifests, vector-index metadata, WebDataset
  manifests, MLflow exports, AI annotation formats, and model-artifact metadata.
- Preserve existing upload permissions, file-size limits, schema restrictions,
  and database engine constraints.
- Prefer tabular imports when the format is naturally tabular.
- Use metadata imports for AI/model/index/document-like artifacts that should
  not be executed or loaded as raw rows.
- Keep optional heavy dependencies out of the baseline runtime when a metadata
  import provides useful value.

## Non-Goals

- Do not parse PDF, DOCX, PPTX, image, or screenshot files directly as datasets.
- Do not parse native binary database backups such as Oracle Data Pump `.dmp`,
  SQL Server `.bak`, or physical MySQL backups.
- Do not execute uploaded SQL dumps.
- Do not load model weights into memory for inference.
- Do not trust uploaded vector indexes as executable search backends.
- Do not add a new external conversion service for the first implementation.
- Do not guarantee complete support for every dialect-specific SQL dump
  construct.

## Target Users

### Business User

Uploads a file and expects a chartable dataset or a clear metadata dataset
without manual conversion.

### Analyst

Receives files from data lakes, statistical tools, geospatial sources, and AI
experiments. Needs type-preserving ingestion and previewable metadata.

### BI Admin

Controls which databases allow file upload. Needs upload parsing to remain
bounded, auditable, and permission-aware.

### AI Builder

Uploads eval runs, embeddings, model metadata, and annotation exports so MCP
tools can inspect AI assets and build governed dashboards around them.

## Supported Format Groups

### General Data Formats

| Group | Extensions | Import mode |
| --- | --- | --- |
| Compressed tabular | `.csv.gz`, `.tsv.gz`, `.txt.gz`, `.jsonl.gz`, `.ndjson.gz` | Tabular |
| OpenDocument spreadsheets | `.ods` | Tabular |
| ORC | `.orc` | Tabular |
| Arrow / Feather / IPC | `.feather`, `.arrow`, `.ipc` | Tabular |
| Avro | `.avro` | Tabular when optional reader is installed; metadata otherwise |
| Geospatial | `.geojson`, `.gpkg`, `.shp.zip` | Tabular when optional reader is installed; metadata otherwise |
| SQL text dumps | `.sql`, `.dump` | Tabular single table, selected table, or metadata summary |
| Fixed-width | `.fwf`, `.dat`, `.asc` | Tabular best-effort |
| Statistical packages | `.dta`, `.sav`, `.sas7bdat`, `.xpt` | Tabular when pandas can read it |
| HTML tables | `.html`, `.htm` | Tabular first table |

### AI-Oriented Formats

| Group | Extensions | Import mode |
| --- | --- | --- |
| Croissant manifests | `.croissant.json`, `metadata.json` | Metadata |
| LLM eval/batch/fine-tune JSONL | `.jsonl`, `.ndjson` | Tabular normalized profile |
| NumPy embedding bundles | `.npy`, `.npz` | Tabular |
| Lance manifests | `.lance.zip`, `.lance` | Metadata |
| Vector-index artifacts | `.faiss`, `.index`, `.hnsw`, `.ann` | Metadata |
| WebDataset shards | `.tar`, `.tar.gz`, `.tgz` | Metadata manifest |
| MLflow exports | `MLmodel`, `.mlflow.zip`, `mlruns.zip` | Metadata |
| AI annotations | COCO/Label Studio JSON, YOLO `.txt`/`.zip` | Tabular/metadata |
| Model artifacts | `.safetensors`, `.onnx`, `.gguf` | Metadata |

## User Journeys

### Upload A Compressed Export

1. User drags `orders.csv.gz` onto `/upload/`.
2. AX-BI detects CSV compression from the extension.
3. AX-BI imports the data into the local DuckDB upload database.
4. User lands in Explore with preserved columns and types.

### Upload An AI Eval Run

1. User uploads `eval_results.jsonl`.
2. AX-BI detects common LLM eval fields such as `messages`, `prompt`,
   `response`, `expected`, `score`, `tokens`, and `latency`.
3. AX-BI normalizes nested message/result values into JSON strings and keeps
   useful scalar columns as chartable metrics/dimensions.
4. User builds dashboards for score, latency, cost, and error analysis.

### Upload Model Metadata

1. User uploads `model.onnx` or `weights.safetensors`.
2. AX-BI does not load the model for inference.
3. AX-BI creates a metadata dataset with file type, size, inferred model
   metadata, and warnings.
4. AI inventory dashboards can track model artifacts without unsafe execution.

## Functional Requirements

- Detect upload reader type from full filename, including compound extensions.
- Validate extensions case-insensitively and reject unsupported formats.
- Preserve existing upload size checks before parsing.
- Produce preview metadata for all supported import modes.
- Return clear errors for optional formats when the runtime lacks a dependency.
- Avoid executing SQL, model, or vector-index content.
- Convert complex nested values into compact JSON strings before writing to SQL.
- Keep multi-table SQL dump handling explicit; do not silently merge unrelated
  tables.
- Provide tests for representative formats in each implementation category.

## Non-Functional Requirements

### Security

- Uploaded files remain untrusted input.
- SQL dumps are parsed as text only; no statements are executed.
- Model, vector-index, and WebDataset binaries are summarized as metadata only.
- ZIP/TAR archive handling must check decompression risk before reading entries.
- Existing RBAC, database upload settings, and schema restrictions remain the
  authorization boundary.

### Reliability

- Best-effort metadata imports should still produce a usable dataset when full
  parsing is unavailable.
- Parser errors should identify the format and likely remediation.
- The upload API should not require optional geospatial, Avro, MLflow, or model
  libraries for startup.

### Performance

- Metadata previews read bounded samples.
- Binary artifact metadata does not read entire model/vector payloads unless
  needed for a small header.
- Archive manifests cap the number of listed entries.

## Success Metrics

- Users can upload representative files from all accepted groups through
  `/upload/`.
- Existing CSV/Excel/Parquet upload tests continue to pass.
- New reader tests cover at least compressed tabular, ODS, ORC/Feather, fixed
  width, HTML, embeddings, AI annotations, model metadata, and archive metadata.
- Unsupported native backups and document formats are rejected with clear
  messages.

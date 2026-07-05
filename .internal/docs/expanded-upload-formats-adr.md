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

# ADR: Extend Existing Upload Readers For Expanded Data And AI Formats

> **Related documents:**
> [PRD](expanded-upload-formats-prd.md) ·
> [Technical Specification](expanded-upload-formats-tech-spec.md) ·
> [GenAI BI Roadmap](../../GENAI_BI_ROADMAP.md)

## Status

Accepted

## Context

AX-BI already has a database upload architecture with four reader families:

- `CSVReader`
- `ExcelReader`
- `ColumnarReader`
- `StructuredReader`

The REST API routes uploads through `UploadFileType`, applies existing
permissions and file-size checks, and writes the resulting DataFrame through
the database engine spec. The zero-config `/upload/` page auto-provisions a
local DuckDB database and maps file extensions to those readers.

The requested expansion covers both tabular formats and AI artifacts. Some
formats are naturally rows and columns. Others, such as model weights, vector
indexes, and WebDataset shards, are valuable for cataloging and BI dashboards
but should not be executed or loaded as opaque binary payloads.

## Decision

Extend the existing upload reader model instead of creating a new ingestion
service.

The implementation will:

- Expand extension validation in `superset/config.py`.
- Use compound-extension detection in upload routing.
- Add compressed file handling to `CSVReader` and `StructuredReader`.
- Extend `ExcelReader` to include `.ods`.
- Extend `ColumnarReader` for ORC and Arrow-family files.
- Extend `StructuredReader` for fixed-width, HTML, statistical files, NumPy
  embeddings, AI manifests, annotation exports, archive manifests, SQL text
  dump dialect conveniences, and metadata-only model/vector artifacts.
- Keep optional-dependency formats optional and return clear parser errors when
  a full tabular parse is not available.
- Keep PDF/DOCX/PPTX/images and native database backups out of direct support.

## Rationale

### Use Existing Readers

The existing readers already integrate with:

- REST API validation,
- upload permissions,
- upload size limits,
- database engine support checks,
- table creation behavior,
- metadata preview generation,
- frontend upload modals and zero-config upload.

Reusing this path minimizes authorization risk and avoids duplicate ingestion
behavior.

### Treat AI Artifacts As Metadata Unless Naturally Tabular

AI artifacts are not all datasets. Eval JSONL and embedding arrays can be
chartable rows. Model files, vector indexes, and WebDataset shards are better
represented as metadata rows. This preserves value for AI inventory and
governance dashboards without unsafe parsing or execution.

### Avoid Mandatory Heavy Dependencies

GeoPandas, Fiona, Pyogrio, FastAvro, MLflow, ONNX, Safetensors, and LanceDB are
valuable but heavy. The baseline AX-BI runtime already includes Pandas, NumPy,
PyArrow, OpenPyXL, and ODF. The first implementation should use baseline
dependencies where possible and degrade to metadata import or clear optional
dependency errors elsewhere.

## Considered Options

### Option 1: Require Conversion To CSV

Pros:

- Lowest implementation effort.
- Existing behavior remains unchanged.

Cons:

- Users lose type information, metadata, provenance, and compression benefits.
- AI-oriented artifacts require manual scripts.
- Weakens AX-BI's zero-config upload and GenAI BI direction.

Decision: rejected.

### Option 2: Add A Separate Ingestion Microservice

Pros:

- Can isolate risky parsers and heavy dependencies.
- Easier to scale conversion separately from Superset.

Cons:

- New service to deploy, secure, monitor, and document.
- Duplicates existing upload authorization and database-write paths.
- Too large for the first milestone.

Decision: rejected for the first implementation.

### Option 3: Extend Existing Readers

Pros:

- Preserves existing permissions and operational model.
- Keeps implementation close to current upload APIs.
- Lets tabular and metadata imports share preview and dataset creation.
- Can add optional full parsers later without changing user workflows.

Cons:

- `StructuredReader` becomes broader and needs careful tests.
- Some formats need metadata-only behavior until optional dependencies are
  available.
- Multi-table archive and dump UX remains limited by a single-table upload API.

Decision: accepted.

## Consequences

### Positive

- `/upload/` can accept a much wider set of useful data and AI artifacts.
- Existing upload security controls remain in force.
- Operators do not need to install new services for the first milestone.
- Future richer parsers can replace metadata-only behavior format by format.

### Negative

- Parser scope is broad and needs conservative error handling.
- Metadata-only support may surprise users who expect full tabular extraction.
- Some formats, especially geospatial and Avro, need optional dependencies for
  best results.

## Rollout

1. Ship expanded extension lists and backend readers behind existing upload
   permissions.
2. Update `/upload/` accepted extensions and user-facing supported-format text.
3. Add unit tests for representative supported groups.
4. Later add richer UI for multi-table dumps, archive table selection, and
   optional parser installation status.

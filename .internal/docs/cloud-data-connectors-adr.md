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

# ADR: Classify Cloud Connectors Above Existing Engine Specs

> **Related documents:**
> [PRD](cloud-data-connectors-prd.md) ·
> [Technical Specification](cloud-data-connectors-tech-spec.md) ·
> [GenAI BI Roadmap](../../GENAI_BI_ROADMAP.md)

## Status

Accepted

## Context

AX-BI already has a broad database connector surface through
`superset/db_engine_specs/`. The most valuable cloud data products largely fit
that model because they expose SQL through DB-API and SQLAlchemy drivers.

The missing piece is a product-level capability model. Existing engine metadata
describes connection strings, packages, categories, and documentation, but it
does not consistently answer:

- whether the connector is a cloud warehouse, lakehouse, data lake query
  engine, NoSQL/search connector, or observability-adjacent integration,
- whether the connector is certified, packaged, compatible, or only an
  integration candidate,
- which cloud provider and data product families it serves.

## Decision

Add a small cloud connector capability layer above existing engine specs.

The first implementation will:

- keep all query execution and permission checks in existing Superset database
  paths,
- classify high-value engine specs through a curated mapping,
- infer generic cloud capability from existing engine metadata categories,
- expose stable support levels and data product types for future docs, UI, MCP,
  and SDK work.

## Rationale

### Preserve The Superset Connector Model

Engine specs already encode SQL dialect behavior, time grains, schema/catalog
support, error extraction, and driver details. Duplicating that in a new
connector framework would create security and maintenance risk.

### Make Cloud Support Explicit

Cloud connector support is a product concept, not only a driver detail. A
capability layer lets AX-BI present a clear cloud data platform story while
continuing to reuse mature Superset execution paths.

### Avoid Treating APIs As Databases

Products such as Datadog and Cloudflare Analytics expose useful data, but not
all of them are relational SQL databases. They should be represented as
integration candidates or queried through exported warehouse/lakehouse data
unless they provide a stable SQLAlchemy-compatible path.

## Considered Options

### Option 1: Only Update Documentation

Pros:

- Minimal code.
- No behavior change.

Cons:

- MCP, SDK, and future UI still need name-based heuristics.
- Connector status cannot be tested.

Decision: rejected.

### Option 2: Build A New Connector Service

Pros:

- Could support non-SQL APIs and ingestion workflows uniformly.
- Could isolate vendor dependencies.

Cons:

- Duplicates Superset's database security model.
- Requires new deployment, monitoring, and secret handling.
- Too large for the first milestone.

Decision: rejected for database and lakehouse connectors.

### Option 3: Add Capability Metadata Above Engine Specs

Pros:

- Small and testable.
- Keeps existing execution, auth, and RBAC behavior.
- Gives docs, SDK, MCP, and UI a common vocabulary.

Cons:

- Does not install missing drivers by itself.
- Requires later work to expose the metadata through APIs and generated docs.

Decision: accepted.

## Consequences

### Positive

- Cloud connector support becomes machine-readable.
- High-value connectors can be prioritized and certified incrementally.
- Future UI and agent flows can reason about connector suitability.

### Negative

- Capability metadata must stay synchronized with engine spec reality.
- Certification remains a separate operational/test commitment.

## Rollout

1. Add capability types and mapping with unit tests.
2. Use capability mapping in generated database docs.
3. Expose capability fields through REST and MCP metadata.
4. Add packaging profiles for common cloud connector bundles.

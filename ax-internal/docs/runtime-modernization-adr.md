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

# ADR: Incremental Runtime Modernization With TypeScript Services And Rust Kernels

> **Related documents:**
> [PRD](runtime-modernization-prd.md) ·
> [Technical Specification](runtime-modernization-tech-spec.md) ·
> [Phased Plan](runtime-modernization-phased-plan.md)

## Status

Proposed

## Context

AX-BI is a fork of Apache Superset with a Python backend and a TypeScript/React
frontend. It also includes fork-specific MCP and GenAI BI code under
`superset/mcp_service`. The backend is large and integration-heavy. It depends
on Flask, Flask-AppBuilder, SQLAlchemy, Marshmallow, Celery, database-engine
plugins, and Superset's established security semantics.

The product direction adds agent-facing and GenAI BI workflows. These workflows
will likely evolve quickly and need stronger type contracts, clearer service
boundaries, and better observability than a broad Python-only implementation
provides. At the same time, replacing Superset core with another runtime would
create high compatibility and security risk.

## Decision

Adopt an incremental runtime modernization strategy:

- Keep Superset core Python for Flask-AppBuilder auth, SQLAlchemy models, DAOs,
  migrations, command-layer business logic, database engine specs, and Celery
  integration until a separate ADR justifies moving a specific boundary.
- Use TypeScript for new or extracted product-facing services, especially MCP
  and GenAI orchestration, metadata indexing, asset search, and API composition.
- Use Rust for isolated CPU-heavy kernels only after profiling identifies a
  bottleneck and compatibility tests can prove equivalent behavior.
- Define stable contracts before extraction and keep authorization decisions
  anchored in Superset until a dedicated permission boundary exists.
- Roll out new implementations behind feature flags, shadow mode, and rollback
  paths.

## Considered Options

### Option 1: Full Rust Backend Rewrite

Pros:

- Strong memory safety and performance.
- Good fit for CPU-heavy parsing, validation, and serialization.
- Could reduce some Python runtime classes of failure.

Cons:

- Requires replacing or reimplementing Flask-AppBuilder, SQLAlchemy behavior,
  migrations, command/DAO patterns, Celery integration, and many Superset APIs.
- High risk of authorization and compatibility regressions.
- Very large migration of tests and operational workflows.
- Poor fit for fast-moving GenAI orchestration where iteration speed matters.

Decision: rejected.

### Option 2: Full TypeScript Backend Rewrite

Pros:

- Easier than Rust for product and API orchestration.
- Stronger type sharing with the existing TypeScript frontend.
- Large ecosystem for service development, validation, and OpenAPI tooling.
- Better fit than Rust for agent workflow orchestration.

Cons:

- Still requires reimplementing Superset core behavior.
- Database and BI connector ecosystem is weaker than Python's for Superset's
  current workload.
- Does not automatically solve CPU-bound performance issues.
- Duplicating auth and ORM behavior remains risky.

Decision: rejected as a full rewrite.

### Option 3: Keep Everything In Python And Optimize Locally

Pros:

- Lowest architectural disruption.
- Reuses all existing Superset patterns.
- Simplest deployment topology.

Cons:

- Does not create strong runtime boundaries for new AX-BI product surfaces.
- Leaves GenAI/MCP orchestration coupled to Superset internals.
- Makes it harder to share contracts with the TypeScript frontend.
- Does not create a clean path for native performance kernels.

Decision: rejected as the only strategy, but accepted for Superset core.

### Option 4: TypeScript Sidecars Plus Rust Hotspots

Pros:

- Balances migration risk with delivery speed.
- Lets new AX-BI surfaces evolve with strong TypeScript contracts.
- Preserves Superset security and metadata authority.
- Applies Rust where it has clear value and narrow ownership.
- Supports phased rollout and rollback.

Cons:

- Adds multi-runtime build, test, and deployment complexity.
- Requires explicit contract governance.
- Requires discipline to avoid duplicating Python business logic.

Decision: accepted.

## Runtime Placement Guidance

### Keep In Python

- Flask-AppBuilder auth, roles, permissions, and security manager integration.
- SQLAlchemy models, DAOs, migrations, and transaction boundaries.
- Existing Superset REST APIs unless a specific boundary is approved.
- Database engine specs and connector behavior.
- Celery task orchestration and report scheduling.
- Security-sensitive object access checks.

### Prefer TypeScript

- New MCP or GenAI orchestration services.
- Metadata indexing and retrieval services.
- Asset search and ranking services.
- API composition or backend-for-frontend layers.
- Shared schema validation for frontend-visible contracts.
- Workflow state machines that interact with LLM providers and external tools.

### Prefer Rust

- SQL parsing and normalization kernels.
- Chart-schema validation kernels if they are CPU-bound.
- Serialization, hashing, compression, and digest computation.
- Dataframe-like transforms where moving data across the boundary is cheap
  enough to preserve the performance gain.
- Other isolated pure functions with benchmarkable output.

## Consequences

### Positive

- Avoids a risky platform rewrite.
- Creates a clear path for AX-BI-specific service evolution.
- Keeps core authorization behavior close to Superset.
- Gives Rust a targeted role where it is likely to pay off.
- Makes future migration decisions evidence-based.

### Negative

- The system will become multi-runtime.
- CI and local development will need additional tooling.
- Observability and deployment documentation must cover more components.
- Contract drift becomes a real risk without generated schemas and compatibility
  tests.

## Security Implications

- Extracted services must not make final authorization decisions for
  data-bearing Superset resources unless they call an authoritative Superset
  permission path or implement a separately reviewed permission service.
- Shadow execution must not leak outputs from unauthorized or experimental
  paths.
- Any service receiving prompts, metadata, SQL, chart data, or dashboard content
  must treat logs as sensitive.
- Security tests must preserve the principal and matrix-row discipline described
  in `SECURITY.md`.

## Open Questions

- Should cross-runtime contracts be generated from OpenAPI, JSON Schema,
  protobuf, or a narrower internal schema format?
- Should the first TypeScript service be deployed as a separate process or as a
  package used by an existing Node runtime?
- Should Rust enter first as Python extensions or service binaries?
- Which runtime owns MCP long term: Python for Superset affinity, TypeScript for
  product velocity, or a split by tool class?

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

# ADR: Runtime Modernization Boundary Decision

> **Related documents:**
> [Initial ADR](runtime-modernization-adr.md) ·
> [Technical Specification](runtime-modernization-tech-spec.md) ·
> [Phased Plan](runtime-modernization-phased-plan.md)

## Status

Accepted for AX-BI implementation planning.

## Context

The initial runtime modernization ADR selected incremental TypeScript sidecars
and Rust kernels instead of a broad rewrite. Since then, AX-BI has added:

- `ax-services`, a TypeScript sidecar with health, readiness, metadata, metrics,
  MCP asset search, and MCP dashboard list contracts.
- Python routing flags for selected MCP workflows with shadow execution,
  serving mode, mismatch reports, and Python fallback.
- A Rust SQL whitespace kernel behind `RUST_SQL_KERNEL`, with Python fallback
  and CI checks.
- Compatibility and rollout manifest CLI commands for release-candidate
  validation and operator dashboard wiring.

The Phase 6 planning question is whether those pilots justify a larger runtime
boundary shift.

## Decision

Keep Superset core and the MCP process Python, and split selected MCP/GenAI tool
workflows into TypeScript by tool class behind explicit contracts and feature
flags.

The long-term boundary is:

- **Python remains authoritative** for Superset auth, RBAC, SQLAlchemy metadata,
  DAOs, commands, migrations, data access checks, and core MCP process
  lifecycle.
- **TypeScript owns selected AX-BI orchestration workflows** when they are
  product-specific, contract-oriented, and can delegate authorization and data
  reads back to Superset.
- **Rust owns only measured pure kernels** where benchmarks and compatibility
  tests show value.
- **No separate permission service is introduced.** Superset remains the only
  authorization authority until a future ADR proves the cost and security model
  of a dedicated permission boundary.
- **Background jobs and Celery task families stay Python.** They need a
  reliability and deployment design before any runtime migration.

## Boundary Decisions

### MCP Service

Decision: split by tool class, not by moving the entire MCP service.

Keep the MCP server, auth hook, Flask context, session lifecycle, and
registration model in Python. Move individual read-only or orchestration-heavy
tools to TypeScript only when they have:

- Versioned request and response contracts.
- Python authoritative fallback.
- Shadow execution compatibility checks.
- Compact mismatch reports.
- Rollout manifest gates.
- Tests proving rollback through feature flags.

This keeps request identity and Superset access behavior close to the existing
security model while allowing AX-BI-specific workflows to evolve in TypeScript.

### GenAI BI

Decision: prefer TypeScript service ownership for new GenAI orchestration, while
delegating Superset resource reads and writes back to Python APIs.

GenAI workflows should not duplicate Superset ORM or authorization logic. They
may own prompt orchestration, model-provider calls, contract validation, ranking,
planning, and derived metadata operations.

### Background Jobs

Decision: do not move Celery reports, screenshots, or task families as part of
this runtime modernization phase.

Those paths mix queue semantics, browser automation, retry behavior, storage,
notifications, and operator deployment concerns. They require a separate
reliability ADR before runtime ownership can change.

### Permission Boundary

Decision: do not introduce a standalone permission service.

The current security model depends on Flask-AppBuilder, the Superset security
manager, DAO filters, object-level checks, and row-level security. Extracted
services must call Superset or operate only on data that Superset has already
authorized for the current principal.

## Rollout Rules

Any new TypeScript-owned MCP or GenAI workflow must satisfy these gates before
serving traffic:

- A contract file is generated in `ax-services/contracts/`.
- The Python path remains available as fallback.
- Shadow mode records match, mismatch, candidate error, and compare error
  metrics.
- Serving mode records served-candidate and fallback metrics.
- `superset runtime-modernization rollout-manifest` includes the workflow.
- Compatibility tests cover match, mismatch, serving, and fallback behavior.
- Production rollout evidence shows acceptable latency, error rate, fallback
  rate, and mismatch rate.

Any new Rust kernel must satisfy these gates before serving traffic:

- Python fallback remains available.
- Compatibility tests cover equivalent behavior.
- Benchmarks prove material value for the selected workload.
- Packaging works in CI and local development.
- The kernel is narrow enough that data transfer does not erase the benefit.

## Consequences

### Positive

- Avoids turning pilots into an unsupported partial rewrite.
- Keeps Superset security behavior anchored in the existing codebase.
- Gives TypeScript a clear product-orchestration role.
- Gives Rust a narrow performance role with measurable gates.
- Makes future migration proposals testable against rollout manifests and
  compatibility reports.

### Negative

- Multi-runtime complexity remains.
- Some workflow logic will exist across Python and TypeScript during shadow and
  fallback periods.
- Operators need dashboards for Python runtime metrics and sidecar route
  metrics.
- Larger boundaries still require future ADRs.

## Revisit Criteria

Write a new ADR before changing this decision if any of the following become
true:

- More than half of MCP tool classes are TypeScript-served in production.
- TypeScript workflows need to perform Superset metadata writes directly.
- A dedicated permission service is proposed.
- Celery/reporting paths need a runtime migration.
- Rust kernels expand beyond narrow pure functions into service ownership.

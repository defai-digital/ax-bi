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

# PRD: Runtime Modernization For Stability And Performance

> **Related documents:**
> [ADR](runtime-modernization-adr.md) ·
> [Technical Specification](runtime-modernization-tech-spec.md) ·
> [Phased Plan](runtime-modernization-phased-plan.md)

## Status

Proposed

## Summary

AX-BI inherits a large Python backend from Apache Superset and adds fork-specific
MCP and GenAI BI surfaces. The current concern is that Python-heavy backend
paths may be slow, fragile, or difficult to evolve. This initiative defines a
pragmatic runtime modernization strategy: keep Superset core in Python where it
is tightly coupled to Flask, Flask-AppBuilder, SQLAlchemy, Marshmallow, Celery,
and existing security behavior; move new product and agent-facing surfaces to
TypeScript where it improves delivery speed and type safety; and use Rust only
for measured, bounded performance hotspots.

The goal is not a language rewrite for its own sake. The goal is a more stable,
observable, and faster AX-BI platform with clear service boundaries and a lower
risk path for future migration.

## Problem Statement

The Python backend has a broad surface area:

- Superset application and extension initialization.
- Flask and Flask-AppBuilder route handling.
- SQLAlchemy models, DAOs, migrations, and transactions.
- Commands and validation logic.
- Database engine specifications and SQL Lab execution.
- Celery background tasks and reports.
- MCP service tools, schemas, auth hooks, and GenAI BI orchestration.

A broad rewrite would be expensive and risky because behavior is intertwined
with Superset's security model, metadata database, permission checks, and API
compatibility. However, AX-BI can still reduce Python risk by extracting bounded
services and kernels behind stable contracts.

## Goals

- Improve platform stability by reducing large, untyped, tightly coupled Python
  change surfaces.
- Improve performance on measured bottlenecks without speculative rewrites.
- Establish clear contracts between Superset core, MCP/GenAI services, frontend
  code, and any native performance modules.
- Prefer TypeScript for new orchestration and product surfaces that benefit from
  shared frontend types and faster iteration.
- Prefer Rust for isolated CPU-heavy logic where benchmarks show a meaningful
  gain.
- Preserve Superset RBAC, dataset permissions, RLS, auditability, and existing
  user workflows.
- Make rollback and incremental adoption possible at every phase.

## Non-Goals

- Rewriting all Superset backend code in Rust.
- Rewriting all Superset backend code in TypeScript.
- Replacing Flask-AppBuilder authentication and RBAC in the first phases.
- Replacing SQLAlchemy models, DAOs, and migrations in the first phases.
- Replacing Celery and report scheduling before a separate reliability analysis.
- Forking behavior away from Superset compatibility without an explicit product
  decision.
- Optimizing unprofiled code paths.

## Target Users

### AX-BI Product Developers

Need faster and safer delivery for MCP, GenAI BI, and product-specific
workflows without being blocked by Superset core complexity.

### BI Operators

Need predictable performance, clear deployment units, observability, and
controlled rollout of any new services.

### End Users

Need dashboards, SQL Lab, data uploads, and AI-assisted flows to become faster
and more reliable without permission or workflow regressions.

### Platform Maintainers

Need an architecture that reduces long-term maintenance burden rather than
creating a second backend that duplicates Superset behavior.

## Product Principles

- Measure first: migration candidates require latency, error-rate, or
  maintainability evidence.
- Contract first: extracted logic must have stable request and response schemas.
- Security preserving: all migrated paths must enforce the same authorization
  behavior as the Python implementation.
- Incremental by default: every phase must be deployable, testable, and
  reversible.
- Type safety where it pays: use generated or shared schemas across Python,
  TypeScript, and Rust boundaries.
- Keep orchestration close to product needs: TypeScript is preferred for new
  agent/product services; Rust is preferred for kernels.

## Functional Requirements

### Runtime Boundary Inventory

- Identify backend paths by ownership, dependency graph, runtime cost, and
  coupling to Superset internals.
- Classify each path as keep in Python, candidate for TypeScript service,
  candidate for Rust extension, or not worth moving.
- Maintain the classification in the technical spec or a follow-up tracker.

### Baseline Observability

- Capture p50, p95, p99 latency for high-traffic API and MCP tool paths.
- Capture task duration and failure rate for background jobs.
- Capture query count and slow SQL for selected routes.
- Capture CPU-heavy local processing such as SQL parsing, chart validation,
  dataframe post-processing, serialization, hashing, and screenshot orchestration.

### TypeScript Service Extraction

- Support new or extracted services where the contract can be expressed as
  JSON, OpenAPI, or protobuf.
- Prioritize MCP/GenAI orchestration, metadata indexing, asset search, and
  product-specific API composition.
- Avoid duplicating Superset RBAC and data-access rules; call back into Superset
  for authoritative authorization until a dedicated permission service exists.

### Rust Kernel Extraction

- Support Python-callable Rust modules for CPU-heavy logic through PyO3 and
  maturin or service-callable Rust binaries where process isolation is preferred.
- Require benchmarks before and after extraction.
- Require compatibility tests against the existing Python implementation.

### Rollout Controls

- Gate extracted paths behind feature flags.
- Support shadow execution where practical: execute the new implementation,
  compare outputs, and keep serving the Python result until confidence is high.
- Support fast rollback to the Python path.

## Non-Functional Requirements

### Security

- Follow `SECURITY.md` for any migrated data-bearing path.
- Tests for security-sensitive migrations must name the assumed principal and
  the permission matrix behavior being preserved.
- Do not expose unauthorized table, column, metric, dashboard, chart, or sample
  value data through extracted services.

### Performance

- A migration candidate should target at least one measurable improvement:
  latency, throughput, memory usage, tail reliability, or development velocity.
- Rust extractions should normally require a material CPU or memory win because
  they add build and interop complexity.

### Reliability

- Each extracted service or module must have health checks, structured logs,
  metrics, and clear error behavior.
- Inter-service calls must have timeouts and bounded retries.
- Degraded modes should preserve core BI functionality where possible.

### Maintainability

- Shared contracts must be generated or validated in CI.
- New TypeScript code must avoid `any` and use existing frontend/backend
  conventions where applicable.
- New Rust code must remain narrowly scoped and owned by a specific package.

## Success Metrics

- p95 latency improves on selected migrated paths by an agreed target, typically
  20-50% for CPU-bound paths.
- Error rate and timeout rate decrease on selected MCP and GenAI workflows.
- New GenAI/MCP product features ship with less Superset-core coupling.
- Compatibility tests show no authorization regressions.
- Rollback can be performed through configuration or feature flags.
- Developers can identify the runtime owner of each major backend path.

## Risks

- Moving code without profiling may increase complexity without improving user
  outcomes.
- Duplicating security logic outside Superset may introduce authorization
  regressions.
- Service extraction may add network latency and operational burden.
- Rust kernels may become hard to maintain if their boundary is too broad.
- TypeScript sidecars may drift from Superset's data model unless contracts are
  generated and tested.

## Open Questions

- Which endpoints and MCP tools are the first measured bottlenecks?
- Should the first TypeScript service live inside the existing frontend
  workspace or as a new top-level workspace package?
- Should Rust kernels be Python extensions first or standalone services first?
- Which schema system should be the source of truth for cross-runtime contracts?
- What is the minimum operator deployment profile for additional services?

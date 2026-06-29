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
> [Boundary Decision ADR](runtime-modernization-boundary-decision-adr.md) ·
> [Technical Specification](runtime-modernization-tech-spec.md) ·
> [Phased Plan](runtime-modernization-phased-plan.md) ·
> [Developer Guide](../../docs/developer_docs/runtime-modernization.md)

## Status

Accepted for AX-BI implementation. The PRD is complete for the scoped partial
runtime modernization effort: selected AX-BI orchestration moves to TypeScript
behind contracts and feature flags, while narrow CPU-heavy kernels may move to
Rust after benchmark and compatibility proof. Treat implementation completion
as evidence-driven, not calendar-driven: the initiative is complete only when
the phase completion audit reports `complete` from production evidence.

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

## MVP Scope

This PRD scopes a partial runtime migration, not a full backend rewrite.

### Included

- A TypeScript sidecar for selected AX-BI product and agent orchestration
  workflows.
- TypeScript-served MCP workflows that remain read-oriented or
  orchestration-oriented and can delegate Superset authorization and source data
  reads back to Python.
- Python routing, shadow execution, mismatch metrics, serving flags, and
  fallback for every migrated TypeScript workflow.
- A Rust proof-of-concept kernel for one measured CPU-heavy path, exposed to
  Python only when the optional extension and feature flag are available.
- Compatibility reports, rollout manifests, production evidence templates, and
  completion audits that prevent generated templates from being mistaken for
  completed rollout proof.

### Excluded

- Moving Superset core, Flask-AppBuilder auth, SQLAlchemy models, DAOs,
  migrations, core commands, or metadata transactions out of Python.
- Moving the MCP server lifecycle, auth hook, Flask context, or session
  management out of Python.
- Moving Celery, reports, screenshots, or task families without a separate
  reliability ADR.
- Introducing a standalone permission service.
- Moving broad business workflows into Rust.

## Completion Definition

The runtime modernization effort is complete only when all of the following are
true:

- Phase 0 has a reviewed runtime inventory with TypeScript and Rust candidates.
- Phase 1 has compatibility evidence for selected Python boundaries.
- Phase 2 has a TypeScript sidecar foundation with health/readiness and
  Superset connectivity.
- Phase 3 has at least one TypeScript workflow serving production traffic behind
  flags, with compatibility, dashboard, and fallback evidence.
- Phase 4 has a Rust kernel benchmark artifact proving compatibility and
  positive measured Python/Rust performance data.
- Phase 5 has at least two TypeScript workflows serving production traffic and
  a Rust rollout decision showing either served production traffic or a
  documented rejection.
- Phase 6 has an accepted boundary decision, explicit compatibility and
  security cost estimates, and operator approval for the enabled workflow scope.
- `superset runtime-modernization completion-audit <evidence-bundle> --strict`
  exits successfully and reports `status: complete`.

Until those conditions are proven by a schema-versioned evidence bundle, the
product state is incomplete even if code, tests, and CI templates exist.

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

### Production Evidence

- Provide a schema-versioned compatibility report with runtime inventory,
  benchmark details, and passing target checks where targets are set.
- Provide a Rust benchmark artifact with kernel name, positive iterations,
  Python duration, Rust duration, throughput, output size, and output
  compatibility.
- Provide a Rust rollout decision artifact documenting either production
  serving behind an enabled flag or a rejected rollout with rationale.
- Provide production flag-state evidence naming the environment, flag-state
  reference, selected workflows, and serving flags.
- Provide an operator dashboard snapshot with a measurement window, service
  health/readiness gates, and workflow gate results for exactly the enabled
  workflows.
- Provide operator approval naming the accepted boundary decision, rollout
  scope, migration decision, compatibility and security cost estimates,
  approval reference, approver, and exactly the enabled production workflows.

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

## Product Acceptance Criteria

- Operators can list migrated workflow owners, routes, flags, metrics, and gates
  with `superset runtime-modernization rollout-manifest`.
- Release candidates can generate compatibility reports and production evidence
  templates in CI.
- The generated production evidence template remains intentionally incomplete
  and fails completion audit until real production artifacts are supplied.
- A completed evidence bundle can be assembled from CI artifacts plus operator
  flag, dashboard, Rust decision, and approval artifacts.
- Strict completion audit fails if any selected workflow scope is empty,
  duplicated, out of scope, missing production flag evidence, missing dashboard
  proof, missing Rust benchmark proof, missing Rust rollout decision proof, or
  missing operator approval.
- The accepted boundary decision keeps Superset as the authorization authority
  and keeps Python as the owner of core metadata writes.

## Risks

- Moving code without profiling may increase complexity without improving user
  outcomes.
- Duplicating security logic outside Superset may introduce authorization
  regressions.
- Service extraction may add network latency and operational burden.
- Rust kernels may become hard to maintain if their boundary is too broad.
- TypeScript sidecars may drift from Superset's data model unless contracts are
  generated and tested.

## Resolved Product Decisions

- The first service boundary is a top-level TypeScript sidecar, `ax-services`,
  rather than code embedded in the frontend application.
- TypeScript ownership is selected by tool class and workflow, not by moving the
  entire MCP service.
- Rust enters first as a Python-callable optional extension for narrow kernels.
- Superset remains the authorization authority; extracted services delegate
  authorization and source data reads back to Python.
- Runtime contracts are versioned JSON contracts and release evidence is
  schema-versioned JSON.
- Completion is proven by `completion-audit`, not by the presence of generated
  templates or local-only tests.

## Remaining External Proof

- Capture live production flag-state evidence for the selected workflows.
- Capture operator dashboard snapshots showing health/readiness and gate results
  for exactly the workflows serving production traffic.
- Supply completed Rust benchmark and Rust rollout decision artifacts for a
  release candidate.
- Supply explicit operator approval with approver, approval reference, migration
  decision, cost estimates, and workflow scope.
- Re-run strict completion audit against the assembled evidence bundle before
  declaring the runtime modernization phases complete.

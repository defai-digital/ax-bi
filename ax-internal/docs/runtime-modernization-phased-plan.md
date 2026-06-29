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

# Phased Plan: Runtime Modernization

> **Related documents:**
> [PRD](runtime-modernization-prd.md) ·
> [ADR](runtime-modernization-adr.md) ·
> [Boundary Decision ADR](runtime-modernization-boundary-decision-adr.md) ·
> [Technical Specification](runtime-modernization-tech-spec.md)

## Status

In progress. Phase 2 foundation is implemented, Phase 3 has six MCP workflows
behind TypeScript routing flags, Phase 4 has a Rust SQL kernel proof of
concept, and the Phase 6 boundary decision is documented. Phase 5 production
rollout evidence remains open.

## Planning Assumptions

- Superset core remains Python through the early phases.
- TypeScript is the preferred runtime for new AX-BI product and orchestration
  services.
- Rust is reserved for measured CPU-heavy kernels.
- Security behavior remains anchored in Superset and `SECURITY.md`.
- Every phase must be independently useful and reversible.

## Phase 0: Baseline And Decision Gates

**Estimated duration:** 2-4 weeks

### Objectives

- Establish measured evidence for slow and unstable paths.
- Define migration gates so language choice is not subjective.
- Build a runtime inventory of the Python backend.

### Work

- Add or configure request tracing for selected APIs and MCP tools.
- Capture latency, errors, query count, payload size, and CPU-heavy processing
  time for candidate paths.
- Classify backend modules as keep Python, TypeScript candidate, Rust candidate,
  or defer.
- Define target metrics for each candidate path.
- Identify the first one TypeScript candidate and first one Rust candidate.

### Exit Criteria

- Candidate matrix exists and is reviewed.
- At least three real bottlenecks are measured.
- First TypeScript and Rust experiments have written success criteria.
- No migration work begins without a rollback plan.

## Phase 1: Stabilize Python Boundaries

**Estimated duration:** 4-8 weeks

### Objectives

- Reduce instability before extracting code.
- Make the existing Python paths easier to compare against.
- Improve test coverage around likely boundaries.

### Work

- Add contract-style tests around selected MCP and GenAI workflows.
- Add security regression tests for data-bearing tool paths.
- Normalize error schemas and response shapes for extraction candidates.
- Add correlation IDs and structured logs to candidate paths.
- Remove avoidable global state or request-context leakage where it blocks
  extraction.

### Exit Criteria

- Selected boundaries have deterministic fixtures.
- Selected paths have stable error and response contracts.
- Security-sensitive behavior is covered by tests naming the assumed principal.
- Observability is sufficient to compare old and new paths.

## Phase 2: TypeScript Service Foundation

**Estimated duration:** 4-6 weeks

### Objectives

- Create the first deployable TypeScript service without moving core behavior.
- Establish generated contracts and service operations.
- Prove Superset connectivity and authorization delegation.

### Work

- Add a top-level TypeScript service package, for example `ax-services/`.
- Implement health, readiness, config loading, structured logging, and metrics.
- Add generated or validated contract schemas.
- Add a Superset internal client with timeouts and correlation ID propagation.
- Add an authorization delegation path that calls Superset rather than
  duplicating permission logic.
- Deploy locally behind disabled feature flags.

### Exit Criteria

- Service starts locally and in CI.
- Service can call Superset health and a safe metadata endpoint.
- Contract tests run in CI.
- Python-only development remains unaffected.

### Current Evidence

- `ax-services/` provides health, readiness, metadata, metrics, and MCP asset
  search endpoints with versioned JSON contracts.
- `.github/workflows/ax-services.yml` runs install, type checking, tests, and
  build for the TypeScript sidecar.
- Superset has a small `AxServicesClient` for health, readiness, metadata,
  metrics, and asset search calls with timeouts and request IDs.

## Phase 3: First TypeScript Product Extraction

**Estimated duration:** 6-10 weeks

### Objectives

- Move one AX-BI-specific orchestration path to TypeScript.
- Avoid moving core Superset mutations or authorization.
- Prove shadow execution and rollback.

### Recommended Candidate

Start with metadata search or GenAI/MCP orchestration, such as asset search,
dataset description compaction, or dashboard planning. These are better
candidates than SQLAlchemy models or core REST APIs because they are
product-specific and contract-oriented.

### Work

- Define versioned request, response, and error schemas.
- Implement the TypeScript path using Superset APIs for source-of-truth data.
- Add shadow execution from the Python MCP path.
- Compare outputs and record mismatches.
- Add feature flag controlled serving from the TypeScript path.
- Add fallback to Python on timeout or error.

### Exit Criteria

- Shadow execution demonstrates acceptable output compatibility.
- p95 latency and error rate meet the target.
- Authorization behavior matches the Python path.
- Rollback through feature flag is tested.

### Current Evidence

- MCP asset search can shadow or serve from `ax-services` behind
  `TS_MCP_ORCHESTRATION` and `TS_ASSET_SEARCH_SERVING`, with Python fallback.
- MCP health check can shadow or serve from `ax-services` behind
  `TS_MCP_ORCHESTRATION` and `TS_HEALTH_CHECK_SERVING`, with Python fallback.
- MCP dashboard listing can shadow or serve from `ax-services` behind
  `TS_MCP_ORCHESTRATION` and `TS_DASHBOARD_LIST_SERVING`, with Python fallback.
- MCP chart listing can shadow or serve from `ax-services` behind
  `TS_MCP_ORCHESTRATION` and `TS_CHART_LIST_SERVING`, with Python fallback.
- MCP dataset listing can shadow or serve from `ax-services` behind
  `TS_MCP_ORCHESTRATION` and `TS_DATASET_LIST_SERVING`, with Python fallback
  after Superset dataset metadata permission checks pass.
- MCP database listing can shadow or serve from `ax-services` behind
  `TS_MCP_ORCHESTRATION` and `TS_DATABASE_LIST_SERVING`, with Python fallback
  after Superset database metadata permission checks pass.
- Compatibility, fallback behavior, compact shadow mismatch reporting, and
  opt-in compatibility report latency gates are covered by unit tests.
  Production rollout evidence still needs to be captured before this phase is
  complete.

## Phase 4: Rust Kernel Proof Of Concept

**Estimated duration:** 4-8 weeks

### Objectives

- Prove Rust can improve a measured hotspot without broad rewrites.
- Establish Rust build, benchmark, and compatibility workflow.

### Recommended Candidates

- SQL parsing or normalization helper.
- Digest, hashing, or serialization helper.
- A chart validation subroutine with narrow input and output.

### Work

- Create a small Rust crate and Python binding through PyO3 and maturin.
- Implement one pure function or narrow kernel.
- Add benchmarks against the Python implementation.
- Add compatibility tests using existing fixtures.
- Add feature flag and fallback to Python.

### Exit Criteria

- Benchmark shows a material improvement for the selected workload.
- Compatibility tests pass against existing Python behavior.
- Build process works locally and in CI.
- Python fallback remains available.

### Current Evidence

- `superset-rust/` contains the `ax_sql` PyO3 proof of concept for SQL
  whitespace normalization.
- `superset/runtime_modernization/rust_sql.py` keeps Python fallback behavior
  and routes to Rust only when the optional extension is importable and
  `RUST_SQL_KERNEL` is enabled.
- `SQLScript` uses the Rust whitespace kernel for normal SQL parsing when the
  feature flag and optional extension are both available, while special engines
  and kernel failures fall back to the existing Python path.
- Compatibility tests cover fallback, Rust-call routing, and parser-level
  integration. CI checks cover Rust format, clippy, tests, maturin wheel
  builds, extension installation, and a SQL kernel benchmark artifact uploaded
  as `sql-kernel-benchmark`.
- The Rust benchmark artifact records output compatibility, Python/Rust
  durations, operations per second, and optional speedup gates. Production
  rollout criteria still need to be completed before this phase is complete.

## Phase 5: Expand Runtime Split Selectively

**Estimated duration:** 2-4 months after successful pilots

### Objectives

- Expand only where pilots prove the model.
- Consolidate contracts, tooling, and operational practices.

### Work

- Move additional GenAI/MCP orchestration paths to TypeScript.
- Add a metadata index if asset search needs lower latency or better ranking.
- Add a second Rust kernel only if profiling justifies it.
- Improve service deployment documentation and dashboards.
- Add automated compatibility reports in CI.

### Exit Criteria

- At least two TypeScript-owned workflows run in production behind flags.
- At least one Rust kernel serves production traffic or is rejected with a
  documented reason.
- Operators have dashboards for service health and fallback rate.
- Developer documentation covers runtime ownership and local setup.

### Current Evidence

- `superset runtime-modernization compatibility-report` emits a
  machine-readable compatibility artifact that combines the runtime inventory,
  SQL parser benchmark checks, and Rust kernel compatibility checks.
- The compatibility report accepts explicit SQL parsing throughput and Rust
  speedup gates for release-candidate validation without making default CI runs
  environment-sensitive.
- The Rust workflow uploads a dedicated `sql-kernel-benchmark` artifact after
  installing the built extension wheel, giving release candidates direct
  evidence that the PyO3 module imports and matches the Python baseline.
- `superset runtime-modernization rollout-manifest` emits the serving flags,
  sidecar routes, Python metrics, sidecar metrics, and rollout gates for each
  migrated MCP workflow so operator dashboards can be generated from a stable
  source.
- `superset runtime-modernization production-evidence` emits the required
  production artifacts for completion: compatibility report, Rust benchmark,
  serving flag state, operator dashboard snapshot, and operator approval.
- `superset runtime-modernization production-evidence-template` emits a
  fillable JSON bundle with the workflow-specific serving flags and dashboard
  gates operators must complete.
- `superset runtime-modernization assemble-production-evidence` combines CI
  artifacts and operator-provided flag, dashboard, and approval JSON into the
  evidence bundle shape.
- `superset runtime-modernization validate-production-evidence` checks a JSON
  evidence bundle against those required artifacts and can fail release gates
  when evidence is missing or failing.
- Python unit CI uploads the compatibility report artifact and production
  evidence template artifact on the current Python version. Live production
  dashboard snapshots, completed rollout evidence, and additional selective
  workflow migrations are still required before this phase is complete.

## Phase 6: Reevaluate Larger Boundaries

**Estimated duration:** decision phase after 2-3 successful extractions

### Objectives

- Decide whether larger migrations are justified.
- Avoid accidental drift into an unsupported partial rewrite.

### Candidate Decisions

- Should the MCP service remain Python, move mostly to TypeScript, or split by
  tool class?
- Should GenAI BI become a separate TypeScript service by default?
- Should any Python background job family move to a service boundary?
- Should a dedicated permission-check service exist, or should Superset remain
  the only authorization authority?

### Exit Criteria

- A new ADR is written for any large boundary move.
- Compatibility and security costs are explicitly estimated.
- Operators approve deployment complexity.
- The team chooses either expand, pause, or stop migration.

### Current Evidence

- [Runtime Modernization Boundary Decision](runtime-modernization-boundary-decision-adr.md)
  selects a split-by-tool-class MCP boundary, keeps Superset as the
  authorization authority, keeps background jobs in Python, and limits Rust to
  measured kernels.
- Operator production approval and live rollout evidence are still required
  before treating the modernization effort as complete.

## Workstreams

### Observability

- Request tracing.
- Runtime path tagging.
- Latency and error dashboards.
- Shadow mismatch reports.
- Fallback rate tracking.

### Contracts

- Schema source of truth.
- Generated clients.
- Compatibility fixtures.
- Versioning rules.
- Error taxonomy.

### Security

- Principal-aware tests.
- Permission delegation.
- Sensitive log review.
- Metadata privacy validation.
- Feature flag and rollback testing.

### Developer Experience

- Local startup commands.
- CI checks for Python, TypeScript, and Rust.
- Build caching for native modules.
- Documentation for runtime ownership.

## Stop Conditions

Pause or stop a migration if:

- The new runtime duplicates Superset authorization logic without review.
- Performance does not improve after boundary overhead is included.
- Operational complexity exceeds the measured benefit.
- Compatibility mismatches are frequent or hard to explain.
- The migrated path requires broad SQLAlchemy or Flask request-context behavior.

## Recommended First Milestone

The first milestone should be:

1. Baseline the MCP chart and dashboard generation paths.
2. Add contract fixtures around one metadata search or planning workflow.
3. Create a TypeScript service skeleton with health/readiness and Superset
   connectivity.
4. Run one workflow in shadow mode.
5. Build one Rust proof of concept for SQL parsing, digest computation, or
   chart validation only after profiling identifies a concrete hotspot.

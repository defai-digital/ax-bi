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

# Technical Specification: Runtime Modernization

> **Related documents:**
> [PRD](runtime-modernization-prd.md) ·
> [ADR](runtime-modernization-adr.md) ·
> [Phased Plan](runtime-modernization-phased-plan.md)

## Status

Draft

## Scope

This specification defines the technical approach for reducing Python runtime
risk and improving performance through measured extraction. It covers runtime
classification, observability, TypeScript service boundaries, Rust kernel
boundaries, rollout controls, testing, and operational requirements.

## Existing System Anchors

Relevant Python modules:

- `superset/app.py`
- `superset/initialization.py`
- `superset/extensions`
- `superset/security`
- `superset/models`
- `superset/daos`
- `superset/commands`
- `superset/views`
- `superset/charts`
- `superset/dashboards`
- `superset/sqllab`
- `superset/sql`
- `superset/utils/pandas_postprocessing`
- `superset/mcp_service`

Relevant frontend and TypeScript modules:

- `superset-frontend/src`
- `superset-frontend/packages`
- `superset-frontend/plugins`

Relevant existing Rust anchor:

- `superset-desktop/src-tauri/Cargo.toml`

## Architecture Overview

```text
Browser / Agent
  -> Superset Python web app for core BI APIs and permissions
  -> Optional TypeScript service for AX-BI orchestration and product APIs
  -> Optional Rust kernels for CPU-heavy pure logic
  -> Metadata DB, cache, broker, and external databases remain operator-owned
```

The Python application remains the source of truth for:

- Authenticated principal.
- Superset roles and permissions.
- Dataset, dashboard, chart, database, and SQL Lab authorization.
- Metadata database writes for core Superset objects.

The TypeScript service is allowed to own:

- Product-specific workflows.
- GenAI/MCP orchestration.
- Metadata indexing that stores derived, non-authoritative views.
- LLM provider integration.
- Frontend-aligned contract validation.

Rust modules are allowed to own:

- Pure or mostly pure compute kernels.
- Parser, validator, transformer, digest, and serialization logic.
- Service binaries only when process isolation is needed.

## Candidate Classification

| Area | Default Runtime | Migration Candidate | Notes |
| --- | --- | --- | --- |
| Auth/RBAC/security manager | Python | No | Keep close to Flask-AppBuilder and `SECURITY.md`. |
| SQLAlchemy models/DAOs | Python | No | Too coupled to migrations and metadata DB behavior. |
| Commands | Python | Limited | Extract only product-specific orchestration, not core mutations. |
| Existing REST APIs | Python | Limited | Use TypeScript BFF only for new AX-BI flows. |
| MCP service orchestration | Python then TypeScript candidate | Yes | Good first service boundary if contracts stabilize. |
| GenAI BI orchestration | TypeScript candidate | Yes | Fast-changing, contract-heavy, frontend-visible. |
| Asset search/indexing | TypeScript candidate | Yes | Derived metadata and ranking logic. |
| SQL parsing/normalization | Rust candidate | Yes | Benchmark first; compare with existing behavior. |
| Chart validation kernels | Rust candidate | Yes | Only if CPU-bound and data transfer is modest. |
| Pandas post-processing | Python or Rust candidate | Maybe | Depends on data size and serialization overhead. |
| Screenshots/browser automation | Python | Maybe later | Likely operational stability work before runtime migration. |
| Celery reports/tasks | Python | No for first phases | Needs separate reliability design. |

## Observability Baseline

Before moving a path, collect:

- Endpoint or tool name.
- Request volume.
- p50, p95, and p99 latency.
- Error rate and timeout rate.
- CPU time where measurable.
- Metadata DB query count.
- External database query duration.
- Cache hit rate where applicable.
- Payload size across any proposed boundary.

Recommended first measurement targets:

- MCP chart generation and preview tools.
- MCP dashboard generation tools.
- Dataset metadata and schema discovery tools.
- SQL parsing and query normalization helpers.
- Chart data API payload serialization.
- Pandas post-processing functions.
- Screenshot/report execution paths.

## Contract Strategy

Each extracted boundary requires:

- Versioned request schema.
- Versioned response schema.
- Error schema.
- Authorization context schema.
- Correlation ID propagation.
- Compatibility test fixtures.

Acceptable schema sources:

- OpenAPI for HTTP service boundaries.
- JSON Schema for internal service contracts and MCP-compatible objects.
- Protobuf only if streaming, binary compatibility, or generated clients become
  necessary.

Schema files should be stored near the owning package and generated into the
consumer languages through CI. Hand-maintained duplicate types are discouraged.

## TypeScript Service Design

### Package Layout

Recommended first layout:

```text
ax-services/
  package.json
  tsconfig.json
  src/
    index.ts
    config.ts
    observability/
    contracts/
    superset/
    mcp/
    genai/
    search/
```

This top-level package avoids mixing server code into the frontend application
while still allowing shared tooling and generated types.

### Runtime

Recommended defaults:

- Node.js aligned with `superset-frontend/package.json` engines.
- Fastify or Hono for HTTP APIs.
- Zod or generated validators for runtime validation.
- OpenTelemetry-compatible tracing.
- Structured JSON logs.

### Superset Integration

The service should call Superset through explicit APIs:

- Auth/session validation endpoint or signed internal token.
- Permission check endpoint for data-bearing resources.
- Metadata read APIs for datasets, charts, dashboards, and databases.
- Draft artifact creation APIs only after user approval.

Direct metadata DB access is discouraged for the first phases because it can
duplicate SQLAlchemy behavior and bypass Python-side security assumptions.

### Failure Behavior

- Timeouts must be explicit.
- Errors must preserve correlation IDs.
- User-facing errors must avoid leaking sensitive metadata.
- Core Superset flows must remain available if the TypeScript service is down.

## Rust Kernel Design

### Python Extension Path

Use this path when the existing Python process should call the kernel directly:

```text
superset-rust/
  Cargo.toml
  crates/
    ax_sql/
    ax_chart_validation/
  python/
    pyproject.toml
```

Recommended tools:

- PyO3 for Python bindings.
- maturin for builds.
- Criterion for Rust benchmarks.
- pytest compatibility tests against existing Python behavior.

### Service Binary Path

Use this path when isolation or non-Python callers matter:

```text
ax-rust-services/
  Cargo.toml
  crates/
    ax_sql_service/
    ax_shared/
```

Recommended defaults:

- Axum for HTTP APIs.
- Tokio for async runtime.
- Serde for schema serialization.
- OpenTelemetry-compatible tracing.

### Extraction Criteria

A Rust candidate should meet most of these conditions:

- CPU-bound or memory-bound in profiling.
- Narrow input and output.
- Low dependency on Flask, SQLAlchemy, Pandas object internals, or request
  context.
- Deterministic enough for fixture-based compatibility tests.
- Expected improvement justifies extra build complexity.

## Feature Flags

Recommended flags:

- `RUNTIME_MODERNIZATION`: parent flag for internal rollout.
- `TS_MCP_ORCHESTRATION`: route selected MCP workflows through TypeScript.
- `TS_ASSET_SEARCH_SERVING`: serve MCP asset search from the TypeScript sidecar.
- `TS_HEALTH_CHECK_SERVING`: serve MCP health check from the TypeScript sidecar.
- `TS_METADATA_INDEX`: enable TypeScript-derived metadata index.
- `RUST_SQL_KERNEL`: enable Rust SQL parsing or normalization.
- `RUST_CHART_VALIDATION_KERNEL`: enable Rust chart validation kernels.
- `RUNTIME_SHADOW_EXECUTION`: run new path beside Python path and compare
  outputs without serving the new result.

All flags default to disabled.

## Shadow Execution

Shadow execution should:

- Execute Python path as authoritative.
- Execute candidate path asynchronously or within a bounded timeout.
- Compare normalized outputs.
- Record mismatches without exposing candidate output to users.
- Support sampling to control load.

Candidate paths can graduate from shadow mode after:

- Output compatibility reaches the agreed threshold.
- Latency meets or exceeds the target.
- Security tests pass for relevant principals.
- Rollback has been tested.

## Testing Strategy

### Python

- Preserve existing unit and integration tests.
- Add compatibility tests around extracted boundaries.
- Add security regression tests for any data-bearing migrated path.
- Use `pytest` for Python-level verification.

### TypeScript

- Use Jest or Vitest for service unit tests.
- Use contract tests against generated schemas.
- Use integration tests with mocked Superset APIs.
- Avoid `any` types.

### Rust

- Use Rust unit tests for kernels.
- Use Criterion benchmarks for performance-sensitive code.
- Use property tests where parser or validator behavior benefits from fuzzing.
- Use Python or service-level compatibility tests against current behavior.

### End-To-End

- Use Playwright only where user workflows are affected.
- Prefer unit and integration tests for service extraction.

## Deployment And Operations

### Local Development

- Python-only development must continue to work.
- TypeScript and Rust services should be opt-in until they are required by a
  product feature.
- Documentation must include start commands and health checks.

### Production

- New services need health endpoints.
- New services need readiness checks that validate required Superset
  connectivity.
- Logs must include request ID, user ID where allowed, principal type, feature
  flag state, and runtime path.
- Metrics must include latency, error rate, timeout rate, and fallback count.

## Migration Guardrails

- Do not move code solely because it is Python.
- Do not duplicate Superset authorization logic without a specific security ADR.
- Do not let TypeScript services write core Superset metadata directly in early
  phases.
- Do not move SQLAlchemy model behavior to another runtime without replacing
  migration, transaction, and compatibility testing.
- Do not introduce Rust for broad business workflows.

## Initial Deliverables

- Runtime inventory and candidate matrix.
- Observability baseline for top candidate paths.
- Generated schema proof of concept.
- One TypeScript service skeleton with health check and Superset connectivity.
- One Rust kernel proof of concept for a measured hotspot.
- Shadow execution framework for selected paths.
- Compatibility test suite for the first migrated boundary.

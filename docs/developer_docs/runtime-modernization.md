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

# Runtime Modernization

AX-BI uses an incremental runtime split. Superset Python remains authoritative
for core BI behavior, `ax-services` owns selected TypeScript orchestration
workflows, and Rust is limited to measured pure kernels with Python fallback.

## Runtime Ownership

Python remains the source of truth for:

- Flask request lifecycle, MCP process lifecycle, and session context.
- Authentication, roles, permissions, row-level security, and object access.
- SQLAlchemy models, DAOs, commands, migrations, and metadata writes.
- Core Superset REST APIs and background jobs.

TypeScript may own workflows that:

- Are product-specific or MCP/GenAI orchestration paths.
- Have versioned JSON contracts in `ax-services/contracts/`.
- Delegate Superset data reads and authorization back to Python APIs.
- Support Python fallback, shadow execution, rollout metrics, and feature flag
  rollback.

Rust may own kernels that:

- Are narrow, pure or mostly pure compute paths.
- Have compatibility tests against existing Python behavior.
- Have benchmarks proving the candidate result is worth the build and
  operational cost.
- Remain behind a feature flag and Python fallback.

Do not move Superset authorization, SQLAlchemy metadata ownership, Celery task
families, or background reporting paths into another runtime without a new ADR.

## Local Setup

Run Superset normally, then start the TypeScript sidecar in a second terminal:

```bash
superset run -p 8088 --with-threads --reload --debugger

cd ax-services
npm install
npm run dev-server
```

The sidecar listens on `127.0.0.1:5010` by default and calls Superset at
`http://127.0.0.1:8088`.

Useful sidecar checks:

```bash
cd ax-services
npm run type
npm test
npm run contracts:write
npm run build
```

Useful Superset checks:

```bash
superset runtime-modernization ax-services --check health
superset runtime-modernization ax-services --check ready
superset runtime-modernization rollout-manifest --format text
superset runtime-modernization compatibility-report --iterations 3 --strict
```

## Feature Flags

Runtime modernization is opt-in. Keep flags disabled unless you are explicitly
testing a candidate path.

Common control flags:

- `RUNTIME_MODERNIZATION`: parent flag for runtime modernization experiments.
- `RUNTIME_SHADOW_EXECUTION`: runs candidate paths beside authoritative Python.
- `TS_MCP_ORCHESTRATION`: routes selected MCP workflows to the TypeScript
  sidecar for shadow or serving.
- `TS_*_SERVING`: serves one workflow from TypeScript with Python fallback.
- `RUST_SQL_KERNEL`: enables the optional Rust SQL whitespace kernel when the
  Python extension is importable.

Serving a TypeScript workflow generally requires both `TS_MCP_ORCHESTRATION`
and that workflow's `TS_*_SERVING` flag.

## Contracts

Each TypeScript workflow must define source contracts in
`ax-services/src/contracts/` and generated JSON schema artifacts in
`ax-services/contracts/`.

After changing a contract, run:

```bash
cd ax-services
npm run contracts:write
npm run type
npm test
```

The Python MCP path must validate the sidecar response, sanitize user-controlled
strings before LLM context, and fall back to the Python path when the candidate
response is invalid or unavailable.

## Rollout Evidence

The phase completion audit is intentionally evidence-driven. Generate templates
and release artifacts with:

```bash
superset runtime-modernization production-evidence --format text
superset runtime-modernization production-evidence-template --format json
superset runtime-modernization production-flag-state \
  --environment prod-us \
  --flag-state-reference flags/runtime-modernization/prod-us-123 \
  --format json
superset runtime-modernization operator-dashboard-snapshot \
  --workflow mcp_asset_search \
  --snapshot-reference observability/runtime-modernization \
  --measurement-window "2026-06-29T00:00Z/2026-06-29T01:00Z" \
  --service-health-passed \
  --passed-workflow-gate mcp_asset_search:shadow_mismatch_rate \
  --passed-workflow-gate mcp_asset_search:fallback_rate \
  --passed-workflow-gate mcp_asset_search:error_rate \
  --passed-workflow-gate mcp_asset_search:latency_p95
superset runtime-modernization rust-kernel-rollout-decision-template --format json
superset runtime-modernization operator-approval \
  --workflow mcp_asset_search \
  --boundary-decision "split MCP by tool class" \
  --rollout-scope "selected TypeScript MCP workflows" \
  --migration-decision expand \
  --compatibility-cost-estimate "versioned contracts preserve Python fallback" \
  --security-cost-estimate "Superset remains the authorization authority" \
  --approval-reference "CHANGE-REFERENCE"
```

Assemble and validate collected evidence with:

```bash
superset runtime-modernization assemble-production-evidence \
  --compatibility-report runtime-modernization-compatibility-report.json \
  --rust-kernel-benchmark sql-kernel-benchmark.json \
  --rust-kernel-rollout-decision rust-kernel-rollout-decision.json \
  --production-flag-state production-flag-state.json \
  --operator-dashboard-snapshot operator-dashboard-snapshot.json \
  --operator-approval operator-approval.json \
  --validate

superset runtime-modernization completion-audit evidence-bundle.json --strict
```

The audit only completes when compatibility evidence, production serving flags,
operator dashboard measurement windows, service-health gates, workflow gates,
Rust kernel rollout decision evidence, and operator approval all pass. Operator
approval must include the team migration decision (`expand`, `pause`, or
`stop`) plus compatibility and security cost estimates for the accepted runtime
boundary. Production evidence bundles are schema-versioned; validation accepts
only `schema_version: 1` with object-shaped `artifacts`.
JSON validation output includes `enabled_workflow_names` and
`dashboard_required_workflow_names` so release automation can report exactly
which production-serving workflows were gated.

## Adding A TypeScript MCP Workflow

For each new TypeScript-routed MCP workflow:

1. Add request and response contracts in `ax-services/src/contracts/`.
2. Generate the JSON schema artifact with `npm run contracts:write`.
3. Add an `ax-services` route and Superset REST client method.
4. Add Python MCP candidate conversion with strict contract validation.
5. Keep the Python path as authoritative fallback.
6. Add shadow comparison, compact mismatch reporting, and migration metrics.
7. Add a disabled `TS_*_SERVING` feature flag.
8. Add the workflow to `superset.runtime_modernization.rollout`.
9. Cover serving, fallback, shadow, contracts, and rollout metadata with tests.

## Adding A Rust Kernel

For each Rust kernel:

1. Keep the kernel narrow and benchmark-driven.
2. Add compatibility tests against the Python behavior.
3. Keep Python fallback available.
4. Gate runtime use behind a feature flag.
5. Upload benchmark evidence from CI with `schema_version`, kernel name, and
   positive iteration count.
6. Record a Rust rollout decision before treating Phase 5 as complete.

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

# PRD: AX BI as the Analytics Authoring Platform

> **Related documents:**
> [ADR](analytics-authoring-platform-adr.md) ·
> [Technical Specification](analytics-authoring-platform-tech-spec.md) ·
> [GenAI BI PRD](genai-bi-prd.md) ·
> [GenAI BI Roadmap](../../GENAI_BI_ROADMAP.md)

## Status

Approved for phased implementation

## Summary

AX BI will be the single product and engineering owner of business-intelligence
artifact authoring across the AX product family. Client applications such as
AX Studio will send high-level intent, dataset references, approved file
content, and execution options. AX BI will own dataset discovery, semantic
resolution, chart selection, chart configuration, validation, preview, save,
dashboard composition, permissions, governance, lineage, and result URLs.

The first integration phase uses AX BI's existing high-level MCP tools:

- create_chart_from_intent
- plan_dashboard
- prompt_to_dashboard
- upload_and_plan

Later phases add transport-neutral application services, a versioned REST
surface, and a typed authoring SDK. MCP, REST, and SDK integrations must remain
adapters over the same AX BI implementation.

## Problem

AX BI already contains governed chart and dashboard authoring, but clients can
still reproduce AX BI domain logic. AX Studio, for example, contains its own
prompt parsing, dataset-column matching, metric mapping, chart configuration,
chart creation, update workarounds, and dashboard composition.

Client-owned BI logic creates four product failures:

1. The same request can produce different artifacts depending on the client.
2. Chart support, validation, and governance drift across releases.
3. Security behavior is difficult to reproduce outside AX BI.
4. Each AX BI improvement requires coordinated client changes.

The desired boundary is not merely a remote rendering API. AX BI must own the
complete lifecycle from governed intent to editable BI artifact.

## Product Principles

- **One authoring authority:** BI chart and dashboard behavior is implemented
  once in AX BI.
- **High-level contracts:** clients send intent and constraints rather than
  constructing AX BI form data.
- **Preview before mutation:** authoring supports review and dry-run paths.
- **Governance by construction:** authoring uses the authenticated AX BI
  principal, RBAC, RLS, metadata privacy, and semantic policies.
- **Transport neutrality:** MCP, REST, and SDK are adapters, not separate
  engines.
- **Explicit dependency:** clients report AX BI unavailability; they do not
  silently fall back to local BI generation.
- **Editable results:** generated artifacts remain ordinary AX BI charts and
  dashboards that users can inspect and modify.

## Goals

- Make AX BI the authoritative implementation for prompt-to-chart and
  prompt-to-dashboard.
- Let AX Studio and future clients delegate authoring without understanding
  chart plugin configuration.
- Preserve a high-level MCP surface for agents.
- Provide a deterministic API and SDK path for product UIs after the shared
  application service is established.
- Standardize request correlation, status, warnings, confidence, clarification,
  errors, and result references.
- Make chart support extensible without client releases.
- Keep authorization, governance, lineage, and audit behavior consistent
  across transports.

## Non-Goals

- AX BI is not a generic diagram, flowchart, SVG, or image generation service.
- The authoring SDK will not contain prompt parsing or chart-selection logic.
- Clients will not be required to embed the full AX BI UI.
- The first phase does not replace the existing chart, dashboard, Explore, or
  embedded-dashboard APIs.
- The first phase does not promise autonomous publishing without approval.
- A broad collection of client-specific orchestration endpoints is not part of
  the target architecture.

## Target Users

### AX Studio User

Creates a chart or dashboard from a prompt or attached dataset without
understanding AX BI chart configuration.

### AX BI User

Uses the same authoring capabilities from AX BI's own UI and receives results
consistent with external clients.

### Agent Builder

Uses MCP to discover assets, plan, preview, create, and explain governed BI
artifacts.

### Application Developer

Uses a typed API or SDK for deterministic workflows, status handling, and
result navigation.

### BI Administrator

Controls feature rollout, permissions, semantic metadata, query limits,
lineage, and audit policy once in AX BI.

## User Journeys

### Create a Chart from AX Studio

1. The user supplies a chart prompt and optionally identifies a dataset.
2. AX Studio sends the intent to create_chart_from_intent.
3. AX BI discovers or resolves the dataset.
4. AX BI maps metrics, dimensions, filters, time range, and chart type.
5. AX BI applies governance and chart validation.
6. AX BI returns a preview or saved chart, explanation, confidence, warnings,
   and an AX BI result URL.
7. AX Studio presents the result without interpreting form data.

### Create a Dashboard

1. The user supplies a dashboard goal.
2. A client requests a plan or invokes prompt_to_dashboard.
3. AX BI discovers assets, constructs a plan, applies a confidence gate,
   creates validated charts, composes the dashboard, and records lineage.
4. The client presents status, clarification questions, warnings, and the
   dashboard URL.

### Author from a File

1. A client sends approved CSV, Excel, or Parquet content to upload_and_plan.
2. AX BI creates the dataset and returns its identifier and a governed plan.
3. The client pins the identifier in create_chart_from_intent or
   prompt_to_dashboard.
4. AX BI owns every column, metric, chart, and layout decision.

### Use AX BI Through an Agent

1. The agent discovers the available high-level tools.
2. The agent calls a plan or authoring tool as the authenticated principal.
3. The host obtains user approval where required.
4. AX BI executes and returns an auditable artifact.

## Functional Requirements

### Authoring Contract

- ABIA-001: AX BI shall expose high-level chart, dashboard, plan, and
  file-to-plan operations.
- ABIA-002: Requests shall accept natural-language intent and optional dataset
  identifiers.
- ABIA-003: Responses shall expose status, warnings, confidence, clarification,
  explanation, and result references where applicable.
- ABIA-004: Clients shall not need AX BI plugin form-data knowledge.
- ABIA-005: Preview and dry-run behavior shall avoid permanent artifacts.
- ABIA-006: Saved results shall be normal editable AX BI artifacts.

### Security and Governance

- ABIA-010: Every operation shall run as the authenticated principal.
- ABIA-011: Dataset discovery and metadata shall respect existing access and
  metadata privacy controls.
- ABIA-012: Queries and previews shall respect RLS and query limits.
- ABIA-013: Chart and dashboard mutation shall use existing command and
  authorization layers.
- ABIA-014: A denied request shall never trigger a less-governed fallback.

### Transport and Client Support

- ABIA-020: MCP remains the agent-facing interface.
- ABIA-021: REST and SDK adapters shall reuse the same application service as
  MCP.
- ABIA-022: Published contracts shall have an explicit compatibility version.
- ABIA-023: Capability discovery shall identify supported operations and
  limits.
- ABIA-024: Mutating operations shall support idempotency before automatic
  client retries are permitted.

### Observability

- ABIA-030: Every workflow shall carry a request or correlation identifier.
- ABIA-031: Audit records shall identify principal, source prompt or redacted
  reference, datasets, operations, artifacts, and outcome.
- ABIA-032: Metrics shall distinguish completed, partial, blocked, failed, and
  dry-run outcomes.
- ABIA-033: Logs and metrics shall not contain file content, credentials, or
  high-cardinality prompt text.

## Non-Functional Requirements

### Reliability

- Malformed or unknown response shapes fail closed.
- Partial dashboard creation reports per-chart outcomes.
- Mutation reconciliation must distinguish failed from unknown outcome.
- Transport adapters must not implement unbounded retries.

### Maintainability

- Chart types and chart plugin schemas are not copied into client SDKs unless
  exposed as generated contract types.
- A new chart type does not require AX Studio code changes.
- Business logic is testable without an MCP server or HTTP route.
- Transport contract tests are generated from or validated against the same
  canonical schemas.

### Performance

- Chart intent planning uses bounded asset discovery and query limits.
- Long-running dashboard workflows expose progress or task status in a later
  asynchronous contract.
- File limits use the existing AX BI upload policy.

## Success Metrics

| Metric | Target |
|---|---|
| AX clients with local chart-config generation | Zero after migration |
| Chart types requiring client release | Zero |
| Cross-transport authoring parity tests | 100% passing |
| Authorization or RLS bypass regressions | Zero tolerated |
| AX Studio BI-domain code reduction | At least 80% |
| Generated chart save or acceptance rate | Measured from AX BI lineage |
| Requests with structured outcome and correlation | 100% |

## Delivery Phases

### Phase 1: Establish Ownership Through MCP

- Treat existing high-level MCP tools as the authoritative client contract.
- Migrate AX Studio away from local chart and dashboard generation.
- Add focused AX BI contract tests for the high-level operations.
- Document unsupported and fallback behavior.

### Phase 2: Extract the Application Service

- Move transport-neutral planning and authoring orchestration out of MCP tool
  modules.
- Keep MCP tools as thin authorization and serialization adapters.
- Add canonical request, response, error, capability, and idempotency models.
- Establish cross-repository contract fixtures.

### Phase 3: REST and Authoring SDK

- Add versioned REST endpoints over the application service.
- Publish a typed authoring SDK separate from rendering and embedding concerns,
  unless an SDK consolidation ADR accepts a combined package.
- Migrate deterministic AX Studio UI flows to the SDK while preserving MCP for
  agent-driven work.

### Phase 4: Asynchronous and Enterprise Hardening

- Add durable jobs, progress, cancellation, reconciliation, and rate limits.
- Add compatibility policy, deprecation windows, and service-level objectives.
- Certify tenant isolation and audit exports across transports.

## Risks

| Risk | Mitigation |
|---|---|
| MCP tool logic becomes the permanent service layer | Phase 2 extraction is a release gate for REST/SDK |
| Clients depend on unversioned schemas | Add contract version and fixtures before SDK publication |
| File upload is repeated after timeout | Add idempotency and reconciliation before retry |
| Low-confidence artifacts are saved | Preserve plan, preview, and confidence gates |
| Feature flags hide required tools | Capability-aware client errors; no local fallback |
| Embedded SDK is overloaded with authoring concerns | Decide package boundary in a dedicated SDK ADR |

## Release Gates

1. AX Studio no longer constructs AX BI chart config.
2. Existing AX BI high-level tools pass unit, security, and integration tests.
3. Chart, dashboard, plan, and upload flows have explicit structured outcomes.
4. No client-side fallback bypasses AX BI permissions or governance.
5. Product documentation clearly distinguishes BI authoring from generic
   diagrams and artifacts.
6. REST or SDK work does not begin until a transport-neutral application
   service boundary is accepted.

## Related Documents

- [ADR: AX BI Owns Analytics Artifact Authoring](analytics-authoring-platform-adr.md)
- [Technical Specification: Analytics Authoring Platform](analytics-authoring-platform-tech-spec.md)
- [PRD: GenAI-Powered Business Intelligence](genai-bi-prd.md)
- [GenAI BI Roadmap](../../GENAI_BI_ROADMAP.md)

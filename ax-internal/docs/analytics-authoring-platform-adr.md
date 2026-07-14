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

# ADR: AX BI Owns Analytics Artifact Authoring

> **Related documents:**
> [PRD](analytics-authoring-platform-prd.md) ·
> [Technical Specification](analytics-authoring-platform-tech-spec.md) ·
> [GenAI BI ADR](genai-bi-adr.md)

## Status

Accepted

## Context

AX BI contains the data, semantic, chart, dashboard, query, security, and
lineage layers required for governed business-intelligence authoring. It also
exposes high-level MCP operations for chart intent, dashboard planning,
prompt-to-dashboard, and file upload.

AX clients can nevertheless implement their own BI authoring orchestration.
AX Studio currently reproduces prompt parsing, chart selection, metric and
filter mapping, AX BI chart configuration, and dashboard assembly. This
duplicates domain behavior and causes client-specific results.

The integration also needs more than one transport:

- Agents benefit from MCP discovery and tool calling.
- Dedicated product UIs benefit from a typed, deterministic API and SDK.
- Both must enforce the same permissions and produce the same artifacts.

If each transport implements its own authoring logic, centralizing ownership in
AX BI does not solve the drift problem.

## Decision

AX BI is the sole owner of analytics artifact authoring.

The authoring implementation will be transport-neutral and will use AX BI's
existing command, DAO, model, semantic, query, security, and audit layers.
MCP, REST, and SDK surfaces are adapters over that application service.

The migration proceeds in this order:

1. Existing high-level MCP tools become the authoritative Phase 1 integration
   contract.
2. AX Studio removes local BI domain logic and delegates to those tools.
3. AX BI extracts authoring orchestration from MCP tool modules into an
   application service.
4. AX BI adds a versioned REST adapter.
5. A typed authoring SDK wraps the REST adapter for deterministic clients.

The embedded-dashboard SDK is not automatically selected as the authoring SDK.
Embedding and authoring have different authentication, mutation, retry, and
package-size concerns. A follow-up ADR must choose whether to extend it or
publish a separate package.

## Ownership Boundary

### AX BI owns

- File ingestion into governed datasets.
- Asset and dataset discovery.
- Semantic grounding and metric resolution.
- Chart type selection and configuration compilation.
- Query validation and preview generation.
- Chart and dashboard mutation.
- Dashboard layout and composition.
- RBAC, RLS, metadata privacy, governance, and audit.
- Contract versioning, compatibility, and capability metadata.
- Idempotency and workflow reconciliation.

### Clients own

- Connection configuration and authentication bootstrap.
- User input and approved file transfer.
- Choosing an explicit product mode such as chart, dashboard, or plan.
- User approval and cancellation intent.
- Rendering progress, warnings, clarification, and result links.
- Generic artifact presentation outside BI authoring.

Clients may choose an operation. They may not choose AX BI internal form data
unless they are an expert low-level API consumer explicitly using a chart CRUD
surface.

## Target Architecture

~~~text
                       +----------------------+
AX Studio Agent ------>| MCP adapter          |
                       +----------+-----------+
                                  |
AX BI UI -------------+           |
                      |           v
                      |  +---------------------------+
Other Product UI ---> |  | Authoring application    |
REST / SDK adapter ---+->| service                   |
                         | plan / chart / dashboard  |
                         +-------------+-------------+
                                       |
                         commands / DAOs / models
                         semantic / query / security
~~~

## Considered Options

### Option 1: Keep Client-Specific Authoring

Pros:

- Clients can ship heuristics independently.
- No service extraction is required.

Cons:

- Results, security, and governance drift.
- Every chart feature becomes a multi-repository migration.
- Client code depends on AX BI internals.

Decision: rejected.

### Option 2: Make Low-Level CRUD the Only Contract

Pros:

- Existing chart and dashboard APIs remain reusable.
- Expert clients have maximum control.

Cons:

- Every client becomes an orchestration engine.
- Natural-language intent and validation are duplicated.
- Agents require many fragile calls.

Decision: retained for expert and internal use, rejected as the product
authoring contract.

### Option 3: Make MCP the Only Permanent Contract

Pros:

- Existing implementation is available.
- Strong fit for agents.
- Tool discovery and annotations are useful.

Cons:

- Deterministic UIs need more direct typed contracts.
- Long jobs, idempotency, and compatibility policy are awkward if designed
  only around tool invocation.
- MCP tool modules can become an accidental business layer.

Decision: accepted for Phase 1, rejected as the only permanent transport.

### Option 4: Build REST and SDK Before Migrating Clients

Pros:

- A clean deterministic interface exists from the beginning.

Cons:

- Delays removal of duplicated client logic.
- Risks implementing REST separately from current MCP behavior.
- Expands scope before the service boundary is proven.

Decision: rejected sequencing. Extract the shared service before publishing the
REST and SDK surfaces.

### Option 5: Shared Application Service with Multiple Adapters

Pros:

- One implementation and one security model.
- Agent and deterministic clients receive equivalent results.
- Contract testing and versioning become tractable.

Cons:

- Requires refactoring MCP-owned orchestration.
- Needs careful transaction, context, and error design.

Decision: accepted target architecture.

## Consequences

### Positive

- AX BI becomes the clear source of truth for chart and dashboard behavior.
- Client repositories become smaller and more stable.
- New chart types and governance rules do not require client releases.
- MCP and UI flows can share evaluation and contract tests.
- Audit and lineage remain attached to AX BI artifacts.

### Negative

- AX BI availability becomes mandatory for BI authoring.
- AX BI must support a stronger compatibility commitment.
- Existing MCP functions must be refactored before REST and SDK publication.
- Cross-repository rollout and compatibility testing are required.

## Security Implications

- All adapters authenticate before invoking the application service.
- The service receives an explicit principal and request context; it does not
  infer trust from localhost.
- The service uses existing object access checks and command layers.
- Nested workflows preserve the strongest required permission. A dashboard
  workflow that creates charts requires both relevant mutation capabilities.
- A client denial cannot trigger a local or lower-privilege fallback.
- Prompt and file content are sensitive inputs and follow existing retention,
  redaction, and logging policy.
- Automatic retries of mutation are prohibited until idempotency is available.

## Contract Policy

- Requests and responses use an explicit major contract version.
- Additive optional fields are minor-compatible.
- Removing or changing meaning requires a new major version.
- Errors use stable codes; clients do not parse human-readable messages.
- Every mutation accepts an idempotency key once the deterministic API is
  published.
- Capability discovery reports supported operations, chart families, upload
  formats, limits, and asynchronous-job support.

## Operational Implications

- MCP remains a separately deployable service and shares AX BI configuration
  and database.
- REST authoring endpoints live with the AX BI web application unless a later
  scaling ADR selects a dedicated service.
- Long-running dashboard authoring may use the AX BI task framework.
- Metrics use bounded labels and correlation identifiers.
- Partial and unknown outcomes are first-class workflow states.

## Follow-Up Decisions

- Canonical application-service package location.
- Pydantic, dataclass, or generated-schema boundary for internal contracts.
- Durable job and event model.
- Idempotency storage and expiry policy.
- Authoring SDK package boundary.
- Public UUID migration for legacy integer artifact identifiers.

These decisions may refine implementation but cannot move BI authoring
ownership back into AX Studio or another client.

## Related Documents

- [PRD: AX BI as the Analytics Authoring Platform](analytics-authoring-platform-prd.md)
- [Technical Specification: Analytics Authoring Platform](analytics-authoring-platform-tech-spec.md)
- [ADR: Governed MCP-Native GenAI BI Architecture](genai-bi-adr.md)

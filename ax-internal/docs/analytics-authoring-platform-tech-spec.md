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

# Technical Specification: Analytics Authoring Platform

> **Related documents:**
> [PRD](analytics-authoring-platform-prd.md) ·
> [ADR](analytics-authoring-platform-adr.md) ·
> [GenAI BI Technical Specification](genai-bi-tech-spec.md)

## Status

Phase 1 implemented; Phase 2 foundation implemented and orchestration extraction in progress

## 1. Scope

This specification defines:

1. The existing MCP contracts used to remove BI domain logic from AX Studio.
2. The target AX BI application-service boundary shared by MCP, REST, and SDK.
3. Compatibility, security, idempotency, observability, and test requirements.

Phase 1 uses existing code and does not expose a new REST API. Phase 2 extracts
transport-neutral services before any public authoring SDK is released.

Implemented Phase 2 foundation:

- canonical v1 outcome, artifact, warning, error, limits, and capability models;
- trusted `AuthoringContext` for MCP, REST, and internal adapters;
- stable `AuthoringCommandError` mapping;
- transport-neutral confidence-gate policy used by prompt-to-dashboard;
- `GetAuthoringCapabilitiesCommand` and the
  `get_authoring_capabilities` MCP adapter.

Planning, chart creation, dashboard orchestration, upload orchestration,
idempotency, and REST adapters remain in the ordered extraction sequence below.

## 2. Existing System Anchors

High-level MCP tools:

- axbi/mcp_service/ai/tool/create_chart_from_intent.py
- axbi/mcp_service/ai/tool/plan_dashboard.py
- axbi/mcp_service/ai/tool/prompt_to_dashboard.py
- axbi/mcp_service/ai/tool/upload_and_plan.py
- axbi/mcp_service/ai/tool/compose_dashboard.py

Canonical MCP schemas:

- axbi/mcp_service/ai/schemas.py
- axbi/mcp_service/chart/schemas.py
- axbi/mcp_service/dashboard/schemas.py

Mutation and data layers:

- axbi/commands/chart/
- axbi/commands/dashboard/
- axbi/commands/database/uploaders/
- axbi/daos/
- axbi/semantic_index/
- axbi/semantic_layers/

Security and runtime:

- axbi/mcp_service/auth.py
- axbi/mcp_service/privacy.py
- axbi/mcp_service/ARCHITECTURE.md
- axbi/mcp_service/SECURITY.md
- axbi/mcp_service/PRODUCTION.md

The existing embedded SDK is focused on iframe/dashboard embedding. It is not a
server authoring client.

## 3. Phase 1 Contract

AX Studio consumes four high-level MCP operations. Each tool receives an MCP
argument object containing a request field.

### 3.1 create_chart_from_intent

Minimum request:

~~~json
{
  "request": {
    "prompt": "Create a saved bar chart of revenue by region",
    "dataset_id": 42,
    "save_chart": true
  }
}
~~~

The client may omit dataset_id and let AX BI discover the dataset. AX Studio
does not send chart_type, metrics, dimensions, filters, or kind in the normal
delegation path. Those structured fields remain available for plans generated
inside AX BI and expert clients.

Required response behavior:

- success is the authoritative success field.
- chart identifies a saved chart when save_chart is true.
- chart_name is available for saved and preview-only results.
- preview_url is optional.
- explanation, confidence, warnings, and alternatives are presentation data.
- form_data is diagnostic and is not interpreted by AX Studio.

### 3.2 plan_dashboard

~~~json
{
  "request": {
    "prompt": "Plan an executive sales dashboard",
    "dataset_candidates": [42],
    "constraints": {
      "max_charts": 6
    }
  }
}
~~~

This operation is read-only and creates no chart or dashboard.

### 3.3 prompt_to_dashboard

~~~json
{
  "request": {
    "prompt": "Create an executive sales dashboard",
    "dataset_ids": [42],
    "max_charts": 6,
    "draft": true,
    "save_charts": true,
    "dry_run": false,
    "min_confidence": 0.25,
    "force": false
  }
}
~~~

Required outcome states:

- completed
- partial
- blocked
- failed
- dry_run

The response includes a plan, per-chart summaries, ordered workflow steps,
warnings, optional error, counts, lineage, and optional dashboard URL.

### 3.4 upload_and_plan

~~~json
{
  "request": {
    "file_content": "<base64>",
    "filename": "sales.xlsx",
    "prompt": "Create a sales dashboard by region",
    "max_charts": 6
  }
}
~~~

The operation creates a dataset and returns dataset metadata plus a read-only
plan. The client uses the returned dataset ID in a chart or dashboard authoring
call. Clients must not use returned columns to implement local chart planning.

## 4. Phase 1 Integration Rules

- AX Studio calls only high-level tools for deterministic authoring.
- AX Studio may allow its general agent to use low-level tools, but it does not
  encode a low-level workflow.
- AX Studio does not retry a mutation.
- AX BI remains responsible for feature flags, permissions, RLS, privacy,
  validation, and audit.
- Tool errors remain failures even if structured content is present.
- Missing result URLs do not become synthesized success URLs.

## 5. Target Application Service

MCP tool modules currently contain orchestration and transport concerns. Before
REST and SDK publication, introduce a transport-neutral package:

~~~text
axbi/commands/ai/authoring/
  __init__.py
  contracts.py
  errors.py
  context.py
  plan_dashboard.py
  create_chart.py
  compose_dashboard.py
  prompt_to_dashboard.py
  upload_and_plan.py
  capabilities.py
  idempotency.py
~~~

The package follows the repository's API to Command to DAO to Model rule.
Public adapters validate their transport envelope and invoke command objects.
Commands may compose existing chart, dashboard, upload, and audit commands.

MCP-only concerns stay in axbi/mcp_service:

- FastMCP Context progress reporting.
- Tool annotations and discovery metadata.
- MCP request and response serialization.
- MCP authentication hook integration.

Shared authoring behavior moves out:

- Dataset discovery and semantic resolution.
- Planning and confidence gates.
- Chart-intent mapping and validation.
- Dashboard workflow orchestration.
- Outcome and lineage construction.

## 6. Internal Contracts

### 6.1 Request Context

~~~python
@dataclass(frozen=True)
class AuthoringContext:
    principal_user_id: int
    tenant_id: str | None
    request_id: str
    correlation_id: str
    transport: Literal["mcp", "rest", "internal"]
    idempotency_key: str | None
    locale: str | None
~~~

The context is supplied by the adapter. The service never trusts a caller-
provided principal identifier.

### 6.2 Canonical Outcome

~~~python
class AuthoringOutcome(BaseModel):
    contract_version: Literal["1.0"]
    request_id: str
    artifact_type: Literal["chart", "dashboard", "plan", "dataset"]
    status: Literal[
        "completed",
        "partial",
        "blocked",
        "failed",
        "dry_run",
        "unknown_outcome",
    ]
    artifact_refs: list[ArtifactRef] = []
    plan: DashboardPlan | None = None
    warnings: list[AuthoringWarning] = []
    clarification_questions: list[str] = []
    confidence: float | None = None
    error: AuthoringError | None = None
~~~

Mutable default syntax in production code must use default factories; the
example is contract shorthand.

### 6.3 Artifact Reference

~~~json
{
  "type": "chart",
  "id": 101,
  "uuid": "optional-during-legacy-migration",
  "url": "http://localhost:8088/explore/?slice_id=101"
}
~~~

New public APIs prefer UUID identifiers. Legacy integer IDs remain during the
repository's UUID migration.

### 6.4 Structured Error

~~~json
{
  "code": "DATASET_NOT_FOUND",
  "message": "No accessible dataset matched the request.",
  "retryable": false,
  "request_id": "req_...",
  "details": {}
}
~~~

Adapters map internal exceptions to stable error codes. Clients do not parse
message text.

## 7. Command Responsibilities

### PlanDashboardCommand

- Resolve pinned datasets or search accessible business assets.
- Load governed semantic metadata.
- Produce a validated plan without mutation.
- Return clarification when confidence is below policy.

### CreateChartFromIntentCommand

- Resolve dataset, metric, dimension, filter, time range, and chart family.
- Apply semantic guardrails.
- Compile and validate chart configuration.
- Preview or call existing chart create command.
- Record lineage for saved artifacts.

### PromptToDashboardCommand

- Invoke plan command.
- Apply confidence and approval gates.
- Invoke chart command for each plan intent.
- Compose a dashboard through existing dashboard commands.
- Preserve per-step and per-chart outcomes.
- Return partial or unknown outcomes accurately.

### UploadAndPlanCommand

- Enforce upload policy and file limits.
- Create a governed dataset through existing uploader commands.
- Invoke PlanDashboardCommand with the dataset pinned.
- Return dataset and plan in one outcome.

## 8. Adapter Design

### MCP Adapter

Existing tool names remain stable through the Phase 2 refactor. Tool functions:

1. Receive and validate Pydantic MCP schema.
2. Obtain authenticated context from the MCP hook.
3. Invoke the command.
4. Translate progress callbacks to FastMCP Context.
5. Serialize the canonical outcome into the backward-compatible tool response.

### REST Adapter

Proposed routes after service extraction:

~~~text
GET  /api/v1/ai/authoring/capabilities
POST /api/v1/ai/authoring/plans
POST /api/v1/ai/authoring/charts
POST /api/v1/ai/authoring/dashboards
POST /api/v1/ai/authoring/uploads
GET  /api/v1/ai/authoring/jobs/{job_id}
POST /api/v1/ai/authoring/jobs/{job_id}/cancel
~~~

Routes use protect(), Marshmallow or canonical generated schemas, and the same
commands as MCP. Routes do not import MCP tool functions.

### TypeScript SDK

The SDK wraps REST and exports generated contract types:

~~~ts
interface AxBiAuthoringClient {
  getCapabilities(): Promise<AuthoringCapabilities>;
  planDashboard(input: PlanDashboardInput): Promise<AuthoringOutcome>;
  createChart(input: CreateChartInput): Promise<AuthoringOutcome>;
  createDashboard(input: CreateDashboardInput): Promise<AuthoringOutcome>;
  uploadAndPlan(input: UploadAndPlanInput): Promise<AuthoringOutcome>;
  getJob(jobId: string): Promise<AuthoringJob>;
  cancelJob(jobId: string): Promise<AuthoringJob>;
}
~~~

The SDK handles auth headers, timeouts, schema validation, and error mapping.
It does not classify prompts or build chart configuration.

## 9. Capability Contract

~~~json
{
  "contract_version": "1.0",
  "operations": [
    "plan_dashboard",
    "create_chart",
    "create_dashboard",
    "upload_and_plan"
  ],
  "deployment_operations": [
    "plan_dashboard",
    "create_chart_from_intent",
    "prompt_to_dashboard",
    "upload_and_plan"
  ],
  "artifact_types": ["chart", "dashboard"],
  "preview_before_save": true,
  "upload_formats": ["csv", "tsv", "xls", "xlsx", "parquet"],
  "limits": {
    "max_charts_per_dashboard": 12,
    "max_upload_bytes": 0
  },
  "async_jobs": false
}
~~~

Limits are resolved from deployment configuration. A zero or omitted value must
not mean unlimited unless explicitly documented.

`deployment_operations` reports feature-enabled operations, while `operations`
contains only the subset authorized for the authenticated principal. Capability
discovery itself requires authentication but no Dashboard-specific permission.

## 10. Idempotency

All deterministic REST mutations require an Idempotency-Key header.

Storage record:

- key hash
- principal and tenant scope
- operation
- canonical request hash
- status
- artifact references
- response snapshot
- created and expiry timestamps

Rules:

1. Same key, scope, operation, and request returns the stored result.
2. Same key with a different request returns 409.
3. In-progress calls return the existing job reference.
4. Unknown outcome requires reconciliation before re-execution.
5. MCP clients cannot assume retry safety until the MCP contract accepts and
   enforces an equivalent idempotency field.

## 11. Transactions and Partial Failure

- Dataset upload, chart creation, and dashboard creation are separate mutation
  boundaries.
- Dashboard orchestration does not hold one database transaction across data
  queries and model calls.
- Every successfully created artifact is recorded before proceeding.
- Partial failure returns created artifact references and cleanup options.
- Automatic rollback of saved charts is not performed unless a dedicated
  compensating command verifies ownership and safety.

## 12. Security

- Adapters authenticate and authorize at the route or tool boundary.
- Commands perform object access checks for every data-bearing resource.
- Dataset discovery uses accessible DAO filters.
- Metadata uses the existing data-model privacy gate.
- RLS applies through existing query execution.
- Prompt-to-dashboard chart creation checks chart mutation capability in
  addition to dashboard capability.
- File upload uses current size, type, database, and upload permissions.
- Prompt injection cannot override semantic policies, RBAC, RLS, or tool
  constraints.
- Audit payload retention is configurable and prompts are treated as sensitive.

Security tests name the principal and expected capability matrix row.

## 13. Observability

Structured events:

- authoring.request.started
- authoring.plan.completed
- authoring.chart.completed
- authoring.dashboard.completed
- authoring.request.blocked
- authoring.request.failed
- authoring.request.partial
- authoring.request.unknown_outcome

Low-cardinality metric labels:

- operation
- artifact_type
- status
- transport
- error_code

Never use prompt, dataset name, user ID, artifact ID, request ID, or filename as
a metric label.

## 14. Compatibility

- Phase 2 preserves existing MCP tool names and request fields.
- Canonical v1 response fields are additive to existing tool responses or
  translated through backward-compatible envelopes.
- REST path major version is v1.
- Generated SDK types pin a compatible contract range.
- Deprecations require documentation, telemetry, and at least one supported
  client migration window.

## 15. Testing

### Existing MCP Contract Tests

- Schema accepts the minimum AX Studio chart request.
- Schema accepts the minimum dashboard request.
- Upload-and-plan returns a dataset identifier and plan.
- Error flags cannot be interpreted as success.
- Tool feature flags and RBAC hide or deny operations correctly.

### Application Service Unit Tests

- Dataset selection and semantic mapping.
- Confidence gates and clarification.
- Preview-only versus save behavior.
- Governance violations.
- Partial chart failures.
- Canonical error mapping.
- Idempotency replay and conflict.

### Integration Tests

- MCP and REST adapters produce equivalent canonical outcomes.
- RLS and metadata privacy across transports.
- File upload to pinned chart and dashboard.
- Saved chart and dashboard editability.
- Lineage and audit correlation.

### Cross-Repository Tests

- AX Studio fixtures validate against AX BI contract fixtures.
- AX Studio sends no chart config in high-level authoring requests.
- New AX BI chart families require no AX Studio change.

## 16. Phase 1 Implementation Checklist

- [x] Document AX BI ownership and current high-level tools.
- [x] Migrate AX Studio to create_chart_from_intent, plan_dashboard,
  prompt_to_dashboard, and upload_and_plan.
- [x] Remove AX Studio chart config generation and tests.
- [x] Run AX BI schema and high-level workflow tests.
- [x] Record remaining application-service, REST, SDK, capability, and idempotency
  work as Phase 2 and Phase 3.

## 17. Phase 2 Refactor Sequence

1. **Done:** Add canonical contracts and AuthoringContext.
2. **Done:** Characterize existing MCP tool behavior with tests.
3. Extract planning into PlanDashboardCommand.
4. Extract chart intent authoring into CreateChartFromIntentCommand.
5. Extract dashboard orchestration into PromptToDashboardCommand.
6. Extract upload-and-plan.
7. Convert MCP tools to thin adapters without changing names or fields.
8. Add canonical outcome and stable error mapping.
9. **Partial:** Capability discovery is implemented; idempotency remains.
10. Certify MCP parity before adding REST.

## 18. Definition of Done

The complete target is done when:

1. No AX client implements AX BI chart configuration or dashboard composition.
2. MCP and REST invoke the same application commands.
3. The authoring SDK contains transport and generated types only.
4. Contract version, capability discovery, stable errors, correlation, and
   idempotency are implemented.
5. RBAC, RLS, privacy, governance, and prompt-injection tests pass across
   transports.
6. Partial and unknown outcomes are observable and reconcilable.
7. AX Studio and at least one independent client pass shared contract fixtures.
8. Existing AX BI charts and dashboards remain editable through standard UI and
   APIs.

## Related Documents

- [PRD: AX BI as the Analytics Authoring Platform](analytics-authoring-platform-prd.md)
- [ADR: AX BI Owns Analytics Artifact Authoring](analytics-authoring-platform-adr.md)
- [Technical Specification: GenAI BI and Prompt-to-Dashboard](genai-bi-tech-spec.md)

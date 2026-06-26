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

# ADR: Governed MCP-Native GenAI BI Architecture

## Status

Proposed

## Context

The project is a Superset-based BI platform with an existing MCP service under
`superset/mcp_service`. The MCP service already includes useful foundations:

- Auth hooks and middleware.
- RBAC-aware tool visibility.
- Privacy controls for data model metadata.
- Schema discovery resources.
- Dataset listing and metadata tools.
- Chart generation with simplified schemas.
- Chart validation and preview flow.
- Dashboard generation from chart IDs.

The product direction is to support GenAI-powered BI, especially
prompt-to-dashboard. Market leaders are converging on semantic grounding,
governed access, verifiable answers, and AI-assisted artifact creation. Raw
text-to-SQL is insufficient as the main architecture because it does not
provide enough governance, explainability, or business metric consistency.

## Decision

Adopt a governed, MCP-native GenAI BI architecture centered on high-level BI
intent tools and semantic metadata.

The system will expose AI workflows through MCP tools that operate at BI
intent level:

- `search_business_assets`
- `describe_dataset_for_ai`
- `plan_dashboard`
- `create_chart_from_intent`
- `validate_chart`
- `compose_dashboard`
- `explain_dashboard`
- `evaluate_ai_answer`

The implementation will reuse existing Superset command, DAO, security, chart,
dashboard, and MCP infrastructure. It will extend the existing MCP service
rather than building a separate AI application beside Superset.

All AI operations must execute as the authenticated Superset principal and inherit
RBAC, dataset permissions, RLS, and metadata privacy controls.

## Architecture Principles

### Semantic Grounding Over Raw Text-To-SQL

AI should resolve business intent to governed datasets, saved metrics, columns,
filters, and chart configurations. SQL can be generated or inspected as a
secondary artifact, but direct raw text-to-SQL should not be the default user
or MCP workflow.

### Preview Before Mutation

Chart generation should default to preview mode. Dashboard generation should
create drafts or plans until the user approves saving or publishing.

### High-Level MCP Tools

Low-level CRUD tools remain useful, but the default agent experience should use
stable high-level BI intent tools. This reduces tool-planning errors and makes
governance easier to reason about.

### Lineage And Auditability

Generated artifacts need explicit lineage. Prompt, normalized intent, model,
tool chain, source assets, validation summary, and user principal should be
recorded.

### Evaluation By Default

Prompt-to-dashboard cannot be considered reliable without repeatable evals.
Evaluation should cover semantic resolution, chart generation, dashboard
quality, query success, and permission enforcement.

## Considered Options

### Option 1: Add A Chat UI On Top Of Existing APIs

This is fast to prototype but weak as a product architecture.

Pros:

- Low initial engineering effort.
- Minimal backend changes.
- Easy demo path.

Cons:

- Encourages hallucinated answers.
- Hard to govern and audit.
- Poor artifact lifecycle.
- Does not make MCP a strong platform surface.

Decision: rejected.

### Option 2: Raw Text-To-SQL Agent

This focuses on generating SQL directly from prompts.

Pros:

- Useful for technical users.
- Easier to build as a narrow feature.
- Can use SQL Lab as execution surface.

Cons:

- Does not reliably preserve business metric definitions.
- Increases risk of incorrect joins and filters.
- Harder to constrain to certified datasets.
- Less suitable for prompt-to-dashboard.

Decision: rejected as the primary architecture. It can remain a supporting
capability for SQL Lab workflows.

### Option 3: Separate AI Service Beside Superset

This creates a new AI service that calls Superset APIs.

Pros:

- Clear isolation.
- Independent release cadence.
- Easier to experiment with provider-specific features.

Cons:

- Duplicates auth, permissions, metadata, and artifact logic.
- Increases deployment complexity.
- Makes it easier to drift from Superset security semantics.
- Splits product experience across systems.

Decision: rejected for the first implementation.

### Option 4: Extend MCP Service With Governed BI Intent Tools

This builds on the existing MCP service and Superset internals.

Pros:

- Reuses auth, privacy, DAO, command, chart, and dashboard infrastructure.
- Makes MCP a first-class product surface.
- Keeps generated artifacts inside Superset lifecycle.
- Provides a good path for external agents and internal UI.

Cons:

- Requires careful tool design to avoid tool sprawl.
- Requires semantic metadata and eval investment.
- MCP service must stay aligned with Superset security model.

Decision: accepted.

## Consequences

### Positive

- Prompt-to-dashboard becomes grounded in governed BI assets.
- External agents can use the same MCP tools as internal flows.
- Security posture remains close to existing Superset behavior.
- Generated artifacts can be inspected, edited, and audited.
- Evaluation can be built around stable tool contracts.

### Negative

- MVP is broader than a chatbot prototype.
- Requires metadata work before dashboards become high quality.
- Requires new data models for lineage, aliases, and evals.
- Requires frontend review flows before users can safely publish.

## Implementation Implications

- Add feature flags for AI BI functionality.
- Add AI-ready metadata APIs and MCP tools.
- Add semantic aliases and asset ranking.
- Add dashboard plan schemas.
- Add lineage storage for generated artifacts.
- Add eval harness and regression tests.
- Keep mutation tools explicit and confirmation-oriented.
- Avoid provider-specific product behavior in core workflows.

## Security Implications

- AI tools must follow `SECURITY.md` and should name the assumed principal in
  tests for security-sensitive behavior.
- All data-bearing access must use existing Superset access checks.
- Metadata visibility must respect existing MCP privacy controls.
- Generated SQL, chart previews, and explanations must not reveal unauthorized
  data or metadata.
- Prompt and response logs must be treated as potentially sensitive.

## Open Questions

- Should semantic aliases be globally visible, dataset-scoped, or role-scoped?
- Should artifact lineage be stored in core Superset tables or a dedicated AI
  schema area?
- Which LLM provider abstraction should be used first?
- Should embeddings be optional from the start or added after SQL-based ranking?
- How should embedded guest-token AI flows restrict prompt-to-dashboard
  mutation behavior?

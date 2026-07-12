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

# GenAI BI Roadmap

## Product Direction

Revamp this AxBI-based project into an open, governed, MCP-native GenAI
business intelligence platform. The target product is not a generic chatbot
attached to BI. The target product is a trusted AI analyst that can discover
business data assets, reason over governed semantics, generate validated charts,
compose dashboards, explain results, and leave an auditable trail.

Recommended positioning:

> Open, governed, MCP-native GenAI BI for prompt-to-dashboard and trusted
> analytics agents.

This positioning uses the project's existing strengths:

- Broad SQL database support through `axbi/db_engine_specs`.
- Existing BI workflow for datasets, charts, dashboards, reports, and security.
- Extensible chart plugins and dashboard authoring UI.
- Existing MCP service with auth, RBAC-aware tool visibility, schema discovery,
  chart generation, chart preview, and dashboard creation.
- Self-hosted and extensible architecture for enterprises that need control over
  data, models, and deployment boundaries.

## Market Pattern

The leading BI vendors are converging on the same pattern: natural language is
only useful when grounded in governed semantic metadata, access controls, and
verifiable generated artifacts.

| Product | Market direction | Relevant lesson |
| --- | --- | --- |
| Microsoft Power BI Copilot | Natural language report generation, summarization, DAX help, and report page creation grounded in semantic models. | Prompt-to-dashboard requires a prepared model; text-to-SQL alone is not enough. |
| Tableau Agent / Tableau Next | Agentic analytics, conversational authoring, trusted semantic layer, data prep, and action-oriented analytics. | BI agents should move users from question to insight to action, not just return charts. |
| ThoughtSpot Spotter | AI analyst grounded in governed analytics, with RBAC/RLS, verifiable answers, and integrations including agent access. | Enterprise value comes from trusted answers and auditability. |
| Sigma AI | Ask, create, automate, govern, warehouse-native security, and MCP client/server positioning. | AI BI should support creation and automation while keeping data governance visible. |
| Omni AI | Semantic-model-grounded agents, workbook/dashboard agents, dashboard generation, evals, and feedback to improve modeling. | Evaluation and semantic feedback loops are product requirements, not optional tooling. |
| Qlik AI | Assistant, predictive analytics, anomaly detection, automation, and MCP server direction. | Alerts, anomalies, and workflows are natural follow-ons after prompt-to-dashboard. |

Source references used for this market scan:

- Power BI Copilot documentation:
  https://learn.microsoft.com/en-us/power-bi/create-reports/copilot-create-report
- Tableau Next:
  https://www.tableau.com/products/tableau-next
- Tableau Agent:
  https://www.tableau.com/products/tableau-agent
- ThoughtSpot Spotter:
  https://www.thoughtspot.com/product/spotter
- Sigma AI:
  https://www.sigmacomputing.com/product/ai
- Omni AI documentation:
  https://docs.omni.co/docs/ai
- Qlik Answers / AI positioning:
  https://www.qlik.com/us/products/qlik-answers

## High-Value Features To Keep And Extend

### 1. Governed Semantic Layer

Relevant code:

- `axbi/datasets`
- `axbi/semantic_layers`
- `axbi/connectors`
- `axbi/mcp_service/dataset`

Upgrade datasets from technical schema containers into AI-ready business assets.
The AI layer should consume:

- Certified datasets and charts.
- Business names and descriptions for columns and metrics.
- Saved metrics and metric expressions.
- Synonyms and glossary terms.
- Common dimensions and time columns.
- Relationships and join hints where available.
- Sample values, cardinality, and null-rate metadata where allowed.
- Owner, freshness, usage, and certification metadata.

This is the core moat. Without it, prompt-to-dashboard becomes fragile
text-to-SQL.

### 2. Prompt-To-Chart Foundation

Relevant code:

- `axbi/mcp_service/chart/tool/generate_chart.py`
- `axbi/mcp_service/chart/schemas.py`
- `axbi/mcp_service/chart/validation`
- `axbi/mcp_service/chart/preview_utils.py`

The existing implementation already has useful ingredients:

- Simplified typed chart configs.
- Preview-first chart generation.
- Save-on-demand behavior.
- Validation pipeline.
- Dataset access checks.
- Chart preview and explore URL generation.

Extend this into a first-class `create_chart_from_intent` capability that
accepts business intent and returns:

- Selected dataset and confidence.
- Selected metrics, dimensions, filters, time range, and chart type.
- Generated form data.
- Preview URL and validation result.
- Explanation of why the chart was selected.
- Warnings for low confidence, missing metadata, empty results, or expensive
  queries.

### 3. Prompt-To-Dashboard

Relevant code:

- `axbi/mcp_service/dashboard/tool/generate_dashboard.py`
- `axbi/mcp_service/dashboard/tool/add_chart_to_existing_dashboard.py`
- `axbi/dashboards`
- `ax-bi-frontend/src/dashboard`

Move from "create dashboard from chart IDs" to a planner/composer workflow:

1. Parse user intent.
2. Discover relevant datasets and prior dashboards.
3. Build a dashboard plan.
4. Generate chart previews.
5. Validate every chart.
6. Compose dashboard layout.
7. Present draft for human review.
8. Save only after explicit approval.

Dashboard plans should include:

- Dashboard title and business goal.
- Data sources and confidence level.
- Global filters and time range.
- Chart specifications.
- Layout sections.
- Narrative text blocks.
- Assumptions and unresolved questions.
- Validation status per chart.

### 4. Security, RBAC, And RLS

Relevant code:

- `axbi/security`
- `axbi/mcp_service/auth.py`
- `axbi/mcp_service/middleware.py`
- `axbi/mcp_service/privacy.py`
- `SECURITY.md`

AI features must never bypass AxBI authorization. Every AI-generated query,
chart, dashboard, and explanation should run as the current principal.

Required behavior:

- MCP tools inherit existing RBAC, dataset permissions, and RLS.
- AI asset search only returns accessible assets.
- Dataset metadata exposure respects privacy controls.
- Generated SQL and result previews never include unauthorized data.
- Every mutation includes audit metadata: principal, prompt, tool, model,
  source assets, and generated artifact IDs.

### 5. Embedded AI BI

Relevant code:

- `ax-bi-embedded-sdk`
- `axbi/embedded`
- `axbi/embedded_dashboard`

Embedding is a differentiator for a GenAI BI platform. Add support for embedded
AI dashboard workflows:

- Prompt-to-dashboard inside a host application.
- Guest-token-aware AI context.
- Embedded dashboard Q&A scoped to the dashboard and guest permissions.
- Theme and UI controls compatible with existing embedded SDK settings.

### 6. Reports, Alerts, And Insight Delivery

Relevant code:

- `axbi/reports`
- `axbi/tasks`
- `axbi/thumbnails`
- `ax-bi-websocket`

After dashboard generation, extend into insight delivery:

- AI summaries for scheduled reports.
- Anomaly explanations attached to alerts.
- "What changed?" summaries for dashboard subscribers.
- Suggested next questions and follow-up charts.
- Human approval before external actions.

## Low-Value Or Complexity-Heavy Work To Avoid

### Avoid Supporting Every Chart Type In The First AI Release

Prompt-to-dashboard should initially support a narrow set of chart types:

- Table
- Big number
- Bar
- Line
- Area
- Scatter
- Pie or donut
- Pivot table
- Basic geospatial map if geospatial metadata is available

Legacy and niche plugins should remain manually usable, but they should not
block the AI roadmap.

### Avoid Raw Text-To-SQL As The Main Product Surface

Raw text-to-SQL creates high risk:

- Hallucinated tables and columns.
- Incorrect joins.
- Metric drift.
- Security ambiguity.
- Hard-to-debug answers.

The preferred flow is:

`prompt -> semantic plan -> dataset/metric resolution -> validated query/chart -> preview -> human review`

SQL Lab can remain a power-user surface, but the AI product should favor
governed datasets and saved metrics.

### Avoid A Large Collection Of Tiny MCP CRUD Tools

Many low-level tools increase planning errors for AI clients. Keep CRUD tools
for completeness, but create higher-level tools around BI intent:

- `search_business_assets`
- `describe_dataset_for_ai`
- `plan_dashboard`
- `create_chart_from_intent`
- `validate_chart`
- `compose_dashboard`
- `explain_dashboard`
- `evaluate_ai_answer`

### Avoid Fully Autonomous Mutations In Early Releases

Initial releases should be human-in-the-loop:

- Preview charts before saving.
- Create dashboards as drafts.
- Require confirmation before publishing.
- Require confirmation before sending reports, Slack messages, or webhooks.

### Avoid Provider-Specific Product Logic

The product should support multiple LLM providers through an internal interface,
but business logic should not depend on a specific provider. Model-specific
prompting should live behind adapters.

## Target Architecture

```text
User prompt
  |
  v
Intent parser
  |
  v
Business asset search
  |
  v
Semantic resolver
  |
  v
Dashboard planner
  |
  v
Chart generator and validator
  |
  v
Preview and critique loop
  |
  v
Dashboard composer
  |
  v
Human review
  |
  v
Save, publish, embed, report, or iterate
```

### Core Components

#### AI Context Index

Build an index over accessible BI metadata:

- Datasets
- Columns
- Saved metrics
- Dashboards
- Charts
- Tags
- Owners
- Certification metadata
- Usage signals
- Recency/freshness signals

The first implementation can use SQL queries and ranking. A later
implementation can add embeddings for semantic retrieval.

#### Semantic Resolver

Input:

- User prompt.
- Candidate assets from the AI context index.
- Current user's permissions.

Output:

- Dataset selection.
- Metric and column mappings.
- Time range and filters.
- Confidence score.
- Unresolved terms.
- Clarifying questions if confidence is too low.

#### Dashboard Planner

Input:

- User prompt.
- Resolved semantic context.
- Existing dashboard/chart examples.

Output:

- Dashboard title.
- Sections.
- Chart intents.
- Global filters.
- Layout hints.
- Narrative blocks.
- Validation checklist.

#### Chart Generator

Use existing chart config schemas and validation. This is an incremental
extension of `generate_chart`, not a rewrite.

#### Dashboard Composer

Extend the current grid layout generation to support:

- Sections.
- Text blocks.
- Filter bar configuration.
- Chart sizing by importance.
- Responsive layout rules.
- Draft metadata and lineage.

#### Evaluation Harness

Add evals before broad release. Evaluation should cover:

- Dataset selection accuracy.
- Metric mapping accuracy.
- Chart type suitability.
- SQL/query validity.
- Permission enforcement.
- Dashboard usefulness.
- Hallucination rate.
- Empty-result handling.

## Recommended MCP Tool Shape

### `search_business_assets`

Purpose: find relevant BI assets for a user question.

Inputs:

- `query`
- `asset_types`
- `include_certified_only`
- `limit`

Outputs:

- Candidate datasets, charts, dashboards, metrics, and tags.
- Relevance reason.
- Certification and ownership metadata.

### `describe_dataset_for_ai`

Purpose: provide safe, compact, AI-ready dataset context.

Inputs:

- `dataset_id`
- `include_sample_values`
- `include_usage_stats`

Outputs:

- Business description.
- Columns and metrics.
- Time columns.
- Synonyms.
- Valid filters.
- Sample values if permitted.
- RLS/privacy note.

### `plan_dashboard`

Purpose: produce a dashboard plan without creating artifacts.

Inputs:

- `prompt`
- `dataset_candidates`
- `constraints`

Outputs:

- Dashboard plan.
- Chart intents.
- Clarifying questions.
- Assumptions.
- Confidence score.

### `create_chart_from_intent`

Purpose: create a validated chart preview from business intent.

Inputs:

- `chart_intent`
- `dataset_id`
- `save_chart`

Outputs:

- Generated chart preview.
- Form data.
- Validation result.
- Explanation.

### `compose_dashboard`

Purpose: create a draft dashboard from a validated plan and chart IDs.

Inputs:

- `dashboard_plan`
- `chart_ids`
- `draft`

Outputs:

- Dashboard ID.
- Dashboard URL.
- Layout summary.
- Warnings.

### `explain_dashboard`

Purpose: summarize and critique an existing dashboard.

Inputs:

- `dashboard_id`
- `question`
- `scope`

Outputs:

- Summary.
- Source charts.
- Caveats.
- Follow-up suggestions.

### `evaluate_ai_answer`

Purpose: run repeatable evaluations for AI-generated BI artifacts.

Inputs:

- `prompt`
- `generated_artifacts`
- `expected_assets`
- `rubric`

Outputs:

- Pass/fail results.
- Scores.
- Regression metadata.

## Data Model Additions

Add explicit metadata for generated artifacts instead of hiding provenance in
descriptions or JSON blobs.

Recommended model: `AIGeneratedArtifact`

Fields:

- `uuid`
- `artifact_type` (`chart`, `dashboard`, `dataset`, `report`)
- `artifact_id`
- `principal_user_id`
- `source_prompt`
- `normalized_intent`
- `llm_provider`
- `llm_model`
- `tool_chain`
- `source_asset_refs`
- `validation_summary`
- `confidence_score`
- `created_on`
- `changed_on`

Recommended model: `AISemanticAlias`

Fields:

- `uuid`
- `dataset_id`
- `object_type` (`dataset`, `column`, `metric`, `dashboard`, `chart`)
- `object_name`
- `alias`
- `source` (`user`, `admin`, `usage`, `generated`)
- `approved_by`
- `created_on`

Recommended model: `AIEvaluationRun`

Fields:

- `uuid`
- `prompt`
- `expected_result`
- `actual_result`
- `scores`
- `model`
- `tool_versions`
- `created_on`

## Frontend Product Experience

Relevant code:

- `ax-bi-frontend/src/features`
- `ax-bi-frontend/src/dashboard`
- `ax-bi-frontend/src/explore`
- `ax-bi-frontend/packages/axbi-ui-core`

Recommended user flows:

### AI Start Page

Primary prompt box with scoped options:

- Create dashboard.
- Create chart.
- Explain dashboard.
- Find data.

Show recent AI drafts and certified datasets.

### Prompt-To-Dashboard Wizard

Steps:

1. Prompt.
2. Data asset selection.
3. Dashboard plan.
4. Chart previews.
5. Layout review.
6. Save draft or publish.

### Dashboard Agent

Contextual assistant inside dashboard:

- Explain this dashboard.
- Explain this chart.
- What changed?
- Create a follow-up chart.
- Add this chart to dashboard.

### Explore Agent

Chart-building assistant inside Explore:

- Suggest chart type.
- Fix invalid fields.
- Explain empty results.
- Recommend filters.

## Phased Implementation

### Phase 0: Product Guardrails

Deliverables:

- Feature flag for AI BI functionality.
- AI audit logging strategy.
- Provider abstraction.
- Security review based on `SECURITY.md`.
- Initial eval dataset and rubric.

Exit criteria:

- AI tools cannot bypass RBAC/RLS.
- All mutations are auditable.
- Risky actions require explicit user confirmation.

### Phase 1: AI-Ready Metadata

Deliverables:

- `describe_dataset_for_ai` tool.
- Metadata compaction for datasets and metrics.
- Semantic aliases.
- Certified asset ranking.
- Dataset freshness and usage signals.

Exit criteria:

- An AI client can reliably discover candidate datasets for common business
  questions.
- Metadata output stays compact enough for LLM context windows.

### Phase 2: Prompt-To-Chart

Deliverables:

- `create_chart_from_intent` tool.
- Chart preview loop.
- Chart explanation.
- Validation warnings surfaced to frontend and MCP clients.
- Initial chart type coverage.

Exit criteria:

- Common prompts produce valid previews without saving by default.
- Invalid prompts return useful clarifying questions or repair suggestions.

### Phase 3: Prompt-To-Dashboard MVP

Deliverables:

- `plan_dashboard` tool.
- Dashboard plan schema.
- `compose_dashboard` draft flow.
- Frontend review flow.
- Artifact lineage model.

Exit criteria:

- A user can create a draft dashboard from a prompt using governed datasets.
- The generated dashboard includes source assets, assumptions, and validation
  status.

### Phase 4: Dashboard Agent

Deliverables:

- Dashboard-scoped Q&A.
- Chart-scoped explanations.
- Follow-up chart generation from dashboard context.
- Dashboard quality critique.

Exit criteria:

- A user can ask questions about an existing dashboard and receive answers
  grounded in the dashboard's accessible charts and datasets.

### Phase 5: Insight Delivery And Automation

Deliverables:

- AI-generated scheduled report narratives.
- Alert explanations.
- Anomaly summaries.
- Human-approved actions through email, Slack, webhook, or task integrations.

Exit criteria:

- AI can explain changes and anomalies in scheduled workflows without bypassing
  existing notification and permission controls.

## Evaluation Strategy

Use a small set of business scenarios before adding broad model support.

Example evaluation scenarios:

- "Create an executive sales dashboard for the last quarter."
- "Show revenue by region and top products with year-over-year growth."
- "Explain why conversion dropped last month."
- "Build a dashboard for customer retention and churn risk."
- "Find the certified dataset for marketing campaign performance."

Rubric:

- Correct dataset selected.
- Correct saved metrics used.
- Correct time grain and time range.
- Correct filters.
- Appropriate chart type.
- Query succeeds.
- Dashboard layout is usable.
- Explanation cites source assets.
- No unauthorized metadata or data appears.
- User can inspect or edit every generated artifact.

## Engineering Risks

### Hallucinated Semantics

Mitigation:

- Prefer certified datasets and saved metrics.
- Return clarifying questions when confidence is low.
- Keep generated assumptions visible.

### Expensive Queries

Mitigation:

- Use preview row limits.
- Enforce query timeout and cost warnings.
- Add runtime validation before saving charts.

### Permission Leaks

Mitigation:

- Run every tool under the current principal.
- Keep dataset metadata privacy controls.
- Add eval cases for RBAC and RLS.

### Tool Sprawl

Mitigation:

- Keep high-level BI intent tools stable.
- Hide low-level tools from default agent search unless needed.
- Maintain tool search metadata and examples.

### Poor Dashboard Quality

Mitigation:

- Use dashboard templates by business domain.
- Add layout heuristics.
- Add human review before publish.
- Measure user edits after generation as feedback.

## Recommended First Epics

1. AI-ready dataset description and asset search.
2. Semantic aliases and certified asset ranking.
3. Prompt-to-chart intent tool built on existing `generate_chart`.
4. Dashboard plan schema and no-mutation planner.
5. Draft dashboard composer with lineage metadata.
6. Evaluation harness for prompt-to-dashboard.
7. Frontend review flow for generated dashboards.

## Non-Goals For The First Release

- Fully autonomous dashboard publishing.
- Support for every chart plugin.
- Replacing SQL Lab for expert users.
- Provider-specific product behavior.
- Cross-tenant AI memory.
- Training on customer data by default.
- Unreviewed external actions.

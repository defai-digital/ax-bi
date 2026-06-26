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

# PRD: GenAI-Powered Business Intelligence

> **Related documents:**
> [ADR](genai-bi-adr.md) ·
> [Technical Specification](genai-bi-tech-spec.md) ·
> [Product Roadmap](../GENAI_BI_ROADMAP.md)

## Status

Proposed

## Summary

This product initiative revamps the Superset-based BI platform into a governed,
MCP-native GenAI BI system. The primary user-facing capability is
prompt-to-dashboard: a user describes an analytical goal in natural language,
the system discovers governed data assets, creates a dashboard plan, generates
validated chart previews, composes a draft dashboard, and asks the user to
review before saving or publishing.

The product should not be a generic chatbot bolted onto BI. It should be a
trusted AI analyst that operates through existing Superset permissions,
semantic metadata, chart generation, dashboard authoring, and audit controls.

## Goals

- Let business users create useful draft dashboards from natural language.
- Let analysts create and refine charts faster without losing visibility into
  datasets, metrics, filters, and SQL behavior.
- Ground every AI answer and generated artifact in accessible Superset assets.
- Preserve RBAC, dataset permissions, RLS, privacy controls, and auditability.
- Make MCP a high-value BI intent interface for external AI agents.
- Establish evaluation, lineage, and quality feedback loops before expanding
  autonomous behavior.

## Non-Goals

Non-goals are documented in the
[Product Roadmap](../GENAI_BI_ROADMAP.md#low-value-or-complexity-heavy-work-to-avoid).
Key exclusions for the first release include fully autonomous publishing,
broad chart plugin support, raw text-to-SQL as the main surface, and
provider-specific product logic.

## Target Users

### Business User

Needs dashboards and answers without knowing SQL or chart configuration details.
Expects plain-language prompts, visible assumptions, and editable results.

### Data Analyst

Knows the business data model and wants faster exploration, chart generation,
and dashboard drafting. Needs inspectable SQL, form data, metrics, and filters.

### BI Admin

Owns governance, certified datasets, permissions, semantic metadata, and rollout
controls. Needs confidence that AI cannot bypass security or create unmanaged
sprawl.

### Developer Or Agent Builder

Uses MCP tools to integrate Superset analytics into assistants, workflows,
embedded applications, or custom automation.

## Market Context

The BI market is converging on semantic-model-grounded AI. The competitive
landscape and strategic lessons are documented in the
[Product Roadmap](../GENAI_BI_ROADMAP.md#market-pattern).
The consistent lesson is that prompt-to-dashboard is valuable only when it is
governed, explainable, and grounded in trusted semantic assets.

## Product Principles

- Governance first: AI must run as the authenticated principal and inherit all access
  controls.
- Preview before mutation: generated charts and dashboards are drafts until the
  user approves.
- Semantic grounding: prefer certified datasets, saved metrics, descriptions,
  aliases, and usage signals over raw SQL generation.
- Inspectability: users can see source assets, assumptions, filters, metrics,
  and validation status.
- Extensibility: MCP tools expose BI intent, not just low-level CRUD.
- Evaluation by default: prompts, generated artifacts, and outcomes must be
  testable through repeatable evals.

## User Journeys

### Create Dashboard From Prompt

1. User opens an AI dashboard creation flow.
2. User enters: "Create an executive sales dashboard for this quarter with
   revenue, region performance, top products, and YoY growth."
3. System finds candidate certified datasets, prior dashboards, and saved
   metrics.
4. System shows a dashboard plan with data sources, chart list, global filters,
   assumptions, and confidence.
5. User confirms or edits the plan.
6. System generates chart previews.
7. System validates chart config, data access, query behavior, and result
   quality.
8. User reviews generated dashboard layout.
9. User saves as draft, publishes, or iterates.

### Create Chart From Intent

1. User asks for a chart in Explore or an AI side panel.
2. System resolves dataset, metric, dimension, chart type, filters, and time
   range.
3. System returns preview, warnings, and explanation.
4. User edits or saves chart.

### Explain Dashboard

1. User opens a dashboard and asks: "What changed since last month?"
2. System scopes the answer to charts and datasets accessible to the user.
3. System summarizes trends, anomalies, source charts, caveats, and follow-up
   questions.

### Agent Integration Through MCP

1. External agent calls `search_business_assets`.
2. Agent calls `describe_dataset_for_ai` on candidate datasets.
3. Agent calls `plan_dashboard`.
4. Agent calls `create_chart_from_intent` for each chart.
5. Agent calls `compose_dashboard` only after the host application presents the
   plan to the end user and receives explicit approval. The MCP protocol itself
   does not provide a UI — approval flows through the calling application.

## Functional Requirements

### Asset Discovery

- Search datasets, charts, dashboards, metrics, tags, and owners by business
  prompt.
- Rank certified assets and recently used assets higher.
- Return reasons for relevance.
- Return only assets visible to the authenticated user.

### AI-Ready Dataset Description

- Provide compact dataset context for AI clients.
- Include columns, saved metrics, time columns, descriptions, aliases, tags,
  certification, owners, and allowed filters.
- Include sample values only when privacy controls allow it.
- Include warnings for uncertified, stale, or low-metadata datasets.

### Dashboard Planning

- Convert a prompt into a structured dashboard plan without creating artifacts.
- Include chart intents, global filters, time range, sections, assumptions,
  confidence, and clarifying questions.
- Prefer asking clarifying questions when confidence is low.

### Chart Generation

- Generate preview-first charts from chart intent.
- Use existing simplified chart schemas and validation pipeline.
- Support initial chart types: table, big number, bar, line, area, scatter,
  pie or donut, pivot table, and basic map when metadata supports it.
- Return form data, preview URL, validation result, warnings, and explanation.

### Dashboard Composition

- Compose a draft dashboard from a validated plan and chart previews.
- Support sections, text blocks, global filters, and chart sizing heuristics.
- Save only after user approval.
- Store lineage for generated artifacts.

### Explanation

- Explain dashboards and charts with citations to source assets.
- Surface assumptions and caveats.
- Avoid answering outside the user's accessible assets.

### Evaluation

- Provide repeatable eval cases for common BI prompts.
- Score dataset selection, metric mapping, chart type suitability, query
  success, dashboard usefulness, permission enforcement, and hallucination.

## Non-Functional Requirements

### Security

- Enforce Superset RBAC, dataset permissions, and RLS for every AI action.
- Respect dataset metadata privacy controls.
- Never expose unauthorized table, column, metric, or sample-value data.
- Require explicit confirmation before mutations and external actions.

### Auditability

- Record principal, prompt, normalized intent, model provider, model name,
  tool chain, source assets, generated artifacts, validation status, and
  confidence score.

### Performance

- Asset discovery should return in under 3 seconds for common deployments.
- Chart preview should use existing Superset query limits and timeouts.
- AI metadata responses should be compact enough for LLM context use.

### Reliability

- Low-confidence prompts should return questions or partial plans.
- Empty results should include repair suggestions.
- Failed chart validation should return actionable errors.

## Success Metrics

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| Dashboard draft creation completion rate | >50% within first quarter | `AIGeneratedArtifact` lineage table: count of prompts that reach `compose_dashboard` vs. total prompts |
| Percentage of generated charts accepted or saved | >30% within first quarter | `AIGeneratedArtifact` lineage table: charts with `save_chart=true` vs. total chart previews |
| Average user edits per generated dashboard | <5 edits per dashboard | Dashboard version history: count of layout/content mutations after initial creation |
| Prompt-to-dashboard time vs. manual workflow | <50% of manual time | Event logging: time from first `search_business_assets` call to `compose_dashboard` completion, compared to baseline manual dashboard creation time |
| Dataset selection accuracy in evals | >80% correct selection | Evaluation harness: `evaluate_ai_answer` scores against expected dataset fixtures |
| Metric mapping accuracy in evals | >80% correct mapping | Evaluation harness: `evaluate_ai_answer` scores against expected metric fixtures |
| Permission leak regression count | Zero tolerated | Security test suite: RBAC/RLS regression tests, metadata privacy tests |
| Percentage of AI answers with cited source assets | >90% | Lineage table: percentage of `AIGeneratedArtifact` records with non-empty `source_asset_refs` |
| User-reported usefulness score for generated dashboards | >3.5/5.0 | User survey or in-app feedback widget on generated dashboard pages |

## Release Plan

The phased rollout (MVP and follow-on) is documented in the
[Product Roadmap](../GENAI_BI_ROADMAP.md#phased-implementation).
The MVP covers feature flags, asset discovery, dataset description, chart
intent generation, draft dashboard composition, artifact lineage, and an
initial eval suite. Follow-on phases add dashboard/Explore assistants, embedded
Q&A, report narratives, and anomaly explanations.

## Related Documents

- [ADR: Governed MCP-Native GenAI BI Architecture](genai-bi-adr.md)
- [Technical Specification: GenAI BI And Prompt-To-Dashboard](genai-bi-tech-spec.md)
- [GenAI BI Roadmap](../GENAI_BI_ROADMAP.md)

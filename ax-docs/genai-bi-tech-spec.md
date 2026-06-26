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

# Technical Specification: GenAI BI And Prompt-To-Dashboard

## Scope

This specification describes the first implementation path for GenAI-powered BI
over the existing Superset and MCP architecture. The core deliverable is a
governed prompt-to-dashboard workflow built from smaller prompt-to-chart and
semantic asset discovery capabilities.

## Existing System Anchors

Relevant backend modules:

- `superset/mcp_service`
- `superset/mcp_service/chart/tool/generate_chart.py`
- `superset/mcp_service/chart/validation`
- `superset/mcp_service/dashboard/tool/generate_dashboard.py`
- `superset/mcp_service/dataset/tool/get_dataset_info.py`
- `superset/mcp_service/system/resources/schema_discovery.py`
- `superset/security`
- `superset/datasets`
- `superset/semantic_layers`
- `superset/charts`
- `superset/dashboards`

Relevant frontend modules:

- `superset-frontend/src/dashboard`
- `superset-frontend/src/explore`
- `superset-frontend/src/features`
- `superset-frontend/packages/superset-ui-core`

## Feature Flags

Add feature flags:

- `GENAI_BI`: enables GenAI BI backend and frontend entry points.
- `GENAI_BI_MCP_TOOLS`: exposes new MCP tools.
- `GENAI_PROMPT_TO_DASHBOARD`: enables dashboard planning and composition.
- `GENAI_EMBEDDED_ASSISTANT`: enables embedded dashboard AI flows.

Default all flags to disabled.

## Backend Architecture

```text
Prompt
  -> intent parser
  -> business asset search
  -> AI-ready dataset description
  -> semantic resolver
  -> dashboard planner
  -> chart intent generator
  -> existing generate_chart validation and preview
  -> dashboard composer
  -> human approval
  -> Superset chart/dashboard commands
```

## New Backend Package Layout

Recommended package additions:

```text
superset/mcp_service/ai/
  __init__.py
  schemas.py
  semantic.py
  asset_search.py
  planning.py
  lineage.py
  evaluation.py
  tool/
    __init__.py
    search_business_assets.py
    describe_dataset_for_ai.py
    plan_dashboard.py
    create_chart_from_intent.py
    compose_dashboard.py
    explain_dashboard.py
    evaluate_ai_answer.py
```

Keep implementation in `mcp_service` initially because the first product
surface is MCP and the existing MCP service already owns AI-agent integration
concerns. Shared primitives can move to `superset-core` after the contracts
stabilize.

## MCP Tool Contracts

### `search_business_assets`

Request:

```json
{
  "query": "sales dashboard by region",
  "asset_types": ["dataset", "chart", "dashboard", "metric"],
  "include_certified_only": false,
  "limit": 10
}
```

Response:

```json
{
  "assets": [
    {
      "asset_type": "dataset",
      "id": 42,
      "uuid": "...",
      "name": "sales_orders",
      "description": "Sales order facts",
      "certified": true,
      "relevance_score": 0.91,
      "relevance_reason": "Matches revenue, region, order date, and product terms",
      "owners": ["Analytics"],
      "tags": ["sales"]
    }
  ],
  "warnings": []
}
```

Implementation notes:

- Use existing DAO/list filters where possible.
- Apply existing access filters.
- Rank by text match, certification, ownership, tags, usage, and freshness.
- Add embeddings later behind an optional provider.

### `describe_dataset_for_ai`

Request:

```json
{
  "dataset_id": 42,
  "include_sample_values": false,
  "include_usage_stats": true
}
```

Response:

```json
{
  "dataset": {
    "id": 42,
    "name": "sales_orders",
    "description": "Sales order facts",
    "certified": true,
    "main_time_column": "order_date",
    "columns": [
      {
        "name": "region",
        "type": "STRING",
        "description": "Sales region",
        "aliases": ["geo", "territory"],
        "is_dimension": true
      }
    ],
    "metrics": [
      {
        "name": "revenue",
        "expression": "SUM(amount)",
        "description": "Booked revenue"
      }
    ],
    "privacy": {
      "sample_values_included": false,
      "metadata_scope": "role_allowed"
    }
  },
  "warnings": []
}
```

Implementation notes:

- Reuse `get_dataset_info` internals.
- Respect `requires_data_model_metadata_access`.
- Limit output size through select fields and compaction.
- Include saved metrics distinctly from raw columns.

### `plan_dashboard`

Request:

```json
{
  "prompt": "Create an executive sales dashboard for this quarter",
  "dataset_candidates": [42],
  "constraints": {
    "max_charts": 8,
    "preferred_time_range": "this quarter",
    "draft_only": true
  }
}
```

Response:

```json
{
  "plan": {
    "title": "Executive Sales Dashboard",
    "business_goal": "Track revenue performance and sales drivers",
    "global_filters": [
      {
        "name": "Order Date",
        "column": "order_date",
        "default_value": "this quarter"
      }
    ],
    "sections": [
      {
        "title": "Executive Summary",
        "charts": [
          {
            "title": "Total Revenue",
            "intent": "Show total revenue for the selected period",
            "dataset_id": 42,
            "chart_type": "big_number",
            "metrics": ["revenue"],
            "dimensions": [],
            "filters": []
          }
        ]
      }
    ],
    "assumptions": ["Revenue maps to saved metric revenue"],
    "clarifying_questions": [],
    "confidence_score": 0.86
  }
}
```

Implementation notes:

- No database mutations.
- Return clarifying questions when confidence is below threshold.
- Prefer saved metrics and certified datasets.

### `create_chart_from_intent`

Request:

```json
{
  "chart_intent": {
    "title": "Revenue by Region",
    "dataset_id": 42,
    "chart_type": "bar",
    "metrics": ["revenue"],
    "dimensions": ["region"],
    "time_range": "this quarter"
  },
  "save_chart": false
}
```

Response:

```json
{
  "chart": {
    "preview_url": "http://localhost:8088/explore/...",
    "form_data": {},
    "validation": {
      "is_valid": true,
      "warnings": []
    },
    "explanation": "Bar chart compares revenue across regions."
  }
}
```

Implementation notes:

- Translate chart intent into existing `GenerateChartRequest`.
- Reuse `generate_chart` validation and preview flow.
- Default `save_chart` to false.

### `compose_dashboard`

Request:

```json
{
  "dashboard_plan": {},
  "chart_ids": [101, 102, 103],
  "draft": true
}
```

Response:

```json
{
  "dashboard": {
    "id": 55,
    "url": "http://localhost:8088/superset/dashboard/55/",
    "draft": true,
    "warnings": []
  }
}
```

Implementation notes:

- Extend existing `generate_dashboard` layout behavior.
- Support sections and text blocks after MVP.
- Persist lineage after artifact creation.

## Data Model

### `AIGeneratedArtifact`

Purpose: lineage and audit for generated BI artifacts.

Columns:

- `id`: integer primary key.
- `uuid`: UUID.
- `artifact_type`: string enum: `chart`, `dashboard`, `dataset`, `report`.
- `artifact_id`: integer.
- `principal_user_id`: foreign key to user.
- `source_prompt`: text.
- `normalized_intent`: JSON.
- `llm_provider`: string.
- `llm_model`: string.
- `tool_chain`: JSON.
- `source_asset_refs`: JSON.
- `validation_summary`: JSON.
- `confidence_score`: numeric.
- `created_on`: datetime.
- `changed_on`: datetime.

Indexes:

- `(artifact_type, artifact_id)`
- `principal_user_id`
- `uuid`

### `AISemanticAlias`

Purpose: business synonyms for AI semantic resolution.

Columns:

- `id`: integer primary key.
- `uuid`: UUID.
- `dataset_id`: nullable foreign key to dataset.
- `object_type`: string enum: `dataset`, `column`, `metric`, `dashboard`,
  `chart`.
- `object_name`: string.
- `alias`: string.
- `source`: string enum: `user`, `admin`, `usage`, `generated`.
- `approved_by`: nullable foreign key to user.
- `created_on`: datetime.

Indexes:

- `(dataset_id, object_type, object_name)`
- `alias`

### `AIEvaluationRun`

Purpose: repeatable prompt-to-dashboard evaluation records.

Columns:

- `id`: integer primary key.
- `uuid`: UUID.
- `prompt`: text.
- `expected_result`: JSON.
- `actual_result`: JSON.
- `scores`: JSON.
- `model`: string.
- `tool_versions`: JSON.
- `created_on`: datetime.

## Security Design

- All tools use existing MCP auth hook behavior.
- All asset searches use existing DAO access filters.
- Dataset metadata tool uses existing metadata privacy controls.
- Chart generation uses existing dataset access checks.
- Dashboard composition checks access to every chart before adding it.
- Generated explanations cite only accessible assets.
- Prompt, response, and lineage storage are treated as sensitive metadata.

Security test cases:

- User without dataset access cannot discover dataset through asset search.
- User without metadata access cannot retrieve AI-ready dataset details.
- RLS-restricted user sees only RLS-filtered preview results.
- User cannot compose dashboard with inaccessible chart IDs.
- Guest-token embedded user cannot mutate dashboards unless explicitly allowed.

## Frontend Design

### Routes Or Entry Points

- AI start page under `superset-frontend/src/features/ai` or equivalent.
- Dashboard creation wizard.
- Dashboard side panel assistant.
- Explore side panel assistant.

### Components

Suggested component structure:

```text
superset-frontend/src/features/ai/
  components/
    AiPromptInput.tsx
    AssetCandidateList.tsx
    DashboardPlanReview.tsx
    ChartPreviewGrid.tsx
    AiValidationPanel.tsx
    AiLineageDrawer.tsx
  hooks/
    useAiAssetSearch.ts
    useDashboardPlan.ts
    useChartIntentPreview.ts
  types.ts
```

Use `@superset-ui/core/components` wrappers and existing theme tokens.

### User Flow

1. User enters prompt.
2. UI calls backend or MCP bridge for asset discovery.
3. UI displays candidate datasets and selected plan.
4. User accepts or edits plan.
5. UI requests chart previews.
6. UI displays chart preview cards with validation warnings.
7. User creates draft dashboard.
8. UI opens dashboard editor with lineage drawer available.

## API And MCP Integration

MCP is the first-class agent interface. The frontend can either call dedicated
REST endpoints that share the same service layer or call an internal bridge
that uses the same planning and generation functions.

Do not duplicate business logic between REST and MCP. Place reusable logic in
service modules:

- `asset_search.py`
- `semantic.py`
- `planning.py`
- `lineage.py`
- `evaluation.py`

## LLM Provider Abstraction

Add an internal provider interface:

```python
class LLMProvider:
    def complete_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_schema: type,
        metadata: dict[str, object],
    ) -> object:
        ...
```

Requirements:

- Structured JSON output.
- Timeout and retry controls.
- Redaction hooks.
- Model name and provider recorded in lineage.
- Provider disabled by default unless configured.

## Evaluation Harness

Add eval fixtures under a test or docs-controlled location:

```text
tests/fixtures/genai_bi/
  prompts.yml
  expected_assets.yml
  rubrics.yml
```

Evaluation dimensions:

- Dataset selection.
- Metric mapping.
- Dimension mapping.
- Time range interpretation.
- Chart type suitability.
- Query success.
- Permission enforcement.
- Dashboard layout quality.
- Source citation quality.

## Testing Plan

### Unit Tests

- Semantic alias matching.
- Asset ranking.
- Dataset metadata compaction.
- Dashboard plan schema validation.
- Chart intent to `GenerateChartRequest` mapping.
- Lineage serialization.

### Integration Tests

- MCP asset search with different roles.
- `describe_dataset_for_ai` privacy behavior.
- Prompt-to-chart preview using example datasets.
- Dashboard composition access checks.
- Lineage creation on saved artifacts.

### Frontend Tests

- Prompt input and loading states.
- Plan review edits.
- Chart preview warning display.
- Save draft flow.
- Lineage drawer rendering.

### Security Tests

- RBAC and RLS regression tests.
- Metadata privacy tests.
- Prompt injection tests for unsafe instructions.
- Output sanitization tests.

## Rollout Plan

1. Add feature flags and provider configuration.
2. Add AI metadata and asset search services.
3. Add MCP tools for asset search and dataset description.
4. Add prompt-to-chart intent service.
5. Add dashboard planner and no-mutation plan tool.
6. Add draft dashboard composer and lineage model.
7. Add frontend wizard.
8. Add eval harness and CI checks for deterministic service behavior.

## Open Technical Questions

- Should embeddings be stored in the metadata database or an external vector
  store?
- Should generated artifact lineage be exposed in standard Superset APIs?
- Should dashboard plans be persisted before artifact creation?
- How should AI prompts be redacted before lineage storage?
- What model/provider should be the default for local development?
- Should semantic aliases require admin approval before use in production?

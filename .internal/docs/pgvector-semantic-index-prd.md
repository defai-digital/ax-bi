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

# PRD: pgvector Semantic Index For GenAI BI

> **Related documents:**
> [ADR](pgvector-semantic-index-adr.md) ·
> [Technical Specification](pgvector-semantic-index-tech-spec.md) ·
> [GenAI BI Roadmap](../../GENAI_BI_ROADMAP.md)

## Status

Proposed

## Summary

AX-BI will add a governed semantic index backed by pgvector in the Superset
metadata database. The index stores embeddings for AI-ready descriptions of
datasets, columns, metrics, charts, dashboards, glossary terms, and uploaded
file summaries. MCP tools and internal AI workflows use this index to retrieve
the right business context before creating charts or dashboards.

The vector index is not the source of truth. It is a retrieval layer. The source
of truth remains relational metadata: datasets, columns, metrics, semantic
aliases, certifications, ownership, lineage, and generated-artifact audit
records. pgvector improves semantic matching when user prompts do not use exact
technical names.

## Problem

Prompt-to-dashboard quality is fragile when the AI layer only sees table names,
column names, and raw schemas. User prompts use business language such as
"pipeline", "net revenue", "retention", or "active customers", while uploaded
files often contain ambiguous technical columns such as `amt`, `dt`, `cust_id`,
or `status`. Raw text search misses these mappings, and raw text-to-SQL tends
to guess business logic.

AX-BI needs an AI retrieval layer that can answer:

- Which dataset is most relevant to this business prompt?
- Which columns and metrics match the user's terms?
- Which existing dashboards or charts are useful examples?
- Which uploaded file summary explains the business meaning of a table?
- Which assumptions, warnings, and confidence signals should be shown before
  dashboard creation?

## Goals

- Improve dataset, metric, and column selection for MCP prompt-to-dashboard.
- Make uploaded files discoverable through business-language summaries.
- Ground MCP tools in governed, permission-aware Superset metadata.
- Preserve existing Superset RBAC, dataset permissions, RLS, and metadata
  privacy controls.
- Keep all AI retrieval context auditable and traceable to source assets.
- Provide a pgvector implementation that can evolve from SQL ranking to hybrid
  lexical/vector retrieval without adding an external vector database.
- Support human review and certification of generated semantic summaries.

## Non-Goals

- Do not store raw uploaded rows in the vector index.
- Do not use vector similarity as an authorization mechanism.
- Do not let embeddings override approved metric definitions or SQL semantics.
- Do not expose unauthorized asset names, metadata, or sample values.
- Do not replace Superset datasets, metrics, semantic layers, charts, or
  dashboards with an AI-only data model.
- Do not require a separate vector database service for the first production
  implementation.
- Do not make AI-generated summaries automatically certified.

## Target Users

### Business User

Uploads files or asks for dashboards using business language. Expects AX-BI to
find the right data and produce a draft dashboard with visible assumptions.

### Analyst

Curates datasets, column descriptions, metrics, and aliases. Needs the AI layer
to use approved definitions and to show why assets were selected.

### BI Admin

Owns governance, privacy settings, semantic metadata, and rollout controls.
Needs assurance that vector retrieval does not bypass permissions or create
unmanaged semantic drift.

### MCP Client Or Agent Builder

Uses MCP tools from a chatbot or automation workflow. Needs compact, relevant,
permission-aware context and stable tool contracts.

## Product Principles

- Relational truth, vector retrieval: store authoritative definitions in tables;
  use pgvector only to retrieve candidates.
- Govern first: every retrieval result is filtered through existing Superset
  visibility rules before it is returned.
- Summaries are draft metadata: generated descriptions need confidence,
  provenance, and review state.
- Hybrid search beats vector-only search: combine text search, semantic
  similarity, certification, usage, freshness, and ownership.
- Preview before mutation: retrieved context can plan dashboards, but created
  artifacts remain drafts until reviewed.
- Measure quality: evaluate retrieval, metric mapping, chart generation, and
  permission enforcement with repeatable tests.

## User Journeys

### Uploaded File Becomes AI-Ready

1. User uploads a CSV, Excel, or Parquet file through the existing upload flow.
2. AX-BI creates or updates a Superset dataset.
3. A background job profiles the dataset: column types, null rates,
   cardinality, date columns, likely measures, likely dimensions, and safe
   value sketches when allowed.
4. The distillation job creates AI-ready semantic documents:
   - dataset summary,
   - column descriptions,
   - likely metrics and dimensions,
   - suggested questions,
   - suggested chart and dashboard ideas,
   - warnings about missing dates, high null rates, ambiguous columns, or PII.
5. Embeddings are generated and stored in pgvector.
6. The dataset remains uncertified until a user or admin reviews the generated
   metadata.

### MCP Creates A Dashboard From A Prompt

1. User asks a chatbot: "Create a revenue dashboard by product and region for
   last quarter."
2. MCP calls `search_business_assets`.
3. The search service embeds the prompt and runs hybrid pgvector plus lexical
   search over semantic documents.
4. The service overfetches candidates, applies Superset permission filters, and
   returns only visible assets.
5. MCP calls `describe_dataset_for_ai` for the best datasets.
6. MCP creates a dashboard plan with selected datasets, metrics, dimensions,
   filters, confidence, and unresolved assumptions.
7. User reviews the plan.
8. MCP creates chart previews and a draft dashboard.

### Analyst Reviews Generated Semantics

1. Analyst opens the dataset metadata review surface.
2. AX-BI shows generated summaries, aliases, metric candidates, and suggested
   questions.
3. Analyst approves, edits, rejects, or adds terms.
4. Approved semantic documents receive higher ranking and are re-embedded when
   text changes.

## Functional Requirements

### Semantic Document Generation

- Generate semantic documents for datasets, columns, metrics, charts,
  dashboards, glossary terms, and dashboard examples.
- Generate uploaded-file summaries after upload and after schema refresh.
- Include source asset references, source hashes, generation status, confidence,
  model metadata, and review status.
- Mark documents stale when source metadata changes.
- Rebuild only changed documents when possible.

### pgvector Retrieval

- Store embeddings in the Superset metadata PostgreSQL database using pgvector.
- Support nearest-neighbor search over AI semantic documents.
- Support hybrid ranking with Postgres full-text search and relational signals.
- Support overfetching and exact fallback when post-filtered approximate search
  returns too few authorized results.
- Support configurable embedding model and dimensions for a deployment.

### Permission-Aware Asset Search

- Return only assets visible to the authenticated Superset principal.
- Reuse existing DAO access filters and MCP privacy checks.
- Avoid exposing unauthorized object names in relevance explanations.
- Treat metadata and prompts as potentially sensitive.

### MCP Integration

- Upgrade `search_business_assets` to use hybrid semantic retrieval when the
  feature flag is enabled and pgvector is available.
- Keep SQL-based lexical search as a fallback for disabled or unsupported
  deployments.
- Use retrieved semantic context in `plan_dashboard`,
  `create_chart_from_intent`, `compose_dashboard`, and `explain_dashboard`.

### Admin Controls

- Feature flag semantic indexing.
- Configure embedding provider, model, dimensions, and batch size.
- Configure whether safe sample-value sketches can be included in semantic
  documents.
- Provide reindex and stale-document repair commands.
- Provide visibility into indexing status and retrieval quality.

## Non-Functional Requirements

### Security

- No authorization decision may depend on embedding similarity.
- Vector search must run as a candidate-generation step only.
- Final returned assets must pass Superset RBAC, dataset permissions, RLS, and
  MCP metadata privacy checks.
- Raw uploaded row values are excluded by default. If value sketches are enabled,
  they must be capped, redacted, and metadata-only.

### Accuracy

- Retrieval must expose relevance reasons and confidence scores.
- Certified and approved semantics must outrank generated unreviewed summaries.
- The system should ask clarifying questions when candidate confidence is low.

### Performance

- Common asset search should return in less than 3 seconds for interactive MCP
  calls on typical AX-BI deployments.
- Indexing runs asynchronously and must not block upload completion.
- Embedding generation is idempotent and resumable.

### Operations

- pgvector must be optional at process startup unless the semantic index feature
  is enabled.
- If enabled without PostgreSQL plus the `vector` extension, startup or health
  checks should fail clearly.
- Index builds and rebuilds should have progress logging and metrics.

## Success Metrics

- Dataset selection accuracy on evaluation prompts.
- Metric and column mapping accuracy.
- Prompt-to-dashboard chart success rate.
- Reduction in "wrong dataset" and "wrong metric" dashboard plans.
- Percent of uploaded datasets with generated semantic documents.
- Percent of generated semantic documents reviewed or approved.
- Retrieval latency p50/p95.
- Security regression tests proving unauthorized metadata is not returned.

## Rollout

### Phase 1: Metadata Documents And SQL Fallback

- Add semantic document tables without enabling vector search in production.
- Generate summaries for uploaded datasets.
- Use existing lexical search plus generated descriptions.

### Phase 2: pgvector Hybrid Retrieval

- Enable pgvector for PostgreSQL metadata deployments.
- Add HNSW index and full-text index.
- Upgrade `search_business_assets` to use hybrid retrieval behind a feature
  flag.

### Phase 3: Review And Certification Workflow

- Add UI/API for reviewing generated summaries, aliases, and suggested metrics.
- Prefer approved semantics in ranking.

### Phase 4: Evaluation-Gated Prompt-To-Dashboard

- Add retrieval and prompt-to-dashboard evaluation suites.
- Gate higher-autonomy dashboard generation on retrieval quality thresholds.

## Open Questions

- Should generated uploaded-file summaries be visible to all users who can see
  the dataset, or only to owners until reviewed?
- Should semantic documents be stored globally or scoped by workspace/domain
  when multi-tenant isolation is added?
- Which embedding provider should be the default for self-hosted deployments?
- Should AX-BI offer a no-network local embedding mode for regulated
  deployments?
- How should review state map to existing certification metadata?

## Reference Notes

- pgvector stores vectors in Postgres and supports exact and approximate nearest
  neighbor search, HNSW, IVFFlat, full Postgres joins, and ACID/PITR behavior:
  https://github.com/pgvector/pgvector
- pgvector recommends `ORDER BY distance LIMIT` for index use, HNSW for a strong
  speed/recall tradeoff, and monitoring recall by comparing approximate search
  with exact search.

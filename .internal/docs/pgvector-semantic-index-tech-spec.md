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

# Technical Specification: pgvector Semantic Index

> **Related documents:**
> [PRD](pgvector-semantic-index-prd.md) ·
> [ADR](pgvector-semantic-index-adr.md) ·
> [GenAI BI Roadmap](../../GENAI_BI_ROADMAP.md)

## Status

Draft

## Scope

This spec describes a pgvector-backed semantic retrieval layer for AX-BI GenAI
BI. It covers data model additions, indexing, ingestion, retrieval, MCP
integration, permissions, rollout, and tests.

It extends the existing AI foundation rather than replacing it:

- `superset/models/ai.py`
- `superset/mcp_service/ai/asset_search.py`
- `superset/mcp_service/ai/tool/search_business_assets.py`
- `superset/mcp_service/ai/tool/describe_dataset_for_ai.py`
- `superset/mcp_service/ai/schemas.py`
- `superset/migrations/versions/2026-06-26_10-00_17a4dfa2f9ab_add_ai_bi_tables.py`

## Runtime Requirements

- PostgreSQL metadata database for semantic vector retrieval.
- pgvector extension installed in the metadata database.
- Feature flag `GENAI_SEMANTIC_INDEX` enabled.
- One active embedding provider/model/dimension per deployment for the first
  release.
- Existing SQL lexical search remains available when the feature is disabled.

If `GENAI_SEMANTIC_INDEX` is enabled and the metadata database is not
PostgreSQL with pgvector, startup or health checks must fail clearly.

## Feature Flags And Configuration

Add feature flags:

- `GENAI_SEMANTIC_INDEX`: enables semantic document generation and retrieval.
- `GENAI_SEMANTIC_INDEX_PGVECTOR`: enables pgvector-backed retrieval.
- `GENAI_UPLOADED_DATASET_DISTILLATION`: enables uploaded dataset profiling and
  summary generation.

Add configuration:

```python
AI_SEMANTIC_INDEX_BACKEND = "pgvector"
AI_SEMANTIC_EMBEDDING_PROVIDER = "ax_engine_http"
AI_SEMANTIC_EMBEDDING_ENDPOINT = "http://host.docker.internal:8099/embed"
AI_SEMANTIC_EMBEDDING_MODEL = "Qwen/Qwen3-Embedding-0.6B"
AI_SEMANTIC_EMBEDDING_DIMENSIONS = 1024
AI_SEMANTIC_INDEX_DISTANCE = "cosine"
AI_SEMANTIC_INDEX_TOP_K = 10
AI_SEMANTIC_INDEX_OVERFETCH_MULTIPLIER = 8
AI_SEMANTIC_INDEX_MAX_CANDIDATES = 200
AI_SEMANTIC_INDEX_HNSW_EF_SEARCH = 100
AI_SEMANTIC_INDEX_INCLUDE_SAMPLE_VALUE_SKETCHES = False
AI_SEMANTIC_INDEX_BATCH_SIZE = 128
```

Provider credentials must use existing Superset secret/config patterns. Do not
store provider API keys in semantic document rows.

## Data Model

### Existing Tables

The implementation reuses:

- `ai_generated_artifacts`: AI artifact lineage and audit.
- `ai_semantic_aliases`: approved or generated business aliases.
- `ai_evaluation_runs`: repeatable eval results.

### New Table: `ai_semantic_documents`

Purpose: stores text documents used for retrieval and their embeddings.

Recommended columns:

| Column | Type | Notes |
| --- | --- | --- |
| `uuid` | UUID primary key | Uses `UUIDType(binary=True)` in SQLAlchemy. |
| `object_type` | string(50) | `dataset`, `column`, `metric`, `chart`, `dashboard`, `glossary`, `example`. |
| `object_id` | integer nullable | Superset object integer ID when available. |
| `object_uuid` | UUID nullable | Superset object UUID when available. |
| `dataset_id` | integer nullable FK to `tables.id` | Present for dataset-scoped docs. |
| `parent_object_type` | string(50) nullable | For column/metric docs. |
| `parent_object_id` | integer nullable | Parent object ID. |
| `title` | string(500) | Compact display label. |
| `body` | text | AI retrieval text; no raw row dumps. |
| `document_kind` | string(50) | `summary`, `column`, `metric`, `suggested_question`, `dashboard_example`, etc. |
| `source` | string(50) | `metadata`, `upload_profile`, `generated`, `user`, `admin`, `usage`. |
| `source_hash` | string(64) | Hash of source text/metadata for idempotent reindexing. |
| `review_status` | string(50) | `generated`, `approved`, `rejected`, `stale`. |
| `confidence_score` | numeric(5,4) nullable | Generation confidence. |
| `metadata_json` | text nullable | JSON with safe structured metadata. Use Superset JSON utilities in code. |
| `embedding_provider` | string(100) nullable | Provider used for embedding. |
| `embedding_model` | string(200) nullable | Model used for embedding. |
| `embedding_dimension` | integer nullable | Expected vector dimension. |
| `embedding` | `vector(n)` nullable | pgvector column, dimension from config. |
| `embedding_generated_at` | datetime nullable | Last embedding time. |
| `created_on` | datetime | AuditMixinNullable. |
| `changed_on` | datetime nullable | AuditMixinNullable. |
| `created_by_fk` | integer nullable | Optional owner/audit field. |
| `changed_by_fk` | integer nullable | Optional owner/audit field. |

Implementation note: use `pgvector.sqlalchemy.Vector` for ORM mapping. The
Alembic migration may use raw SQL for the `vector(n)` column and HNSW indexes
because pgvector is PostgreSQL-specific.

### Indexes

Relational indexes:

```sql
CREATE INDEX ix_ai_sem_doc_object
ON ai_semantic_documents (object_type, object_id);

CREATE INDEX ix_ai_sem_doc_dataset
ON ai_semantic_documents (dataset_id);

CREATE INDEX ix_ai_sem_doc_review
ON ai_semantic_documents (review_status);

CREATE INDEX ix_ai_sem_doc_model
ON ai_semantic_documents (embedding_model, embedding_dimension);

CREATE UNIQUE INDEX uq_ai_sem_doc_source_hash
ON ai_semantic_documents (object_type, object_id, document_kind, source_hash);
```

Full-text index:

```sql
ALTER TABLE ai_semantic_documents
ADD COLUMN textsearch tsvector
GENERATED ALWAYS AS (
  to_tsvector('simple', coalesce(title, '') || ' ' || coalesce(body, ''))
) STORED;

CREATE INDEX ix_ai_sem_doc_textsearch
ON ai_semantic_documents USING gin (textsearch);
```

Vector index:

```sql
CREATE INDEX ix_ai_sem_doc_embedding_hnsw
ON ai_semantic_documents
USING hnsw (embedding vector_cosine_ops)
WHERE embedding IS NOT NULL
  AND review_status IN ('generated', 'approved');
```

Use `vector_ip_ops` only if the deployment validates normalized embeddings and
benchmarks inner product as better than cosine.

## Migration Strategy

Create a new migration after `17a4dfa2f9ab`.

Upgrade behavior:

1. Verify dialect is PostgreSQL before creating pgvector-specific objects.
2. Execute `CREATE EXTENSION IF NOT EXISTS vector`.
3. Create `ai_semantic_documents`.
4. Create relational indexes.
5. Create full-text generated column and GIN index.
6. Create the HNSW index on the initially empty table.

Initial index creation can run in the migration because the table is empty.
Rebuilds on populated tables should use `CREATE INDEX CONCURRENTLY` outside a
transaction through an admin command.

Downgrade behavior:

1. Drop `ai_semantic_documents`.
2. Do not drop the `vector` extension automatically. Other database objects may
   depend on it.

Unsupported dialect behavior:

- If the feature is disabled, non-PostgreSQL development environments can skip
  vector retrieval.
- If the feature is enabled on non-PostgreSQL, health checks should fail with a
  clear message.

## Semantic Document Generation

### Dataset Upload Trigger

After upload creates or updates a Superset dataset:

1. Enqueue `index_dataset_for_ai(dataset_id, reason="upload")`.
2. Return upload success without waiting for indexing.
3. Mark the dataset as `indexing_pending` in metadata status.

### Dataset Profiling

Profile only metadata-safe signals:

- Column names and types.
- Null rate.
- Approximate cardinality.
- Min/max for temporal and numeric columns.
- Candidate time columns.
- Candidate measures and dimensions.
- Existing dataset description, owners, tags, certification, and metrics.
- Optional top-value sketches only when privacy config allows them.

Do not profile or embed raw free-form text cells by default.

### Distillation Output

For each dataset, generate:

- one dataset summary document,
- one document for each saved metric,
- one document for each important column,
- one suggested-question document,
- one suggested-dashboard document.

Example dataset summary body:

```text
Dataset: sales_orders
Business summary: Order-level sales facts for booked revenue analysis.
Main time column: order_date.
Likely measures: revenue, quantity, discount.
Likely dimensions: region, product_category, customer_segment.
Warnings: status has ambiguous values; no certified revenue metric found.
```

### Idempotency

- Compute `source_hash` from source metadata and generated body.
- If hash is unchanged, skip embedding generation.
- If source metadata changes, mark old docs `stale` and insert new docs.
- If a user approves or edits a generated document, preserve the edited doc and
  re-embed it.

## Embedding Generation

Add package:

```text
superset/mcp_service/ai/semantic_index/
  __init__.py
  documents.py
  embeddings.py
  indexer.py
  repository.py
  search.py
  health.py
```

Recommended interfaces:

```python
class EmbeddingProvider(Protocol):
    """Generate embeddings for semantic index documents."""

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Return one embedding per input text."""
```

```python
class SemanticIndexRepository:
    """Persistence and search repository for semantic documents."""

    def upsert_documents(self, documents: list[SemanticDocumentInput]) -> None:
        """Insert or update semantic documents and embeddings."""

    def hybrid_search(
        self,
        query: str,
        query_embedding: list[float],
        asset_types: list[str],
        limit: int,
    ) -> list[SemanticSearchCandidate]:
        """Return untrusted retrieval candidates before permission filtering."""
```

The repository returns candidates. It does not decide authorization.

## Retrieval Algorithm

### Query Flow

1. Normalize the prompt.
2. Embed the prompt.
3. Run hybrid candidate search.
4. Overfetch by `AI_SEMANTIC_INDEX_OVERFETCH_MULTIPLIER`.
5. Apply Superset DAO access filters and MCP privacy checks.
6. Rerank authorized candidates.
7. If authorized results are too few, run fallback search:
   - broader HNSW search with higher `hnsw.ef_search`,
   - lexical search,
   - exact vector search for small candidate sets.
8. Return only authorized assets and relevance reasons.

### Hybrid SQL Pattern

```sql
BEGIN;
SET LOCAL hnsw.ef_search = :ef_search;
SET LOCAL hnsw.iterative_scan = relaxed_order;

WITH vector_candidates AS MATERIALIZED (
  SELECT
    uuid,
    object_type,
    object_id,
    dataset_id,
    title,
    body,
    review_status,
    embedding <=> :query_embedding AS vector_distance
  FROM ai_semantic_documents
  WHERE embedding IS NOT NULL
    AND embedding_model = :embedding_model
    AND embedding_dimension = :embedding_dimension
    AND review_status IN ('generated', 'approved')
    AND object_type = ANY(:asset_types)
  ORDER BY embedding <=> :query_embedding
  LIMIT :candidate_limit
),
lexical_candidates AS MATERIALIZED (
  SELECT
    uuid,
    ts_rank_cd(textsearch, plainto_tsquery('simple', :query_text)) AS text_rank
  FROM ai_semantic_documents
  WHERE textsearch @@ plainto_tsquery('simple', :query_text)
    AND object_type = ANY(:asset_types)
  LIMIT :candidate_limit
)
SELECT
  v.*,
  coalesce(l.text_rank, 0) AS text_rank
FROM vector_candidates v
LEFT JOIN lexical_candidates l ON l.uuid = v.uuid;

COMMIT;
```

The application layer combines:

- vector distance,
- lexical rank,
- exact alias match,
- certification,
- review status,
- usage/freshness,
- requested asset types.

### Permission Filtering

Implement `filter_authorized_candidates(user, candidates)` by object type:

- `dataset`: use `DatasetDAO._apply_base_filter` or an equivalent public DAO
  method if added.
- `chart`: use `ChartDAO._apply_base_filter`.
- `dashboard`: use `DashboardDAO._apply_base_filter`.
- `metric` and `column`: authorize through the parent dataset.
- `glossary` and `example`: authorize through referenced assets or admin scope.

Never serialize candidates before this filter.

### Fallback Rules

Fallback when:

- fewer than requested authorized results remain after filtering,
- all top candidates have low score,
- vector extension is unavailable,
- embedding provider fails,
- query is too short or only contains exact object identifiers.

Fallback order:

1. Current SQL lexical search.
2. Alias search in `ai_semantic_aliases`.
3. Exact vector search for small filtered candidate sets.
4. Clarifying question.

## MCP Tool Integration

### `search_business_assets`

Current behavior: SQL text search.

New behavior:

- If `GENAI_SEMANTIC_INDEX` and pgvector health checks pass, use hybrid search.
- Else use current SQL text search.
- Response should add optional fields:
  - `semantic_score`,
  - `lexical_score`,
  - `review_status`,
  - `source_document_uuid`,
  - `matched_terms`,
  - `retrieval_backend`.

### `describe_dataset_for_ai`

Enhance response with:

- generated dataset summary,
- reviewed summary if available,
- suggested questions,
- suggested dashboard ideas,
- stale metadata warning,
- semantic document review status.

### `plan_dashboard`

Use semantic search results as the first candidate set, then call
`describe_dataset_for_ai` on selected datasets. The plan should include:

- source document UUIDs,
- retrieval confidence,
- unresolved terms,
- fallback reason if vector retrieval was bypassed.

## API And Admin Commands

Add CLI commands:

```bash
superset ai index-dataset --dataset-id 42
superset ai index-all-datasets --only-stale
superset semantic-index backfill-datasets --json-output
superset ai semantic-index-health
superset ai semantic-index-eval --suite prompt_to_dashboard
```

Add admin API endpoints later if a UI review flow is implemented:

- `GET /api/v1/ai/semantic_documents/?dataset_id=42`
- `POST /api/v1/ai/semantic_documents/{uuid}/approve`
- `POST /api/v1/ai/semantic_documents/{uuid}/reject`
- `PUT /api/v1/ai/semantic_documents/{uuid}`

## Security And Privacy

### Invariants

- Vector similarity is never authorization.
- Retrieved documents are not returned until their source objects are
  authorized.
- Sample values are excluded unless metadata privacy config explicitly allows
  safe sketches.
- Prompt, embedding text, and retrieved context are sensitive logs.
- Relevance explanations must reference only authorized assets.

### Data Retention

- Deleted datasets should mark related semantic documents as stale or delete
  them.
- Rejected generated documents should remain audit-visible to admins but should
  not participate in retrieval.
- Embeddings should be regenerated when source text, provider, model, or
  dimension changes.

## Observability

Emit metrics:

- indexing job count, duration, failures,
- embeddings generated,
- stale document count,
- vector search latency,
- permission-filtered candidate count,
- authorized result count,
- fallback rate,
- exact-search recall sample score,
- dashboard plan dataset-selection score.

Log structured events:

- `ai.semantic_index.index_dataset`
- `ai.semantic_index.search`
- `ai.semantic_index.permission_filter`
- `ai.semantic_index.fallback`
- `ai.semantic_index.reindex`

Use existing MCP event logging patterns where the search is invoked through MCP.

## Evaluation

Add evaluation suites:

- uploaded file discovery,
- dataset selection,
- column and metric mapping,
- prompt-to-chart,
- prompt-to-dashboard,
- unauthorized metadata retrieval.

Retrieval eval row shape:

```json
{
  "prompt": "sales by region last quarter",
  "principal": "Gamma",
  "expected_assets": [
    {"asset_type": "dataset", "id": 42}
  ],
  "forbidden_assets": [
    {"asset_type": "dataset", "id": 99}
  ],
  "minimum_score": 0.75
}
```

Store results in `ai_evaluation_runs`.

## Testing

### Unit Tests

- Semantic document generation from dataset metadata.
- Source hash idempotency.
- Prompt embedding error fallback.
- Reranking math.
- Permission filtering by object type.
- MCP response schema additions.
- Redaction of sample value sketches.

### Integration Tests

Run against PostgreSQL with pgvector enabled:

- Migration creates extension-dependent table and HNSW index.
- Hybrid search returns expected assets.
- HNSW search falls back when post-filtering removes too many candidates.
- Unauthorized user cannot see forbidden dataset metadata.
- Reindex updates changed source documents and marks old docs stale.

### Performance Tests

- 10k, 100k, and 1M semantic documents if practical.
- Measure p50/p95 retrieval latency.
- Compare HNSW recall against exact search.
- Compare vector-only, lexical-only, and hybrid ranking.

## Rollout Checklist

1. Add pgvector dependency and migration.
2. Add semantic document ORM model.
3. Add embedding provider abstraction.
4. Add indexer job for uploaded datasets.
5. Add hybrid search repository.
6. Wire `search_business_assets` behind feature flags.
7. Add health checks.
8. Add eval suite.
9. Add admin reindex commands.
10. Enable in a staging environment with PostgreSQL metadata DB.

## Known Risks

- Generated summaries can be wrong. Mitigation: review state, confidence, and
  uncertified status.
- ANN filters can return too few rows. Mitigation: overfetch, iterative scans,
  exact fallback, and recall monitoring.
- Embeddings can leak sensitive metadata. Mitigation: do not embed raw rows and
  permission-filter before serialization.
- Embedding model changes can invalidate rankings. Mitigation: model metadata
  and explicit reindex jobs.
- PostgreSQL metadata DB can become overloaded. Mitigation: async indexing,
  rate limits, monitoring, and future external vector DB option if needed.

## References

- pgvector README: https://github.com/pgvector/pgvector
- pgvector guidance used here:
  - use `ORDER BY distance LIMIT` for index use,
  - HNSW has better query speed/recall tradeoff than IVFFlat,
  - create indexes after initial load,
  - use `SET LOCAL hnsw.ef_search` for query-level recall tuning,
  - use iterative scans for filtered ANN search,
  - combine pgvector with Postgres full-text search for hybrid retrieval,
  - monitor recall by comparing approximate results with exact search.

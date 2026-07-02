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

# ADR: Use pgvector For Governed Semantic Retrieval

> **Related documents:**
> [PRD](pgvector-semantic-index-prd.md) ·
> [Technical Specification](pgvector-semantic-index-tech-spec.md) ·
> [GenAI BI Roadmap](../../GENAI_BI_ROADMAP.md)

## Status

Proposed

## Context

AX-BI already has a GenAI BI direction, MCP tools, and early AI metadata tables:

- `superset/mcp_service/ai`
- `superset/mcp_service/ai/tool/search_business_assets.py`
- `superset/mcp_service/ai/tool/describe_dataset_for_ai.py`
- `superset/models/ai.py`
- `ai_generated_artifacts`
- `ai_semantic_aliases`
- `ai_evaluation_runs`

The current asset search path is primarily lexical. It works when the prompt
matches dataset, chart, or dashboard names, but it does not reliably map
business language to technical schemas. Uploaded files make this harder because
their initial column names and descriptions are often weak.

The product needs semantic retrieval, but the retrieval layer must remain
governed by Superset permissions and easy to operate in self-hosted AX-BI
deployments.

## Decision

Use pgvector in the Superset metadata PostgreSQL database as the first
production vector index for AX-BI semantic retrieval.

The implementation will:

- Store canonical business metadata in relational tables.
- Store AI semantic documents and their embeddings in Postgres.
- Use pgvector HNSW indexes for approximate nearest-neighbor retrieval.
- Use Postgres full-text search and relational ranking signals for hybrid
  retrieval.
- Use Superset DAO access filters and MCP privacy controls for final
  authorization.
- Keep SQL-based lexical search as a fallback when the feature is disabled.

pgvector will be an AX-BI production requirement only when
`GENAI_SEMANTIC_INDEX` is enabled. Deployments without a PostgreSQL metadata DB
can keep the feature disabled and continue using SQL-based search.

## Best-Practice Position

### Source Of Truth

Vector documents are not authoritative business logic. They are retrieval
documents derived from authoritative metadata. The source of truth remains:

- Superset datasets, columns, metrics, charts, and dashboards.
- Existing semantic layer objects.
- `ai_semantic_aliases` for business terms and synonyms.
- Certification and ownership metadata.
- Audit records in `ai_generated_artifacts`.

### Index Type

Use HNSW as the default pgvector ANN index because pgvector documents it as
having better query speed/recall tradeoff than IVFFlat, at the cost of slower
builds and higher memory use. The semantic index is metadata-sized first, so
query quality is more important than minimal index memory.

Use IVFFlat only if a deployment has very large, relatively static semantic
document volumes and benchmark evidence shows better behavior for that workload.

### Distance Function

Use cosine distance by default for text embeddings. If the selected embedding
provider guarantees unit-normalized embeddings, inner product can be benchmarked
for better performance, but the first implementation should prefer cosine for
clarity and portability across providers.

### Filtering And Permissions

Do not depend on pgvector filters for authorization. pgvector approximate
indexes apply filters after index scan in important cases, which can return too
few rows and is not a security boundary. The retrieval service must:

1. Retrieve candidates.
2. Overfetch.
3. Apply Superset permission filters.
4. Fallback to broader or exact search if authorized results are insufficient.
5. Return only authorized assets.

### Hybrid Retrieval

Use vector search together with:

- Postgres full-text search.
- Exact text matching.
- Semantic aliases.
- Certification status.
- Usage and freshness signals.
- Object type preferences from the MCP request.

Hybrid retrieval reduces both false positives from vector-only matching and
false negatives from lexical-only matching.

### Embedding Model Governance

Use one active embedding model and dimension per deployment for the first
release. Store `embedding_model`, `embedding_dimension`, `embedding_provider`,
and `source_hash` on every semantic document. Changing the embedding model is a
reindex operation, not an in-place silent mutation.

## Considered Options

### Option 1: FAISS In The MCP Service

FAISS is fast and useful for prototypes, but it is a library rather than a
governed database.

Pros:

- Very fast local ANN search.
- Simple prototype path.
- No database extension required.

Cons:

- Separate persistence, backup, and restore path.
- No native Superset metadata joins.
- No native RBAC/RLS/SQL filtering.
- Harder multi-process and multi-instance consistency.
- More operational burden for production.

Decision: rejected for production. FAISS can be used only for local experiments
or test fixtures.

### Option 2: External Vector Database

Examples include Qdrant, Milvus, Weaviate, and Pinecone.

Pros:

- Strong vector search feature sets.
- Independent scaling.
- Useful for very large vector corpora.

Cons:

- Additional service to deploy, secure, monitor, and back up.
- More complex consistency with Superset metadata.
- Permission filtering must be duplicated or synchronized.
- Harder default path for self-hosted AX-BI.

Decision: rejected for the first production implementation. Revisit only if
pgvector cannot meet scale or latency requirements.

### Option 3: PostgreSQL Full-Text Search Only

Pros:

- Simple and portable within Postgres.
- Good exact-token and phrase behavior.
- Easy to combine with relational filters.

Cons:

- Misses semantic matches and synonyms not already encoded.
- Weak for uploaded files with sparse or inconsistent column names.
- Less useful for natural-language MCP prompts.

Decision: rejected as the only retrieval layer. Keep it as part of hybrid
ranking.

### Option 4: pgvector In The Metadata Database

Pros:

- Keeps vectors beside governed BI metadata.
- Reuses Postgres backup, PITR, transactions, joins, and operational practices.
- Simpler deployment than an external vector database.
- Supports HNSW, IVFFlat, exact search, full-text search, and relational
  filtering.
- Aligns with AX-BI's governed, self-hosted product direction.

Cons:

- Requires PostgreSQL metadata DB and the `vector` extension.
- Approximate search requires recall monitoring.
- Filtering with ANN indexes needs careful overfetch and fallback behavior.
- Large-scale vector workloads may eventually need dedicated scaling.

Decision: accepted.

## Consequences

### Positive

- MCP asset discovery becomes semantic without adding a new service.
- Uploaded datasets become discoverable through generated business summaries.
- Retrieval stays close to Superset metadata and audit tables.
- The implementation can use SQL joins, full-text search, and vector search in
  one query plan.
- Operators can use existing Postgres monitoring and backup practices.

### Negative

- AX-BI deployments that want semantic vector retrieval must run PostgreSQL
  metadata storage with pgvector installed.
- Migrations and health checks need explicit pgvector handling.
- Search quality requires evaluation and index tuning.
- Large tenants may need partitioning, partial indexes, or future external
  vector storage.

## Security Implications

- Embeddings and semantic documents may leak business metadata if exposed to an
  unauthorized user, so they must be treated as sensitive metadata.
- Search results must be permission-filtered before serialization.
- Prompt logs, retrieved context, and relevance explanations must avoid
  unauthorized asset names.
- Raw data values must not be embedded unless the metadata privacy policy
  explicitly allows safe sketches.
- Admins need a way to delete or reindex semantic documents when source data is
  removed or access policy changes.

## Operational Implications

- Add a health check that verifies:
  - metadata DB dialect is PostgreSQL,
  - `vector` extension is installed,
  - expected semantic index table exists,
  - embedding model config matches indexed rows.
- Use async jobs for indexing and reindexing.
- Create initial HNSW indexes on empty tables in migrations; use concurrent
  index creation for later rebuilds on populated tables.
- Monitor retrieval latency, authorized-result count, fallback rate, and recall.

## Open Questions

- Should AX-BI standardize on PostgreSQL metadata DB for all GenAI BI
  deployments?
- Should embedding generation run in Superset workers, `ax-services`, or a
  separate job queue?
- Should generated semantic summaries become part of dataset certification, or
  remain a separate AI metadata review state?
- When multi-tenant isolation is added, should semantic documents be partitioned
  by tenant, workspace, or security domain?

## References

- pgvector README: https://github.com/pgvector/pgvector
- pgvector HNSW, IVFFlat, filtering, iterative scans, hybrid search, and
  monitoring guidance are used as the basis for the implementation choices in
  this ADR.

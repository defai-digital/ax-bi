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

# PRD: Cloud Data Connectors

> **Related documents:**
> [ADR](cloud-data-connectors-adr.md) ·
> [Technical Specification](cloud-data-connectors-tech-spec.md) ·
> [GenAI BI Roadmap](../../GENAI_BI_ROADMAP.md)

## Status

Draft

## Problem

AX-BI can already connect to many databases through Superset engine specs and
SQLAlchemy drivers, but users evaluating cloud BI need a clearer answer to:

- which cloud warehouses, lakehouses, data lakes, and data products are
  supported,
- which support is packaged versus merely compatible,
- which products should be queried directly versus through a lakehouse/query
  engine,
- how MCP and SDK consumers can discover connector capability without scraping
  documentation.

The current connector surface is technically broad but product-signaling is
uneven. High-value systems such as Databricks, Snowflake, BigQuery, Redshift,
Athena, Azure Data Explorer, Azure Synapse, Trino, Dremio, MotherDuck, and
Cloudflare D1 should be presented as a coherent cloud data platform story.

## Goals

- Establish AX-BI's cloud connector taxonomy for warehouses, lakehouses, query
  engines, NoSQL/search, and observability-adjacent products.
- Prioritize the most commercially valuable systems across AWS, Azure, Google
  Cloud, Databricks, Snowflake, Cloudflare, and open lakehouse engines.
- Add a machine-readable capability layer over existing engine specs.
- Keep query execution routed through existing Superset database connections.
- Give MCP, SDK, docs, and future UI work a stable classification surface.

## Non-Goals

- Do not build a separate ingestion or federation service.
- Do not bypass Superset database permissions, SQL Lab execution paths, or
  engine specs.
- Do not directly query object stores such as S3, GCS, ADLS, or R2 as
  databases. Query them through Athena, Trino, Dremio, Databricks, BigQuery,
  Snowflake, DuckDB, or equivalent engines.
- Do not treat observability APIs such as Datadog as full SQL databases unless
  a stable SQLAlchemy dialect exists.

## Target Users

- BI admins configuring enterprise cloud data connections.
- Data platform engineers standardizing warehouse and lakehouse access.
- AX-BI MCP/SDK consumers that need to select a database for AI-assisted
  queries.
- Operators packaging AX-BI images for cloud-native deployments.

## Product Requirements

### P0: Certified Cloud Data Connectors

AX-BI should identify and document these as primary cloud connectors:

- Databricks SQL Warehouse and Unity Catalog
- Snowflake
- Google BigQuery
- Amazon Redshift
- Amazon Athena over S3, Glue, and Iceberg
- Azure Data Explorer and Kusto
- Azure Synapse and Microsoft Fabric SQL endpoint compatibility
- Trino
- Dremio
- ClickHouse
- DuckDB and MotherDuck
- Cloudflare D1

### P1: Data Lake And Lakehouse Patterns

AX-BI should document lake access as query-engine patterns:

- S3 via Athena, Trino, Dremio, Databricks, Snowflake external tables, or
  DuckDB.
- GCS via BigQuery external tables, Dataproc/Spark SQL, Trino, or Dremio.
- ADLS via Synapse, Databricks, Trino, Dremio, or Fabric SQL endpoints.
- R2 via Cloudflare D1 where data is relational, or external query engines for
  object data.

### P2: Observability And Data Products

Observability platforms should be supported in one of two ways:

- direct SQL-compatible connectors when a DB-API and SQLAlchemy path exists,
- exported or archived data queried from a warehouse/lakehouse.

Datadog should be positioned as an API/archive integration candidate, not a
direct relational database connector.

## Success Metrics

- High-value cloud connectors have capability metadata.
- Docs and SDK/MCP can identify cloud connectors without name-based heuristics.
- Connector support status is visible as `certified`, `packaged`, `compatible`,
  or `integration_candidate`.
- Adding a new cloud connector requires updating one capability mapping and the
  engine spec metadata, not scattered UI conditionals.

## Risks

- Installing every cloud driver in the base image can increase image size and
  dependency conflicts.
- Vendor auth flows vary significantly and need careful secret handling.
- Some products expose analytics APIs rather than SQL, making them poor fits
  for Superset engine specs.
- SQL dialect differences affect AI-generated SQL quality.

## Rollout

1. Add cloud connector capability metadata and tests.
2. Fill metadata gaps for the highest-value existing engine specs.
3. Add generated docs sections and UI filters based on capability metadata.
4. Add MCP/SDK endpoints or fields that expose connector capability.
5. Package optional AX-BI cloud connector extras/images for common deployments.

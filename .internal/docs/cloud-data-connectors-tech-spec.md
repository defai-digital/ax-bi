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

# Technical Specification: Cloud Data Connectors

> **Related documents:**
> [PRD](cloud-data-connectors-prd.md) ·
> [ADR](cloud-data-connectors-adr.md) ·
> [GenAI BI Roadmap](../../GENAI_BI_ROADMAP.md)

## Status

Draft

## Scope

This spec covers the first connector-productization slice:

- `superset/db_engine_specs/cloud_capabilities.py`
- unit tests for high-value cloud connector classification
- later consumers in docs, REST, MCP, SDK, and frontend database UI

It does not add a migration, install cloud drivers, change SQL execution, or
change database connection persistence.

## Capability Model

Add a module that defines:

- `CloudDataProductType`
- `CloudConnectorSupportLevel`
- `CloudConnectorCapability`
- `get_cloud_connector_capability(spec)`
- `list_high_value_cloud_connectors()`

### Data Product Types

The first model supports:

- `cloud_warehouse`
- `lakehouse`
- `data_lake_query_engine`
- `query_engine`
- `nosql_or_search`
- `embedded_or_edge_sql`
- `observability_analytics`

### Support Levels

Support levels are product-facing:

- `certified`: AX-BI tests and documents this connector as a primary cloud
  connector.
- `packaged`: driver metadata and optional package support exist, but the
  connector is not yet certified end to end.
- `compatible`: SQLAlchemy compatibility exists, but AX-BI has not committed
  primary packaging or certification.
- `integration_candidate`: valuable data product, but best implemented through
  an API, archive, or exported warehouse/lakehouse path.

## Initial High-Value Mapping

The first curated list includes:

| Product | Type | Support | Notes |
| --- | --- | --- | --- |
| Databricks | Lakehouse | Packaged | SQL warehouses, clusters, Unity Catalog |
| Snowflake | Cloud warehouse | Packaged | Warehouse, external tables, Iceberg |
| Google BigQuery | Cloud warehouse | Packaged | Native and external tables |
| Amazon Redshift | Cloud warehouse | Packaged | Cluster and serverless IAM patterns |
| Amazon Athena | Data lake query engine | Packaged | S3, Glue, Iceberg |
| Azure Data Explorer | Observability analytics | Packaged | SQL and KQL paths |
| Azure Synapse | Cloud warehouse | Compatible | Synapse SQL and Fabric-like SQL endpoints |
| Trino | Data lake query engine | Packaged | Iceberg, Hive, Delta via catalogs |
| Dremio | Lakehouse | Compatible | Arrow Flight lakehouse connector |
| MotherDuck | Cloud warehouse | Packaged | DuckDB-compatible cloud analytics |
| DuckDB | Query engine | Packaged | Local and object-store analytics |
| Cloudflare D1 | Embedded or edge SQL | Compatible | Serverless SQLite semantics |
| Amazon DynamoDB | NoSQL/search | Compatible | SQL-like driver path |
| Google Datastore | NoSQL/search | Compatible | SQL-like driver path |
| ClickHouse | Cloud warehouse | Compatible | Cloud and self-hosted analytics |

## Inference Rules

If a spec is not in the curated mapping:

1. Inspect `spec.metadata["categories"]`.
2. If it includes cloud categories, infer providers.
3. If it includes `Cloud Data Warehouses`, return a compatible
   `cloud_warehouse` capability.
4. If it includes `Query Engines`, return a compatible `query_engine`
   capability.
5. If it includes `Search & NoSQL`, return a compatible `nosql_or_search`
   capability.
6. Otherwise return `None`.

## Future REST/MCP/SDK Exposure

Later changes should expose capability data through:

- database metadata endpoint for engine types,
- MCP `get_instance_info` or a new connector discovery tool,
- `packages/ax-sdk` database resource types,
- docs database index filters.

## Testing

Add unit tests that verify:

- primary high-value specs return expected capability fields,
- generic cloud categories can be inferred,
- non-cloud local specs return `None`,
- `list_high_value_cloud_connectors()` is stable and sorted.

## Operational Notes

- Capability classification is not a security control.
- Support level does not imply a driver is installed in a running deployment.
- Certification requires separate integration tests against live or emulated
  services.

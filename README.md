<!--
This product is derived from Apache Superset, which is licensed to the
Apache Software Foundation (ASF) under one or more contributor license
agreements.  See the NOTICE file distributed with this work for additional
information regarding copyright ownership.  The ASF licenses the underlying
work to you under the Apache License, Version 2.0 (the "License"); you may
not use this file except in compliance with the License.  You may obtain a
copy of the License at

  http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.  See the
License for the specific language governing permissions and limitations
under the License.
-->

# AX-BI

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/license/apache-2-0)
[![Built on Apache Superset](https://img.shields.io/badge/built%20on-Apache%20Superset-20A6C9.svg)](https://superset.apache.org)
[![MCP-native](https://img.shields.io/badge/MCP-native-6E56CF.svg)](#mcp-native-genai-bi)
[![Maintained by DEFAI](https://img.shields.io/badge/maintained%20by-DEFAI%20Private%20Limited-0A0A0A.svg)](#about-defai)

<!-- TODO: replace with the AX-BI logo once brand assets are finalized. -->
<h3>Open, governed, MCP-native GenAI BI for prompt-to-dashboard and trusted analytics agents.</h3>

**AX-BI** is a GenAI-native business intelligence platform by **DEFAI Private Limited**. It is not a chatbot bolted onto BI — it is a trusted AI analyst that discovers governed data assets, reasons over a semantic layer, generates validated charts, composes dashboards, explains results, and leaves an auditable trail. AX-BI builds on the proven [Apache Superset](https://superset.apache.org) foundation and extends it with a first-class [Model Context Protocol (MCP)](https://modelcontextprotocol.io) service so AI agents can operate on your data within your existing roles and row-level security.

[**Why BI Agents Break Down**](#why-bi-agents-break-down) |
[**MCP-Native GenAI BI**](#mcp-native-genai-bi) |
[**Get Started**](#get-started-in-60-seconds) |
[**Supported Databases**](#supported-databases) |
[**Architecture**](#workspace-architecture) |
[**Development**](#development) |
[**Contributing**](#contributing) |
[**Built on Apache Superset**](#built-on-apache-superset) |
[**About DEFAI**](#about-defai)

## Why BI Agents Break Down

Natural-language BI is only useful when it is grounded in governed metadata and produces artifacts people can inspect. Most BI assistants break down when they rely on raw text-to-SQL, disconnected chat transcripts, or model-only summaries that bypass the platform's permission model.

Common failure modes:

- **Ungoverned discovery** - agents see table names but not business meaning, certification status, owners, metrics, or usage context.
- **Permission drift** - generated queries and asset search do not consistently inherit the user's RBAC, dataset permissions, and row-level security.
- **Opaque answers** - users get prose or screenshots instead of real charts, dashboards, SQL, and validation results.
- **No audit trail** - prompts, tool calls, generated assets, and approval steps are not visible to operators.
- **Disconnected workflows** - data upload, dataset creation, chart authoring, dashboard composition, and explanation happen in separate tools.

AX-BI addresses this with a self-hosted BI workspace where AI agents call governed platform tools instead of scraping around the application.

## What AX-BI Is

AX-BI is a Superset-based analytics platform extended for AI-native business intelligence. It combines the standard BI surface - datasets, SQL Lab, charts, dashboards, reports, alerts, security, and database connectivity - with an MCP service that exposes those same resources as governed tools for AI agents.

Use AX-BI when you need:

- **Prompt-to-dashboard** workflows that create real Superset dashboards from governed data assets.
- **AI-ready semantic context** for datasets, columns, metrics, certified assets, owners, tags, and dashboard layouts.
- **Agent-safe operations** where AI actions run through the same permission, command, DAO, validation, and event-logging layers as the web app.
- **Self-hosted deployment** with control over databases, authentication, model connections, and infrastructure boundaries.
- **Extensible analytics infrastructure** through REST APIs, MCP tools, chart plugins, Python extensions, and a TypeScript sidecar.

## Why Teams Choose AX-BI

| Requirement | Typical BI assistant | AX-BI |
| --- | --- | --- |
| Discover trusted business data | Often relies on raw schemas or loose search | RBAC-aware search over datasets, charts, dashboards, tags, certification metadata, and owners |
| Build governed charts | Often returns SQL or narrative only | Generates validated Superset chart artifacts with preview and save paths |
| Compose dashboards | Often produces static mockups | Plans and composes real Superset dashboards from generated or existing charts |
| Respect security | Often requires separate agent policy glue | Uses Superset RBAC, dataset access checks, row-level security, and MCP auth hooks |
| Operate in production | Often demo-oriented | Ships Docker, Helm, health/readiness checks, audit-oriented middleware, and production MCP guidance |
| Extend beyond the browser | Usually web-only | Adds MCP, REST APIs, `ax-services`, desktop shell, and extension tooling |

## Primary Users

### Primary

- **Data and analytics teams** building governed self-service BI with AI-assisted authoring.
- **Product and operations teams** that want prompt-to-dashboard workflows inside controlled deployments.
- **Platform and infrastructure teams** exposing analytics resources to internal agents through MCP.

### Secondary

- **Developers** building Superset extensions, MCP-enabled workflows, embedded analytics, or desktop BI clients.
- **Advanced analysts** who need SQL Lab, dashboard authoring, and AI-assisted exploration in one platform.

## High-Value Use Cases

1. **Prompt-to-dashboard** - turn a business question into a dashboard plan, chart previews, validation results, and a saved dashboard after review.
2. **Dashboard Q&A** - answer questions against existing dashboards while preserving permissions and asset context.
3. **Governed data discovery** - find certified datasets, charts, dashboards, tags, owners, and schema details through RBAC-aware search.
4. **Upload-to-insight** - upload spreadsheet or CSV data, create a dataset, generate charts, and compose a dashboard.
5. **Agent-ready analytics infrastructure** - expose Superset resources to tools such as AX Studio, Claude Desktop, or other MCP-compatible clients.
6. **Embedded AI BI** - scope dashboard Q&A and prompt-to-dashboard behavior to host applications and embedded guest permissions.

## When To Use AX-BI

- You need an open BI platform that can be self-hosted and extended.
- You want AI workflows grounded in a governed semantic layer rather than free-form SQL generation.
- You need AI agents to create inspectable dashboards, charts, datasets, saved queries, and reports.
- You need Superset compatibility while adding MCP-native agent access and AX runtime components.

## Core Features

AX-BI provides the Superset BI foundation plus AX-specific agent and runtime layers:

- A **no-code interface** for building charts quickly
- A powerful, web-based **SQL Editor** for advanced querying
- A **lightweight semantic layer** for quickly defining custom dimensions and metrics
- Out-of-the-box support for **nearly any SQL** database or data engine
- A wide array of **beautiful visualizations**, from simple bar charts to geospatial maps
- A lightweight, configurable **caching layer** to ease database load
- Highly extensible **security roles and authentication** options
- An **MCP service and REST API** for programmatic and AI-agent access
- **Prompt-to-chart** and **prompt-to-dashboard** tools for governed AI authoring
- **Dashboard explanation and Q&A** tools for existing BI assets
- **Spreadsheet and CSV upload** paths exposed through MCP dataset tools
- **AX Services** TypeScript sidecar for runtime health, readiness, contracts, and Superset connectivity
- **AX-BI Desktop** thin Tauri shell with deep links and desktop-grade web app integration
- **Extension tooling** for scaffolding and packaging Superset extensions
- A **cloud-native architecture** designed from the ground up for scale

## MCP-Native GenAI BI

What sets AX-BI apart from a traditional BI stack is that it is **agent-ready by design**. The built-in MCP service exposes Superset's core resources — datasets, charts, dashboards, queries, and the semantic layer — as governed tools that any MCP-compatible AI agent can call.

- **Prompt-to-dashboard** — turn natural-language questions into validated charts and composed dashboards, grounded in governed semantics rather than raw text-to-SQL.
- **Governed by default** — agent tool visibility and every generated query respect your existing RBAC and row-level security. Agents cannot see or do more than the user they act for.
- **Verifiable artifacts** — generated charts and dashboards are real, inspectable Superset objects, not opaque answers.
- **Auditable** — agent actions flow through the same command, DAO, and event-logging layers as the rest of the platform.

Available MCP tool groups include:

- `search_business_assets` — searches governed datasets, charts, and dashboards
  with RBAC-aware filtering, relevance scoring, and optional certified-only
  results.
- `describe_dataset_for_ai` — returns compact, AI-ready dataset context with
  semantic alias lookup and privacy-aware metadata controls.
- `create_chart_from_intent`, `generate_chart`, and `validate_chart` — create
  and validate chart specifications from business intent.
- `plan_dashboard`, `compose_dashboard`, and `prompt_to_dashboard` — move from
  natural-language intent to a dashboard plan and composed dashboard artifact.
- `ask_dashboard_question`, `explain_dashboard`, and
  `evaluate_ai_answer` — inspect and explain existing dashboards.
- `list_*` and `get_*` tools for charts, dashboards, databases, datasets,
  reports, saved queries, roles, RLS filters, tags, tasks, users, and system
  metadata.
- SQL Lab and dataset tools for executing SQL, saving queries, creating
  datasets, querying datasets, and uploading files where permitted.

The MCP service lives in [`superset/mcp_service/`](https://github.com/defai-digital/ax-bi/tree/main/superset/mcp_service) and ships with its own architecture, security, and production guides. See the [GenAI BI Roadmap](https://github.com/defai-digital/ax-bi/blob/main/GENAI_BI_ROADMAP.md) for the product direction.

## Workspace Architecture

AX-BI keeps the browser, API, MCP, and sidecar layers connected to one governed Superset metadata and security model.

```text
AX-BI
├── Web app and REST API
│   ├── Flask/AppBuilder backend
│   ├── React/TypeScript frontend
│   ├── SQL Lab, Explore, dashboards, reports, alerts
│   └── RBAC, RLS, authentication, event logging
├── MCP service
│   ├── FastMCP server process
│   ├── RBAC-aware tool registration and auth hooks
│   ├── Dataset, chart, dashboard, SQL Lab, and AI tools
│   └── Middleware for validation, privacy, telemetry, and audit context
├── AX Services sidecar
│   ├── Health, readiness, metrics, runtime contracts
│   └── Superset asset and permission proxy endpoints
├── Extension and desktop surfaces
│   ├── superset-core shared abstractions
│   ├── superset-extensions CLI
│   └── Tauri desktop shell with axbi:// deep links
└── Data and infrastructure
    ├── SQLAlchemy database connectors
    ├── Metadata database, cache, async workers, and WebSocket support
    └── Docker and Helm deployment paths
```

## Get Started in 60 Seconds

### Prerequisites

- Docker and Docker Compose
- A generated `SUPERSET_SECRET_KEY`
- Values for `DATABASE_PASSWORD` and `ADMIN_PASSWORD`

```bash
git clone https://github.com/defai-digital/ax-bi.git
cd ax-bi

cp docker/.env-axbi.example docker/.env-axbi
# Fill SUPERSET_SECRET_KEY, DATABASE_PASSWORD, and ADMIN_PASSWORD.
# Generate secrets with: openssl rand -base64 42

docker compose --env-file docker/.env-axbi -f docker-compose-axbi.yml up -d
```

Default local endpoints:

| Service | URL |
| --- | --- |
| AX-BI web app | `http://localhost:8088` |
| MCP service | `http://localhost:5008` |
| AX Services sidecar | `http://localhost:5010` |

To build images from this checkout instead of pulling published images:

```bash
docker compose \
  --env-file docker/.env-axbi \
  -f docker-compose-axbi.yml \
  -f docker-compose-axbi-build.yml \
  up -d --build
```

## Supported Databases

AX-BI can query data from any SQL-speaking datastore or data engine (Presto, Trino, Athena, [and more](https://superset.apache.org/user-docs/databases)) that has a Python DB-API driver and a SQLAlchemy dialect.

Here are some of the major database solutions that are supported:

<!-- SUPPORTED_DATABASES_START -->
<div align="center">
  <a href="https://superset.apache.org/user-docs/databases/supported/amazon-athena" title="Amazon Athena"><img src="docs/static/img/databases/amazon-athena.jpg" alt="Amazon Athena" width="76" height="40" /></a> &nbsp;
  <a href="https://superset.apache.org/user-docs/databases/supported/amazon-dynamodb" title="Amazon DynamoDB"><img src="docs/static/img/databases/aws.png" alt="Amazon DynamoDB" width="40" height="40" /></a> &nbsp;
  <a href="https://superset.apache.org/user-docs/databases/supported/amazon-redshift" title="Amazon Redshift"><img src="docs/static/img/databases/redshift.png" alt="Amazon Redshift" width="100" height="40" /></a> &nbsp;
  <a href="https://superset.apache.org/user-docs/databases/supported/apache-doris" title="Apache Doris"><img src="docs/static/img/databases/doris.png" alt="Apache Doris" width="103" height="40" /></a> &nbsp;
  <a href="https://superset.apache.org/user-docs/databases/supported/apache-drill" title="Apache Drill"><img src="docs/static/img/databases/apache-drill.png" alt="Apache Drill" width="81" height="40" /></a> &nbsp;
  <a href="https://superset.apache.org/user-docs/databases/supported/apache-druid" title="Apache Druid"><img src="docs/static/img/databases/druid.png" alt="Apache Druid" width="117" height="40" /></a> &nbsp;
  <a href="https://superset.apache.org/user-docs/databases/supported/apache-hive" title="Apache Hive"><img src="docs/static/img/databases/apache-hive.svg" alt="Apache Hive" width="44" height="40" /></a> &nbsp;
  <a href="https://superset.apache.org/user-docs/databases/supported/apache-impala" title="Apache Impala"><img src="docs/static/img/databases/apache-impala.png" alt="Apache Impala" width="21" height="40" /></a> &nbsp;
  <a href="https://superset.apache.org/user-docs/databases/supported/apache-kylin" title="Apache Kylin"><img src="docs/static/img/databases/apache-kylin.png" alt="Apache Kylin" width="44" height="40" /></a> &nbsp;
  <a href="https://superset.apache.org/user-docs/databases/supported/apache-pinot" title="Apache Pinot"><img src="docs/static/img/databases/apache-pinot.svg" alt="Apache Pinot" width="76" height="40" /></a> &nbsp;
  <a href="https://superset.apache.org/user-docs/databases/supported/apache-solr" title="Apache Solr"><img src="docs/static/img/databases/apache-solr.png" alt="Apache Solr" width="79" height="40" /></a> &nbsp;
  <a href="https://superset.apache.org/user-docs/databases/supported/apache-spark-sql" title="Apache Spark SQL"><img src="docs/static/img/databases/apache-spark.png" alt="Apache Spark SQL" width="75" height="40" /></a> &nbsp;
  <a href="https://superset.apache.org/user-docs/databases/supported/ascend" title="Ascend"><img src="docs/static/img/databases/ascend.webp" alt="Ascend" width="117" height="40" /></a> &nbsp;
  <a href="https://superset.apache.org/user-docs/databases/supported/aurora-mysql-data-api" title="Aurora MySQL (Data API)"><img src="docs/static/img/databases/mysql.png" alt="Aurora MySQL (Data API)" width="77" height="40" /></a> &nbsp;
  <a href="https://superset.apache.org/user-docs/databases/supported/aurora-postgresql-data-api" title="Aurora PostgreSQL (Data API)"><img src="docs/static/img/databases/postgresql.svg" alt="Aurora PostgreSQL (Data API)" width="76" height="40" /></a> &nbsp;
  <a href="https://superset.apache.org/user-docs/databases/supported/azure-data-explorer" title="Azure Data Explorer"><img src="docs/static/img/databases/kusto.png" alt="Azure Data Explorer" width="40" height="40" /></a> &nbsp;
  <a href="https://superset.apache.org/user-docs/databases/supported/azure-synapse" title="Azure Synapse"><img src="docs/static/img/databases/azure.svg" alt="Azure Synapse" width="40" height="40" /></a> &nbsp;
  <a href="https://superset.apache.org/user-docs/databases/supported/clickhouse" title="ClickHouse"><img src="docs/static/img/databases/clickhouse.png" alt="ClickHouse" width="150" height="37" /></a> &nbsp;
  <a href="https://superset.apache.org/user-docs/databases/supported/cloudflare-d1" title="Cloudflare D1"><img src="docs/static/img/databases/cloudflare.png" alt="Cloudflare D1" width="40" height="40" /></a> &nbsp;
  <a href="https://superset.apache.org/user-docs/databases/supported/cockroachdb" title="CockroachDB"><img src="docs/static/img/databases/cockroachdb.png" alt="CockroachDB" width="150" height="24" /></a> &nbsp;
  <a href="https://superset.apache.org/user-docs/databases/supported/couchbase" title="Couchbase"><img src="docs/static/img/databases/couchbase.svg" alt="Couchbase" width="150" height="35" /></a> &nbsp;
  <a href="https://superset.apache.org/user-docs/databases/supported/cratedb" title="CrateDB"><img src="docs/static/img/databases/cratedb.svg" alt="CrateDB" width="180" height="24" /></a> &nbsp;
  <a href="https://superset.apache.org/user-docs/databases/supported/databend" title="Databend"><img src="docs/static/img/databases/databend.png" alt="Databend" width="100" height="40" /></a> &nbsp;
  <a href="https://superset.apache.org/user-docs/databases/supported/databricks" title="Databricks"><img src="docs/static/img/databases/databricks.png" alt="Databricks" width="152" height="24" /></a> &nbsp;
  <a href="https://superset.apache.org/user-docs/databases/supported/denodo" title="Denodo"><img src="docs/static/img/databases/denodo.png" alt="Denodo" width="138" height="40" /></a> &nbsp;
  <a href="https://superset.apache.org/user-docs/databases/supported/dremio" title="Dremio"><img src="docs/static/img/databases/dremio.png" alt="Dremio" width="126" height="40" /></a> &nbsp;
  <a href="https://superset.apache.org/user-docs/databases/supported/duckdb" title="DuckDB"><img src="docs/static/img/databases/duckdb.png" alt="DuckDB" width="52" height="40" /></a> &nbsp;
  <a href="https://superset.apache.org/user-docs/databases/supported/elasticsearch" title="Elasticsearch"><img src="docs/static/img/databases/elasticsearch.png" alt="Elasticsearch" width="40" height="40" /></a> &nbsp;
  <a href="https://superset.apache.org/user-docs/databases/supported/exasol" title="Exasol"><img src="docs/static/img/databases/exasol.png" alt="Exasol" width="72" height="40" /></a> &nbsp;
  <a href="https://superset.apache.org/user-docs/databases/supported/firebird" title="Firebird"><img src="docs/static/img/databases/firebird.png" alt="Firebird" width="100" height="40" /></a> &nbsp;
  <a href="https://superset.apache.org/user-docs/databases/supported/firebolt" title="Firebolt"><img src="docs/static/img/databases/firebolt.png" alt="Firebolt" width="100" height="40" /></a> &nbsp;
  <a href="https://superset.apache.org/user-docs/databases/supported/google-bigquery" title="Google BigQuery"><img src="docs/static/img/databases/google-big-query.svg" alt="Google BigQuery" width="76" height="40" /></a> &nbsp;
  <a href="https://superset.apache.org/user-docs/databases/supported/google-sheets" title="Google Sheets"><img src="docs/static/img/databases/google-sheets.svg" alt="Google Sheets" width="76" height="40" /></a> &nbsp;
  <a href="https://superset.apache.org/user-docs/databases/supported/greenplum" title="Greenplum"><img src="docs/static/img/databases/greenplum.png" alt="Greenplum" width="124" height="40" /></a> &nbsp;
  <a href="https://superset.apache.org/user-docs/databases/supported/hologres" title="Hologres"><img src="docs/static/img/databases/hologres.png" alt="Hologres" width="44" height="40" /></a> &nbsp;
  <a href="https://superset.apache.org/user-docs/databases/supported/ibm-db2" title="IBM Db2"><img src="docs/static/img/databases/ibm-db2.svg" alt="IBM Db2" width="91" height="40" /></a> &nbsp;
  <a href="https://superset.apache.org/user-docs/databases/supported/ibm-netezza-performance-server" title="IBM Netezza Performance Server"><img src="docs/static/img/databases/netezza.png" alt="IBM Netezza Performance Server" width="40" height="40" /></a> &nbsp;
  <a href="https://superset.apache.org/user-docs/databases/supported/mariadb" title="MariaDB"><img src="docs/static/img/databases/mariadb.png" alt="MariaDB" width="150" height="37" /></a> &nbsp;
  <a href="https://superset.apache.org/user-docs/databases/supported/microsoft-sql-server" title="Microsoft SQL Server"><img src="docs/static/img/databases/msql.png" alt="Microsoft SQL Server" width="50" height="40" /></a> &nbsp;
  <a href="https://superset.apache.org/user-docs/databases/supported/monetdb" title="MonetDB"><img src="docs/static/img/databases/monet-db.png" alt="MonetDB" width="100" height="40" /></a> &nbsp;
  <a href="https://superset.apache.org/user-docs/databases/supported/mongodb" title="MongoDB"><img src="docs/static/img/databases/mongodb.png" alt="MongoDB" width="150" height="38" /></a> &nbsp;
  <a href="https://superset.apache.org/user-docs/databases/supported/motherduck" title="MotherDuck"><img src="docs/static/img/databases/motherduck.png" alt="MotherDuck" width="40" height="40" /></a> &nbsp;
  <a href="https://superset.apache.org/user-docs/databases/supported/oceanbase" title="OceanBase"><img src="docs/static/img/databases/oceanbase.svg" alt="OceanBase" width="175" height="24" /></a> &nbsp;
  <a href="https://superset.apache.org/user-docs/databases/supported/oracle" title="Oracle"><img src="docs/static/img/databases/oraclelogo.png" alt="Oracle" width="111" height="40" /></a> &nbsp;
  <a href="https://superset.apache.org/user-docs/databases/supported/presto" title="Presto"><img src="docs/static/img/databases/presto-og.png" alt="Presto" width="127" height="40" /></a> &nbsp;
  <a href="https://superset.apache.org/user-docs/databases/supported/risingwave" title="RisingWave"><img src="docs/static/img/databases/risingwave.svg" alt="RisingWave" width="147" height="40" /></a> &nbsp;
  <a href="https://superset.apache.org/user-docs/databases/supported/sap-hana" title="SAP HANA"><img src="docs/static/img/databases/sap-hana.png" alt="SAP HANA" width="137" height="40" /></a> &nbsp;
  <a href="https://superset.apache.org/user-docs/databases/supported/sap-sybase" title="SAP Sybase"><img src="docs/static/img/databases/sybase.png" alt="SAP Sybase" width="100" height="40" /></a> &nbsp;
  <a href="https://superset.apache.org/user-docs/databases/supported/shillelagh" title="Shillelagh"><img src="docs/static/img/databases/shillelagh.png" alt="Shillelagh" width="40" height="40" /></a> &nbsp;
  <a href="https://superset.apache.org/user-docs/databases/supported/singlestore" title="SingleStore"><img src="docs/static/img/databases/singlestore.png" alt="SingleStore" width="150" height="31" /></a> &nbsp;
  <a href="https://superset.apache.org/user-docs/databases/supported/snowflake" title="Snowflake"><img src="docs/static/img/databases/snowflake.svg" alt="Snowflake" width="76" height="40" /></a> &nbsp;
  <a href="https://superset.apache.org/user-docs/databases/supported/sqlite" title="SQLite"><img src="docs/static/img/databases/sqlite.png" alt="SQLite" width="84" height="40" /></a> &nbsp;
  <a href="https://superset.apache.org/user-docs/databases/supported/starrocks" title="StarRocks"><img src="docs/static/img/databases/starrocks.png" alt="StarRocks" width="149" height="40" /></a> &nbsp;
  <a href="https://superset.apache.org/user-docs/databases/supported/superset-meta-database" title="Meta database"><img src="docs/static/img/databases/superset.svg" alt="Meta database" width="150" height="39" /></a> &nbsp;
  <a href="https://superset.apache.org/user-docs/databases/supported/tdengine" title="TDengine"><img src="docs/static/img/databases/tdengine.png" alt="TDengine" width="140" height="40" /></a> &nbsp;
  <a href="https://superset.apache.org/user-docs/databases/supported/teradata" title="Teradata"><img src="docs/static/img/databases/teradata.png" alt="Teradata" width="124" height="40" /></a> &nbsp;
  <a href="https://superset.apache.org/user-docs/databases/supported/timescaledb" title="TimescaleDB"><img src="docs/static/img/databases/timescale.png" alt="TimescaleDB" width="150" height="36" /></a> &nbsp;
  <a href="https://superset.apache.org/user-docs/databases/supported/trino" title="Trino"><img src="docs/static/img/databases/trino.png" alt="Trino" width="89" height="40" /></a> &nbsp;
  <a href="https://superset.apache.org/user-docs/databases/supported/vertica" title="Vertica"><img src="docs/static/img/databases/vertica.png" alt="Vertica" width="128" height="40" /></a> &nbsp;
  <a href="https://superset.apache.org/user-docs/databases/supported/ydb" title="YDB"><img src="docs/static/img/databases/ydb.svg" alt="YDB" width="110" height="40" /></a> &nbsp;
  <a href="https://superset.apache.org/user-docs/databases/supported/yugabytedb" title="YugabyteDB"><img src="docs/static/img/databases/yugabyte.png" alt="YugabyteDB" width="150" height="26" /></a>
</div>
<!-- SUPPORTED_DATABASES_END -->

**A more comprehensive list of supported databases** along with configuration instructions can be found in the [Apache Superset database docs](https://superset.apache.org/user-docs/databases), which apply to the AX-BI data layer.

Want to add support for your datastore or data engine? Read about the [technical requirements](https://superset.apache.org/user-docs/faq#does-superset-work-with-insert-database-engine-here).

## Installation and Configuration

AX-BI runs anywhere the underlying Superset platform runs.

- **Docker deployment** — the recommended path for AX-BI users:
  ```bash
  cp docker/.env-axbi.example docker/.env-axbi
  # Fill SUPERSET_SECRET_KEY, DATABASE_PASSWORD, and ADMIN_PASSWORD.
  # Generate secrets with: openssl rand -base64 42
  docker compose --env-file docker/.env-axbi -f docker-compose-axbi.yml up -d
  ```
  To build images from this checkout instead of pulling published images, add
  `-f docker-compose-axbi-build.yml --build`.
- **Production deployments** — use the Docker stack above with managed Postgres/Redis or see the [Helm chart](https://github.com/defai-digital/ax-bi/tree/main/helm/superset) and the architecture guidance in the [Superset admin docs](https://superset.apache.org/admin-docs/installation/architecture), which apply to AX-BI.
- **MCP service in production** — see [`superset/mcp_service/PRODUCTION.md`](https://github.com/defai-digital/ax-bi/blob/main/superset/mcp_service/PRODUCTION.md).

## Development

AX-BI has a Flask/Python backend and a React/TypeScript frontend.

```bash
# Backend (Flask dev server)
make flask-app

# Frontend dev server (port 9000)
cd superset-frontend && npm run dev-server

# Run the MCP service
superset mcp run            # requires: pip install fastmcp

# Tests
pytest                                 # backend
cd superset-frontend && npm run test   # frontend

# Always run before pushing
pre-commit run --all-files
```

See [`CLAUDE.md`](https://github.com/defai-digital/ax-bi/blob/main/CLAUDE.md) for the full engineering guide (commands, architecture, conventions, and the MCP service), [`GENAI_BI_ROADMAP.md`](https://github.com/defai-digital/ax-bi/blob/main/GENAI_BI_ROADMAP.md) for product direction, and [`SECURITY.md`](https://github.com/defai-digital/ax-bi/blob/main/SECURITY.md) for the security and threat model.

## Contributing

At this time, AX-BI is not accepting unsolicited public code contributions or pull requests.

What we do welcome:

- Bug reports
- Feature requests and wishlist items
- Product feedback
- Reproducible issue reports with logs, screenshots, configuration details, or environment details

See [`CONTRIBUTING.md`](https://github.com/defai-digital/ax-bi/blob/main/CONTRIBUTING.md) for the current repository policy and the best way to submit feedback.

## Built on Apache Superset

AX-BI is a derivative work of [Apache Superset](https://superset.apache.org), a project of the Apache Software Foundation, used under the [Apache License 2.0](https://github.com/defai-digital/ax-bi/blob/main/LICENSE). DEFAI Private Limited is grateful to the Apache Superset community for the foundation this product is built on.

*Apache Superset, Apache, and the Apache feather logo are trademarks of the Apache Software Foundation. DEFAI Private Limited and AX-BI are not affiliated with or endorsed by the Apache Software Foundation.* Upstream attribution and license terms are retained in the [`NOTICE`](https://github.com/defai-digital/ax-bi/blob/main/NOTICE) and [`LICENSE`](https://github.com/defai-digital/ax-bi/blob/main/LICENSE) files; the documentation links above point to the upstream Apache Superset docs, which apply to the corresponding AX-BI functionality.

## License

AX-BI is distributed under the [Apache License 2.0](https://github.com/defai-digital/ax-bi/blob/main/LICENSE). See [`LICENSE`](https://github.com/defai-digital/ax-bi/blob/main/LICENSE) and [`NOTICE`](https://github.com/defai-digital/ax-bi/blob/main/NOTICE) for details.

## About DEFAI

**AX-BI** is developed and maintained by **DEFAI Private Limited**.

<!-- TODO: add DEFAI website, contact email, and support channel once finalized. -->
- Website: _coming soon_
- Support: _coming soon_

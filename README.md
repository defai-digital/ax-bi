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
[**Get Started**](#quick-start-with-docker) |
[**Supported File Types**](#supported-file-types) |
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

## Naming Policy

AX-BI uses an external rename strategy. Public commands and local development
paths use AX-BI names: `ax-bi`, `ax-bi-mcp`, and `ax-bi-frontend/`.

Core Superset namespaces remain in place for compatibility with upstream
Superset, existing imports, migrations, extensions, package contracts, Helm
values, and deployment configuration. This is intentional: directories such as
`superset/`, `superset-core/`, `superset-extensions-cli/`,
`superset-embedded-sdk/`, `superset-websocket/`, and `helm/superset` are not
unfinished rename work. See the
[AX-BI Rename Policy](https://github.com/defai-digital/ax-bi/blob/main/docs/developer_docs/ax-bi-rename-policy.md)
before renaming any remaining `superset*` surface.

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

## Quick Start with Docker

The fastest way to try AX-BI is Docker Compose. This pulls the public
multi-architecture images from GitHub Container Registry:

- `ghcr.io/defai-digital/ax-bi`
- `ghcr.io/defai-digital/ax-bi-services`

### 1. Install Prerequisites

- Docker and Docker Compose
- Git

### 2. Clone AX-BI

```shell
git clone https://github.com/defai-digital/ax-bi.git
cd ax-bi
```

### 3. Create Your Environment File

```shell
cp docker/.env-axbi.example docker/.env-axbi
```

Edit `docker/.env-axbi` and fill the required values:

```env
SUPERSET_SECRET_KEY=<generated secret>
DATABASE_PASSWORD=<generated database password>
ADMIN_PASSWORD=<admin login password>
```

Generate secure values with:

```shell
openssl rand -base64 42
```

The sample file uses the public images:

```env
AXBI_IMAGE=ghcr.io/defai-digital/ax-bi:latest
AX_SERVICES_IMAGE=ghcr.io/defai-digital/ax-bi-services:latest
```

For production or repeatable demos, replace `latest` with a pinned release tag
when one is available.

### 4. Start AX-BI

```shell
docker compose --env-file docker/.env-axbi -f docker-compose-axbi.yml up -d
```

The first startup initializes Postgres, runs migrations, creates the admin user,
and starts the web app, MCP service, AX Services sidecar, Redis, and Celery
workers.

Check the containers:

```shell
docker compose --env-file docker/.env-axbi -f docker-compose-axbi.yml ps
```

Wait until the `superset` service is healthy, then open:

| Service | URL |
| --- | --- |
| AX-BI web app | `http://localhost:8088` |
| MCP service | `http://localhost:5008` |
| AX Services sidecar | `http://localhost:5010` |

Log in with:

```text
username: admin
password: ADMIN_PASSWORD from docker/.env-axbi
```

### 5. Stop or Update

Stop the stack without deleting data:

```shell
docker compose --env-file docker/.env-axbi -f docker-compose-axbi.yml stop
```

Pull newer images and restart:

```shell
docker compose --env-file docker/.env-axbi -f docker-compose-axbi.yml pull
docker compose --env-file docker/.env-axbi -f docker-compose-axbi.yml up -d
```

### Notes for Shared or Public Deployments

This quick start is for local trials. Before exposing AX-BI on a network:

- Put the web app behind HTTPS.
- Keep Postgres and Redis private.
- Pin image tags instead of using `latest`.
- Back up the Postgres metadata database.
- Leave `MCP_DEV_USERNAME` empty.
- Configure JWT authentication before exposing MCP with
  `MCP_AUTH_ENABLED=true`.

See [`docker/README.md`](https://github.com/defai-digital/ax-bi/tree/main/docker)
for Docker details and
[`superset/mcp_service/PRODUCTION.md`](https://github.com/defai-digital/ax-bi/blob/main/superset/mcp_service/PRODUCTION.md)
for MCP production guidance.

To build images from this checkout instead of pulling published images:

```shell
docker compose \
  --env-file docker/.env-axbi \
  -f docker-compose-axbi.yml \
  -f docker-compose-axbi-build.yml \
  up -d --build
```

## Supported File Types

AX-BI supports local data-file upload through the web/API upload paths and the
MCP dataset tools when `ENABLE_LOCAL_FILE_UPLOAD` is enabled and the acting user
has the required database upload permission. Uploaded files are loaded into the
local analytics database and registered as Superset datasets.

| Category | Extensions | Notes |
| --- | --- | --- |
| Delimited text | `.csv`, `.tsv`, `.txt` | Treated as CSV-style tabular data. |
| Excel workbooks | `.xls`, `.xlsx` | Supports sheet selection; MCP upload responses can return available sheet names. |
| Columnar data | `.parquet` | Supported for direct local/MCP uploads. The global upload allow-list also includes `.zip` for columnar upload paths. |
| Structured files | `.json`, `.jsonl`, `.ndjson`, `.xml` | Parsed through the structured upload reader. |
| SQL and database extracts | `.sql`, `.dump`, `.sqlite`, `.sqlite3`, `.db` | Useful for local database-style imports; `.db` is supported by the web/API local upload path. |

MCP upload tools accept base64-encoded file contents through `upload_file` for a
single file and `upload_files` for batch upload. Batch uploads are capped at 10
files per request. The default per-file upload limit is 100 MB and can be
changed with `UPLOAD_MAX_FILE_SIZE_BYTES`.

## Supported Databases

AX-BI can query data from any SQL-speaking datastore or data engine (Presto, Trino, Athena, [and more](https://superset.apache.org/user-docs/databases)) that has a Python DB-API driver and a SQLAlchemy dialect.

Here are some of the major database solutions that are supported:

<!-- SUPPORTED_DATABASES_START -->
| Category | Supported databases and engines |
| --- | --- |
| Cloud warehouses and lakehouses | [Amazon Athena](https://superset.apache.org/user-docs/databases/supported/amazon-athena), [Amazon Redshift](https://superset.apache.org/user-docs/databases/supported/amazon-redshift), [Azure Synapse](https://superset.apache.org/user-docs/databases/supported/azure-synapse), [Databricks](https://superset.apache.org/user-docs/databases/supported/databricks), [Google BigQuery](https://superset.apache.org/user-docs/databases/supported/google-bigquery), [Snowflake](https://superset.apache.org/user-docs/databases/supported/snowflake) |
| Query engines and data lake analytics | [Apache Drill](https://superset.apache.org/user-docs/databases/supported/apache-drill), [Apache Druid](https://superset.apache.org/user-docs/databases/supported/apache-druid), [Apache Hive](https://superset.apache.org/user-docs/databases/supported/apache-hive), [Apache Impala](https://superset.apache.org/user-docs/databases/supported/apache-impala), [Apache Kylin](https://superset.apache.org/user-docs/databases/supported/apache-kylin), [Apache Pinot](https://superset.apache.org/user-docs/databases/supported/apache-pinot), [Apache Spark SQL](https://superset.apache.org/user-docs/databases/supported/apache-spark-sql), [Dremio](https://superset.apache.org/user-docs/databases/supported/dremio), [Presto](https://superset.apache.org/user-docs/databases/supported/presto), [Trino](https://superset.apache.org/user-docs/databases/supported/trino) |
| PostgreSQL-compatible and analytical SQL | [CockroachDB](https://superset.apache.org/user-docs/databases/supported/cockroachdb), [CrateDB](https://superset.apache.org/user-docs/databases/supported/cratedb), [Greenplum](https://superset.apache.org/user-docs/databases/supported/greenplum), [Hologres](https://superset.apache.org/user-docs/databases/supported/hologres), [OceanBase](https://superset.apache.org/user-docs/databases/supported/oceanbase), [PostgreSQL / Aurora PostgreSQL Data API](https://superset.apache.org/user-docs/databases/supported/aurora-postgresql-data-api), [RisingWave](https://superset.apache.org/user-docs/databases/supported/risingwave), [TimescaleDB](https://superset.apache.org/user-docs/databases/supported/timescaledb), [YDB](https://superset.apache.org/user-docs/databases/supported/ydb), [YugabyteDB](https://superset.apache.org/user-docs/databases/supported/yugabytedb) |
| MySQL-compatible and operational SQL | [Aurora MySQL Data API](https://superset.apache.org/user-docs/databases/supported/aurora-mysql-data-api), [MariaDB](https://superset.apache.org/user-docs/databases/supported/mariadb), [MySQL](https://superset.apache.org/user-docs/databases/supported/mysql), [SingleStore](https://superset.apache.org/user-docs/databases/supported/singlestore), [StarRocks](https://superset.apache.org/user-docs/databases/supported/starrocks), [TDengine](https://superset.apache.org/user-docs/databases/supported/tdengine) |
| Enterprise databases | [Denodo](https://superset.apache.org/user-docs/databases/supported/denodo), [Exasol](https://superset.apache.org/user-docs/databases/supported/exasol), [Firebird](https://superset.apache.org/user-docs/databases/supported/firebird), [IBM Db2](https://superset.apache.org/user-docs/databases/supported/ibm-db2), [IBM Netezza Performance Server](https://superset.apache.org/user-docs/databases/supported/ibm-netezza-performance-server), [Microsoft SQL Server](https://superset.apache.org/user-docs/databases/supported/microsoft-sql-server), [MonetDB](https://superset.apache.org/user-docs/databases/supported/monetdb), [Oracle](https://superset.apache.org/user-docs/databases/supported/oracle), [SAP HANA](https://superset.apache.org/user-docs/databases/supported/sap-hana), [SAP Sybase](https://superset.apache.org/user-docs/databases/supported/sap-sybase), [Teradata](https://superset.apache.org/user-docs/databases/supported/teradata), [Vertica](https://superset.apache.org/user-docs/databases/supported/vertica) |
| Search, NoSQL, and API-backed sources | [Amazon DynamoDB](https://superset.apache.org/user-docs/databases/supported/amazon-dynamodb), [Apache Solr](https://superset.apache.org/user-docs/databases/supported/apache-solr), [Azure Data Explorer](https://superset.apache.org/user-docs/databases/supported/azure-data-explorer), [Cloudflare D1](https://superset.apache.org/user-docs/databases/supported/cloudflare-d1), [Couchbase](https://superset.apache.org/user-docs/databases/supported/couchbase), [Elasticsearch](https://superset.apache.org/user-docs/databases/supported/elasticsearch), [Google Sheets](https://superset.apache.org/user-docs/databases/supported/google-sheets), [MongoDB](https://superset.apache.org/user-docs/databases/supported/mongodb), [Shillelagh](https://superset.apache.org/user-docs/databases/supported/shillelagh) |
| Embedded and local analytics | [DuckDB](https://superset.apache.org/user-docs/databases/supported/duckdb), [MotherDuck](https://superset.apache.org/user-docs/databases/supported/motherduck), [SQLite](https://superset.apache.org/user-docs/databases/supported/sqlite), [Superset meta database](https://superset.apache.org/user-docs/databases/supported/superset-meta-database) |
| Additional engines | [Apache Doris](https://superset.apache.org/user-docs/databases/supported/apache-doris), [Ascend](https://superset.apache.org/user-docs/databases/supported/ascend), [ClickHouse](https://superset.apache.org/user-docs/databases/supported/clickhouse), [Databend](https://superset.apache.org/user-docs/databases/supported/databend), [Firebolt](https://superset.apache.org/user-docs/databases/supported/firebolt) |
<!-- SUPPORTED_DATABASES_END -->

**A more comprehensive list of supported databases** along with configuration instructions can be found in the [Apache Superset database docs](https://superset.apache.org/user-docs/databases), which apply to the AX-BI data layer.

Want to add support for your datastore or data engine? Read about the [technical requirements](https://superset.apache.org/user-docs/faq#does-superset-work-with-insert-database-engine-here).

## Installation and Configuration

AX-BI runs anywhere the underlying Superset platform runs.

- **Docker deployment** — the recommended path for local AX-BI trials:
  ```bash
  cp docker/.env-axbi.example docker/.env-axbi
  # Fill SUPERSET_SECRET_KEY, DATABASE_PASSWORD, and ADMIN_PASSWORD.
  # Generate secrets with: openssl rand -base64 42
  docker compose --env-file docker/.env-axbi -f docker-compose-axbi.yml up -d
  ```
  To build images from this checkout instead of pulling published images, add
  `-f docker-compose-axbi-build.yml --build`.
- **Production deployments** — use managed Postgres/Redis, pinned image tags,
  JWT-backed MCP authentication, and only the externally exposed services your
  deployment needs. For Kubernetes, use the [AX-BI Helm chart](https://github.com/defai-digital/ax-bi/tree/main/helm/superset) with `helm/superset/values-axbi.yaml` and replace all placeholder secrets.
- **MCP service in production** — see [`superset/mcp_service/PRODUCTION.md`](https://github.com/defai-digital/ax-bi/blob/main/superset/mcp_service/PRODUCTION.md).

## Development

AX-BI has a Flask/Python backend and a React/TypeScript frontend.

```bash
# Backend (Flask dev server)
make flask-app

# Frontend dev server (port 9000)
cd ax-bi-frontend && npm run dev-server

# Run the MCP service
ax-bi mcp run            # requires: pip install fastmcp

# Tests
pytest                                 # backend
cd ax-bi-frontend && npm run test   # frontend

# Always run before pushing
pre-commit run --all-files
```

See [`GENAI_BI_ROADMAP.md`](https://github.com/defai-digital/ax-bi/blob/main/GENAI_BI_ROADMAP.md) for product direction, [`SECURITY.md`](https://github.com/defai-digital/ax-bi/blob/main/SECURITY.md) for the security and threat model, and the developer docs for engineering guidance.

AX-BI tracks Apache Superset through a controlled upstream sync process: security
fixes and critical bug fixes are prioritized, stable release branches are
reviewed in dedicated sync branches, and AX-BI-specific MCP/GenAI/governance
behavior must be regression-tested before merge. See the
[`Upstream Sync Policy`](https://github.com/defai-digital/ax-bi/blob/main/docs/developer_docs/upstream-sync-policy.md).

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

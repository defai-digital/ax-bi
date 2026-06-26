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

[**Why AX-BI?**](#why-ax-bi) |
[**MCP-Native GenAI BI**](#mcp-native-genai-bi) |
[**Supported Databases**](#supported-databases) |
[**Installation**](#installation-and-configuration) |
[**Development**](#development) |
[**Built on Apache Superset**](#built-on-apache-superset) |
[**About DEFAI**](#about-defai)

## Why AX-BI?

AX-BI is a modern data exploration, visualization, and AI-analytics platform. It can replace or augment proprietary business intelligence tools while keeping you in control of your data, models, and deployment boundaries — fully self-hosted and extensible.

AX-BI provides:

- A **no-code interface** for building charts quickly
- A powerful, web-based **SQL Editor** for advanced querying
- A **lightweight semantic layer** for quickly defining custom dimensions and metrics
- Out-of-the-box support for **nearly any SQL** database or data engine
- A wide array of **beautiful visualizations**, from simple bar charts to geospatial maps
- A lightweight, configurable **caching layer** to ease database load
- Highly extensible **security roles and authentication** options
- An **MCP service and REST API** for programmatic and AI-agent access
- A **cloud-native architecture** designed from the ground up for scale

## MCP-Native GenAI BI

What sets AX-BI apart from a traditional BI stack is that it is **agent-ready by design**. The built-in MCP service exposes Superset's core resources — datasets, charts, dashboards, queries, and the semantic layer — as governed tools that any MCP-compatible AI agent can call.

- **Prompt-to-dashboard** — turn natural-language questions into validated charts and composed dashboards, grounded in governed semantics rather than raw text-to-SQL.
- **Governed by default** — agent tool visibility and every generated query respect your existing RBAC and row-level security. Agents cannot see or do more than the user they act for.
- **Verifiable artifacts** — generated charts and dashboards are real, inspectable Superset objects, not opaque answers.
- **Auditable** — agent actions flow through the same command, DAO, and event-logging layers as the rest of the platform.

The MCP service lives in [`superset/mcp_service/`](superset/mcp_service/) and ships with its own architecture, security, and production guides. See the [GenAI BI Roadmap](GENAI_BI_ROADMAP.md) for the product direction.

## Screenshots & Gifs

<!-- TODO: replace the images below with AX-BI-branded captures. The current
     images are representative of the underlying Superset UI that AX-BI extends. -->

**Large Gallery of Visualizations**

<kbd><img title="Gallery" src="https://superset.apache.org/img/screenshots/gallery.jpg"/></kbd><br/>

**Craft Beautiful, Dynamic Dashboards**

<kbd><img title="View Dashboards" src="https://superset.apache.org/img/screenshots/dashboard.jpg"/></kbd><br/>

**No-Code Chart Builder**

<kbd><img title="Slice & dice your data" src="https://superset.apache.org/img/screenshots/explore.jpg"/></kbd><br/>

**Powerful SQL Editor**

<kbd><img title="SQL Lab" src="https://superset.apache.org/img/screenshots/sql_lab.jpg"/></kbd><br/>

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

- **Quick local trial** — use the bundled Docker Compose stack:
  ```bash
  docker compose -f docker-compose-non-dev.yml up
  ```
- **Production deployments** — see the [Helm chart](helm/superset/) and the architecture guidance in the [Superset admin docs](https://superset.apache.org/admin-docs/installation/architecture), which apply to AX-BI.
- **MCP service in production** — see [`superset/mcp_service/PRODUCTION.md`](superset/mcp_service/PRODUCTION.md).

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

See [`CLAUDE.md`](CLAUDE.md) for the full engineering guide (commands, architecture, conventions, and the MCP service), [`GENAI_BI_ROADMAP.md`](GENAI_BI_ROADMAP.md) for product direction, and [`SECURITY.md`](SECURITY.md) for the security and threat model.

## Built on Apache Superset

AX-BI is a derivative work of [Apache Superset](https://superset.apache.org), a project of the Apache Software Foundation, used under the [Apache License 2.0](LICENSE). DEFAI Private Limited is grateful to the Apache Superset community for the foundation this product is built on.

*Apache Superset, Apache, and the Apache feather logo are trademarks of the Apache Software Foundation. DEFAI Private Limited and AX-BI are not affiliated with or endorsed by the Apache Software Foundation.* Upstream attribution and license terms are retained in the [`NOTICE`](NOTICE) and [`LICENSE`](LICENSE) files; the documentation links above point to the upstream Apache Superset docs, which apply to the corresponding AX-BI functionality.

## License

AX-BI is distributed under the [Apache License 2.0](LICENSE). See [`LICENSE`](LICENSE) and [`NOTICE`](NOTICE) for details.

## About DEFAI

**AX-BI** is developed and maintained by **DEFAI Private Limited**.

<!-- TODO: add DEFAI website, contact email, and support channel once finalized. -->
- Website: _coming soon_
- Support: _coming soon_

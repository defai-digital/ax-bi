---
title: AX-BI Rename Policy
sidebar_position: 4
---

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

# AX-BI Rename Policy

AX-BI follows an external rename strategy. Public commands, user-facing
documentation, local development paths, and AX-BI-owned entry points use the
AX-BI name. Core Superset Python modules, package namespaces, extension
contracts, migrations, and upstream compatibility surfaces keep their Superset
names unless there is a dedicated migration plan.

This keeps the product experience branded as AX-BI while preserving upstream
syncability, import compatibility, extension compatibility, and migration
history.

## Renamed Surfaces

Use AX-BI names for surfaces that users, operators, and developers invoke
directly:

| Surface | AX-BI name |
| --- | --- |
| Main CLI command | `ax-bi` |
| MCP wrapper command | `ax-bi-mcp` |
| Frontend workspace directory | `ax-bi-frontend/` |
| Route prefix | `/ax-bi` |
| Docker image | `ghcr.io/defai-digital/ax-bi` |
| AX-BI repository links | `https://github.com/defai-digital/ax-bi` |
| Local development docs | `cd ax-bi-frontend`, `ax-bi run`, `ax-bi mcp run` |
| App name (UI title, logo alt) | `AX-BI` |
| User-Agent header | `AX-BI` |

Legacy `/superset/*` routes redirect to `/ax-bi/*` for compatibility with
upstream Superset route history.

The CLI command is `ax-bi`.

New public documentation should not introduce `superset run`,
`superset mcp run`, `superset db`, `superset load-examples`,
`superset-frontend`, or `superset-mcp`.

## Kept Superset Names

Keep the following Superset names unless the work is explicitly scoped as a
full compatibility migration:

| Surface | Reason to keep |
| --- | --- |
| `superset/` Python package | Thousands of imports, Flask config paths, migrations, plugins, and upstream patches depend on it. |
| `superset_config.py`, `SUPERSET_CONFIG`, `SUPERSET_HOME`, `SUPERSET_ENV` | Established deployment contract for operators and Docker/Kubernetes configs. |
| `superset-core/` and `superset_core.*` | Shared extension/core package compatibility. |
| `superset-extensions-cli/` and `superset-extensions` | Extension ecosystem compatibility. |
| `superset-websocket/`, `superset-desktop/`, `superset-embedded-sdk/` | Sub-project compatibility. |
| `@superset-ui/*` and `@apache-superset/core` | Existing chart plugin and extension dependency contracts. |
| `apache_superset` / `apache-superset-*` package metadata | Python packaging and upgrade compatibility. |
| `helm/superset` and chart internals | Helm chart compatibility with upstream values and deployment conventions. |
| Permission resource `'Superset'` | RBAC compatibility; used in `findPermission` calls across frontend. |
| `/api/v1/*` REST API paths | API contract stability for clients and integrations. |
| Alembic migration files | Database migration history integrity. |

## When a Full Rename Is Justified

Do not rename internal Superset namespaces opportunistically. A full rename
requires a separate migration plan covering at least:

- Import aliases and deprecation windows.
- Database migration history and Alembic references.
- Flask config, environment variables, and operator documentation.
- Frontend package names, extension peer dependencies, and Module Federation
  runtime globals.
- Docker, Helm, CI, release artifacts, and published package names.
- Upstream sync strategy and conflict handling.
- Compatibility tests for existing dashboards, embedded deployments,
  extensions, and operator configs.

Until that plan exists, treat remaining `superset*` directories as deliberate
compatibility surfaces, not unfinished rename work.

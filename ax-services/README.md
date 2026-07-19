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

# AX Services

`ax-services` is the TypeScript sidecar foundation for AX BI runtime
modernization. It is intentionally small: health checks, readiness checks,
configuration, logging, and Superset connectivity.

## Commands

```bash
npm install
npm run type
npm test
npm run contracts:write
npm run build
npm run dev-server
```

## Configuration

Environment variables:

| Variable                          | Default                              | Purpose                                                                                       |
| --------------------------------- | ------------------------------------ | --------------------------------------------------------------------------------------------- |
| `AX_SERVICES_HOST`                | `127.0.0.1`                          | Host for the service listener.                                                                |
| `AX_SERVICES_PORT`                | `31424`                              | Port for the service listener.                                                                |
| `AX_SERVICES_INTERNAL_TOKEN`      | unset                                | Inbound bearer token. Required for non-loopback listeners; `/health` remains unauthenticated. |
| `AXBI_BASE_URL`                   | `http://127.0.0.1:31423`             | AX BI base URL used by readiness checks and internal clients.                                 |
| `AXBI_HEALTH_PATH`                | `/health`                            | AX BI health path.                                                                            |
| `AXBI_METADATA_PATH`              | `/api/v1/dashboard/_info`            | Safe AX BI REST metadata endpoint used by the sidecar metadata probe.                         |
| `AXBI_PERMISSION_PATH`            | `/api/v1/security/permissions/check` | AX BI permission delegation path for data-bearing workflows.                                  |
| `AXBI_ANNOTATION_LAYER_LIST_PATH` | `/api/v1/annotation_layer/`          | AX BI annotation layer list endpoint.                                                         |
| `AXBI_CHART_LIST_PATH`            | `/api/v1/chart/`                     | AX BI chart list endpoint.                                                                    |
| `AXBI_DASHBOARD_LIST_PATH`        | `/api/v1/dashboard/`                 | AX BI dashboard list endpoint.                                                                |
| `AXBI_DATABASE_LIST_PATH`         | `/api/v1/database/`                  | AX BI database list endpoint.                                                                 |
| `AXBI_DATASET_LIST_PATH`          | `/api/v1/dataset/`                   | AX BI dataset list endpoint.                                                                  |
| `AXBI_QUERY_LIST_PATH`            | `/api/v1/query/`                     | AX BI query list endpoint.                                                                    |
| `AXBI_REPORT_LIST_PATH`           | `/api/v1/report/`                    | AX BI report list endpoint.                                                                   |
| `AXBI_ROLE_LIST_PATH`             | `/api/v1/role/`                      | AX BI role list endpoint.                                                                     |
| `AXBI_RLS_LIST_PATH`              | `/api/v1/rowlevelsecurity/`          | AX BI row-level security list endpoint.                                                       |
| `AXBI_SAVED_QUERY_LIST_PATH`      | `/api/v1/saved_query/`               | AX BI saved query list endpoint.                                                              |
| `AXBI_TAG_LIST_PATH`              | `/api/v1/tag/`                       | AX BI tag list endpoint.                                                                      |
| `AXBI_TASK_LIST_PATH`             | `/api/v1/task/`                      | AX BI task list endpoint.                                                                     |
| `AXBI_TIMEOUT_MS`                 | `2000`                               | AX BI connectivity timeout in milliseconds.                                                   |
| `AXBI_INTERNAL_TOKEN`             | unset                                | Optional bearer token for calls from the sidecar to AX BI.                                    |
| `AX_SERVICES_LOG_LEVEL`           | `info`                               | Structured log level.                                                                         |

## Runtime Contract

The service exposes versioned runtime responses with
`contractVersion: "runtime.v1"`.

Current endpoints:

- `GET /health`
- `GET /metadata`
- `GET /ready`
- `GET /metrics`
- `POST /mcp/assets/search`
- `POST /mcp/annotations/list`
- `POST /mcp/annotation-layers/list`
- `POST /mcp/permissions/check`
- `POST /mcp/charts/list`
- `POST /mcp/dashboards/list`
- `POST /mcp/databases/list`
- `POST /mcp/datasets/list`
- `POST /mcp/queries/list`
- `POST /mcp/reports/list`
- `POST /mcp/roles/list`
- `POST /mcp/rls-filters/list`
- `POST /mcp/saved-queries/list`
- `POST /mcp/tags/list`
- `POST /mcp/tasks/list`

Generated JSON schema artifacts live in `contracts/`.

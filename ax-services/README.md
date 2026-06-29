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

`ax-services` is the TypeScript sidecar foundation for AX-BI runtime
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

| Variable | Default | Purpose |
| --- | --- | --- |
| `AX_SERVICES_HOST` | `127.0.0.1` | Host for the service listener. |
| `AX_SERVICES_PORT` | `5010` | Port for the service listener. |
| `AX_SUPERSET_BASE_URL` | `http://127.0.0.1:8088` | Superset base URL used by readiness checks and future internal clients. |
| `AX_SUPERSET_HEALTH_PATH` | `/health` | Superset health path. |
| `AX_SUPERSET_METADATA_PATH` | `/api/v1/dashboard/_info` | Safe Superset REST metadata endpoint used by the sidecar metadata probe. |
| `AX_SUPERSET_PERMISSION_PATH` | `/api/v1/security/permissions/check` | Superset permission delegation path for future data-bearing workflows. |
| `AX_SUPERSET_CHART_LIST_PATH` | `/api/v1/chart/` | Superset chart list endpoint for TypeScript asset search and chart listing. |
| `AX_SUPERSET_DASHBOARD_LIST_PATH` | `/api/v1/dashboard/` | Superset dashboard list endpoint for TypeScript asset search and dashboard listing. |
| `AX_SUPERSET_DATABASE_LIST_PATH` | `/api/v1/database/` | Superset database list endpoint for TypeScript database listing. |
| `AX_SUPERSET_DATASET_LIST_PATH` | `/api/v1/dataset/` | Superset dataset list endpoint for TypeScript asset search and dataset listing. |
| `AX_SUPERSET_TIMEOUT_MS` | `2000` | Superset connectivity timeout in milliseconds. |
| `AX_SUPERSET_INTERNAL_TOKEN` | unset | Optional bearer token for internal Superset calls. |
| `AX_SERVICES_LOG_LEVEL` | `info` | Structured log level. |

## Runtime Contract

The service exposes versioned runtime responses with
`contractVersion: "runtime.v1"`.

Current endpoints:

- `GET /health`
- `GET /metadata`
- `GET /ready`
- `GET /metrics`
- `POST /mcp/assets/search`
- `POST /mcp/charts/list`
- `POST /mcp/dashboards/list`
- `POST /mcp/databases/list`
- `POST /mcp/datasets/list`

Generated JSON schema artifacts live in `contracts/`.

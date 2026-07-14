<!--
Licensed to the Apache Software Foundation (ASF) under one or more
contributor license agreements.  See the NOTICE file distributed with
this work for additional information regarding copyright ownership.
The ASF licenses this file to You under the Apache License, Version 2.0
(the "License"); you may not use this file except in compliance with
the License.  You may obtain a copy of the License at

  http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
-->

# @defai/ax-sdk

TypeScript SDK for integrating with the AX BI analytics platform. Provides typed access to AX BI via REST API and AI tools via MCP (Model Context Protocol).

## Installation

```bash
# From within the monorepo
cd packages/ax-sdk
npm install
npm run build
```

Then reference it from your project:

```json
{
  "dependencies": {
    "@defai/ax-sdk": "file:../../packages/ax-sdk"
  }
}
```

## Quick Start

```typescript
import { AxBI } from '@defai/ax-sdk';

const axbi = new AxBI({
  baseUrl: 'https://bi.example.com',
  auth: { type: 'token', accessToken: 'my-jwt-token' },
});

// REST: List dashboards
const { results } = await axbi.dashboards.list({ pageSize: 10 });

// AI: Plan a dashboard from a natural language prompt
const plan = await axbi.ai.planDashboard({
  prompt: 'Sales overview for Q4',
});
```

## Authentication

Four strategies are supported:

```typescript
// Username/password (auto-login on first request)
new AxBI({
  baseUrl,
  auth: { type: 'credentials', username: 'admin', password: 'admin' },
});

// Pre-existing JWT / access token
new AxBI({ baseUrl, auth: { type: 'token', accessToken: 'eyJ...' } });

// Static API key
new AxBI({ baseUrl, auth: { type: 'apiKey', apiKey: 'sk-...' } });

// Guest token (for embedded dashboards)
new AxBI({ baseUrl, auth: { type: 'guestToken', guestToken: '...' } });
```

## REST API

Five resource modules provide full CRUD access:

| Module     | Access            | Example                                                                                   |
| ---------- | ----------------- | ----------------------------------------------------------------------------------------- |
| Dashboards | `axbi.dashboards` | `list()`, `getById()`, `create()`, `update()`, `delete()`                                 |
| Charts     | `axbi.charts`     | `list()`, `getById()`, `create()`, `update()`, `delete()`                                 |
| Datasets   | `axbi.datasets`   | `list()`, `getById()`, `create()`, `update()`, `delete()`, `getColumns()`, `getMetrics()` |
| Databases  | `axbi.databases`  | `list()`, `getById()`, `getSchemas()`, `getTables()`                                      |
| Queries    | `axbi.queries`    | `list()`, `getById()`, `create()`                                                         |

### Pagination

All `list()` methods support page-based pagination:

```typescript
const page = await axbi.charts.list({ page: 0, pageSize: 25 });
// { results: ChartItem[], count: 25, totalCount: 142 }
```

For iterating over all results, use `listAll()` with async iteration:

```typescript
for await (const batch of axbi.dashboards.listAll({ pageSize: 100 })) {
  console.log(`Got ${batch.length} dashboards`);
}
```

### Filtering

```typescript
const { results } = await axbi.dashboards.list({
  filters: [{ col: 'dashboard_title', operator: 'ct', value: 'Sales' }],
  orderBy: 'changed_on_delta_humanized',
  orderDesc: true,
});
```

## AI / MCP Tools

The `axbi.ai` namespace exposes typed wrappers for GenAI tools served by the AX BI MCP service (port 5008):

| Method                          | Description                                                               |
| ------------------------------- | ------------------------------------------------------------------------- |
| `getAuthoringCapabilities()`    | Discover authorized authoring operations, limits, formats, and LLM status |
| `uploadAndPlan(params)`         | Upload CSV/TSV/Excel/Parquet data and return a governed plan              |
| `promptToDashboard(params)`     | **Preferred** — one call from prompt to draft dashboard                   |
| `searchAssets(params)`          | Semantic search across charts, dashboards, datasets                       |
| `describeDataset(params)`       | Get schema, metrics, and sample values for a dataset                      |
| `planDashboard(params)`         | Generate a dashboard plan from a natural language prompt                  |
| `createChartFromIntent(params)` | Create a chart from business intent (or structured plan fields)           |
| `composeDashboard(params)`      | Compose a full dashboard from a plan                                      |
| `explainDashboard(params)`      | Analyze and explain an existing dashboard                                 |
| `executeSql(params)`            | Execute SQL via SQL Lab                                                   |
| `validateChart(params)`         | Validate a chart configuration                                            |

```typescript
// Preferred: single-call prompt-to-dashboard (agents / Codex / Claude Code)
const result = await axbi.ai.promptToDashboard({
  prompt: 'Create an executive sales dashboard with revenue trends',
  draft: true,
});
console.log(result.dashboard_url);

// Discover availability before offering deterministic authoring actions
const capabilities = await axbi.ai.getAuthoringCapabilities();

// Search across all assets
const results = await axbi.ai.searchAssets({
  query: 'monthly revenue',
  assetTypes: ['chart', 'dashboard'],
});

// Multi-step: plan, create charts with structured intents, then compose
const { plan } = await axbi.ai.planDashboard({
  prompt: 'Revenue by region with YoY comparison',
});
// Pass metrics/dimensions/chart_type from plan.chart_intents into createChartFromIntent
await axbi.ai.composeDashboard({ plan, chart_ids: [101, 102] });
```

Requires Superset feature flags: `GENAI_BI`, `GENAI_BI_MCP_TOOLS`, and
`GENAI_PROMPT_TO_DASHBOARD` (enabled by default in the AX Docker AI profile).

The MCP URL is auto-derived from `baseUrl` by replacing the port with `5008`.
`mcpUrl` accepts either a service base URL or a full endpoint ending in `/mcp`.
Use `mcpHeaders` for deployment-specific headers in addition to the selected
authentication strategy.

## Error Handling

All SDK errors extend `AxBIError`:

```typescript
import {
  AxBIAuthError,
  AxBINotFoundError,
  AxBIValidationError,
} from '@defai/ax-sdk';

try {
  await axbi.dashboards.getById(999);
} catch (err) {
  if (err instanceof AxBINotFoundError) {
    console.log('Dashboard not found');
  } else if (err instanceof AxBIAuthError) {
    console.log('Authentication failed');
  }
}
```

| Error Class           | HTTP Status |
| --------------------- | ----------- |
| `AxBIAuthError`       | 401         |
| `AxBIForbiddenError`  | 403         |
| `AxBINotFoundError`   | 404         |
| `AxBIConflictError`   | 409         |
| `AxBIValidationError` | 422         |
| `AxBIRateLimitError`  | 429         |

## Configuration

```typescript
new AxBI({
  baseUrl: 'https://bi.example.com',  // Required
  auth: { ... },                       // Required
  mcpUrl: 'https://mcp.example.com',  // Optional, defaults to baseUrl:5008
  timeout: 30000,                      // Optional, request timeout in ms
  retries: 3,                          // Optional, max retries for transient failures
});
```

The HTTP transport automatically retries on 408, 429, 500, 502, 503, 504 with exponential backoff. For credentials-based auth, it auto-re-authenticates on 401.

## Development

```bash
cd packages/ax-sdk

npm run build       # Build ESM + CJS + type declarations
npm run test        # Run 32 unit tests
npm run type        # TypeScript type check only
npm run clean       # Remove dist/
```

### Project Structure

```
packages/ax-sdk/
├── src/
│   ├── auth/          # Auth strategies (credentials, token, apiKey, guestToken)
│   ├── transport/     # HTTP client with retry and error mapping
│   ├── resources/     # REST resource modules (dashboards, charts, datasets, etc.)
│   ├── mcp/           # MCP JSON-RPC client and AI tool wrappers
│   ├── shared/        # Error hierarchy, pagination utilities
│   ├── client.ts      # Main AxBI entry point
│   └── index.ts       # Public barrel exports
├── package.json
├── tsconfig.json
├── tsconfig.esm.json
├── tsconfig.cjs.json
└── tsconfig.types.json
```

## Requirements

- Node.js >= 24
- Zero runtime dependencies (uses native `fetch`)

## License

Apache-2.0

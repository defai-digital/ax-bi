/**
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */

// ---- Main client ----
export { AxBI, type AxBIConfig, type HealthStatus } from './client.js';

// ---- Auth types ----
export type {
  AuthConfig,
  CredentialsAuth,
  TokenAuth,
  ApiKeyAuth,
  GuestTokenAuth,
} from './auth/types.js';

// ---- Error hierarchy ----
export {
  AxBIError,
  AxBIAuthError,
  AxBIForbiddenError,
  AxBINotFoundError,
  AxBIValidationError,
  AxBIConflictError,
  AxBIRateLimitError,
} from './shared/errors.js';

// ---- Pagination ----
export {
  paginate,
  type PaginatedResponse,
  type ListParams,
  type ListFilter,
} from './shared/pagination.js';

// ---- Resource types ----
export type {
  DashboardItem,
  ChartItem,
  DatasetItem,
  DatabaseItem,
  QueryItem,
  CreateDashboardInput,
  UpdateDashboardInput,
  CreateChartInput,
  UpdateChartInput,
  CreateDatasetInput,
  UpdateDatasetInput,
} from './resources/types.js';

// ---- Resource classes (for advanced usage) ----
export { DashboardsResource } from './resources/dashboards.js';
export { ChartsResource } from './resources/charts.js';
export { DatasetsResource } from './resources/datasets.js';
export { DatabasesResource } from './resources/databases.js';
export { QueriesResource } from './resources/queries.js';

// ---- MCP / AI types ----
export { MCPClient, type MCPToolDefinition, type MCPToolResult } from './mcp/mcpClient.js';
export {
  AIResource,
  type AssetSearchParams,
  type AssetSearchResult,
  type DescribeDatasetParams,
  type DatasetDescription,
  type PlanDashboardParams,
  type DashboardPlan,
  type ChartIntentParams,
  type ChartPreview,
  type PromptToDashboardParams,
  type PromptToDashboardResult,
  type PromptToDashboardChartSummary,
  type WorkflowStepStatus,
  type ComposeDashboardParams,
  type ComposeResult,
  type ExplainDashboardParams,
  type DashboardExplanation,
  type ExecuteSqlParams,
  type SqlResult,
  type ValidateChartParams,
  type ChartValidation,
} from './mcp/ai.js';

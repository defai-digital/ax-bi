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

import { MCPClient, type MCPToolResult } from './mcpClient.js';

// ---- AI tool parameter types ----

export interface AssetSearchParams {
  query: string;
  assetTypes?: Array<'chart' | 'dashboard' | 'dataset' | 'metric'>;
  includeCertifiedOnly?: boolean;
  limit?: number;
}

export interface DescribeDatasetParams {
  dataset_id: number;
  include_sample_values?: boolean;
  include_usage_stats?: boolean;
}

export interface PlanDashboardParams {
  prompt: string;
  dataset_candidates?: number[];
  constraints?: Record<string, unknown>;
}

export interface ChartIntentParams {
  chart_intent: {
    metric: string;
    dimension?: string;
    chart_type?: string;
    filters?: Array<{ column: string; operator: string; value: unknown }>;
    time_range?: string;
  };
  dataset_id: number;
  save_chart?: boolean;
}

export interface ComposeDashboardParams {
  dashboard_plan: {
    title: string;
    description?: string;
    sections?: Array<{
      title: string;
      chart_ids: number[];
    }>;
    global_filters?: Record<string, unknown>;
  };
  chart_ids: number[];
  draft?: boolean;
}

export interface ExplainDashboardParams {
  dashboard_id: number;
  question?: string;
  scope?: 'full' | 'summary' | 'charts';
}

export interface ExecuteSqlParams {
  database_id: number;
  sql: string;
  schema?: string;
  limit?: number;
}

export interface ValidateChartParams {
  chart_id: number;
}

export interface SearchAssetsParams {
  query: string;
  asset_types?: string[];
  limit?: number;
}

// ---- AI tool response types ----

export interface AssetSearchResult {
  assets: Array<{
    assetType: string;
    id: number;
    uuid: string;
    name: string;
    description?: string;
    certified: boolean;
    relevanceScore: number;
    relevanceReason?: string;
    owners: string[];
    tags: string[];
  }>;
  warnings: string[];
}

export interface DatasetDescription {
  dataset_id: number;
  name: string;
  description?: string;
  columns: Array<{
    name: string;
    type: string;
    is_dttm: boolean;
    description?: string;
    sample_values?: unknown[];
  }>;
  metrics: Array<{
    name: string;
    expression: string;
    description?: string;
  }>;
  time_columns?: string[];
  synonyms?: string[];
}

export interface DashboardPlan {
  title: string;
  description?: string;
  sections: Array<{
    title: string;
    chart_intents: Array<{
      metric: string;
      dimension?: string;
      chart_type: string;
    }>;
  }>;
  global_filters?: Record<string, unknown>;
  clarifying_questions?: string[];
  assumptions?: string[];
  confidence_score?: number;
}

export interface ChartPreview {
  chart_id?: number;
  preview_url?: string;
  form_data: Record<string, unknown>;
  validation_result: {
    is_valid: boolean;
    errors?: string[];
    warnings?: string[];
  };
  explanation?: string;
}

export interface ComposeResult {
  dashboard_id: number;
  dashboard_url: string;
  layout_summary?: string;
  warnings?: string[];
  draft: boolean;
}

export interface DashboardExplanation {
  summary: string;
  charts: Array<{
    chart_id: number;
    title: string;
    description: string;
  }>;
  caveats?: string[];
  follow_up_suggestions?: string[];
}

export interface SqlResult {
  columns: Array<{ name: string; type: string }>;
  data: Array<Record<string, unknown>>;
  row_count: number;
  query_id?: string;
}

export interface ChartValidation {
  is_valid: boolean;
  errors: string[];
  warnings: string[];
  suggestions?: string[];
}

/**
 * High-level typed wrappers for AX-BI AI/GenAI MCP tools.
 *
 * These tools run on the MCP service (typically port 5008) and provide
 * semantic search, prompt-to-dashboard, chart generation, and SQL execution.
 */
export class AIResource {
  private readonly mcp: MCPClient;

  constructor(mcp: MCPClient) {
    this.mcp = mcp;
  }

  /** Search across BI assets (dashboards, charts, datasets, metrics). */
  async searchAssets(params: AssetSearchParams): Promise<AssetSearchResult> {
    return this.callMcpTool<AssetSearchResult>('search_business_assets', {
      query: params.query,
      asset_types: params.assetTypes ?? ['dashboard', 'chart', 'dataset'],
      include_certified_only: params.includeCertifiedOnly ?? false,
      limit: params.limit ?? 20,
    });
  }

  /** Get AI-ready dataset metadata (columns, metrics, sample values). */
  async describeDataset(params: DescribeDatasetParams): Promise<DatasetDescription> {
    return this.callMcpTool<DatasetDescription>('describe_dataset_for_ai', {
      dataset_id: params.dataset_id,
      include_sample_values: params.include_sample_values ?? false,
      include_usage_stats: params.include_usage_stats ?? false,
    });
  }

  /** Create a dashboard plan without creating artifacts. */
  async planDashboard(params: PlanDashboardParams): Promise<DashboardPlan> {
    return this.callMcpTool<DashboardPlan>('plan_dashboard', {
      prompt: params.prompt,
      dataset_candidates: params.dataset_candidates ?? [],
      constraints: params.constraints ?? {},
    });
  }

  /** Generate a chart from business intent. Returns preview + validation. */
  async createChartFromIntent(params: ChartIntentParams): Promise<ChartPreview> {
    return this.callMcpTool<ChartPreview>('create_chart_from_intent', {
      chart_intent: params.chart_intent,
      dataset_id: params.dataset_id,
      save_chart: params.save_chart ?? false,
    });
  }

  /** Compose a dashboard from a plan and chart IDs. */
  async composeDashboard(params: ComposeDashboardParams): Promise<ComposeResult> {
    return this.callMcpTool<ComposeResult>('compose_dashboard', {
      dashboard_plan: params.dashboard_plan,
      chart_ids: params.chart_ids,
      draft: params.draft ?? true,
    });
  }

  /** Explain or critique an existing dashboard. */
  async explainDashboard(params: ExplainDashboardParams): Promise<DashboardExplanation> {
    return this.callMcpTool<DashboardExplanation>('explain_dashboard', {
      dashboard_id: params.dashboard_id,
      question: params.question,
      scope: params.scope ?? 'full',
    });
  }

  /** Execute a SQL query against a database. */
  async executeSql(params: ExecuteSqlParams): Promise<SqlResult> {
    return this.callMcpTool<SqlResult>('execute_sql', {
      database_id: params.database_id,
      sql: params.sql,
      schema: params.schema,
      limit: params.limit ?? 1000,
    });
  }

  /** Validate a chart's configuration without rendering. */
  async validateChart(params: ValidateChartParams): Promise<ChartValidation> {
    return this.callMcpTool<ChartValidation>('validate_chart', {
      chart_id: params.chart_id,
    });
  }

  /**
   * Invoke a raw MCP tool by name. Useful for calling tools not
   * covered by the typed wrappers.
   */
  async callTool<T = MCPToolResult>(
    name: string,
    args?: Record<string, unknown>,
  ): Promise<T> {
    return this.mcp.callTool<T>(name, args);
  }

  /** List all available MCP tools. */
  async listTools() {
    return this.mcp.listTools();
  }

  /**
   * Helper: call an MCP tool and extract structuredContent from the result.
   * Falls back to parsing the first text content block if structuredContent is absent.
   */
  private async callMcpTool<T>(
    name: string,
    args: Record<string, unknown>,
  ): Promise<T> {
    const result = await this.mcp.callTool<MCPToolResult>(name, args);

    // Prefer structuredContent if available
    if (result.structuredContent) {
      return result.structuredContent as T;
    }

    // Fall back to parsing the first text content block
    const textBlock = result.content?.find((c) => c.type === 'text');
    if (textBlock?.text) {
      try {
        return JSON.parse(textBlock.text) as T;
      } catch {
        return textBlock.text as unknown as T;
      }
    }

    throw new Error(`MCP tool "${name}" returned no content`);
  }
}

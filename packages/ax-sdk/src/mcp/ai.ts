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
import { AxBIError } from '../shared/errors.js';

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
  prompt: string;
  dataset_id?: number | string;
  save_chart?: boolean;
  max_preview_rows?: number;
  /** Structured fields from plan_dashboard chart_intents (preferred). */
  chart_type?: string;
  metrics?: string[];
  dimensions?: string[];
  filters?: Array<Record<string, unknown>>;
  time_range?: string;
  kind?: 'line' | 'bar' | 'area' | 'scatter';
}

export interface PromptToDashboardParams {
  prompt: string;
  dataset_ids?: number[];
  max_charts?: number;
  draft?: boolean;
  save_charts?: boolean;
  /** Plan/preview only — do not create charts or a dashboard. */
  dry_run?: boolean;
  /** Minimum plan confidence required before mutations (default 0.25). */
  min_confidence?: number;
  /** Bypass the low-confidence gate and create artifacts anyway. */
  force?: boolean;
}

export interface ComposeDashboardParams {
  plan: Record<string, unknown>;
  chart_ids: number[];
  draft?: boolean;
  narrative_blocks?: Array<{ content: string; position?: string }>;
}

export interface ExplainDashboardParams {
  dashboard_id: number | string;
  question?: string;
  scope?: 'overview' | 'chart' | 'data';
}

export interface ExecuteSqlParams {
  database_id: number;
  sql: string;
  schema?: string;
  limit?: number;
}

export interface ValidateChartParams {
  dataset_id: number;
  config: Record<string, unknown>;
}

export interface SearchAssetsParams {
  query: string;
  asset_types?: string[];
  limit?: number;
}

// ---- AI tool response types ----

export interface AssetSearchResult {
  assets: Array<{
    asset_type: string;
    id: number;
    uuid: string;
    name: string;
    description?: string;
    certified: boolean;
    relevance_score?: number;
    relevance_reason?: string;
    owners: string[];
    tags: string[];
  }>;
  warnings: string[];
}

export interface DatasetDescription {
  id: number;
  name: string;
  description?: string;
  certified: boolean;
  main_time_column?: string;
  columns: Array<{
    name: string;
    type: string;
    description?: string;
    aliases?: string[];
    is_dimension?: boolean;
  }>;
  metrics: Array<{
    name: string;
    expression: string;
    description?: string;
  }>;
  privacy?: Record<string, unknown>;
}

export interface DatasetDescriptionEnvelope {
  dataset: DatasetDescription;
  warnings: string[];
}

export interface DashboardPlanEnvelope {
  plan: DashboardPlan;
  warnings: string[];
}
export interface DashboardPlan {
  plan_id: string;
  title: string;
  description?: string;
  datasets?: Array<Record<string, unknown>>;
  sections: Array<{
    title: string;
    chart_intents: Array<Record<string, unknown>>;
  }>;
  chart_intents?: Array<Record<string, unknown>>;
  global_filters?: Array<Record<string, unknown>>;
  layout_hints?: Record<string, unknown>;
  assumptions?: string[];
  clarifying_questions?: string[];
  confidence?: number;
}

export interface ChartPreview {
  chart?: Record<string, unknown>;
  chart_name?: string;
  form_data?: Record<string, unknown>;
  success?: boolean;
  dataset_used?: Record<string, unknown>;
  chart_type_selected?: string;
  explanation?: string;
  confidence?: number;
  warnings?: string[];
  preview_url?: string;
  alternatives?: string[];
}

export interface ComposeResult {
  dashboard?: Record<string, unknown>;
  dashboard_url?: string;
  layout_summary?: string;
  lineage?: Record<string, unknown>;
  warnings?: string[];
  error?: string;
}

export interface PromptToDashboardChartSummary {
  chart_id?: number | null;
  chart_name?: string;
  chart_type?: string;
  purpose?: string;
  confidence?: number;
  preview_url?: string | null;
  warnings?: string[];
}

export interface WorkflowStepStatus {
  name: string;
  status: 'pending' | 'running' | 'succeeded' | 'failed' | 'skipped';
  detail?: string;
  duration_ms?: number;
}

export interface PromptToDashboardResult {
  dashboard?: Record<string, unknown> | null;
  dashboard_url?: string | null;
  plan?: DashboardPlan | null;
  charts?: PromptToDashboardChartSummary[];
  layout_summary?: string;
  lineage?: Record<string, unknown> | null;
  warnings?: string[];
  error?: string | null;
  total_duration_ms?: number;
  status?: 'completed' | 'partial' | 'blocked' | 'failed' | 'dry_run';
  steps?: WorkflowStepStatus[];
  charts_succeeded?: number;
  charts_failed?: number;
}

export interface DashboardExplanation {
  summary: string;
  source_charts: Array<Record<string, unknown>>;
  key_metrics?: Array<Record<string, unknown>>;
  caveats?: string[];
  follow_up_suggestions?: string[];
  warnings?: string[];
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
 * High-level typed wrappers for AX BI AI/GenAI MCP tools.
 *
 * These tools run on the MCP service (typically port 31421) and provide
 * semantic search, prompt-to-dashboard, chart generation, and SQL execution.
 */
export class AIResource {
  private readonly mcp: MCPClient;
  private readonly ensureInitialized: () => Promise<void>;

  constructor(mcp: MCPClient, ensureInitialized?: () => Promise<void>) {
    this.mcp = mcp;
    this.ensureInitialized = ensureInitialized ?? (async () => {});
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
  async describeDataset(params: DescribeDatasetParams): Promise<DatasetDescriptionEnvelope> {
    return this.callMcpTool<DatasetDescriptionEnvelope>('describe_dataset_for_ai', {
      dataset_id: params.dataset_id,
      include_sample_values: params.include_sample_values ?? false,
      include_usage_stats: params.include_usage_stats ?? true,
    });
  }

  /** Create a dashboard plan without creating artifacts. */
  async planDashboard(params: PlanDashboardParams): Promise<DashboardPlanEnvelope> {
    return this.callMcpTool<DashboardPlanEnvelope>('plan_dashboard', {
      prompt: params.prompt,
      dataset_candidates: params.dataset_candidates ?? [],
      constraints: params.constraints ?? {},
    });
  }

  /** Generate a chart from business intent. Returns preview + validation. */
  async createChartFromIntent(params: ChartIntentParams): Promise<ChartPreview> {
    return this.callMcpTool<ChartPreview>('create_chart_from_intent', {
      prompt: params.prompt,
      dataset_id: params.dataset_id,
      save_chart: params.save_chart ?? true,
      max_preview_rows: params.max_preview_rows ?? 100,
      chart_type: params.chart_type,
      metrics: params.metrics ?? [],
      dimensions: params.dimensions ?? [],
      filters: params.filters ?? [],
      time_range: params.time_range,
      kind: params.kind,
    });
  }

  /**
   * Create a complete dashboard from a natural language prompt in one call.
   *
   * This is the preferred entry point for agent clients (Codex, Claude Code).
   * Chains plan → create charts → compose dashboard on the server.
   */
  async promptToDashboard(
    params: PromptToDashboardParams,
  ): Promise<PromptToDashboardResult> {
    return this.callMcpTool<PromptToDashboardResult>('prompt_to_dashboard', {
      prompt: params.prompt,
      dataset_ids: params.dataset_ids ?? [],
      max_charts: params.max_charts ?? 6,
      draft: params.draft ?? true,
      save_charts: params.save_charts ?? true,
      dry_run: params.dry_run ?? false,
      min_confidence: params.min_confidence ?? 0.25,
      force: params.force ?? false,
    });
  }

  /** Compose a dashboard from a plan and chart IDs. */
  async composeDashboard(params: ComposeDashboardParams): Promise<ComposeResult> {
    return this.callMcpTool<ComposeResult>('compose_dashboard', {
      plan: params.plan,
      chart_ids: params.chart_ids,
      draft: params.draft ?? true,
      narrative_blocks: params.narrative_blocks,
    });
  }

  /** Explain or critique an existing dashboard. */
  async explainDashboard(params: ExplainDashboardParams): Promise<DashboardExplanation> {
    return this.callMcpTool<DashboardExplanation>('explain_dashboard', {
      dashboard_id: params.dashboard_id,
      question: params.question,
      scope: params.scope ?? 'overview',
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

  /** Validate a chart configuration against a dataset. */
  async validateChart(params: ValidateChartParams): Promise<ChartValidation> {
    return this.callMcpTool<ChartValidation>('validate_chart', {
      dataset_id: params.dataset_id,
      config: params.config,
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
    await this.ensureInitialized();
    return this.mcp.callTool<T>(name, args);
  }

  /** List all available MCP tools. */
  async listTools() {
    await this.ensureInitialized();
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
    await this.ensureInitialized();
    // AX BI MCP tools expose a single Pydantic ``request`` parameter. Keep
    // the envelope here so every typed wrapper follows the live FastMCP schema
    // while raw ``callTool`` remains available for non-standard tools.
    const result = await this.mcp.callTool<unknown>(name, { request: args });

    if (!isRecord(result)) {
      throw new AxBIError(`MCP tool "${name}" returned malformed result`, {
        responseBody: result,
      });
    }

    if (
      Object.prototype.hasOwnProperty.call(result, 'isError') &&
      typeof result['isError'] !== 'boolean'
    ) {
      throw new AxBIError(`MCP tool "${name}" returned malformed result`, {
        responseBody: result,
      });
    }

    const toolResult = result as Partial<MCPToolResult>;

    if (toolResult.isError) {
      throw new AxBIError(`MCP tool "${name}" returned an error`, {
        responseBody: toolResult,
      });
    }

    // Prefer structuredContent if available
    if (Object.prototype.hasOwnProperty.call(toolResult, 'structuredContent')) {
      if (!isRecord(toolResult.structuredContent)) {
        throw new AxBIError(
          `MCP tool "${name}" returned malformed structured content`,
          {
            responseBody: toolResult,
          },
        );
      }
      return toolResult.structuredContent as T;
    }

    if (
      toolResult.content !== undefined &&
      !Array.isArray(toolResult.content)
    ) {
      throw new AxBIError(`MCP tool "${name}" returned malformed content`, {
        responseBody: toolResult,
      });
    }

    // Fall back to parsing the first text content block
    const textBlock = toolResult.content?.find((c) => c.type === 'text');
    if (textBlock?.text) {
      try {
        return JSON.parse(textBlock.text) as T;
      } catch (error) {
        throw new AxBIError(`MCP tool "${name}" returned malformed JSON`, {
          cause: error instanceof Error ? error : new Error(String(error)),
          responseBody: textBlock.text,
        });
      }
    }

    throw new AxBIError(`MCP tool "${name}" returned no content`);
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

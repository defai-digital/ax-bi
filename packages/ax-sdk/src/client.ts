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

import type { AuthConfig } from './auth/types.js';
import { AuthProvider } from './auth/authProvider.js';
import { HttpClient } from './transport/httpClient.js';
import { DashboardsResource } from './resources/dashboards.js';
import { ChartsResource } from './resources/charts.js';
import { DatasetsResource } from './resources/datasets.js';
import { DatabasesResource } from './resources/databases.js';
import { QueriesResource } from './resources/queries.js';
import { ApiKeysResource } from './resources/apiKeys.js';
import { MCPClient } from './mcp/mcpClient.js';
import { AIResource } from './mcp/ai.js';
import { normalizeHttpBaseUrl } from './shared/url.js';

/** Configuration for the AxBI client. */
export interface AxBIConfig {
  /** Base URL of the AX BI web server (e.g., 'https://bi.example.com'). */
  baseUrl: string;
  /**
   * URL of the MCP service. Defaults to `${baseUrl}` with port 31421.
   * Only needed if MCP AI tools are used.
   */
  mcpUrl?: string;
  /** Authentication strategy. */
  auth: AuthConfig;
  /** Default request timeout in milliseconds. Defaults to 30000. */
  timeout?: number;
  /** Max number of retries for transient failures. Defaults to 3. */
  retries?: number;
}

/** Health status of the AX BI server. */
export interface HealthStatus {
  status: 'ok' | 'error';
  message?: string;
}

/**
 * Main entry point for the AX BI SDK.
 *
 * Provides access to:
 * - REST operations for dashboards, charts, datasets, databases, queries,
 *   and user-bound API keys
 * - AI/GenAI tools via MCP (prompt-to-dashboard, semantic search, SQL execution)
 *
 * @example
 * ```typescript
 * import { AxBI } from '@defai/ax-sdk';
 *
 * const axbi = new AxBI({
 *   baseUrl: 'https://bi.example.com',
 *   auth: { type: 'token', accessToken: 'my-jwt-token' },
 * });
 *
 * // REST: List dashboards
 * const { results } = await axbi.dashboards.list({ pageSize: 10 });
 *
 * // AI: Plan a dashboard from a prompt
 * const plan = await axbi.ai.planDashboard({
 *   prompt: 'Sales overview for Q4',
 * });
 * ```
 */
export class AxBI {
  /** Dashboard CRUD operations. */
  readonly dashboards: DashboardsResource;
  /** Chart CRUD operations. */
  readonly charts: ChartsResource;
  /** Dataset CRUD operations. */
  readonly datasets: DatasetsResource;
  /** Database connection operations. */
  readonly databases: DatabasesResource;
  /** Saved query operations. */
  readonly queries: QueriesResource;
  /** Current-user API-key management operations. */
  readonly apiKeys: ApiKeysResource;
  /** AI/GenAI tools (MCP). */
  readonly ai: AIResource;

  private readonly auth: AuthProvider;
  private readonly http: HttpClient;
  private readonly mcp: MCPClient;
  private mcpInitialized = false;
  private mcpInitialization: Promise<void> | null = null;

  constructor(config: AxBIConfig) {
    const baseUrl = normalizeHttpBaseUrl(config.baseUrl, 'baseUrl');
    this.auth = new AuthProvider(config.auth, baseUrl, config.timeout);
    this.http = new HttpClient({
      baseUrl,
      auth: this.auth,
      timeout: config.timeout,
      retries: config.retries,
    });

    // Derive MCP URL from baseUrl if not provided
    const mcpUrl = config.mcpUrl ?? this.deriveMcpUrl(baseUrl);
    this.mcp = new MCPClient({
      mcpUrl,
      auth: this.auth,
      timeout: config.timeout,
    });

    // Initialize resource modules
    this.dashboards = new DashboardsResource(this.http);
    this.charts = new ChartsResource(this.http);
    this.datasets = new DatasetsResource(this.http);
    this.databases = new DatabasesResource(this.http);
    this.queries = new QueriesResource(this.http);
    this.apiKeys = new ApiKeysResource(this.http);
    this.ai = new AIResource(this.mcp, () => this.ensureMcpInitialized());
  }

  /**
   * Authenticate with the server.
   * Required for credentials-based auth before making any API calls.
   * For token/apiKey auth, this is a no-op but initializes the MCP session.
   */
  async login(): Promise<void> {
    await this.auth.login();
    await this.ensureMcpInitialized({ allowFailure: true });
  }

  /** Check server health. */
  async health(): Promise<HealthStatus> {
    try {
      const response = await this.http.get<unknown>('/health');
      return {
        status: isHealthyResponse(response) ? 'ok' : 'error',
      };
    } catch (error) {
      return {
        status: 'error',
        message: error instanceof Error ? error.message : String(error),
      };
    }
  }

  /**
   * Ensure the MCP session is initialized.
   * Called in tolerant mode by login and strictly on first AI tool usage.
   */
  private async ensureMcpInitialized(
    options: { allowFailure?: boolean } = {},
  ): Promise<void> {
    if (this.mcpInitialized) {
      return;
    }
    if (this.mcpInitialization === null) {
      this.mcpInitialization = this.mcp
        .initialize()
        .then(() => {
          this.mcpInitialized = true;
        })
        .finally(() => {
          this.mcpInitialization = null;
        });
    }
    try {
      await this.mcpInitialization;
    } catch (error) {
      if (options.allowFailure) {
        return;
      }
      throw error;
    }
  }

  /**
   * Derive MCP URL from the base URL by replacing the port with 31421
   * or appending :31421 if no port is specified.
   */
  private deriveMcpUrl(baseUrl: string): string {
    try {
      const url = new URL(baseUrl);
      url.port = '31421';
      return url.toString();
    } catch {
      return `${baseUrl}:31421`;
    }
  }
}

function isHealthyResponse(response: unknown): boolean {
  if (typeof response === 'string') {
    return response.trim().toLowerCase() === 'ok';
  }
  if (response && typeof response === 'object') {
    const status = (response as Record<string, unknown>)['status'];
    return typeof status === 'string' && status.trim().toLowerCase() === 'ok';
  }
  return false;
}

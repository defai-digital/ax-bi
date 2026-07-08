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

import { AuthProvider } from '../auth/authProvider.js';
import { AxBIError } from '../shared/errors.js';
import { stripTrailingSlashes } from '../shared/url.js';

/** JSON-RPC 2.0 request envelope. */
interface JsonRpcRequest {
  jsonrpc: '2.0';
  id: string;
  method: string;
  params?: Record<string, unknown>;
}

/** JSON-RPC 2.0 success response. */
interface JsonRpcSuccessResponse {
  jsonrpc: '2.0';
  id: string;
  result: unknown;
}

/** JSON-RPC 2.0 error response. */
interface JsonRpcErrorResponse {
  jsonrpc: '2.0';
  id: string;
  error: {
    code: number;
    message: string;
    data?: unknown;
  };
}

type JsonRpcResponse = JsonRpcSuccessResponse | JsonRpcErrorResponse;

/** MCP tool metadata returned by tools/list. */
export interface MCPToolDefinition {
  name: string;
  description?: string;
  inputSchema?: Record<string, unknown>;
}

/** Result of a tools/call invocation. */
export interface MCPToolResult {
  content: Array<{ type: string; text?: string; data?: unknown }>;
  isError?: boolean;
  structuredContent?: Record<string, unknown>;
}

/**
 * Low-level MCP client that communicates with the AX-BI MCP service
 * using JSON-RPC 2.0 over HTTP with streamable transport.
 *
 * The MCP service typically runs on port 5008.
 */
export class MCPClient {
  private readonly mcpUrl: string;
  private readonly auth: AuthProvider;
  private readonly timeout: number;
  private requestId = 0;
  /** MCP session ID returned by the server on initialization. */
  private sessionId: string | null = null;

  constructor(options: {
    mcpUrl: string;
    auth: AuthProvider;
    timeout?: number;
  }) {
    this.mcpUrl = stripTrailingSlashes(options.mcpUrl);
    this.auth = options.auth;
    this.timeout = options.timeout ?? 60_000;
  }

  /** Initialize the MCP session. Must be called before tool invocations. */
  async initialize(): Promise<void> {
    const response = await this.sendRequest<unknown>({
      method: 'initialize',
      params: {
        protocolVersion: '2025-03-26',
        capabilities: {},
        clientInfo: {
          name: '@defai/ax-sdk',
          version: '0.1.0',
        },
      },
    });

    // Extract session ID from response if available
    if (response && typeof response === 'object') {
      const resp = response as Record<string, unknown>;
      if (typeof resp['sessionId'] === 'string') {
        this.sessionId = resp['sessionId'];
      }
    }

    // Send initialized notification (no response expected)
    await this.sendNotification('notifications/initialized');
  }

  /** List all available MCP tools. */
  async listTools(): Promise<MCPToolDefinition[]> {
    const response = await this.sendRequest<unknown>({
      method: 'tools/list',
    });
    if (!isRecord(response)) {
      throw new AxBIError('MCP tools/list result must be a JSON object', {
        responseBody: response,
      });
    }
    const tools = response['tools'];
    if (tools === undefined) {
      return [];
    }
    if (!Array.isArray(tools)) {
      throw new AxBIError('MCP tools/list result tools field must be an array', {
        responseBody: response,
      });
    }
    return tools as MCPToolDefinition[];
  }

  /** Invoke an MCP tool by name with typed arguments. */
  async callTool<T = MCPToolResult>(
    name: string,
    args?: Record<string, unknown>,
  ): Promise<T> {
    const response = await this.sendRequest<T>({
      method: 'tools/call',
      params: { name, arguments: args ?? {} },
    });
    return response;
  }

  /** Send a JSON-RPC request and return the result. */
  private async sendRequest<T>(
    request: Omit<JsonRpcRequest, 'jsonrpc' | 'id'>,
  ): Promise<T> {
    const id = String(++this.requestId);
    const body: JsonRpcRequest = {
      jsonrpc: '2.0',
      id,
      ...request,
    };

    const headers = this.buildHeaders('application/json, text/event-stream');

    let response: Response;
    try {
      response = await fetch(`${this.mcpUrl}/mcp`, {
        method: 'POST',
        headers,
        body: JSON.stringify(body),
        signal: AbortSignal.timeout(this.timeout),
      });
    } catch (error) {
      const cause = normalizeError(error);
      throw new AxBIError(`MCP request failed: ${cause.message}`, { cause });
    }

    if (!response.ok) {
      const text = await response.text().catch(() => null);
      throw new AxBIError(`MCP request failed (${response.status})`, {
        statusCode: response.status,
        responseBody: text,
      });
    }

    // Capture session ID from response header
    const newSessionId = response.headers.get('mcp-session-id');
    if (newSessionId) {
      this.sessionId = newSessionId;
    }

    const contentType = response.headers.get('content-type') ?? '';

    // Handle SSE stream response
    if (contentType.includes('text/event-stream')) {
      return this.parseSseResponse<T>(response, id);
    }

    // Handle direct JSON response
    const json = await this.parseJsonResponse(response);
    return this.extractResult<T>(json, id);
  }

  /** Send a notification (no response expected). */
  private async sendNotification(method: string): Promise<void> {
    const headers = this.buildHeaders();

    await fetch(`${this.mcpUrl}/mcp`, {
      method: 'POST',
      headers,
      body: JSON.stringify({
        jsonrpc: '2.0',
        method,
      }),
      signal: AbortSignal.timeout(5000),
    }).catch(() => {
      // Notifications are fire-and-forget; swallow errors.
    });
  }

  private buildHeaders(accept?: string): Record<string, string> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...this.auth.getAuthHeaders(),
    };

    if (accept !== undefined) {
      headers['Accept'] = accept;
    }

    if (this.sessionId) {
      headers['Mcp-Session-Id'] = this.sessionId;
    }

    return headers;
  }

  /**
   * Parse an SSE stream and return the final JSON-RPC result.
   * SSE events contain `data:` lines with JSON-RPC messages.
   */
  private async parseSseResponse<T>(
    response: Response,
    expectedId: string,
  ): Promise<T> {
    let text: string;
    try {
      text = await response.text();
    } catch (error) {
      throw new AxBIError('MCP SSE response could not be read', {
        cause: normalizeError(error),
      });
    }
    const events = text.split(/\r?\n\r?\n/);

    // Walk backwards to find the last JSON-RPC response with our ID
    for (let i = events.length - 1; i >= 0; i--) {
      const dataLines = events[i]!
        .split(/\r?\n/)
        .map(line => line.trim())
        .filter(line => line.startsWith('data:'))
        .map(line => line.slice(5).replace(/^ /, ''));
      const jsonStr = dataLines.join('\n').trim();
      if (!jsonStr) {
        continue;
      }
      let parsed: unknown;
      try {
        parsed = JSON.parse(jsonStr) as unknown;
      } catch {
        // Skip non-JSON events
        continue;
      }
      if (isRecord(parsed) && parsed['id'] === expectedId) {
        return this.extractResult<T>(parsed, expectedId);
      }
    }

    throw new AxBIError('No valid JSON-RPC response found in SSE stream');
  }

  private async parseJsonResponse(response: Response): Promise<unknown> {
    try {
      return await response.json();
    } catch (error) {
      throw new AxBIError('MCP response was not valid JSON', {
        cause: normalizeError(error),
      });
    }
  }

  private extractResult<T>(response: unknown, expectedId: string): T {
    const parsed = this.parseJsonRpcResponse(response, expectedId);

    if ('error' in parsed) {
      throw new AxBIError(parsed.error.message, {
        responseBody: parsed.error.data,
      });
    }

    return parsed.result as T;
  }

  private parseJsonRpcResponse(
    response: unknown,
    expectedId: string,
  ): JsonRpcResponse {
    if (!isRecord(response)) {
      throw new AxBIError('MCP response must be a JSON-RPC object', {
        responseBody: response,
      });
    }
    if (response['jsonrpc'] !== '2.0') {
      throw new AxBIError('MCP response has an invalid JSON-RPC version', {
        responseBody: response,
      });
    }
    if (response['id'] !== expectedId) {
      throw new AxBIError(
        `Unexpected JSON-RPC response ID: ${String(response['id'])} (expected ${expectedId})`,
        { responseBody: response },
      );
    }

    if ('error' in response) {
      const error = response['error'];
      if (
        !isRecord(error) ||
        typeof error['code'] !== 'number' ||
        typeof error['message'] !== 'string'
      ) {
        throw new AxBIError('MCP JSON-RPC error response is malformed', {
          responseBody: response,
        });
      }
      return {
        jsonrpc: '2.0',
        id: expectedId,
        error: {
          code: error['code'],
          message: error['message'],
          data: error['data'],
        },
      };
    }

    if (!Object.prototype.hasOwnProperty.call(response, 'result')) {
      throw new AxBIError('MCP JSON-RPC response missing result', {
        responseBody: response,
      });
    }

    return {
      jsonrpc: '2.0',
      id: expectedId,
      result: response['result'],
    };
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function normalizeError(error: unknown): Error {
  return error instanceof Error ? error : new Error(String(error));
}

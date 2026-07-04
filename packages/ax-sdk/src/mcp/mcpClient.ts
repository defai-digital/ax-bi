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

  constructor(options: { mcpUrl: string; auth: AuthProvider; timeout?: number }) {
    this.mcpUrl = options.mcpUrl.replace(/\/+$/, '');
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

    // Send initialized notification (no response expected)
    await this.sendNotification('notifications/initialized');

    // Extract session ID from response if available
    if (response && typeof response === 'object') {
      const resp = response as Record<string, unknown>;
      if (typeof resp['sessionId'] === 'string') {
        this.sessionId = resp['sessionId'];
      }
    }
  }

  /** List all available MCP tools. */
  async listTools(): Promise<MCPToolDefinition[]> {
    const response = await this.sendRequest<{ tools: MCPToolDefinition[] }>({
      method: 'tools/list',
    });
    return response.tools ?? [];
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
  private async sendRequest<T>(request: Omit<JsonRpcRequest, 'jsonrpc' | 'id'>): Promise<T> {
    const id = String(++this.requestId);
    const body: JsonRpcRequest = {
      jsonrpc: '2.0',
      id,
      ...request,
    };

    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      Accept: 'application/json, text/event-stream',
      ...this.auth.getAuthHeaders(),
    };

    if (this.sessionId) {
      headers['Mcp-Session-Id'] = this.sessionId;
    }

    const response = await fetch(`${this.mcpUrl}/mcp`, {
      method: 'POST',
      headers,
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(this.timeout),
    });

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
    const json = (await response.json()) as JsonRpcResponse;
    return this.extractResult<T>(json, id);
  }

  /** Send a notification (no response expected). */
  private async sendNotification(method: string): Promise<void> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...this.auth.getAuthHeaders(),
    };
    if (this.sessionId) {
      headers['Mcp-Session-Id'] = this.sessionId;
    }

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

  /**
   * Parse an SSE stream and return the final JSON-RPC result.
   * SSE events contain `data:` lines with JSON-RPC messages.
   */
  private async parseSseResponse<T>(response: Response, expectedId: string): Promise<T> {
    const text = await response.text();
    const lines = text.split('\n');

    // Walk backwards to find the last JSON-RPC response with our ID
    for (let i = lines.length - 1; i >= 0; i--) {
      const line = lines[i]!.trim();
      if (line.startsWith('data:')) {
        const jsonStr = line.slice(5).trim();
        if (!jsonStr) continue;
        try {
          const parsed = JSON.parse(jsonStr) as JsonRpcResponse;
          if ('id' in parsed && parsed.id === expectedId) {
            return this.extractResult<T>(parsed, expectedId);
          }
        } catch {
          // Skip non-JSON lines
        }
      }
    }

    throw new AxBIError('No valid JSON-RPC response found in SSE stream');
  }

  private extractResult<T>(response: JsonRpcResponse, expectedId: string): T {
    if ('error' in response) {
      throw new AxBIError(response.error.message, {
        responseBody: response.error.data,
      });
    }
    if (response.id !== expectedId) {
      throw new AxBIError(`Unexpected JSON-RPC response ID: ${response.id} (expected ${expectedId})`);
    }
    return response.result as T;
  }
}

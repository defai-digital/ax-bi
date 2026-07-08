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

import { jest } from '@jest/globals';

import { AxBI } from './client.js';
import { AxBIError } from './shared/errors.js';

const mockFetch = jest.fn<typeof fetch>();
global.fetch = mockFetch;

function jsonRpcResponse(id: string, result: unknown): Response {
  return new Response(
    JSON.stringify({
      jsonrpc: '2.0',
      id,
      result,
    }),
    {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    },
  );
}

function jsonResponse(body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
  });
}

function textResponse(body: string): Response {
  return new Response(body, {
    status: 200,
    headers: { 'Content-Type': 'text/plain' },
  });
}

describe('AxBI', () => {
  beforeEach(() => {
    jest.restoreAllMocks();
    mockFetch.mockReset();
  });

  test('initializes MCP lazily before the first AI tool call', async () => {
    const client = new AxBI({
      baseUrl: 'http://localhost:8088',
      mcpUrl: 'http://localhost:5008',
      auth: { type: 'token', accessToken: 'test-token' },
    });
    mockFetch
      .mockResolvedValueOnce(jsonRpcResponse('1', {}))
      .mockResolvedValueOnce(new Response(null, { status: 202 }))
      .mockResolvedValueOnce(jsonRpcResponse('2', { content: [] }));

    await client.ai.callTool('health_check');

    expect(mockFetch).toHaveBeenCalledTimes(3);
    const initializeBody = JSON.parse(
      String((mockFetch.mock.calls[0]![1] as RequestInit).body),
    ) as { method: string };
    const initializedBody = JSON.parse(
      String((mockFetch.mock.calls[1]![1] as RequestInit).body),
    ) as { method: string };
    const toolCallBody = JSON.parse(
      String((mockFetch.mock.calls[2]![1] as RequestInit).body),
    ) as { method: string; params: { name: string } };

    expect(initializeBody.method).toBe('initialize');
    expect(initializedBody.method).toBe('notifications/initialized');
    expect(toolCallBody.method).toBe('tools/call');
    expect(toolCallBody.params.name).toBe('health_check');
  });

  test('passes configured timeout to credentials auth login', async () => {
    const timeoutSpy = jest.spyOn(AbortSignal, 'timeout');
    const client = new AxBI({
      baseUrl: 'http://localhost:8088',
      mcpUrl: 'http://localhost:5008',
      timeout: 2345,
      auth: { type: 'credentials', username: 'admin', password: 'admin' },
    });
    mockFetch
      .mockResolvedValueOnce(jsonResponse({ access_token: 'access-jwt' }))
      .mockResolvedValueOnce(jsonResponse({ result: 'csrf-token' }))
      .mockResolvedValueOnce(jsonRpcResponse('1', {}))
      .mockResolvedValueOnce(new Response(null, { status: 202 }));

    await client.login();

    expect(timeoutSpy).toHaveBeenNthCalledWith(1, 2345);
    expect(timeoutSpy).toHaveBeenNthCalledWith(2, 2345);
    expect(timeoutSpy).toHaveBeenNthCalledWith(3, 2345);
    expect(timeoutSpy).toHaveBeenNthCalledWith(4, 5000);
  });

  test('login tolerates unavailable MCP initialization', async () => {
    const client = new AxBI({
      baseUrl: 'http://localhost:8088',
      mcpUrl: 'http://localhost:5008',
      auth: { type: 'token', accessToken: 'test-token' },
    });
    mockFetch.mockRejectedValue(new Error('mcp unavailable'));

    await expect(client.login()).resolves.toBeUndefined();
    expect(mockFetch).toHaveBeenCalledTimes(1);
  });

  test('AI calls fail when MCP initialization fails', async () => {
    const client = new AxBI({
      baseUrl: 'http://localhost:8088',
      mcpUrl: 'http://localhost:5008',
      auth: { type: 'token', accessToken: 'test-token' },
    });
    mockFetch.mockRejectedValue(new Error('mcp unavailable'));

    await expect(client.ai.callTool('health_check')).rejects.toThrow(
      AxBIError,
    );
    expect(mockFetch).toHaveBeenCalledTimes(1);
  });

  test('treats plain text OK health responses as healthy', async () => {
    const client = new AxBI({
      baseUrl: 'http://localhost:8088',
      mcpUrl: 'http://localhost:5008',
      auth: { type: 'token', accessToken: 'test-token' },
      retries: 0,
    });
    mockFetch.mockResolvedValue(textResponse('OK'));

    await expect(client.health()).resolves.toEqual({ status: 'ok' });

    const [url, init] = mockFetch.mock.calls[0]!;
    expect(url).toBe('http://localhost:8088/health');
    expect((init as RequestInit).method).toBe('GET');
  });

  test('treats JSON OK health responses as healthy', async () => {
    const client = new AxBI({
      baseUrl: 'http://localhost:8088',
      mcpUrl: 'http://localhost:5008',
      auth: { type: 'token', accessToken: 'test-token' },
      retries: 0,
    });
    mockFetch.mockResolvedValue(jsonResponse({ status: 'ok' }));

    await expect(client.health()).resolves.toEqual({ status: 'ok' });
  });

  test('reports unexpected health response bodies as errors', async () => {
    const client = new AxBI({
      baseUrl: 'http://localhost:8088',
      mcpUrl: 'http://localhost:5008',
      auth: { type: 'token', accessToken: 'test-token' },
      retries: 0,
    });
    mockFetch.mockResolvedValue(textResponse('DOWN'));

    await expect(client.health()).resolves.toEqual({ status: 'error' });
  });
});

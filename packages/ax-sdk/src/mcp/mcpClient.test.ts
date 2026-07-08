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

import { AuthProvider } from '../auth/authProvider.js';
import { AxBIError } from '../shared/errors.js';
import { MCPClient } from './mcpClient.js';

const mockFetch = jest.fn<typeof fetch>();
global.fetch = mockFetch;

function makeClient(): MCPClient {
  const auth = new AuthProvider(
    { type: 'token', accessToken: 'access-jwt' },
    'http://localhost:8088',
  );
  return new MCPClient({
    mcpUrl: 'http://localhost:5008/',
    auth,
    timeout: 1234,
  });
}

function jsonRpcResponse(
  id: string,
  result: unknown,
  headers?: Record<string, string>,
): Response {
  return new Response(
    JSON.stringify({
      jsonrpc: '2.0',
      id,
      result,
    }),
    {
      status: 200,
      headers: { 'Content-Type': 'application/json', ...headers },
    },
  );
}

function sseResponse(data: unknown): Response {
  return new Response(`event: message\ndata: ${JSON.stringify(data)}\n\n`, {
    status: 200,
    headers: { 'Content-Type': 'text/event-stream' },
  });
}

describe('MCPClient', () => {
  beforeEach(() => {
    jest.restoreAllMocks();
    mockFetch.mockReset();
  });

  test('sends JSON-RPC tools/list requests with auth and timeout', async () => {
    const timeoutSpy = jest.spyOn(AbortSignal, 'timeout');
    const client = makeClient();
    mockFetch.mockResolvedValue(
      jsonRpcResponse('1', { tools: [{ name: 'health_check' }] }),
    );

    const tools = await client.listTools();

    expect(tools).toEqual([{ name: 'health_check' }]);
    expect(mockFetch).toHaveBeenCalledTimes(1);
    expect(timeoutSpy).toHaveBeenCalledWith(1234);
    const [url, init] = mockFetch.mock.calls[0]!;
    const headers = (init as RequestInit).headers as Record<string, string>;
    const body = JSON.parse(String((init as RequestInit).body)) as {
      id: string;
      method: string;
    };
    expect(url).toBe('http://localhost:5008/mcp');
    expect((init as RequestInit).method).toBe('POST');
    expect(headers['Authorization']).toBe('Bearer access-jwt');
    expect(headers['Accept']).toBe('application/json, text/event-stream');
    expect(body).toMatchObject({ id: '1', method: 'tools/list' });
  });

  test('sends captured MCP session ID on later requests', async () => {
    const client = makeClient();
    mockFetch
      .mockResolvedValueOnce(
        jsonRpcResponse('1', { tools: [] }, { 'Mcp-Session-Id': 'session-1' }),
      )
      .mockResolvedValueOnce(
        jsonRpcResponse('2', { content: [{ type: 'text', text: 'ok' }] }),
      );

    await client.listTools();
    await client.callTool('health_check');

    const [, init] = mockFetch.mock.calls[1]!;
    const headers = (init as RequestInit).headers as Record<string, string>;
    expect(headers['Mcp-Session-Id']).toBe('session-1');
  });

  test('sends result MCP session ID on initialized notification', async () => {
    const client = makeClient();
    mockFetch
      .mockResolvedValueOnce(
        jsonRpcResponse('1', { sessionId: 'session-from-result' }),
      )
      .mockResolvedValueOnce(new Response(null, { status: 202 }));

    await client.initialize();

    const [, init] = mockFetch.mock.calls[1]!;
    const headers = (init as RequestInit).headers as Record<string, string>;
    expect(headers['Mcp-Session-Id']).toBe('session-from-result');
  });

  test('maps HTTP failures to AxBIError with status and response body', async () => {
    const client = makeClient();
    mockFetch.mockResolvedValue(new Response('unavailable', { status: 503 }));

    try {
      await client.listTools();
      throw new Error('Expected request to fail');
    } catch (error) {
      expect(error).toBeInstanceOf(AxBIError);
      expect(error).toMatchObject({
        statusCode: 503,
        responseBody: 'unavailable',
      });
    }
  });

  test('wraps fetch failures in AxBIError', async () => {
    const client = makeClient();
    mockFetch.mockRejectedValue(new Error('connect failed'));

    await expect(client.listTools()).rejects.toThrow(AxBIError);
  });

  test('wraps invalid JSON responses in AxBIError', async () => {
    const client = makeClient();
    mockFetch.mockResolvedValue(
      new Response('not-json', {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    );

    await expect(client.listTools()).rejects.toThrow(AxBIError);
  });

  test('rejects malformed JSON-RPC responses as AxBIError', async () => {
    const client = makeClient();
    mockFetch.mockResolvedValue(
      new Response(JSON.stringify({ jsonrpc: '2.0', id: '1' }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    );

    await expect(client.listTools()).rejects.toThrow(AxBIError);
  });

  test('rejects invalid tools/list result shape as AxBIError', async () => {
    const client = makeClient();
    mockFetch.mockResolvedValue(jsonRpcResponse('1', null));

    await expect(client.listTools()).rejects.toThrow(AxBIError);
  });

  test('propagates JSON-RPC error responses as AxBIError', async () => {
    const client = makeClient();
    mockFetch.mockResolvedValue(
      new Response(
        JSON.stringify({
          jsonrpc: '2.0',
          id: '1',
          error: { code: -32000, message: 'tool failed', data: { detail: 1 } },
        }),
        {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        },
      ),
    );

    try {
      await client.listTools();
      throw new Error('Expected request to fail');
    } catch (error) {
      expect(error).toBeInstanceOf(AxBIError);
      expect(error).toMatchObject({
        message: 'tool failed',
        responseBody: { detail: 1 },
      });
    }
  });

  test('parses SSE JSON-RPC responses', async () => {
    const client = makeClient();
    mockFetch.mockResolvedValue(
      sseResponse({
        jsonrpc: '2.0',
        id: '1',
        result: { content: [{ type: 'text', text: 'ok' }] },
      }),
    );

    await expect(client.callTool('health_check')).resolves.toEqual({
      content: [{ type: 'text', text: 'ok' }],
    });
  });

  test('parses multi-line SSE JSON-RPC data events', async () => {
    const client = makeClient();
    mockFetch.mockResolvedValue(
      new Response(
        [
          'event: message',
          'data: {"jsonrpc":"2.0",',
          'data: "id":"1",',
          'data: "result":{"content":[{"type":"text","text":"ok"}]}}',
          '',
          '',
        ].join('\n'),
        {
          status: 200,
          headers: { 'Content-Type': 'text/event-stream' },
        },
      ),
    );

    await expect(client.callTool('health_check')).resolves.toEqual({
      content: [{ type: 'text', text: 'ok' }],
    });
  });
});

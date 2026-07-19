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

import { AxBI } from '../client.js';
import { MANAGED_MCP_API_KEY_NAME } from './apiKeys.js';

const mockFetch = jest.fn<typeof fetch>();
global.fetch = mockFetch;

const listedKey = {
  uuid: 'old-key',
  name: MANAGED_MCP_API_KEY_NAME,
  key_prefix: 'M8hayd7iay8hfdsG',
  scopes: null,
  active: true,
  created_on: '2026-07-18T11:00:00Z',
  expires_on: null,
  revoked_on: null,
  last_used_on: null,
};

const createdKey = {
  uuid: 'new-key',
  name: MANAGED_MCP_API_KEY_NAME,
  key: 'sst_M8hayd7-secret-value-iay8hfdsG',
  key_prefix: 'M8hayd7iay8hfdsG',
  scopes: null,
  created_on: '2026-07-18T12:00:00Z',
  expires_on: null,
};

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

function makeClient(): AxBI {
  return new AxBI({
    baseUrl: 'http://localhost:31423',
    mcpUrl: 'http://localhost:31421',
    auth: { type: 'apiKey', apiKey: createdKey.key },
    retries: 0,
  });
}

beforeEach(() => {
  jest.restoreAllMocks();
  mockFetch.mockReset();
});

test('lists only non-secret current-user API key metadata', async () => {
  mockFetch.mockResolvedValue(jsonResponse({ result: [listedKey] }));

  const result = await makeClient().apiKeys.list();

  expect(result).toEqual([listedKey]);
  expect(result[0]).not.toHaveProperty('key');
  const [url, init] = mockFetch.mock.calls[0]!;
  const headers = (init as RequestInit).headers as Record<string, string>;
  expect(url).toBe('http://localhost:31423/api/v1/security/api_keys/');
  expect((init as RequestInit).method).toBe('GET');
  expect(headers['Authorization']).toBe(`Bearer ${createdKey.key}`);
});

test('creates a dedicated MCP key and returns its one-time plaintext', async () => {
  mockFetch.mockResolvedValue(jsonResponse({ result: createdKey }, 201));

  const result = await makeClient().apiKeys.createMcpKey();

  expect(result).toEqual(createdKey);
  const [url, init] = mockFetch.mock.calls[0]!;
  expect(url).toBe('http://localhost:31423/api/v1/security/api_keys/');
  expect((init as RequestInit).method).toBe('POST');
  expect(JSON.parse(String((init as RequestInit).body))).toEqual({
    name: MANAGED_MCP_API_KEY_NAME,
  });
});

test('revokes a current-user key by encoded UUID', async () => {
  mockFetch.mockResolvedValue(jsonResponse({ message: 'API key revoked' }));

  await expect(
    makeClient().apiKeys.revoke('key/with spaces'),
  ).resolves.toBeUndefined();

  const [url, init] = mockFetch.mock.calls[0]!;
  expect(url).toBe(
    'http://localhost:31423/api/v1/security/api_keys/key%2Fwith%20spaces',
  );
  expect((init as RequestInit).method).toBe('DELETE');
});

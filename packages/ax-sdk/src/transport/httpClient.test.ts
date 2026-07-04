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
import { HttpClient } from './httpClient.js';
import { AuthProvider } from '../auth/authProvider.js';
import {
  AxBIError,
  AxBINotFoundError,
  AxBIValidationError,
} from '../shared/errors.js';

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const mockFetch = jest.fn<(...args: any[]) => any>();
global.fetch = mockFetch as typeof fetch;

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

describe('HttpClient', () => {
  let auth: AuthProvider;
  let client: HttpClient;

  beforeEach(() => {
    mockFetch.mockReset();
    auth = new AuthProvider(
      { type: 'token', accessToken: 'test-token' },
      'http://localhost:8088',
    );
    client = new HttpClient({
      baseUrl: 'http://localhost:8088',
      auth,
      retries: 0,
      timeout: 5000,
    });
  });

  test('GET request sends correct URL and auth header', async () => {
    mockFetch.mockResolvedValue(jsonResponse({ result: { id: 1 } }));

    const result = await client.get<{ result: { id: number } }>('/api/v1/dashboard/1');
    expect(result).toEqual({ result: { id: 1 } });

    const [url, init] = mockFetch.mock.calls[0]!;
    expect(url).toBe('http://localhost:8088/api/v1/dashboard/1');
    expect((init as RequestInit).method).toBe('GET');
    expect(((init as RequestInit).headers as Record<string, string>)['Authorization']).toBe(
      'Bearer test-token',
    );
  });

  test('POST request sends JSON body', async () => {
    mockFetch.mockResolvedValue(
      jsonResponse({ id: 1, result: { dashboard_title: 'Test' } }),
    );

    await client.post('/api/v1/dashboard/', { dashboard_title: 'Test' });

    const [, init] = mockFetch.mock.calls[0]!;
    expect((init as RequestInit).method).toBe('POST');
    expect((init as RequestInit).body).toBe(JSON.stringify({ dashboard_title: 'Test' }));
    expect(((init as RequestInit).headers as Record<string, string>)['Content-Type']).toBe(
      'application/json',
    );
  });

  test('throws AxBINotFoundError on 404', async () => {
    mockFetch.mockResolvedValue(jsonResponse({ message: 'Not found' }, 404));

    await expect(client.get('/api/v1/dashboard/999')).rejects.toThrow(AxBINotFoundError);
  });

  test('throws AxBIValidationError on 422', async () => {
    mockFetch.mockResolvedValue(jsonResponse({ message: 'bad input' }, 422));

    await expect(client.post('/api/v1/dashboard/', {})).rejects.toThrow(AxBIValidationError);
  });

  test('throws AxBIError on unhandled status', async () => {
    mockFetch.mockResolvedValue(jsonResponse(null, 418));

    await expect(client.get('/api/v1/dashboard/1')).rejects.toThrow(AxBIError);
  });

  test('query params are appended to URL', async () => {
    mockFetch.mockResolvedValue(jsonResponse({ result: [] }));

    await client.get('/api/v1/dashboard/', { page: 1, page_size: 10 });

    const [url] = mockFetch.mock.calls[0]!;
    const parsed = new URL(url as string);
    expect(parsed.searchParams.get('page')).toBe('1');
    expect(parsed.searchParams.get('page_size')).toBe('10');
  });

  test('retries on 500 when retries > 0', async () => {
    const retryClient = new HttpClient({
      baseUrl: 'http://localhost:8088',
      auth,
      retries: 2,
      timeout: 5000,
    });

    mockFetch
      .mockResolvedValueOnce(jsonResponse({ message: 'error' }, 500))
      .mockResolvedValueOnce(jsonResponse({ result: 'ok' }));

    const result = await retryClient.get<{ result: string }>('/api/v1/health');
    expect(result).toEqual({ result: 'ok' });
    expect(mockFetch).toHaveBeenCalledTimes(2);
  });
});

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
  AxBIRateLimitError,
  AxBIValidationError,
} from '../shared/errors.js';

const mockFetch = jest.fn<typeof fetch>();
global.fetch = mockFetch;

function jsonResponse(
  body: unknown,
  status = 200,
  headers?: Record<string, string>,
): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json', ...headers },
  });
}

describe('HttpClient', () => {
  let auth: AuthProvider;
  let client: HttpClient;

  beforeEach(() => {
    jest.restoreAllMocks();
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

  test('parses JSON responses with case-insensitive content type', async () => {
    mockFetch.mockResolvedValue(
      new Response(JSON.stringify({ result: { id: 1 } }), {
        status: 200,
        headers: { 'Content-Type': 'Application/JSON; Charset=UTF-8' },
      }),
    );

    await expect(client.get('/api/v1/dashboard/1')).resolves.toEqual({
      result: { id: 1 },
    });
  });

  test('retries on 500 when retries > 0', async () => {
    const retryClient = new HttpClient({
      baseUrl: 'http://localhost:8088',
      auth,
      retries: 2,
      timeout: 5000,
    });
    const sleepSpy = jest
      .spyOn(
        retryClient as unknown as { sleep(ms: number): Promise<void> },
        'sleep',
      )
      .mockResolvedValue(undefined);

    mockFetch
      .mockResolvedValueOnce(jsonResponse({ message: 'error' }, 500))
      .mockResolvedValueOnce(jsonResponse({ result: 'ok' }));

    const result = await retryClient.get<{ result: string }>('/api/v1/health');
    expect(result).toEqual({ result: 'ok' });
    expect(mockFetch).toHaveBeenCalledTimes(2);
    expect(sleepSpy).toHaveBeenCalledWith(1000);
  });

  test('creates a fresh timeout signal for each retry attempt', async () => {
    const retryClient = new HttpClient({
      baseUrl: 'http://localhost:8088',
      auth,
      retries: 1,
      timeout: 5000,
    });
    jest
      .spyOn(
        retryClient as unknown as { sleep(ms: number): Promise<void> },
        'sleep',
      )
      .mockResolvedValue(undefined);

    mockFetch
      .mockResolvedValueOnce(jsonResponse({ message: 'error' }, 500))
      .mockResolvedValueOnce(jsonResponse({ result: 'ok' }));

    await retryClient.get('/api/v1/health');

    const firstSignal = (mockFetch.mock.calls[0]![1] as RequestInit).signal;
    const secondSignal = (mockFetch.mock.calls[1]![1] as RequestInit).signal;
    expect(firstSignal).toBeDefined();
    expect(secondSignal).toBeDefined();
    expect(secondSignal).not.toBe(firstSignal);
  });

  test('preserves API key auth headers when retrying after 401', async () => {
    const apiKeyAuth = new AuthProvider(
      {
        type: 'apiKey',
        apiKey: 'key-123',
        headerName: 'X-API-Key',
        headerPrefix: '',
      },
      'http://localhost:8088',
    );
    const retryClient = new HttpClient({
      baseUrl: 'http://localhost:8088',
      auth: apiKeyAuth,
      retries: 1,
      timeout: 5000,
    });

    mockFetch
      .mockResolvedValueOnce(jsonResponse({ message: 'unauthorized' }, 401))
      .mockResolvedValueOnce(jsonResponse({ result: 'ok' }));

    await expect(retryClient.get('/api/v1/dashboard/')).resolves.toEqual({
      result: 'ok',
    });

    const firstHeaders = mockFetch.mock.calls[0]![1]!.headers as Record<
      string,
      string
    >;
    const secondHeaders = mockFetch.mock.calls[1]![1]!.headers as Record<
      string,
      string
    >;
    expect(firstHeaders['X-API-Key']).toBe('key-123');
    expect(secondHeaders['X-API-Key']).toBe('key-123');
    expect(secondHeaders['Authorization']).toBeUndefined();
  });

  test('does not retry POST transient failures by default', async () => {
    const retryClient = new HttpClient({
      baseUrl: 'http://localhost:8088',
      auth,
      retries: 1,
      timeout: 5000,
    });

    mockFetch.mockResolvedValue(jsonResponse({ message: 'error' }, 500));

    await expect(
      retryClient.post('/api/v1/dashboard/', { dashboard_title: 'Test' }),
    ).rejects.toThrow(AxBIError);
    expect(mockFetch).toHaveBeenCalledTimes(1);
  });

  test('allows explicit retry opt-in for POST requests', async () => {
    const retryClient = new HttpClient({
      baseUrl: 'http://localhost:8088',
      auth,
      retries: 1,
      timeout: 5000,
    });
    const sleepSpy = jest
      .spyOn(
        retryClient as unknown as { sleep(ms: number): Promise<void> },
        'sleep',
      )
      .mockResolvedValue(undefined);

    mockFetch
      .mockResolvedValueOnce(jsonResponse({ message: 'error' }, 500))
      .mockResolvedValueOnce(jsonResponse({ result: { id: 1 } }));

    const result = await retryClient.request<{ result: { id: number } }>({
      method: 'POST',
      path: '/api/v1/dashboard/',
      body: { dashboard_title: 'Test' },
      retry: true,
    });

    expect(result).toEqual({ result: { id: 1 } });
    expect(mockFetch).toHaveBeenCalledTimes(2);
    expect(sleepSpy).toHaveBeenCalledWith(1000);
  });

  test('honors Retry-After before retrying', async () => {
    const retryClient = new HttpClient({
      baseUrl: 'http://localhost:8088',
      auth,
      retries: 1,
      timeout: 5000,
    });
    const sleepSpy = jest
      .spyOn(
        retryClient as unknown as { sleep(ms: number): Promise<void> },
        'sleep',
      )
      .mockResolvedValue(undefined);

    mockFetch
      .mockResolvedValueOnce(
        jsonResponse({ message: 'slow down' }, 429, { 'Retry-After': '2' }),
      )
      .mockResolvedValueOnce(jsonResponse({ result: 'ok' }));

    const result = await retryClient.get('/api/v1/dashboard/');

    expect(result).toEqual({ result: 'ok' });
    expect(mockFetch).toHaveBeenCalledTimes(2);
    expect(sleepSpy).toHaveBeenCalledWith(2000);
  });

  test('ignores invalid Retry-After values', async () => {
    const retryClient = new HttpClient({
      baseUrl: 'http://localhost:8088',
      auth,
      retries: 1,
      timeout: 5000,
    });
    const sleepSpy = jest
      .spyOn(
        retryClient as unknown as { sleep(ms: number): Promise<void> },
        'sleep',
      )
      .mockResolvedValue(undefined);

    mockFetch
      .mockResolvedValueOnce(
        jsonResponse({ message: 'slow down' }, 429, {
          'Retry-After': '2.5',
        }),
      )
      .mockResolvedValueOnce(jsonResponse({ result: 'ok' }));

    await retryClient.get('/api/v1/dashboard/');

    expect(mockFetch).toHaveBeenCalledTimes(2);
    expect(sleepSpy).toHaveBeenCalledWith(1000);
  });

  test('exposes Retry-After on final rate limit errors', async () => {
    mockFetch.mockResolvedValue(
      jsonResponse({ message: 'slow down' }, 429, { 'Retry-After': '3' }),
    );

    try {
      await client.get('/api/v1/dashboard/');
      throw new Error('Expected request to fail');
    } catch (error) {
      expect(error).toBeInstanceOf(AxBIRateLimitError);
      expect(error).toMatchObject({ retryAfterMs: 3000 });
    }
  });

  test('parses successful binary responses as blobs', async () => {
    mockFetch.mockResolvedValue(
      new Response('zip-data', {
        status: 200,
        headers: { 'Content-Type': 'application/zip' },
      }),
    );

    const result = await client.request<Blob>({
      method: 'GET',
      path: '/api/v1/dashboard/export/',
      responseType: 'blob',
    });

    expect(result).toBeInstanceOf(Blob);
    await expect(result.text()).resolves.toBe('zip-data');
  });
});

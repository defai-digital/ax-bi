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
import { AxBIError, AxBIAuthError, errorFromStatus } from '../shared/errors.js';
import { stripTrailingSlashes } from '../shared/url.js';
import type { HttpMethod, RequestOptions, ResponseType } from './types.js';

/** Default request timeout in milliseconds. */
const DEFAULT_TIMEOUT_MS = 30_000;

/** Base delay between retries in milliseconds (doubles on each attempt). */
const BASE_RETRY_DELAY_MS = 1_000;

/** HTTP status codes eligible for automatic retry. */
const RETRYABLE_STATUSES = new Set([408, 429, 500, 502, 503, 504]);

/** Methods that can be replayed automatically under HTTP semantics. */
const DEFAULT_RETRYABLE_METHODS = new Set<HttpMethod>(['GET', 'PUT', 'DELETE']);

/** Upper bound for honoring Retry-After headers in the SDK. */
const MAX_RETRY_AFTER_MS = 60_000;

/**
 * Thin fetch wrapper providing:
 * - Auth header injection via AuthProvider
 * - JSON request/response serialization
 * - Method-aware retry with exponential backoff for 429/5xx
 * - Structured error mapping into the AxBIError hierarchy
 * - Per-request timeout support
 */
export class HttpClient {
  private readonly baseUrl: string;
  private readonly auth: AuthProvider;
  private readonly defaultTimeout: number;
  private readonly maxRetries: number;

  constructor(options: {
    baseUrl: string;
    auth: AuthProvider;
    timeout?: number;
    retries?: number;
  }) {
    this.baseUrl = stripTrailingSlashes(options.baseUrl);
    this.auth = options.auth;
    this.defaultTimeout = options.timeout ?? DEFAULT_TIMEOUT_MS;
    this.maxRetries = options.retries ?? 3;
  }

  /**
   * Execute an HTTP request and return the parsed JSON body.
   * Throws an AxBIError subclass on non-2xx responses.
   */
  async request<T = unknown>(options: RequestOptions): Promise<T> {
    const url = this.buildUrl(options.path, options.query);
    const method = options.method ?? 'GET';
    const timeout = options.timeout ?? this.defaultTimeout;
    const retryEnabled =
      options.retry ?? DEFAULT_RETRYABLE_METHODS.has(method);
    let headers = this.buildHeaders(options);

    const requestBody =
      options.body !== undefined ? JSON.stringify(options.body) : undefined;

    let lastError: Error | null = null;

    for (let attempt = 0; attempt <= this.maxRetries; attempt++) {
      try {
        const init: RequestInit = {
          method,
          headers,
          body: requestBody,
          signal: AbortSignal.timeout(timeout),
        };
        const response = await fetch(url, init);
        const body = await this.parseBody(
          response,
          response.ok ? options.responseType : undefined,
        );

        if (response.ok) {
          return body as T;
        }

        const retryAfterMs = this.parseRetryAfterMs(
          response.headers.get('retry-after'),
        );

        // Check for auth failure — attempt one re-login if credentials-based
        if (response.status === 401 && attempt === 0) {
          try {
            await this.auth.login();
            headers = this.buildHeaders(options);
            continue;
          } catch {
            throw new AxBIAuthError('Authentication failed', {
              responseBody: body,
            });
          }
        }

        // Retry on transient errors
        if (
          retryEnabled &&
          RETRYABLE_STATUSES.has(response.status) &&
          attempt < this.maxRetries
        ) {
          await this.sleep(retryAfterMs ?? this.retryDelayMs(attempt));
          continue;
        }

        // Extract error message from response body if available
        const message =
          this.extractErrorMessage(body) ??
          `Request failed (${response.status})`;
        throw errorFromStatus(response.status, body, message, { retryAfterMs });
      } catch (error) {
        if (error instanceof AxBIError) {
          throw error;
        }

        lastError = error instanceof Error ? error : new Error(String(error));

        if (retryEnabled && attempt < this.maxRetries) {
          await this.sleep(this.retryDelayMs(attempt));
          continue;
        }

        break;
      }
    }

    throw new AxBIError(
      `Request to ${method} ${options.path} failed after ${this.maxRetries + 1} attempts`,
      { cause: lastError ?? undefined },
    );
  }

  /** Convenience: GET request. */
  async get<T = unknown>(
    path: string,
    query?: Record<string, string | number | boolean | undefined>,
  ): Promise<T> {
    return this.request<T>({ method: 'GET', path, query });
  }

  /** Convenience: POST request. */
  async post<T = unknown>(path: string, body?: unknown): Promise<T> {
    return this.request<T>({ method: 'POST', path, body });
  }

  /** Convenience: PUT request. */
  async put<T = unknown>(path: string, body?: unknown): Promise<T> {
    return this.request<T>({ method: 'PUT', path, body });
  }

  /** Convenience: DELETE request. */
  async delete<T = unknown>(path: string): Promise<T> {
    return this.request<T>({ method: 'DELETE', path });
  }

  private buildHeaders(options: RequestOptions): Record<string, string> {
    const headers: Record<string, string> = {
      Accept: 'application/json',
      ...this.auth.getAuthHeaders(),
      ...options.headers,
    };

    if (options.body !== undefined) {
      headers['Content-Type'] = 'application/json';
    }

    return headers;
  }

  private buildUrl(
    path: string,
    query?: Record<string, string | number | boolean | undefined>,
  ): string {
    const normalizedPath = path.startsWith('/') ? path : `/${path}`;
    const url = new URL(`${this.baseUrl}${normalizedPath}`);

    if (query) {
      for (const [key, value] of Object.entries(query)) {
        if (value !== undefined) {
          url.searchParams.set(key, String(value));
        }
      }
    }

    return url.toString();
  }

  private async parseBody(
    response: Response,
    responseType?: ResponseType,
  ): Promise<unknown> {
    if (responseType === 'blob') {
      return response.blob();
    }
    if (responseType === 'arrayBuffer') {
      return response.arrayBuffer();
    }
    if (responseType === 'text') {
      const text = await response.text().catch(() => null);
      return text || null;
    }
    if (responseType === 'json') {
      try {
        return await response.json();
      } catch {
        return null;
      }
    }
    const contentType = response.headers.get('content-type') ?? '';
    if (contentType.includes('application/json')) {
      try {
        return await response.json();
      } catch {
        return null;
      }
    }
    const text = await response.text().catch(() => null);
    return text || null;
  }

  private extractErrorMessage(body: unknown): string | null {
    if (body && typeof body === 'object') {
      const obj = body as Record<string, unknown>;
      if (typeof obj['message'] === 'string') return obj['message'];
      if (typeof obj['msg'] === 'string') return obj['msg'];
    }
    return null;
  }

  private retryDelayMs(attempt: number): number {
    return BASE_RETRY_DELAY_MS * Math.pow(2, attempt);
  }

  private parseRetryAfterMs(value: string | null): number | undefined {
    if (!value) {
      return undefined;
    }

    const trimmed = value.trim();
    if (!trimmed) {
      return undefined;
    }

    const seconds = Number(trimmed);
    if (Number.isFinite(seconds) && !Number.isInteger(seconds)) {
      return undefined;
    }
    if (Number.isInteger(seconds) && seconds >= 0) {
      return Math.min(seconds * 1000, MAX_RETRY_AFTER_MS);
    }

    const retryAt = Date.parse(trimmed);
    if (Number.isNaN(retryAt)) {
      return undefined;
    }

    return Math.min(Math.max(retryAt - Date.now(), 0), MAX_RETRY_AFTER_MS);
  }

  private sleep(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }
}

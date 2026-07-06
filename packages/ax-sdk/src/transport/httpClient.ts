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
import type { RequestOptions } from './types.js';

/** Default request timeout in milliseconds. */
const DEFAULT_TIMEOUT_MS = 30_000;

/** Base delay between retries in milliseconds (doubles on each attempt). */
const BASE_RETRY_DELAY_MS = 1_000;

/** HTTP status codes eligible for automatic retry. */
const RETRYABLE_STATUSES = new Set([408, 429, 500, 502, 503, 504]);

/**
 * Thin fetch wrapper providing:
 * - Auth header injection via AuthProvider
 * - JSON request/response serialization
 * - Retry with exponential backoff for 429/5xx
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

    const headers: Record<string, string> = {
      Accept: 'application/json',
      ...this.auth.getAuthHeaders(),
      ...options.headers,
    };

    if (options.body !== undefined) {
      headers['Content-Type'] = 'application/json';
    }

    const init: RequestInit = {
      method,
      headers,
      body:
        options.body !== undefined ? JSON.stringify(options.body) : undefined,
      signal: AbortSignal.timeout(timeout),
    };

    let lastError: Error | null = null;

    for (let attempt = 0; attempt <= this.maxRetries; attempt++) {
      try {
        const response = await fetch(url, init);
        const body = await this.parseBody(response);

        if (response.ok) {
          return body as T;
        }

        // Check for auth failure — attempt one re-login if credentials-based
        if (response.status === 401 && attempt === 0) {
          try {
            await this.auth.login();
            // Retry with refreshed token
            headers['Authorization'] = `Bearer ${this.auth.getAccessToken()}`;
            continue;
          } catch {
            throw new AxBIAuthError('Authentication failed', {
              responseBody: body,
            });
          }
        }

        // Retry on transient errors
        if (
          RETRYABLE_STATUSES.has(response.status) &&
          attempt < this.maxRetries
        ) {
          await this.sleep(BASE_RETRY_DELAY_MS * Math.pow(2, attempt));
          continue;
        }

        // Extract error message from response body if available
        const message =
          this.extractErrorMessage(body) ??
          `Request failed (${response.status})`;
        throw errorFromStatus(response.status, body, message);
      } catch (error) {
        if (error instanceof AxBIError) {
          throw error;
        }

        lastError = error instanceof Error ? error : new Error(String(error));

        // Abort / timeout errors may be retryable
        if (attempt < this.maxRetries) {
          await this.sleep(BASE_RETRY_DELAY_MS * Math.pow(2, attempt));
          continue;
        }
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

  private async parseBody(response: Response): Promise<unknown> {
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

  private sleep(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }
}

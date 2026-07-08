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

import type { AuthConfig } from './types.js';
import { AxBIAuthError } from '../shared/errors.js';
import { normalizeTimeoutMs } from '../shared/numbers.js';
import { normalizeHttpBaseUrl } from '../shared/url.js';

/** Default auth request timeout in milliseconds. */
const DEFAULT_AUTH_TIMEOUT_MS = 30_000;

const CONTROL_CHARACTER_PATTERN = /[\u0000-\u001f\u007f]/;
const HTTP_HEADER_NAME_PATTERN = /^[!#$%&'*+\-.^_`|~0-9A-Za-z]+$/;

/**
 * Manages authentication state and header injection for the HTTP transport.
 *
 * Supports four auth strategies:
 * - **credentials**: Logs in via `/api/v1/security/login`, stores the access token.
 * - **token**: Uses a pre-existing access token directly.
 * - **apiKey**: Sends the key in a configurable header.
 * - **guestToken**: Sends the guest token for embedded dashboard access.
 */
export class AuthProvider {
  private accessToken: string | null = null;
  private csrfToken: string | null = null;
  private readonly config: AuthConfig;
  private readonly baseUrl: string;
  private readonly timeout: number;

  constructor(config: AuthConfig, baseUrl: string, timeout?: number) {
    this.config = validateAuthConfig(config);
    this.baseUrl = normalizeHttpBaseUrl(baseUrl, 'baseUrl');
    this.timeout = normalizeTimeoutMs(timeout, DEFAULT_AUTH_TIMEOUT_MS);

    // Seed token for token-based auth
    if (this.config.type === 'token') {
      this.accessToken = this.config.accessToken;
    } else if (this.config.type === 'guestToken') {
      this.accessToken = this.config.guestToken;
    }
  }

  /**
   * Perform login flow for credentials-based auth.
   * Fetches access token and CSRF token.
   */
  async login(): Promise<void> {
    if (this.config.type !== 'credentials') {
      return;
    }

    const loginUrl = `${this.baseUrl}/api/v1/security/login`;
    let response: Response;
    try {
      response = await fetch(loginUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username: this.config.username,
          password: this.config.password,
          provider: 'db',
          refresh: true,
        }),
        signal: AbortSignal.timeout(this.timeout),
      });
    } catch (error) {
      throw new AxBIAuthError('Login request failed', {
        cause: normalizeError(error),
      });
    }

    if (!response.ok) {
      const body = await response.text().catch(() => null);
      throw new AxBIAuthError('Login failed', { responseBody: body });
    }

    let data: { access_token?: string };
    try {
      data = (await response.json()) as { access_token?: string };
    } catch (error) {
      throw new AxBIAuthError('Login response was not valid JSON', {
        cause: normalizeError(error),
      });
    }
    if (!data.access_token) {
      throw new AxBIAuthError('Login response missing access_token');
    }
    try {
      this.accessToken = validateHeaderValue(data.access_token, 'access_token');
    } catch (error) {
      throw new AxBIAuthError('Login response access_token was unsafe', {
        cause: normalizeError(error),
      });
    }

    // Attempt CSRF token fetch (non-fatal if unavailable)
    await this.fetchCsrfToken();
  }

  /** Build the Authorization / API-key headers for an outgoing request. */
  getAuthHeaders(): Record<string, string> {
    const headers: Record<string, string> = {};

    if (this.config.type === 'apiKey') {
      const headerName = this.config.headerName ?? 'Authorization';
      const prefix = this.config.headerPrefix ?? 'Bearer ';
      headers[headerName] = `${prefix}${this.config.apiKey}`;
    } else if (this.accessToken) {
      headers['Authorization'] = `Bearer ${this.accessToken}`;
    }

    if (this.csrfToken) {
      headers['X-CSRFToken'] = this.csrfToken;
    }

    return headers;
  }

  /** Check whether an access token is currently available. */
  get isAuthenticated(): boolean {
    return this.accessToken !== null || this.config.type === 'apiKey';
  }

  /** Update the access token (e.g. after a refresh). */
  setAccessToken(token: string): void {
    this.accessToken = validateHeaderValue(token, 'accessToken');
  }

  /** Retrieve the current access token, if any. */
  getAccessToken(): string | null {
    return this.accessToken;
  }

  private async fetchCsrfToken(): Promise<void> {
    try {
      const csrfUrl = `${this.baseUrl}/api/v1/security/csrf_token/`;
      const response = await fetch(csrfUrl, {
        headers: {
          ...(this.accessToken
            ? { Authorization: `Bearer ${this.accessToken}` }
            : {}),
        },
        signal: AbortSignal.timeout(this.timeout),
      });
      if (response.ok) {
        const data = (await response.json()) as { result?: string };
        if (data.result) {
          validateHeaderValue(data.result, 'CSRF token');
          this.csrfToken = data.result;
        }
      }
    } catch {
      // CSRF token is optional for some deployments; swallow the error.
    }
  }
}

function normalizeError(error: unknown): Error {
  return error instanceof Error ? error : new Error(String(error));
}

function validateAuthConfig(config: AuthConfig): AuthConfig {
  if (config.type === 'token') {
    return {
      ...config,
      accessToken: validateHeaderValue(config.accessToken, 'accessToken'),
    };
  }
  if (config.type === 'guestToken') {
    return {
      ...config,
      guestToken: validateHeaderValue(config.guestToken, 'guestToken'),
    };
  }
  if (config.type === 'apiKey') {
    return {
      ...config,
      apiKey: validateHeaderValue(config.apiKey, 'apiKey'),
      headerName: validateHeaderName(config.headerName ?? 'Authorization'),
      headerPrefix: validateHeaderValuePart(
        config.headerPrefix ?? 'Bearer ',
        'headerPrefix',
      ),
    };
  }
  return config;
}

function validateHeaderName(value: string): string {
  if (!HTTP_HEADER_NAME_PATTERN.test(value)) {
    throw new Error('headerName must be a valid HTTP header name');
  }
  return value;
}

function validateHeaderValue(value: string, name: string): string {
  if (value.trim() === '') {
    throw new Error(`${name} must not be empty`);
  }
  return validateHeaderValuePart(value, name);
}

function validateHeaderValuePart(value: string, name: string): string {
  if (CONTROL_CHARACTER_PATTERN.test(value)) {
    throw new Error(`${name} must not contain control characters`);
  }
  return value;
}

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

import { HttpClient } from '../transport/httpClient.js';

const API_KEY_PATH = '/api/v1/security/api_keys';

/** The name reserved for the key managed by AX BI's navbar and MCP clients. */
export const MANAGED_MCP_API_KEY_NAME = 'AX BI MCP';

/** Non-secret metadata returned when an API key is listed or fetched. */
export interface ApiKeyItem {
  uuid: string;
  name: string;
  /** A non-secret display hint. This is not a usable credential. */
  key_prefix: string;
  scopes: string | null;
  active: boolean;
  created_on: string;
  expires_on: string | null;
  revoked_on: string | null;
  last_used_on: string | null;
}

/** Parameters accepted by the current-user API-key creation endpoint. */
export interface CreateApiKeyInput {
  name: string;
  scopes?: string;
  expires_on?: string;
}

/**
 * Result returned only when a key is created.
 *
 * `key` is the sole plaintext copy of the credential. Store it before
 * revoking an older key because subsequent GET requests cannot recover it.
 */
export interface CreatedApiKey {
  uuid: string;
  name: string;
  key: string;
  key_prefix: string;
  scopes: string | null;
  created_on: string;
  expires_on: string | null;
}

interface ApiKeyListEnvelope {
  result: ApiKeyItem[];
}

interface ApiKeyItemEnvelope<T> {
  result: T;
}

/** Current-user API-key management operations. */
export class ApiKeysResource {
  constructor(private readonly http: HttpClient) {}

  /** List only keys owned by the authenticated user. Plaintext is never returned. */
  async list(): Promise<ApiKeyItem[]> {
    const envelope = await this.http.get<ApiKeyListEnvelope>(`${API_KEY_PATH}/`);
    return envelope.result;
  }

  /** Fetch non-secret metadata for one key owned by the authenticated user. */
  async getByUuid(uuid: string): Promise<ApiKeyItem> {
    const envelope = await this.http.get<ApiKeyItemEnvelope<ApiKeyItem>>(
      this.buildItemPath(uuid),
    );
    return envelope.result;
  }

  /** Create a key. The plaintext `key` field is returned by this call only. */
  async create(input: CreateApiKeyInput): Promise<CreatedApiKey> {
    const envelope = await this.http.post<ApiKeyItemEnvelope<CreatedApiKey>>(
      `${API_KEY_PATH}/`,
      input,
    );
    return envelope.result;
  }

  /** Create a navbar-compatible, user-bound MCP key. */
  async createMcpKey(): Promise<CreatedApiKey> {
    return this.create({ name: MANAGED_MCP_API_KEY_NAME });
  }

  /** Revoke a key owned by the authenticated user. */
  async revoke(uuid: string): Promise<void> {
    await this.http.delete(this.buildItemPath(uuid));
  }

  private buildItemPath(uuid: string): string {
    return `${API_KEY_PATH}/${encodeURIComponent(uuid)}`;
  }
}

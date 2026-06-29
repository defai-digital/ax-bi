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
import {
  AUTHORIZATION_CONTRACT_VERSION,
  PermissionCheckRequest,
  PermissionCheckResult,
} from './contracts/authorization';
import { ServiceConfig } from './config';

export interface DependencyHealth {
  ok: boolean;
  url: string;
  statusCode?: number;
  error?: string;
}

export interface DependencyMetadata extends DependencyHealth {
  keyCount?: number;
  keys?: string[];
}

export interface SupersetHealthClient {
  checkHealth(correlationId?: string): Promise<DependencyHealth>;
}

export interface SupersetMetadataClient {
  probeMetadata(correlationId?: string): Promise<DependencyMetadata>;
}

export class SupersetClient
  implements SupersetHealthClient, SupersetMetadataClient
{
  private readonly healthUrl: string;
  private readonly metadataUrl: string;
  private readonly permissionUrl: string;

  constructor(private readonly config: ServiceConfig) {
    this.healthUrl = `${config.supersetBaseUrl}${config.supersetHealthPath}`;
    this.metadataUrl = `${config.supersetBaseUrl}${config.supersetMetadataPath}`;
    this.permissionUrl = `${config.supersetBaseUrl}${config.supersetPermissionPath}`;
  }

  private buildHeaders(
    correlationId?: string,
    contentType?: string,
  ): HeadersInit {
    const headers: Record<string, string> = {};

    if (correlationId !== undefined) {
      headers['x-request-id'] = correlationId;
    }

    if (contentType !== undefined) {
      headers['content-type'] = contentType;
    }

    if (this.config.supersetInternalToken !== undefined) {
      headers.authorization = `Bearer ${this.config.supersetInternalToken}`;
    }

    return headers;
  }

  async checkHealth(correlationId?: string): Promise<DependencyHealth> {
    try {
      const response = await fetch(this.healthUrl, {
        headers: this.buildHeaders(correlationId),
        signal: AbortSignal.timeout(this.config.supersetTimeoutMs),
      });

      return {
        ok: response.ok,
        statusCode: response.status,
        url: this.healthUrl,
      };
    } catch (error) {
      return {
        ok: false,
        error: error instanceof Error ? error.message : String(error),
        url: this.healthUrl,
      };
    }
  }

  async probeMetadata(correlationId?: string): Promise<DependencyMetadata> {
    try {
      const response = await fetch(this.metadataUrl, {
        headers: this.buildHeaders(correlationId),
        signal: AbortSignal.timeout(this.config.supersetTimeoutMs),
      });
      const payload = (await response.json()) as unknown;
      const keys = extractObjectKeys(payload);

      return {
        ok: response.ok,
        statusCode: response.status,
        url: this.metadataUrl,
        keyCount: keys.length,
        keys,
      };
    } catch (error) {
      return {
        ok: false,
        error: error instanceof Error ? error.message : String(error),
        url: this.metadataUrl,
      };
    }
  }

  async checkPermission(
    request: PermissionCheckRequest,
    correlationId?: string,
  ): Promise<PermissionCheckResult> {
    try {
      const response = await fetch(this.permissionUrl, {
        method: 'POST',
        headers: this.buildHeaders(correlationId, 'application/json'),
        body: JSON.stringify(request),
        signal: AbortSignal.timeout(this.config.supersetTimeoutMs),
      });
      const payload = (await response.json()) as Partial<PermissionCheckResult>;

      return {
        contractVersion: AUTHORIZATION_CONTRACT_VERSION,
        allowed: payload.allowed === true,
        reason: typeof payload.reason === 'string' ? payload.reason : undefined,
        statusCode: response.status,
      };
    } catch (error) {
      return {
        contractVersion: AUTHORIZATION_CONTRACT_VERSION,
        allowed: false,
        error: error instanceof Error ? error.message : String(error),
      };
    }
  }
}

function extractObjectKeys(payload: unknown): string[] {
  if (payload === null || typeof payload !== 'object' || Array.isArray(payload)) {
    return [];
  }

  return Object.keys(payload).sort();
}

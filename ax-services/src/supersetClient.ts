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
  ASSET_SEARCH_CONTRACT_VERSION,
  AssetSearchRequest,
  AssetSearchResponse,
  AssetSearchResult,
  AssetType,
} from './contracts/assetSearch';
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

export interface SupersetAssetSearchClient {
  searchAssets(
    request: AssetSearchRequest,
    correlationId?: string,
  ): Promise<AssetSearchResponse>;
}

export class SupersetClient
  implements
    SupersetHealthClient,
    SupersetMetadataClient,
    SupersetAssetSearchClient
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

      if (!response.ok) {
        return {
          ok: false,
          statusCode: response.status,
          url: this.metadataUrl,
          keyCount: 0,
          keys: [],
        };
      }

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

  async searchAssets(
    request: AssetSearchRequest,
    correlationId?: string,
  ): Promise<AssetSearchResponse> {
    const warnings: string[] = [];
    const requestedTypes =
      request.assetTypes.length > 0
        ? request.assetTypes
        : (['chart', 'dashboard', 'dataset'] satisfies AssetType[]);
    const supportedTypes = requestedTypes.filter(isSupportedSearchType);

    if (requestedTypes.includes('metric')) {
      warnings.push('Metric search is not supported by the TypeScript path.');
    }

    const results = await Promise.all(
      supportedTypes.map(async assetType =>
        this.searchAssetType(assetType, request, correlationId),
      ),
    );
    const assets = results
      .flatMap(result => result.assets)
      .sort((left, right) => right.relevanceScore - left.relevanceScore)
      .slice(0, request.limit);

    warnings.push(...results.flatMap(result => result.warnings));

    return {
      contractVersion: ASSET_SEARCH_CONTRACT_VERSION,
      assets,
      warnings,
    };
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

      if (!response.ok) {
        return {
          contractVersion: AUTHORIZATION_CONTRACT_VERSION,
          allowed: false,
          statusCode: response.status,
        };
      }

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

  private async searchAssetType(
    assetType: SearchableAssetType,
    request: AssetSearchRequest,
    correlationId?: string,
  ): Promise<{ assets: AssetSearchResult[]; warnings: string[] }> {
    const url = this.buildAssetSearchUrl(assetType, request);

    try {
      const response = await fetch(url, {
        headers: this.buildHeaders(correlationId),
        signal: AbortSignal.timeout(this.config.supersetTimeoutMs),
      });

      if (!response.ok) {
        return {
          assets: [],
          warnings: [
            `${assetType} search returned status ${response.status} from Superset`,
          ],
        };
      }

      const payload = (await response.json()) as unknown;

      return {
        assets: extractSupersetResults(payload)
          .map(item => toAssetSearchResult(assetType, item, request.query))
          .filter(isDefined),
        warnings: [],
      };
    } catch (error) {
      return {
        assets: [],
        warnings: [
          `${assetType} search failed: ${
            error instanceof Error ? error.message : String(error)
          }`,
        ],
      };
    }
  }

  private buildAssetSearchUrl(
    assetType: SearchableAssetType,
    request: AssetSearchRequest,
  ): string {
    const path = this.config.supersetAssetSearchPaths[assetType];
    const filterColumn = assetSearchFilterColumns[assetType];
    const query = buildSupersetListQuery(
      filterColumn,
      request.query,
      request.limit,
      request.includeCertifiedOnly,
    );
    const url = new URL(`${this.config.supersetBaseUrl}${path}`);
    url.searchParams.set('q', query);
    return url.toString();
  }
}

function extractObjectKeys(payload: unknown): string[] {
  if (payload === null || typeof payload !== 'object' || Array.isArray(payload)) {
    return [];
  }

  return Object.keys(payload).sort();
}

type SearchableAssetType = Exclude<AssetType, 'metric'>;

interface SupersetListItem {
  id?: number;
  uuid?: string;
  name?: string;
  table_name?: string;
  slice_name?: string;
  dashboard_title?: string;
  description?: string;
  certified_by?: string | null;
  owners?: unknown[];
  tags?: unknown[];
}

const assetSearchFilterColumns: Record<SearchableAssetType, string> = {
  chart: 'slice_name',
  dashboard: 'dashboard_title',
  dataset: 'table_name',
};

function isSupportedSearchType(
  assetType: AssetType,
): assetType is SearchableAssetType {
  return (
    assetType === 'chart' ||
    assetType === 'dashboard' ||
    assetType === 'dataset'
  );
}

function buildSupersetListQuery(
  filterColumn: string,
  query: string,
  limit: number,
  includeCertifiedOnly: boolean,
): string {
  const filters = [
    `(col:${filterColumn},opr:ct,value:'${escapeRisonString(query)}')`,
  ];

  if (includeCertifiedOnly) {
    filters.push('(col:id,opr:certified,value:true)');
  }

  return `(page:0,page_size:${limit},filters:!(${filters.join(',')}))`;
}

function escapeRisonString(value: string): string {
  return value.replace(/!/g, '!!').replace(/'/g, "!'");
}

function extractSupersetResults(payload: unknown): SupersetListItem[] {
  if (!isRecord(payload) || !Array.isArray(payload.result)) {
    return [];
  }

  return payload.result.filter(isRecord).map(item => item as SupersetListItem);
}

function toAssetSearchResult(
  assetType: SearchableAssetType,
  item: SupersetListItem,
  query: string,
): AssetSearchResult | undefined {
  if (typeof item.id !== 'number') {
    return undefined;
  }

  const name = extractAssetName(assetType, item);
  const description = typeof item.description === 'string' ? item.description : '';
  const certified = Boolean(item.certified_by);

  return {
    assetType,
    id: item.id,
    uuid: typeof item.uuid === 'string' ? item.uuid : '',
    name,
    description,
    certified,
    relevanceScore: scoreAsset(name, description, query) + (certified ? 0.2 : 0),
    relevanceReason: buildRelevanceReason(name, description, query),
    owners: extractNameList(item.owners),
    tags: extractNameList(item.tags),
  };
}

function extractAssetName(
  assetType: SearchableAssetType,
  item: SupersetListItem,
): string {
  if (assetType === 'chart' && typeof item.slice_name === 'string') {
    return item.slice_name;
  }
  if (assetType === 'dashboard' && typeof item.dashboard_title === 'string') {
    return item.dashboard_title;
  }
  if (assetType === 'dataset' && typeof item.table_name === 'string') {
    return item.table_name;
  }
  return typeof item.name === 'string' ? item.name : '';
}

function scoreAsset(name: string, description: string, query: string): number {
  const normalizedQuery = query.toLowerCase();
  let score = 0;
  if (name.toLowerCase().includes(normalizedQuery)) {
    score += 1;
  }
  if (description.toLowerCase().includes(normalizedQuery)) {
    score += 0.5;
  }
  return Number(score.toFixed(4));
}

function buildRelevanceReason(
  name: string,
  description: string,
  query: string,
): string {
  const normalizedQuery = query.toLowerCase();
  const reasons: string[] = [];

  if (name.toLowerCase().includes(normalizedQuery)) {
    reasons.push(`name matches '${query}'`);
  }
  if (description.toLowerCase().includes(normalizedQuery)) {
    reasons.push(`description matches '${query}'`);
  }

  return reasons.length > 0 ? reasons.join(', ') : 'metadata match';
}

function extractNameList(values: unknown[] | undefined): string[] {
  if (!values) {
    return [];
  }

  return values.flatMap(value => {
    if (typeof value === 'string') {
      return [value];
    }
    if (isRecord(value)) {
      const name = value.name ?? value.username ?? value.first_name;
      return typeof name === 'string' ? [name] : [];
    }
    return [];
  });
}

function isDefined<T>(value: T | undefined): value is T {
  return value !== undefined;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

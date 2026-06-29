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
  CHART_LIST_CONTRACT_VERSION,
  ChartFilterValue,
  ChartListItem,
  ChartListRequest,
  ChartListResponse,
} from './contracts/chartList';
import {
  DASHBOARD_LIST_CONTRACT_VERSION,
  DashboardListItem,
  DashboardListRequest,
  DashboardListResponse,
  DashboardFilterValue,
} from './contracts/dashboardList';
import {
  DATABASE_LIST_CONTRACT_VERSION,
  DatabaseFilterValue,
  DatabaseListItem,
  DatabaseListRequest,
  DatabaseListResponse,
} from './contracts/databaseList';
import {
  DATASET_LIST_CONTRACT_VERSION,
  DatasetFilterValue,
  DatasetListItem,
  DatasetListRequest,
  DatasetListResponse,
} from './contracts/datasetList';
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

export interface SupersetDashboardListClient {
  listDashboards(
    request: DashboardListRequest,
    correlationId?: string,
  ): Promise<DashboardListResponse>;
}

export interface SupersetChartListClient {
  listCharts(
    request: ChartListRequest,
    correlationId?: string,
  ): Promise<ChartListResponse>;
}

export interface SupersetDatabaseListClient {
  listDatabases(
    request: DatabaseListRequest,
    correlationId?: string,
  ): Promise<DatabaseListResponse>;
}

export interface SupersetDatasetListClient {
  listDatasets(
    request: DatasetListRequest,
    correlationId?: string,
  ): Promise<DatasetListResponse>;
}

export class SupersetClient
  implements
    SupersetHealthClient,
    SupersetMetadataClient,
    SupersetAssetSearchClient,
    SupersetDashboardListClient,
    SupersetChartListClient,
    SupersetDatabaseListClient,
    SupersetDatasetListClient
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

  async listDashboards(
    request: DashboardListRequest,
    correlationId?: string,
  ): Promise<DashboardListResponse> {
    const url = this.buildDashboardListUrl(request);

    try {
      const response = await fetch(url, {
        headers: this.buildHeaders(correlationId),
        signal: AbortSignal.timeout(this.config.supersetTimeoutMs),
      });

      if (!response.ok) {
        return emptyDashboardListResponse(request, [
          `dashboard list returned status ${response.status} from Superset`,
        ]);
      }

      const payload = (await response.json()) as unknown;
      const dashboards = extractSupersetResults(payload)
        .map(toDashboardListItem)
        .filter(isDefined);
      const totalCount = extractSupersetCount(payload, dashboards.length);
      const totalPages = Math.ceil(totalCount / request.pageSize);

      return {
        contractVersion: DASHBOARD_LIST_CONTRACT_VERSION,
        dashboards,
        count: dashboards.length,
        totalCount,
        page: request.page,
        pageSize: request.pageSize,
        totalPages,
        hasNext: request.page < totalPages,
        hasPrevious: request.page > 1,
        columnsRequested: requestedDashboardColumns(request),
        columnsLoaded: dashboardColumnsLoaded(dashboards),
        warnings: [],
      };
    } catch (error) {
      return emptyDashboardListResponse(request, [
        `dashboard list failed: ${
          error instanceof Error ? error.message : String(error)
        }`,
      ]);
    }
  }

  async listCharts(
    request: ChartListRequest,
    correlationId?: string,
  ): Promise<ChartListResponse> {
    const url = this.buildChartListUrl(request);

    try {
      const response = await fetch(url, {
        headers: this.buildHeaders(correlationId),
        signal: AbortSignal.timeout(this.config.supersetTimeoutMs),
      });

      if (!response.ok) {
        return emptyChartListResponse(request, [
          `chart list returned status ${response.status} from Superset`,
        ]);
      }

      const payload = (await response.json()) as unknown;
      const charts = extractSupersetResults(payload)
        .map(toChartListItem)
        .filter(isDefined);
      const totalCount = extractSupersetCount(payload, charts.length);
      const totalPages = Math.ceil(totalCount / request.pageSize);

      return {
        contractVersion: CHART_LIST_CONTRACT_VERSION,
        charts,
        count: charts.length,
        totalCount,
        page: request.page,
        pageSize: request.pageSize,
        totalPages,
        hasNext: request.page < totalPages,
        hasPrevious: request.page > 1,
        columnsRequested: requestedChartColumns(request),
        columnsLoaded: chartColumnsLoaded(charts),
        warnings: [],
      };
    } catch (error) {
      return emptyChartListResponse(request, [
        `chart list failed: ${
          error instanceof Error ? error.message : String(error)
        }`,
      ]);
    }
  }

  async listDatasets(
    request: DatasetListRequest,
    correlationId?: string,
  ): Promise<DatasetListResponse> {
    const url = this.buildDatasetListUrl(request);

    try {
      const response = await fetch(url, {
        headers: this.buildHeaders(correlationId),
        signal: AbortSignal.timeout(this.config.supersetTimeoutMs),
      });

      if (!response.ok) {
        return emptyDatasetListResponse(request, [
          `dataset list returned status ${response.status} from Superset`,
        ]);
      }

      const payload = (await response.json()) as unknown;
      const datasets = extractSupersetResults(payload)
        .map(toDatasetListItem)
        .filter(isDefined);
      const totalCount = extractSupersetCount(payload, datasets.length);
      const totalPages = Math.ceil(totalCount / request.pageSize);

      return {
        contractVersion: DATASET_LIST_CONTRACT_VERSION,
        datasets,
        count: datasets.length,
        totalCount,
        page: request.page,
        pageSize: request.pageSize,
        totalPages,
        hasNext: request.page < totalPages,
        hasPrevious: request.page > 1,
        columnsRequested: requestedDatasetColumns(request),
        columnsLoaded: datasetColumnsLoaded(datasets),
        warnings: [],
      };
    } catch (error) {
      return emptyDatasetListResponse(request, [
        `dataset list failed: ${
          error instanceof Error ? error.message : String(error)
        }`,
      ]);
    }
  }

  async listDatabases(
    request: DatabaseListRequest,
    correlationId?: string,
  ): Promise<DatabaseListResponse> {
    const url = this.buildDatabaseListUrl(request);

    try {
      const response = await fetch(url, {
        headers: this.buildHeaders(correlationId),
        signal: AbortSignal.timeout(this.config.supersetTimeoutMs),
      });

      if (!response.ok) {
        return emptyDatabaseListResponse(request, [
          `database list returned status ${response.status} from Superset`,
        ]);
      }

      const payload = (await response.json()) as unknown;
      const databases = extractSupersetResults(payload)
        .map(toDatabaseListItem)
        .filter(isDefined);
      const totalCount = extractSupersetCount(payload, databases.length);
      const totalPages = Math.ceil(totalCount / request.pageSize);

      return {
        contractVersion: DATABASE_LIST_CONTRACT_VERSION,
        databases,
        count: databases.length,
        totalCount,
        page: request.page,
        pageSize: request.pageSize,
        totalPages,
        hasNext: request.page < totalPages,
        hasPrevious: request.page > 1,
        columnsRequested: requestedDatabaseColumns(request),
        columnsLoaded: databaseColumnsLoaded(databases),
        warnings: [],
      };
    } catch (error) {
      return emptyDatabaseListResponse(request, [
        `database list failed: ${
          error instanceof Error ? error.message : String(error)
        }`,
      ]);
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

  private buildDashboardListUrl(request: DashboardListRequest): string {
    const url = new URL(
      `${this.config.supersetBaseUrl}${this.config.supersetAssetSearchPaths.dashboard}`,
    );
    url.searchParams.set('q', buildDashboardListQuery(request));
    return url.toString();
  }

  private buildChartListUrl(request: ChartListRequest): string {
    const url = new URL(
      `${this.config.supersetBaseUrl}${this.config.supersetAssetSearchPaths.chart}`,
    );
    url.searchParams.set('q', buildChartListQuery(request));
    return url.toString();
  }

  private buildDatasetListUrl(request: DatasetListRequest): string {
    const url = new URL(
      `${this.config.supersetBaseUrl}${this.config.supersetAssetSearchPaths.dataset}`,
    );
    url.searchParams.set('q', buildDatasetListQuery(request));
    return url.toString();
  }

  private buildDatabaseListUrl(request: DatabaseListRequest): string {
    const url = new URL(
      `${this.config.supersetBaseUrl}${this.config.supersetAssetSearchPaths.database}`,
    );
    url.searchParams.set('q', buildDatabaseListQuery(request));
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
  schema?: string;
  database_name?: string;
  database?: {
    id?: number;
    database_name?: string;
  };
  slice_name?: string;
  viz_type?: string;
  dashboard_title?: string;
  slug?: string;
  description?: string;
  certified_by?: string | null;
  certification_details?: string | null;
  published?: boolean;
  url?: string;
  changed_on?: string;
  changed_on_humanized?: string;
  is_virtual?: boolean;
  database_id?: number;
  type?: string;
  backend?: string;
  expose_in_sqllab?: boolean;
  allow_ctas?: boolean;
  allow_cvas?: boolean;
  allow_dml?: boolean;
  allow_file_upload?: boolean;
  allow_run_async?: boolean;
  cache_timeout?: number | null;
  configuration_method?: string;
  force_ctas_schema?: string | null;
  impersonate_user?: boolean;
  is_managed_externally?: boolean;
  external_url?: string | null;
  extra?: unknown;
  created_on?: string;
  created_on_humanized?: string;
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

function buildDashboardListQuery(request: DashboardListRequest): string {
  const filters = [...request.filters];
  if (request.search !== undefined && request.search !== '') {
    filters.push({
      col: 'dashboard_title',
      opr: 'ct',
      value: request.search,
    });
  }

  const parts = [
    `page:${request.page - 1}`,
    `page_size:${request.pageSize}`,
    `filters:!(${filters.map(formatDashboardFilter).join(',')})`,
  ];

  if (request.orderColumn !== undefined && request.orderColumn !== '') {
    parts.push(`order_column:${request.orderColumn}`);
    parts.push(`order_direction:${request.orderDirection}`);
  }

  return `(${parts.join(',')})`;
}

function buildChartListQuery(request: ChartListRequest): string {
  const filters = [...request.filters];
  if (request.search !== undefined && request.search !== '') {
    filters.push({
      col: 'slice_name',
      opr: 'ct',
      value: request.search,
    });
  }

  const parts = [
    `page:${request.page - 1}`,
    `page_size:${request.pageSize}`,
    `filters:!(${filters.map(formatChartFilter).join(',')})`,
  ];

  if (request.orderColumn !== undefined && request.orderColumn !== '') {
    parts.push(`order_column:${request.orderColumn}`);
    parts.push(`order_direction:${request.orderDirection}`);
  }

  return `(${parts.join(',')})`;
}

function buildDatasetListQuery(request: DatasetListRequest): string {
  const filters = [...request.filters];
  if (request.search !== undefined && request.search !== '') {
    filters.push({
      col: 'table_name',
      opr: 'ct',
      value: request.search,
    });
  }

  const parts = [
    `page:${request.page - 1}`,
    `page_size:${request.pageSize}`,
    `filters:!(${filters.map(formatDatasetFilter).join(',')})`,
  ];

  if (request.orderColumn !== undefined && request.orderColumn !== '') {
    parts.push(`order_column:${request.orderColumn}`);
    parts.push(`order_direction:${request.orderDirection}`);
  }

  return `(${parts.join(',')})`;
}

function buildDatabaseListQuery(request: DatabaseListRequest): string {
  const filters = [...request.filters];
  if (request.search !== undefined && request.search !== '') {
    filters.push({
      col: 'database_name',
      opr: 'ct',
      value: request.search,
    });
  }

  const parts = [
    `page:${request.page - 1}`,
    `page_size:${request.pageSize}`,
    `filters:!(${filters.map(formatDatabaseFilter).join(',')})`,
  ];

  if (request.orderColumn !== undefined && request.orderColumn !== '') {
    parts.push(`order_column:${request.orderColumn}`);
    parts.push(`order_direction:${request.orderDirection}`);
  }

  return `(${parts.join(',')})`;
}

function formatDashboardFilter(filter: {
  col: string;
  opr: string;
  value: DashboardFilterValue;
}): string {
  return `(col:${filter.col},opr:${filter.opr},value:${formatRisonValue(
    filter.value,
  )})`;
}

function formatChartFilter(filter: {
  col: string;
  opr: string;
  value: ChartFilterValue;
}): string {
  return `(col:${filter.col},opr:${filter.opr},value:${formatChartRisonValue(
    filter.value,
  )})`;
}

function formatDatasetFilter(filter: {
  col: string;
  opr: string;
  value: DatasetFilterValue;
}): string {
  return `(col:${filter.col},opr:${filter.opr},value:${formatDatasetRisonValue(
    filter.value,
  )})`;
}

function formatDatabaseFilter(filter: {
  col: string;
  opr: string;
  value: DatabaseFilterValue;
}): string {
  return `(col:${filter.col},opr:${filter.opr},value:${formatDatabaseRisonValue(
    filter.value,
  )})`;
}

function formatRisonValue(value: DashboardFilterValue): string {
  if (Array.isArray(value)) {
    return `!(${value.map(formatScalarRisonValue).join(',')})`;
  }
  return formatScalarRisonValue(value);
}

function formatChartRisonValue(value: ChartFilterValue): string {
  if (Array.isArray(value)) {
    return `!(${value.map(formatScalarRisonValue).join(',')})`;
  }
  return formatScalarRisonValue(value);
}

function formatDatasetRisonValue(value: DatasetFilterValue): string {
  if (Array.isArray(value)) {
    return `!(${value.map(formatScalarRisonValue).join(',')})`;
  }
  return formatScalarRisonValue(value);
}

function formatDatabaseRisonValue(value: DatabaseFilterValue): string {
  if (Array.isArray(value)) {
    return `!(${value.map(formatScalarRisonValue).join(',')})`;
  }
  return formatScalarRisonValue(value);
}

function formatScalarRisonValue(value: string | number | boolean): string {
  if (typeof value === 'string') {
    return `'${escapeRisonString(value)}'`;
  }
  return String(value);
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

function extractSupersetCount(payload: unknown, fallback: number): number {
  if (!isRecord(payload) || typeof payload.count !== 'number') {
    return fallback;
  }
  return payload.count;
}

function toDashboardListItem(
  item: SupersetListItem,
): DashboardListItem | undefined {
  if (typeof item.id !== 'number') {
    return undefined;
  }

  return {
    id: item.id,
    dashboardTitle:
      typeof item.dashboard_title === 'string' ? item.dashboard_title : undefined,
    slug: typeof item.slug === 'string' ? item.slug : undefined,
    description:
      typeof item.description === 'string' ? item.description : undefined,
    certifiedBy:
      typeof item.certified_by === 'string' ? item.certified_by : undefined,
    certificationDetails:
      typeof item.certification_details === 'string'
        ? item.certification_details
        : undefined,
    published: typeof item.published === 'boolean' ? item.published : undefined,
    uuid: typeof item.uuid === 'string' ? item.uuid : undefined,
    url: typeof item.url === 'string' ? item.url : undefined,
    changedOn: typeof item.changed_on === 'string' ? item.changed_on : undefined,
    changedOnHumanized:
      typeof item.changed_on_humanized === 'string'
        ? item.changed_on_humanized
        : undefined,
  };
}

function toChartListItem(item: SupersetListItem): ChartListItem | undefined {
  if (typeof item.id !== 'number') {
    return undefined;
  }

  return {
    id: item.id,
    sliceName: typeof item.slice_name === 'string' ? item.slice_name : undefined,
    vizType: typeof item.viz_type === 'string' ? item.viz_type : undefined,
    description:
      typeof item.description === 'string' ? item.description : undefined,
    certifiedBy:
      typeof item.certified_by === 'string' ? item.certified_by : undefined,
    certificationDetails:
      typeof item.certification_details === 'string'
        ? item.certification_details
        : undefined,
    uuid: typeof item.uuid === 'string' ? item.uuid : undefined,
    url: typeof item.url === 'string' ? item.url : undefined,
    changedOn: typeof item.changed_on === 'string' ? item.changed_on : undefined,
    changedOnHumanized:
      typeof item.changed_on_humanized === 'string'
        ? item.changed_on_humanized
        : undefined,
  };
}

function toDatasetListItem(item: SupersetListItem): DatasetListItem | undefined {
  if (typeof item.id !== 'number') {
    return undefined;
  }

  return {
    id: item.id,
    tableName: typeof item.table_name === 'string' ? item.table_name : undefined,
    schema: typeof item.schema === 'string' ? item.schema : undefined,
    databaseName: extractDatabaseName(item),
    description:
      typeof item.description === 'string' ? item.description : undefined,
    certifiedBy:
      typeof item.certified_by === 'string' ? item.certified_by : undefined,
    certificationDetails:
      typeof item.certification_details === 'string'
        ? item.certification_details
        : undefined,
    changedOn: typeof item.changed_on === 'string' ? item.changed_on : undefined,
    changedOnHumanized:
      typeof item.changed_on_humanized === 'string'
        ? item.changed_on_humanized
        : undefined,
    isVirtual:
      typeof item.is_virtual === 'boolean'
        ? item.is_virtual
        : item.type === 'virtual',
    databaseId:
      typeof item.database_id === 'number'
        ? item.database_id
        : typeof item.database?.id === 'number'
          ? item.database.id
          : undefined,
    uuid: typeof item.uuid === 'string' ? item.uuid : undefined,
    url: typeof item.url === 'string' ? item.url : undefined,
  };
}

function toDatabaseListItem(item: SupersetListItem): DatabaseListItem | undefined {
  if (typeof item.id !== 'number') {
    return undefined;
  }

  return {
    id: item.id,
    uuid: typeof item.uuid === 'string' ? item.uuid : undefined,
    databaseName:
      typeof item.database_name === 'string' ? item.database_name : undefined,
    backend: typeof item.backend === 'string' ? item.backend : undefined,
    exposeInSqllab:
      typeof item.expose_in_sqllab === 'boolean'
        ? item.expose_in_sqllab
        : undefined,
    allowCtas:
      typeof item.allow_ctas === 'boolean' ? item.allow_ctas : undefined,
    allowCvas:
      typeof item.allow_cvas === 'boolean' ? item.allow_cvas : undefined,
    allowDml: typeof item.allow_dml === 'boolean' ? item.allow_dml : undefined,
    allowFileUpload:
      typeof item.allow_file_upload === 'boolean'
        ? item.allow_file_upload
        : undefined,
    allowRunAsync:
      typeof item.allow_run_async === 'boolean'
        ? item.allow_run_async
        : undefined,
    cacheTimeout:
      typeof item.cache_timeout === 'number' ? item.cache_timeout : undefined,
    configurationMethod:
      typeof item.configuration_method === 'string'
        ? item.configuration_method
        : undefined,
    forceCtasSchema:
      typeof item.force_ctas_schema === 'string'
        ? item.force_ctas_schema
        : undefined,
    impersonateUser:
      typeof item.impersonate_user === 'boolean'
        ? item.impersonate_user
        : undefined,
    isManagedExternally:
      typeof item.is_managed_externally === 'boolean'
        ? item.is_managed_externally
        : undefined,
    externalUrl:
      typeof item.external_url === 'string' ? item.external_url : undefined,
    extra: isRecord(item.extra) ? item.extra : undefined,
    changedOn: typeof item.changed_on === 'string' ? item.changed_on : undefined,
    changedOnHumanized:
      typeof item.changed_on_humanized === 'string'
        ? item.changed_on_humanized
        : undefined,
    createdOn: typeof item.created_on === 'string' ? item.created_on : undefined,
    createdOnHumanized:
      typeof item.created_on_humanized === 'string'
        ? item.created_on_humanized
        : undefined,
  };
}

function extractDatabaseName(item: SupersetListItem): string | undefined {
  if (typeof item.database_name === 'string') {
    return item.database_name;
  }
  return typeof item.database?.database_name === 'string'
    ? item.database.database_name
    : undefined;
}

function requestedDashboardColumns(request: DashboardListRequest): string[] {
  return request.selectColumns.length > 0
    ? request.selectColumns
    : [
        'id',
        'dashboard_title',
        'slug',
        'description',
        'certified_by',
        'certification_details',
        'url',
        'changed_on',
        'changed_on_humanized',
      ];
}

function dashboardColumnsLoaded(dashboards: DashboardListItem[]): string[] {
  const loaded = new Set<string>(['id']);
  for (const dashboard of dashboards) {
    if (dashboard.dashboardTitle !== undefined) loaded.add('dashboard_title');
    if (dashboard.slug !== undefined) loaded.add('slug');
    if (dashboard.description !== undefined) loaded.add('description');
    if (dashboard.certifiedBy !== undefined) loaded.add('certified_by');
    if (dashboard.certificationDetails !== undefined) {
      loaded.add('certification_details');
    }
    if (dashboard.published !== undefined) loaded.add('published');
    if (dashboard.uuid !== undefined) loaded.add('uuid');
    if (dashboard.url !== undefined) loaded.add('url');
    if (dashboard.changedOn !== undefined) loaded.add('changed_on');
    if (dashboard.changedOnHumanized !== undefined) {
      loaded.add('changed_on_humanized');
    }
  }
  return [...loaded];
}

function requestedChartColumns(request: ChartListRequest): string[] {
  return request.selectColumns.length > 0
    ? request.selectColumns
    : [
        'id',
        'slice_name',
        'viz_type',
        'description',
        'certified_by',
        'certification_details',
        'url',
        'changed_on',
        'changed_on_humanized',
      ];
}

function chartColumnsLoaded(charts: ChartListItem[]): string[] {
  const loaded = new Set<string>(['id']);
  for (const chart of charts) {
    if (chart.sliceName !== undefined) loaded.add('slice_name');
    if (chart.vizType !== undefined) loaded.add('viz_type');
    if (chart.description !== undefined) loaded.add('description');
    if (chart.certifiedBy !== undefined) loaded.add('certified_by');
    if (chart.certificationDetails !== undefined) {
      loaded.add('certification_details');
    }
    if (chart.uuid !== undefined) loaded.add('uuid');
    if (chart.url !== undefined) loaded.add('url');
    if (chart.changedOn !== undefined) loaded.add('changed_on');
    if (chart.changedOnHumanized !== undefined) {
      loaded.add('changed_on_humanized');
    }
  }
  return [...loaded];
}

function requestedDatasetColumns(request: DatasetListRequest): string[] {
  return request.selectColumns.length > 0
    ? request.selectColumns
    : [
        'id',
        'table_name',
        'schema',
        'database_name',
        'database',
        'description',
        'certified_by',
        'certification_details',
        'changed_on',
        'changed_on_humanized',
      ];
}

function requestedDatabaseColumns(request: DatabaseListRequest): string[] {
  return request.selectColumns.length > 0
    ? request.selectColumns
    : [
        'id',
        'uuid',
        'database_name',
        'backend',
        'expose_in_sqllab',
        'allow_file_upload',
        'changed_on',
        'changed_on_humanized',
      ];
}

function datasetColumnsLoaded(datasets: DatasetListItem[]): string[] {
  const loaded = new Set<string>(['id']);
  for (const dataset of datasets) {
    if (dataset.tableName !== undefined) loaded.add('table_name');
    if (dataset.schema !== undefined) loaded.add('schema');
    if (dataset.databaseName !== undefined) {
      loaded.add('database_name');
      loaded.add('database');
    }
    if (dataset.description !== undefined) loaded.add('description');
    if (dataset.certifiedBy !== undefined) loaded.add('certified_by');
    if (dataset.certificationDetails !== undefined) {
      loaded.add('certification_details');
    }
    if (dataset.changedOn !== undefined) loaded.add('changed_on');
    if (dataset.changedOnHumanized !== undefined) {
      loaded.add('changed_on_humanized');
    }
    if (dataset.isVirtual !== undefined) loaded.add('is_virtual');
    if (dataset.databaseId !== undefined) loaded.add('database_id');
    if (dataset.uuid !== undefined) loaded.add('uuid');
    if (dataset.url !== undefined) loaded.add('url');
  }
  return [...loaded];
}

function databaseColumnsLoaded(databases: DatabaseListItem[]): string[] {
  const loaded = new Set<string>(['id']);
  for (const database of databases) {
    if (database.uuid !== undefined) loaded.add('uuid');
    if (database.databaseName !== undefined) loaded.add('database_name');
    if (database.backend !== undefined) loaded.add('backend');
    if (database.exposeInSqllab !== undefined) loaded.add('expose_in_sqllab');
    if (database.allowCtas !== undefined) loaded.add('allow_ctas');
    if (database.allowCvas !== undefined) loaded.add('allow_cvas');
    if (database.allowDml !== undefined) loaded.add('allow_dml');
    if (database.allowFileUpload !== undefined) loaded.add('allow_file_upload');
    if (database.allowRunAsync !== undefined) loaded.add('allow_run_async');
    if (database.cacheTimeout !== undefined) loaded.add('cache_timeout');
    if (database.configurationMethod !== undefined) {
      loaded.add('configuration_method');
    }
    if (database.forceCtasSchema !== undefined) loaded.add('force_ctas_schema');
    if (database.impersonateUser !== undefined) loaded.add('impersonate_user');
    if (database.isManagedExternally !== undefined) {
      loaded.add('is_managed_externally');
    }
    if (database.externalUrl !== undefined) loaded.add('external_url');
    if (database.extra !== undefined) loaded.add('extra');
    if (database.changedOn !== undefined) loaded.add('changed_on');
    if (database.changedOnHumanized !== undefined) {
      loaded.add('changed_on_humanized');
    }
    if (database.createdOn !== undefined) loaded.add('created_on');
    if (database.createdOnHumanized !== undefined) {
      loaded.add('created_on_humanized');
    }
  }
  return [...loaded];
}

function emptyDashboardListResponse(
  request: DashboardListRequest,
  warnings: string[],
): DashboardListResponse {
  return {
    contractVersion: DASHBOARD_LIST_CONTRACT_VERSION,
    dashboards: [],
    count: 0,
    totalCount: 0,
    page: request.page,
    pageSize: request.pageSize,
    totalPages: 0,
    hasNext: false,
    hasPrevious: request.page > 1,
    columnsRequested: requestedDashboardColumns(request),
    columnsLoaded: [],
    warnings,
  };
}

function emptyChartListResponse(
  request: ChartListRequest,
  warnings: string[],
): ChartListResponse {
  return {
    contractVersion: CHART_LIST_CONTRACT_VERSION,
    charts: [],
    count: 0,
    totalCount: 0,
    page: request.page,
    pageSize: request.pageSize,
    totalPages: 0,
    hasNext: false,
    hasPrevious: request.page > 1,
    columnsRequested: requestedChartColumns(request),
    columnsLoaded: [],
    warnings,
  };
}

function emptyDatasetListResponse(
  request: DatasetListRequest,
  warnings: string[],
): DatasetListResponse {
  return {
    contractVersion: DATASET_LIST_CONTRACT_VERSION,
    datasets: [],
    count: 0,
    totalCount: 0,
    page: request.page,
    pageSize: request.pageSize,
    totalPages: 0,
    hasNext: false,
    hasPrevious: request.page > 1,
    columnsRequested: requestedDatasetColumns(request),
    columnsLoaded: [],
    warnings,
  };
}

function emptyDatabaseListResponse(
  request: DatabaseListRequest,
  warnings: string[],
): DatabaseListResponse {
  return {
    contractVersion: DATABASE_LIST_CONTRACT_VERSION,
    databases: [],
    count: 0,
    totalCount: 0,
    page: request.page,
    pageSize: request.pageSize,
    totalPages: 0,
    hasNext: false,
    hasPrevious: request.page > 1,
    columnsRequested: requestedDatabaseColumns(request),
    columnsLoaded: [],
    warnings,
  };
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

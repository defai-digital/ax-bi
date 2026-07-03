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
  ANNOTATION_LIST_CONTRACT_VERSION,
  AnnotationListItem,
  AnnotationListRequest,
  AnnotationListResponse,
} from './contracts/annotationList';
import {
  ANNOTATION_LAYER_LIST_CONTRACT_VERSION,
  AnnotationLayerListItem,
  AnnotationLayerListRequest,
  AnnotationLayerListResponse,
} from './contracts/annotationLayerList';
import {
  ASSET_SEARCH_CONTRACT_VERSION,
  AssetSearchRequest,
  AssetSearchResponse,
  AssetSearchResult,
  AssetType,
} from './contracts/assetSearch';
import {
  CHART_LIST_CONTRACT_VERSION,
  ChartListItem,
  ChartListRequest,
  ChartListResponse,
} from './contracts/chartList';
import {
  DASHBOARD_LIST_CONTRACT_VERSION,
  DashboardListItem,
  DashboardListRequest,
  DashboardListResponse,
} from './contracts/dashboardList';
import {
  DATABASE_LIST_CONTRACT_VERSION,
  DatabaseListItem,
  DatabaseListRequest,
  DatabaseListResponse,
} from './contracts/databaseList';
import {
  DATASET_LIST_CONTRACT_VERSION,
  DatasetListItem,
  DatasetListRequest,
  DatasetListResponse,
} from './contracts/datasetList';
import {
  QUERY_LIST_CONTRACT_VERSION,
  QueryListItem,
  QueryListRequest,
  QueryListResponse,
} from './contracts/queryList';
import {
  AUTHORIZATION_CONTRACT_VERSION,
  PermissionCheckRequest,
  PermissionCheckResult,
} from './contracts/authorization';
import {
  REPORT_LIST_CONTRACT_VERSION,
  ReportListItem,
  ReportListRequest,
  ReportListResponse,
} from './contracts/reportList';
import {
  ROLE_LIST_CONTRACT_VERSION,
  RoleListItem,
  RoleListRequest,
  RoleListResponse,
} from './contracts/roleList';
import {
  RLS_LIST_CONTRACT_VERSION,
  RlsListItem,
  RlsListRequest,
  RlsListResponse,
  RlsRoleRef,
  RlsTableRef,
} from './contracts/rlsList';
import {
  SAVED_QUERY_LIST_CONTRACT_VERSION,
  SavedQueryListItem,
  SavedQueryListRequest,
  SavedQueryListResponse,
} from './contracts/savedQueryList';
import {
  TAG_LIST_CONTRACT_VERSION,
  TagListItem,
  TagListRequest,
  TagListResponse,
} from './contracts/tagList';
import {
  TASK_LIST_CONTRACT_VERSION,
  TaskListItem,
  TaskListRequest,
  TaskListResponse,
} from './contracts/taskList';
import { type ListFilter, type ListFilterValue } from './contracts/listColumn';
import { ServiceConfig } from './config';
import { normalizeRequestId } from './requestId';

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

export interface SupersetPermissionClient {
  checkPermission(
    request: PermissionCheckRequest,
    correlationId?: string,
  ): Promise<PermissionCheckResult>;
}

export interface SupersetAnnotationListClient {
  listAnnotations(
    request: AnnotationListRequest,
    correlationId?: string,
  ): Promise<AnnotationListResponse>;
}

export interface SupersetAnnotationLayerListClient {
  listAnnotationLayers(
    request: AnnotationLayerListRequest,
    correlationId?: string,
  ): Promise<AnnotationLayerListResponse>;
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

export interface SupersetQueryListClient {
  listQueries(
    request: QueryListRequest,
    correlationId?: string,
  ): Promise<QueryListResponse>;
}

export interface SupersetReportListClient {
  listReports(
    request: ReportListRequest,
    correlationId?: string,
  ): Promise<ReportListResponse>;
}

export interface SupersetRoleListClient {
  listRoles(
    request: RoleListRequest,
    correlationId?: string,
  ): Promise<RoleListResponse>;
}

export interface SupersetRlsListClient {
  listRlsFilters(
    request: RlsListRequest,
    correlationId?: string,
  ): Promise<RlsListResponse>;
}

export interface SupersetSavedQueryListClient {
  listSavedQueries(
    request: SavedQueryListRequest,
    correlationId?: string,
  ): Promise<SavedQueryListResponse>;
}

export interface SupersetTagListClient {
  listTags(
    request: TagListRequest,
    correlationId?: string,
  ): Promise<TagListResponse>;
}

export interface SupersetTaskListClient {
  listTasks(
    request: TaskListRequest,
    correlationId?: string,
  ): Promise<TaskListResponse>;
}

const MAX_EXTERNAL_MESSAGE_LENGTH = 256;
const MAX_ASSET_TEXT_LENGTH = 256;
const MAX_ASSET_DESCRIPTION_LENGTH = 1024;
const MAX_ASSET_LIST_VALUE_LENGTH = 128;
const MAX_METADATA_KEYS = 100;
const MAX_METADATA_KEY_LENGTH = 128;
const CONTROL_CHARACTER_PATTERN = /[\u0000-\u001f\u007f]/g;

export class SupersetClient
  implements
    SupersetHealthClient,
    SupersetMetadataClient,
    SupersetAnnotationListClient,
    SupersetAnnotationLayerListClient,
    SupersetAssetSearchClient,
    SupersetPermissionClient,
    SupersetDashboardListClient,
    SupersetChartListClient,
    SupersetDatabaseListClient,
    SupersetDatasetListClient,
    SupersetQueryListClient,
    SupersetReportListClient,
    SupersetRoleListClient,
    SupersetRlsListClient,
    SupersetSavedQueryListClient,
    SupersetTagListClient,
    SupersetTaskListClient
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
    const safeCorrelationId = normalizeRequestId(correlationId);

    if (safeCorrelationId !== undefined) {
      headers['x-request-id'] = safeCorrelationId;
    }

    if (contentType !== undefined) {
      headers['content-type'] = contentType;
    }

    if (this.config.supersetInternalToken !== undefined) {
      headers['authorization'] = `Bearer ${this.config.supersetInternalToken}`;
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
        error: externalErrorMessage(error),
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
      if (!isRecord(payload)) {
        return {
          ok: false,
          statusCode: response.status,
          error: 'metadata response must be a JSON object',
          url: this.metadataUrl,
          keyCount: 0,
          keys: [],
        };
      }
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
        error: externalErrorMessage(error),
        url: this.metadataUrl,
      };
    }
  }

  async listAnnotationLayers(
    request: AnnotationLayerListRequest,
    correlationId?: string,
  ): Promise<AnnotationLayerListResponse> {
    if (!hasValidListPagination(request)) {
      return emptyAnnotationLayerListResponse(
        withFallbackListPagination(request),
        ['annotation layer list request contains invalid pagination'],
      );
    }
    if (!hasValidListColumns(request)) {
      return emptyAnnotationLayerListResponse(request, [
        'annotation layer list request contains invalid columns',
      ]);
    }
    if (!hasValidListOrdering(request)) {
      return emptyAnnotationLayerListResponse(request, [
        'annotation layer list request contains invalid ordering',
      ]);
    }
    if (!hasValidListFilters(request)) {
      return emptyAnnotationLayerListResponse(request, [
        'annotation layer list request contains invalid filters',
      ]);
    }
    if (
      !hasExpectedContractVersion(
        request,
        ANNOTATION_LAYER_LIST_CONTRACT_VERSION,
      )
    ) {
      return emptyAnnotationLayerListResponse(request, [
        'annotation layer list request contains invalid contract version',
      ]);
    }

    const url = this.buildAnnotationLayerListUrl(request);

    try {
      const response = await fetch(url, {
        headers: this.buildHeaders(correlationId),
        signal: AbortSignal.timeout(this.config.supersetTimeoutMs),
      });

      if (!response.ok) {
        return emptyAnnotationLayerListResponse(request, [
          `annotation layer list returned status ${response.status} from Superset`,
        ]);
      }

      const payload = (await response.json()) as unknown;
      const annotationLayers = extractSupersetResults(payload)
        .map(toAnnotationLayerListItem)
        .filter(isDefined);
      const totalCount = extractSupersetCount(payload, annotationLayers.length);

      return {
        contractVersion: ANNOTATION_LAYER_LIST_CONTRACT_VERSION,
        annotationLayers,
        ...listResponseMetadata(
          request,
          annotationLayers.length,
          totalCount,
          requestedAnnotationLayerColumns(request),
          annotationLayerColumnsLoaded(annotationLayers),
          [],
        ),
      };
    } catch (error) {
      return emptyAnnotationLayerListResponse(request, [
        `annotation layer list failed: ${
          externalErrorMessage(error)
        }`,
      ]);
    }
  }

  async listAnnotations(
    request: AnnotationListRequest,
    correlationId?: string,
  ): Promise<AnnotationListResponse> {
    if (!hasValidAnnotationLayerId(request)) {
      return emptyAnnotationListResponse(
        withFallbackAnnotationLayerId(request),
        ['annotation list request contains invalid layer id'],
      );
    }

    if (!hasValidListPagination(request)) {
      return emptyAnnotationListResponse(withFallbackListPagination(request), [
        'annotation list request contains invalid pagination',
      ]);
    }
    if (!hasValidListColumns(request)) {
      return emptyAnnotationListResponse(request, [
        'annotation list request contains invalid columns',
      ]);
    }
    if (!hasValidListOrdering(request)) {
      return emptyAnnotationListResponse(request, [
        'annotation list request contains invalid ordering',
      ]);
    }
    if (!hasValidListFilters(request)) {
      return emptyAnnotationListResponse(request, [
        'annotation list request contains invalid filters',
      ]);
    }
    if (
      !hasExpectedContractVersion(request, ANNOTATION_LIST_CONTRACT_VERSION)
    ) {
      return emptyAnnotationListResponse(request, [
        'annotation list request contains invalid contract version',
      ]);
    }

    const url = this.buildAnnotationListUrl(request);

    try {
      const response = await fetch(url, {
        headers: this.buildHeaders(correlationId),
        signal: AbortSignal.timeout(this.config.supersetTimeoutMs),
      });

      if (!response.ok) {
        return emptyAnnotationListResponse(request, [
          `annotation list returned status ${response.status} from Superset`,
        ]);
      }

      const payload = (await response.json()) as unknown;
      const annotations = extractSupersetResults(payload)
        .map(item => toAnnotationListItem(item, request.layerId))
        .filter(isDefined);
      const totalCount = extractSupersetCount(payload, annotations.length);

      return {
        contractVersion: ANNOTATION_LIST_CONTRACT_VERSION,
        annotations,
        layerId: request.layerId,
        ...listResponseMetadata(
          request,
          annotations.length,
          totalCount,
          requestedAnnotationColumns(request),
          annotationColumnsLoaded(annotations),
          [],
        ),
      };
    } catch (error) {
      return emptyAnnotationListResponse(request, [
        `annotation list failed: ${
          externalErrorMessage(error)
        }`,
      ]);
    }
  }

  async searchAssets(
    request: AssetSearchRequest,
    correlationId?: string,
  ): Promise<AssetSearchResponse> {
    if (!hasValidAssetSearchRequestShape(request)) {
      return {
        contractVersion: ASSET_SEARCH_CONTRACT_VERSION,
        assets: [],
        warnings: ['asset search request contains invalid request shape'],
      };
    }

    if (!hasValidAssetSearchQuery(request.query)) {
      return {
        contractVersion: ASSET_SEARCH_CONTRACT_VERSION,
        assets: [],
        warnings: ['asset search request contains invalid query'],
      };
    }

    if (!isAssetSearchLimit(request.limit)) {
      return {
        contractVersion: ASSET_SEARCH_CONTRACT_VERSION,
        assets: [],
        warnings: ['asset search request contains invalid limit'],
      };
    }

    const warnings: string[] = [];
    const requestedTypes =
      request.assetTypes.length > 0
        ? request.assetTypes
        : (['chart', 'dashboard', 'dataset'] satisfies AssetType[]);
    const supportedTypes = [
      ...new Set(requestedTypes.filter(isSupportedSearchType)),
    ];

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
    if (!hasValidAuthorizationRequestShape(request)) {
      return {
        contractVersion: AUTHORIZATION_CONTRACT_VERSION,
        allowed: false,
        error: 'authorization request contains invalid request shape',
      };
    }

    if (!hasValidAuthorizationIds(request)) {
      return {
        contractVersion: AUTHORIZATION_CONTRACT_VERSION,
        allowed: false,
        error: 'authorization request contains invalid numeric identifier',
      };
    }

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

      const payload = (await response.json()) as unknown;
      if (
        !isRecord(payload) ||
        payload['contractVersion'] !== AUTHORIZATION_CONTRACT_VERSION
      ) {
        return {
          contractVersion: AUTHORIZATION_CONTRACT_VERSION,
          allowed: false,
          error: 'authorization response contract version mismatch',
          statusCode: response.status,
        };
      }
      if (typeof payload['allowed'] !== 'boolean') {
        return {
          contractVersion: AUTHORIZATION_CONTRACT_VERSION,
          allowed: false,
          error: 'authorization response allowed field must be boolean',
          statusCode: response.status,
        };
      }

      const result: PermissionCheckResult = {
        contractVersion: AUTHORIZATION_CONTRACT_VERSION,
        allowed: payload['allowed'],
        statusCode: response.status,
      };
      const reason = optionalExternalMessage(payload['reason']);
      if (reason !== undefined) {
        result.reason = reason;
      }
      return result;
    } catch (error) {
      return {
        contractVersion: AUTHORIZATION_CONTRACT_VERSION,
        allowed: false,
        error: externalErrorMessage(error),
      };
    }
  }

  async listDashboards(
    request: DashboardListRequest,
    correlationId?: string,
  ): Promise<DashboardListResponse> {
    if (!hasValidListPagination(request)) {
      return emptyDashboardListResponse(withFallbackListPagination(request), [
        'dashboard list request contains invalid pagination',
      ]);
    }
    if (!hasValidListColumns(request)) {
      return emptyDashboardListResponse(request, [
        'dashboard list request contains invalid columns',
      ]);
    }
    if (!hasValidListOrdering(request)) {
      return emptyDashboardListResponse(request, [
        'dashboard list request contains invalid ordering',
      ]);
    }
    if (!hasValidListFilters(request)) {
      return emptyDashboardListResponse(request, [
        'dashboard list request contains invalid filters',
      ]);
    }
    if (!hasExpectedContractVersion(request, DASHBOARD_LIST_CONTRACT_VERSION)) {
      return emptyDashboardListResponse(request, [
        'dashboard list request contains invalid contract version',
      ]);
    }
    if (!hasValidOwnershipFlags(request, true)) {
      return emptyDashboardListResponse(request, [
        'dashboard list request contains invalid ownership flags',
      ]);
    }

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

      return {
        contractVersion: DASHBOARD_LIST_CONTRACT_VERSION,
        dashboards,
        ...listResponseMetadata(
          request,
          dashboards.length,
          totalCount,
          requestedDashboardColumns(request),
          dashboardColumnsLoaded(dashboards),
          [],
        ),
      };
    } catch (error) {
      return emptyDashboardListResponse(request, [
        `dashboard list failed: ${
          externalErrorMessage(error)
        }`,
      ]);
    }
  }

  async listCharts(
    request: ChartListRequest,
    correlationId?: string,
  ): Promise<ChartListResponse> {
    if (!hasValidListPagination(request)) {
      return emptyChartListResponse(withFallbackListPagination(request), [
        'chart list request contains invalid pagination',
      ]);
    }
    if (!hasValidListColumns(request)) {
      return emptyChartListResponse(request, [
        'chart list request contains invalid columns',
      ]);
    }
    if (!hasValidListOrdering(request)) {
      return emptyChartListResponse(request, [
        'chart list request contains invalid ordering',
      ]);
    }
    if (!hasValidListFilters(request)) {
      return emptyChartListResponse(request, [
        'chart list request contains invalid filters',
      ]);
    }
    if (!hasExpectedContractVersion(request, CHART_LIST_CONTRACT_VERSION)) {
      return emptyChartListResponse(request, [
        'chart list request contains invalid contract version',
      ]);
    }
    if (!hasValidOwnershipFlags(request, true)) {
      return emptyChartListResponse(request, [
        'chart list request contains invalid ownership flags',
      ]);
    }

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

      return {
        contractVersion: CHART_LIST_CONTRACT_VERSION,
        charts,
        ...listResponseMetadata(
          request,
          charts.length,
          totalCount,
          requestedChartColumns(request),
          chartColumnsLoaded(charts),
          [],
        ),
      };
    } catch (error) {
      return emptyChartListResponse(request, [
        `chart list failed: ${
          externalErrorMessage(error)
        }`,
      ]);
    }
  }

  async listDatasets(
    request: DatasetListRequest,
    correlationId?: string,
  ): Promise<DatasetListResponse> {
    if (!hasValidListPagination(request)) {
      return emptyDatasetListResponse(withFallbackListPagination(request), [
        'dataset list request contains invalid pagination',
      ]);
    }
    if (!hasValidListColumns(request)) {
      return emptyDatasetListResponse(request, [
        'dataset list request contains invalid columns',
      ]);
    }
    if (!hasValidListOrdering(request)) {
      return emptyDatasetListResponse(request, [
        'dataset list request contains invalid ordering',
      ]);
    }
    if (!hasValidListFilters(request)) {
      return emptyDatasetListResponse(request, [
        'dataset list request contains invalid filters',
      ]);
    }
    if (!hasExpectedContractVersion(request, DATASET_LIST_CONTRACT_VERSION)) {
      return emptyDatasetListResponse(request, [
        'dataset list request contains invalid contract version',
      ]);
    }
    if (!hasValidOwnershipFlags(request, true)) {
      return emptyDatasetListResponse(request, [
        'dataset list request contains invalid ownership flags',
      ]);
    }

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

      return {
        contractVersion: DATASET_LIST_CONTRACT_VERSION,
        datasets,
        ...listResponseMetadata(
          request,
          datasets.length,
          totalCount,
          requestedDatasetColumns(request),
          datasetColumnsLoaded(datasets),
          [],
        ),
      };
    } catch (error) {
      return emptyDatasetListResponse(request, [
        `dataset list failed: ${
          externalErrorMessage(error)
        }`,
      ]);
    }
  }

  async listDatabases(
    request: DatabaseListRequest,
    correlationId?: string,
  ): Promise<DatabaseListResponse> {
    if (!hasValidListPagination(request)) {
      return emptyDatabaseListResponse(withFallbackListPagination(request), [
        'database list request contains invalid pagination',
      ]);
    }
    if (!hasValidListColumns(request)) {
      return emptyDatabaseListResponse(request, [
        'database list request contains invalid columns',
      ]);
    }
    if (!hasValidListOrdering(request)) {
      return emptyDatabaseListResponse(request, [
        'database list request contains invalid ordering',
      ]);
    }
    if (!hasValidListFilters(request)) {
      return emptyDatabaseListResponse(request, [
        'database list request contains invalid filters',
      ]);
    }
    if (!hasExpectedContractVersion(request, DATABASE_LIST_CONTRACT_VERSION)) {
      return emptyDatabaseListResponse(request, [
        'database list request contains invalid contract version',
      ]);
    }
    if (!hasValidOwnershipFlags(request, false)) {
      return emptyDatabaseListResponse(request, [
        'database list request contains invalid ownership flags',
      ]);
    }

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

      return {
        contractVersion: DATABASE_LIST_CONTRACT_VERSION,
        databases,
        ...listResponseMetadata(
          request,
          databases.length,
          totalCount,
          requestedDatabaseColumns(request),
          databaseColumnsLoaded(databases),
          [],
        ),
      };
    } catch (error) {
      return emptyDatabaseListResponse(request, [
        `database list failed: ${
          externalErrorMessage(error)
        }`,
      ]);
    }
  }

  async listQueries(
    request: QueryListRequest,
    correlationId?: string,
  ): Promise<QueryListResponse> {
    if (!hasValidListPagination(request)) {
      return emptyQueryListResponse(withFallbackListPagination(request), [
        'query list request contains invalid pagination',
      ]);
    }
    if (!hasValidListColumns(request)) {
      return emptyQueryListResponse(request, [
        'query list request contains invalid columns',
      ]);
    }
    if (!hasValidListOrdering(request)) {
      return emptyQueryListResponse(request, [
        'query list request contains invalid ordering',
      ]);
    }
    if (!hasValidListFilters(request)) {
      return emptyQueryListResponse(request, [
        'query list request contains invalid filters',
      ]);
    }
    if (!hasExpectedContractVersion(request, QUERY_LIST_CONTRACT_VERSION)) {
      return emptyQueryListResponse(request, [
        'query list request contains invalid contract version',
      ]);
    }

    const url = this.buildQueryListUrl(request);

    try {
      const response = await fetch(url, {
        headers: this.buildHeaders(correlationId),
        signal: AbortSignal.timeout(this.config.supersetTimeoutMs),
      });

      if (!response.ok) {
        return emptyQueryListResponse(request, [
          `query list returned status ${response.status} from Superset`,
        ]);
      }

      const payload = (await response.json()) as unknown;
      const queries = extractSupersetResults(payload)
        .map(toQueryListItem)
        .filter(isDefined);
      const totalCount = extractSupersetCount(payload, queries.length);

      return {
        contractVersion: QUERY_LIST_CONTRACT_VERSION,
        queries,
        ...listResponseMetadata(
          request,
          queries.length,
          totalCount,
          requestedQueryColumns(request),
          queryColumnsLoaded(queries),
          [],
        ),
      };
    } catch (error) {
      return emptyQueryListResponse(request, [
        `query list failed: ${
          externalErrorMessage(error)
        }`,
      ]);
    }
  }

  async listSavedQueries(
    request: SavedQueryListRequest,
    correlationId?: string,
  ): Promise<SavedQueryListResponse> {
    if (!hasValidListPagination(request)) {
      return emptySavedQueryListResponse(withFallbackListPagination(request), [
        'saved query list request contains invalid pagination',
      ]);
    }
    if (!hasValidListColumns(request)) {
      return emptySavedQueryListResponse(request, [
        'saved query list request contains invalid columns',
      ]);
    }
    if (!hasValidListOrdering(request)) {
      return emptySavedQueryListResponse(request, [
        'saved query list request contains invalid ordering',
      ]);
    }
    if (!hasValidListFilters(request)) {
      return emptySavedQueryListResponse(request, [
        'saved query list request contains invalid filters',
      ]);
    }
    if (
      !hasExpectedContractVersion(request, SAVED_QUERY_LIST_CONTRACT_VERSION)
    ) {
      return emptySavedQueryListResponse(request, [
        'saved query list request contains invalid contract version',
      ]);
    }

    const url = this.buildSavedQueryListUrl(request);

    try {
      const response = await fetch(url, {
        headers: this.buildHeaders(correlationId),
        signal: AbortSignal.timeout(this.config.supersetTimeoutMs),
      });

      if (!response.ok) {
        return emptySavedQueryListResponse(request, [
          `saved query list returned status ${response.status} from Superset`,
        ]);
      }

      const payload = (await response.json()) as unknown;
      const savedQueries = extractSupersetResults(payload)
        .map(toSavedQueryListItem)
        .filter(isDefined);
      const totalCount = extractSupersetCount(payload, savedQueries.length);

      return {
        contractVersion: SAVED_QUERY_LIST_CONTRACT_VERSION,
        savedQueries,
        ...listResponseMetadata(
          request,
          savedQueries.length,
          totalCount,
          requestedSavedQueryColumns(request),
          savedQueryColumnsLoaded(savedQueries),
          [],
        ),
      };
    } catch (error) {
      return emptySavedQueryListResponse(request, [
        `saved query list failed: ${
          externalErrorMessage(error)
        }`,
      ]);
    }
  }

  async listReports(
    request: ReportListRequest,
    correlationId?: string,
  ): Promise<ReportListResponse> {
    if (!hasValidListPagination(request)) {
      return emptyReportListResponse(withFallbackListPagination(request), [
        'report list request contains invalid pagination',
      ]);
    }
    if (!hasValidListColumns(request)) {
      return emptyReportListResponse(request, [
        'report list request contains invalid columns',
      ]);
    }
    if (!hasValidListOrdering(request)) {
      return emptyReportListResponse(request, [
        'report list request contains invalid ordering',
      ]);
    }
    if (!hasValidListFilters(request)) {
      return emptyReportListResponse(request, [
        'report list request contains invalid filters',
      ]);
    }
    if (!hasExpectedContractVersion(request, REPORT_LIST_CONTRACT_VERSION)) {
      return emptyReportListResponse(request, [
        'report list request contains invalid contract version',
      ]);
    }

    const url = this.buildReportListUrl(request);

    try {
      const response = await fetch(url, {
        headers: this.buildHeaders(correlationId),
        signal: AbortSignal.timeout(this.config.supersetTimeoutMs),
      });

      if (!response.ok) {
        return emptyReportListResponse(request, [
          `report list returned status ${response.status} from Superset`,
        ]);
      }

      const payload = (await response.json()) as unknown;
      const reports = extractSupersetResults(payload)
        .map(toReportListItem)
        .filter(isDefined);
      const totalCount = extractSupersetCount(payload, reports.length);

      return {
        contractVersion: REPORT_LIST_CONTRACT_VERSION,
        reports,
        ...listResponseMetadata(
          request,
          reports.length,
          totalCount,
          requestedReportColumns(request),
          reportColumnsLoaded(reports),
          [],
        ),
      };
    } catch (error) {
      return emptyReportListResponse(request, [
        `report list failed: ${
          externalErrorMessage(error)
        }`,
      ]);
    }
  }

  async listRoles(
    request: RoleListRequest,
    correlationId?: string,
  ): Promise<RoleListResponse> {
    if (!hasValidListPagination(request)) {
      return emptyRoleListResponse(withFallbackListPagination(request), [
        'role list request contains invalid pagination',
      ]);
    }
    if (!hasValidListColumns(request)) {
      return emptyRoleListResponse(request, [
        'role list request contains invalid columns',
      ]);
    }
    if (!hasValidListOrdering(request)) {
      return emptyRoleListResponse(request, [
        'role list request contains invalid ordering',
      ]);
    }
    if (!hasValidListFilters(request)) {
      return emptyRoleListResponse(request, [
        'role list request contains invalid filters',
      ]);
    }
    if (!hasExpectedContractVersion(request, ROLE_LIST_CONTRACT_VERSION)) {
      return emptyRoleListResponse(request, [
        'role list request contains invalid contract version',
      ]);
    }

    const url = this.buildRoleListUrl(request);

    try {
      const response = await fetch(url, {
        headers: this.buildHeaders(correlationId),
        signal: AbortSignal.timeout(this.config.supersetTimeoutMs),
      });

      if (!response.ok) {
        return emptyRoleListResponse(request, [
          `role list returned status ${response.status} from Superset`,
        ]);
      }

      const payload = (await response.json()) as unknown;
      const roles = extractSupersetResults(payload)
        .map(toRoleListItem)
        .filter(isDefined);
      const totalCount = extractSupersetCount(payload, roles.length);

      return {
        contractVersion: ROLE_LIST_CONTRACT_VERSION,
        roles,
        ...listResponseMetadata(
          request,
          roles.length,
          totalCount,
          requestedRoleColumns(request),
          roleColumnsLoaded(roles),
          [],
        ),
      };
    } catch (error) {
      return emptyRoleListResponse(request, [
        `role list failed: ${
          externalErrorMessage(error)
        }`,
      ]);
    }
  }

  async listRlsFilters(
    request: RlsListRequest,
    correlationId?: string,
  ): Promise<RlsListResponse> {
    if (!hasValidListPagination(request)) {
      return emptyRlsListResponse(withFallbackListPagination(request), [
        'RLS filter list request contains invalid pagination',
      ]);
    }
    if (!hasValidListColumns(request)) {
      return emptyRlsListResponse(request, [
        'RLS filter list request contains invalid columns',
      ]);
    }
    if (!hasValidListOrdering(request)) {
      return emptyRlsListResponse(request, [
        'RLS filter list request contains invalid ordering',
      ]);
    }
    if (!hasValidListFilters(request)) {
      return emptyRlsListResponse(request, [
        'RLS filter list request contains invalid filters',
      ]);
    }
    if (!hasExpectedContractVersion(request, RLS_LIST_CONTRACT_VERSION)) {
      return emptyRlsListResponse(request, [
        'RLS filter list request contains invalid contract version',
      ]);
    }

    const url = this.buildRlsListUrl(request);

    try {
      const response = await fetch(url, {
        headers: this.buildHeaders(correlationId),
        signal: AbortSignal.timeout(this.config.supersetTimeoutMs),
      });

      if (!response.ok) {
        return emptyRlsListResponse(request, [
          `RLS filter list returned status ${response.status} from Superset`,
        ]);
      }

      const payload = (await response.json()) as unknown;
      const rlsFilters = extractSupersetResults(payload)
        .map(toRlsListItem)
        .filter(isDefined);
      const totalCount = extractSupersetCount(payload, rlsFilters.length);

      return {
        contractVersion: RLS_LIST_CONTRACT_VERSION,
        rlsFilters,
        ...listResponseMetadata(
          request,
          rlsFilters.length,
          totalCount,
          requestedRlsColumns(request),
          rlsColumnsLoaded(rlsFilters),
          [],
        ),
      };
    } catch (error) {
      return emptyRlsListResponse(request, [
        `RLS filter list failed: ${
          externalErrorMessage(error)
        }`,
      ]);
    }
  }

  async listTags(
    request: TagListRequest,
    correlationId?: string,
  ): Promise<TagListResponse> {
    if (!hasValidListPagination(request)) {
      return emptyTagListResponse(withFallbackListPagination(request), [
        'tag list request contains invalid pagination',
      ]);
    }
    if (!hasValidListColumns(request)) {
      return emptyTagListResponse(request, [
        'tag list request contains invalid columns',
      ]);
    }
    if (!hasValidListOrdering(request)) {
      return emptyTagListResponse(request, [
        'tag list request contains invalid ordering',
      ]);
    }
    if (!hasValidListFilters(request)) {
      return emptyTagListResponse(request, [
        'tag list request contains invalid filters',
      ]);
    }
    if (!hasExpectedContractVersion(request, TAG_LIST_CONTRACT_VERSION)) {
      return emptyTagListResponse(request, [
        'tag list request contains invalid contract version',
      ]);
    }

    const url = this.buildTagListUrl(request);

    try {
      const response = await fetch(url, {
        headers: this.buildHeaders(correlationId),
        signal: AbortSignal.timeout(this.config.supersetTimeoutMs),
      });

      if (!response.ok) {
        return emptyTagListResponse(request, [
          `tag list returned status ${response.status} from Superset`,
        ]);
      }

      const payload = (await response.json()) as unknown;
      const tags = extractSupersetResults(payload)
        .map(toTagListItem)
        .filter(isDefined);
      const totalCount = extractSupersetCount(payload, tags.length);

      return {
        contractVersion: TAG_LIST_CONTRACT_VERSION,
        tags,
        ...listResponseMetadata(
          request,
          tags.length,
          totalCount,
          requestedTagColumns(request),
          tagColumnsLoaded(tags),
          [],
        ),
      };
    } catch (error) {
      return emptyTagListResponse(request, [
        `tag list failed: ${
          externalErrorMessage(error)
        }`,
      ]);
    }
  }

  async listTasks(
    request: TaskListRequest,
    correlationId?: string,
  ): Promise<TaskListResponse> {
    if (!hasValidListPagination(request)) {
      return emptyTaskListResponse(withFallbackListPagination(request), [
        'task list request contains invalid pagination',
      ]);
    }
    if (!hasValidListColumns(request)) {
      return emptyTaskListResponse(request, [
        'task list request contains invalid columns',
      ]);
    }
    if (!hasValidListOrdering(request)) {
      return emptyTaskListResponse(request, [
        'task list request contains invalid ordering',
      ]);
    }
    if (!hasValidListFilters(request)) {
      return emptyTaskListResponse(request, [
        'task list request contains invalid filters',
      ]);
    }
    if (!hasExpectedContractVersion(request, TASK_LIST_CONTRACT_VERSION)) {
      return emptyTaskListResponse(request, [
        'task list request contains invalid contract version',
      ]);
    }

    const url = this.buildTaskListUrl(request);

    try {
      const response = await fetch(url, {
        headers: this.buildHeaders(correlationId),
        signal: AbortSignal.timeout(this.config.supersetTimeoutMs),
      });

      if (!response.ok) {
        return emptyTaskListResponse(request, [
          `task list returned status ${response.status} from Superset`,
        ]);
      }

      const payload = (await response.json()) as unknown;
      const tasks = extractSupersetResults(payload)
        .map(toTaskListItem)
        .filter(isDefined);
      const totalCount = extractSupersetCount(payload, tasks.length);

      return {
        contractVersion: TASK_LIST_CONTRACT_VERSION,
        tasks,
        ...listResponseMetadata(
          request,
          tasks.length,
          totalCount,
          requestedTaskColumns(request),
          taskColumnsLoaded(tasks),
          [],
        ),
      };
    } catch (error) {
      return emptyTaskListResponse(request, [
        `task list failed: ${
          externalErrorMessage(error)
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
            externalErrorMessage(error)
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
    return this.buildSupersetQueryUrl(path, query);
  }

  private buildAnnotationLayerListUrl(
    request: AnnotationLayerListRequest,
  ): string {
    return this.buildSupersetQueryUrl(
      this.config.supersetAssetSearchPaths.annotationLayer,
      buildAnnotationLayerListQuery(request),
    );
  }

  private buildAnnotationListUrl(request: AnnotationListRequest): string {
    const basePath = this.config.supersetAssetSearchPaths.annotationLayer.replace(
      /\/$/,
      '',
    );
    return this.buildSupersetQueryUrl(
      `${basePath}/${request.layerId}/annotation/`,
      buildAnnotationListQuery(request),
    );
  }

  private buildDashboardListUrl(request: DashboardListRequest): string {
    return this.buildSupersetQueryUrl(
      this.config.supersetAssetSearchPaths.dashboard,
      buildDashboardListQuery(request),
    );
  }

  private buildChartListUrl(request: ChartListRequest): string {
    return this.buildSupersetQueryUrl(
      this.config.supersetAssetSearchPaths.chart,
      buildChartListQuery(request),
    );
  }

  private buildDatasetListUrl(request: DatasetListRequest): string {
    return this.buildSupersetQueryUrl(
      this.config.supersetAssetSearchPaths.dataset,
      buildDatasetListQuery(request),
    );
  }

  private buildDatabaseListUrl(request: DatabaseListRequest): string {
    return this.buildSupersetQueryUrl(
      this.config.supersetAssetSearchPaths.database,
      buildDatabaseListQuery(request),
    );
  }

  private buildQueryListUrl(request: QueryListRequest): string {
    return this.buildSupersetQueryUrl(
      this.config.supersetAssetSearchPaths.query,
      buildQueryListQuery(request),
    );
  }

  private buildSavedQueryListUrl(request: SavedQueryListRequest): string {
    return this.buildSupersetQueryUrl(
      this.config.supersetAssetSearchPaths.savedQuery,
      buildSavedQueryListQuery(request),
    );
  }

  private buildReportListUrl(request: ReportListRequest): string {
    return this.buildSupersetQueryUrl(
      this.config.supersetAssetSearchPaths.report,
      buildReportListQuery(request),
    );
  }

  private buildRoleListUrl(request: RoleListRequest): string {
    return this.buildSupersetQueryUrl(
      this.config.supersetAssetSearchPaths.role,
      buildRoleListQuery(request),
    );
  }

  private buildRlsListUrl(request: RlsListRequest): string {
    return this.buildSupersetQueryUrl(
      this.config.supersetAssetSearchPaths.rls,
      buildRlsListQuery(request),
    );
  }

  private buildTagListUrl(request: TagListRequest): string {
    return this.buildSupersetQueryUrl(
      this.config.supersetAssetSearchPaths.tag,
      buildTagListQuery(request),
    );
  }

  private buildTaskListUrl(request: TaskListRequest): string {
    return this.buildSupersetQueryUrl(
      this.config.supersetAssetSearchPaths.task,
      buildTaskListQuery(request),
    );
  }

  private buildSupersetQueryUrl(path: string, query: string): string {
    const url = new URL(`${this.config.supersetBaseUrl}${path}`);
    url.searchParams.set('q', query);
    return url.toString();
  }
}

function extractObjectKeys(payload: unknown): string[] {
  if (payload === null || typeof payload !== 'object' || Array.isArray(payload)) {
    return [];
  }

  return [
    ...new Set(
      Object.keys(payload)
        .map(key => cleanMetadataKey(key))
        .filter((key): key is string => key !== undefined),
    ),
  ]
    .sort()
    .slice(0, MAX_METADATA_KEYS);
}

type SearchableAssetType = Exclude<AssetType, 'metric'>;

interface ListPaginationRequest {
  page: number;
  pageSize: number;
}

interface ListResponseMetadata {
  count: number;
  totalCount: number;
  page: number;
  pageSize: number;
  totalPages: number;
  hasNext: boolean;
  hasPrevious: boolean;
  columnsRequested: string[];
  columnsLoaded: string[];
  warnings: string[];
}

interface ListOrderingRequest {
  orderColumn?: unknown;
  orderDirection: unknown;
}

interface ListFilterRequest {
  filters: unknown;
}

interface ListColumnRequest {
  selectColumns?: unknown;
}

interface SupersetListItem {
  id?: number;
  uuid?: string;
  name?: string;
  descr?: string;
  short_descr?: string;
  long_descr?: string;
  start_dttm?: string;
  end_dttm?: string;
  json_metadata?: string;
  layer_id?: number;
  table_name?: string;
  schema?: string;
  database_name?: string;
  database?: {
    id?: number;
    database_name?: string;
  };
  user?: {
    id?: number;
    first_name?: string;
    last_name?: string;
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
  label?: string;
  sql?: string;
  executed_sql?: string;
  db_id?: number;
  catalog?: string;
  tab_name?: string;
  start_time?: number;
  end_time?: number;
  rows?: number;
  error_message?: string;
  client_id?: string;
  limit?: number;
  progress?: number;
  user_id?: number;
  last_run?: string;
  task_type?: string;
  task_key?: string;
  task_name?: string;
  scope?: string;
  status?: string;
  active?: boolean;
  crontab?: string;
  dashboard_id?: number;
  chart_id?: number;
  last_eval_dttm?: string;
  last_eval_dttm_humanized?: string;
  last_state?: string;
  creation_method?: string;
  created_on?: string;
  created_on_humanized?: string;
  owners?: unknown[];
  tags?: unknown[];
  filter_type?: string;
  tables?: unknown[];
  roles?: unknown[];
  clause?: string;
  group_key?: string;
  changed_on_delta_humanized?: string;
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

function buildAnnotationLayerListQuery(
  request: AnnotationLayerListRequest,
): string {
  const filters = [...request.filters];
  if (request.search !== undefined && request.search !== '') {
    filters.push({
      col: 'name',
      opr: 'ct',
      value: request.search,
    });
  }

  const parts = [
    `page:${request.page - 1}`,
    `page_size:${request.pageSize}`,
    `filters:!(${filters.map(formatListFilter).join(',')})`,
  ];

  if (request.orderColumn !== undefined && request.orderColumn !== '') {
    parts.push(`order_column:${request.orderColumn}`);
    parts.push(`order_direction:${request.orderDirection}`);
  }

  return `(${parts.join(',')})`;
}

function buildAnnotationListQuery(request: AnnotationListRequest): string {
  const filters = [...request.filters];
  if (request.search !== undefined && request.search !== '') {
    filters.push({
      col: 'short_descr',
      opr: 'ct',
      value: request.search,
    });
  }

  const parts = [
    `page:${request.page - 1}`,
    `page_size:${request.pageSize}`,
    `filters:!(${filters.map(formatListFilter).join(',')})`,
  ];

  if (request.orderColumn !== undefined && request.orderColumn !== '') {
    parts.push(`order_column:${request.orderColumn}`);
    parts.push(`order_direction:${request.orderDirection}`);
  }

  return `(${parts.join(',')})`;
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
    `filters:!(${filters.map(formatListFilter).join(',')})`,
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
    `filters:!(${filters.map(formatListFilter).join(',')})`,
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
    `filters:!(${filters.map(formatListFilter).join(',')})`,
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
    `filters:!(${filters.map(formatListFilter).join(',')})`,
  ];

  if (request.orderColumn !== undefined && request.orderColumn !== '') {
    parts.push(`order_column:${request.orderColumn}`);
    parts.push(`order_direction:${request.orderDirection}`);
  }

  return `(${parts.join(',')})`;
}

function buildQueryListQuery(request: QueryListRequest): string {
  const filters = [...request.filters];
  if (request.search !== undefined && request.search !== '') {
    filters.push({
      col: 'sql',
      opr: 'ct',
      value: request.search,
    });
  }

  const parts = [
    `page:${request.page - 1}`,
    `page_size:${request.pageSize}`,
    `filters:!(${filters.map(formatListFilter).join(',')})`,
  ];

  if (request.orderColumn !== undefined && request.orderColumn !== '') {
    parts.push(`order_column:${request.orderColumn}`);
    parts.push(`order_direction:${request.orderDirection}`);
  }

  return `(${parts.join(',')})`;
}

function buildSavedQueryListQuery(request: SavedQueryListRequest): string {
  const filters = [...request.filters];
  if (request.search !== undefined && request.search !== '') {
    filters.push({
      col: 'label',
      opr: 'ct',
      value: request.search,
    });
  }

  const parts = [
    `page:${request.page - 1}`,
    `page_size:${request.pageSize}`,
    `filters:!(${filters.map(formatListFilter).join(',')})`,
  ];

  if (request.orderColumn !== undefined && request.orderColumn !== '') {
    parts.push(`order_column:${request.orderColumn}`);
    parts.push(`order_direction:${request.orderDirection}`);
  }

  return `(${parts.join(',')})`;
}

function buildReportListQuery(request: ReportListRequest): string {
  const filters = [...request.filters];
  if (request.search !== undefined && request.search !== '') {
    filters.push({
      col: 'name',
      opr: 'ct',
      value: request.search,
    });
  }

  const parts = [
    `page:${request.page - 1}`,
    `page_size:${request.pageSize}`,
    `filters:!(${filters.map(formatListFilter).join(',')})`,
  ];

  if (request.orderColumn !== undefined && request.orderColumn !== '') {
    parts.push(`order_column:${request.orderColumn}`);
    parts.push(`order_direction:${request.orderDirection}`);
  }

  return `(${parts.join(',')})`;
}

function buildRoleListQuery(request: RoleListRequest): string {
  const filters = [...request.filters];
  if (request.search !== undefined && request.search !== '') {
    filters.push({
      col: 'name',
      opr: 'ct',
      value: request.search,
    });
  }

  const parts = [
    `page:${request.page - 1}`,
    `page_size:${request.pageSize}`,
    `filters:!(${filters.map(formatListFilter).join(',')})`,
  ];

  if (request.orderColumn !== undefined && request.orderColumn !== '') {
    parts.push(`order_column:${request.orderColumn}`);
    parts.push(`order_direction:${request.orderDirection}`);
  }

  return `(${parts.join(',')})`;
}

function buildRlsListQuery(request: RlsListRequest): string {
  const filters = [...request.filters];
  if (request.search !== undefined && request.search !== '') {
    filters.push({
      col: 'name',
      opr: 'ct',
      value: request.search,
    });
  }

  const parts = [
    `page:${request.page - 1}`,
    `page_size:${request.pageSize}`,
    `filters:!(${filters.map(formatListFilter).join(',')})`,
  ];

  if (request.orderColumn !== undefined && request.orderColumn !== '') {
    parts.push(`order_column:${request.orderColumn}`);
    parts.push(`order_direction:${request.orderDirection}`);
  }

  return `(${parts.join(',')})`;
}

function buildTagListQuery(request: TagListRequest): string {
  const filters = [...request.filters];
  if (request.search !== undefined && request.search !== '') {
    filters.push({
      col: 'name',
      opr: 'ct',
      value: request.search,
    });
  }

  const parts = [
    `page:${request.page - 1}`,
    `page_size:${request.pageSize}`,
    `filters:!(${filters.map(formatListFilter).join(',')})`,
  ];

  if (request.orderColumn !== undefined && request.orderColumn !== '') {
    parts.push(`order_column:${request.orderColumn}`);
    parts.push(`order_direction:${request.orderDirection}`);
  }

  return `(${parts.join(',')})`;
}

function buildTaskListQuery(request: TaskListRequest): string {
  const filters = [...request.filters];
  if (request.search !== undefined && request.search !== '') {
    filters.push({
      col: 'task_name',
      opr: 'ct',
      value: request.search,
    });
  }

  const parts = [
    `page:${request.page - 1}`,
    `page_size:${request.pageSize}`,
    `filters:!(${filters.map(formatListFilter).join(',')})`,
  ];

  if (request.orderColumn !== undefined && request.orderColumn !== '') {
    parts.push(`order_column:${request.orderColumn}`);
    parts.push(`order_direction:${request.orderDirection}`);
  }

  return `(${parts.join(',')})`;
}

function formatListFilter(filter: ListFilter): string {
  return `(col:${filter.col},opr:${filter.opr},value:${formatRisonValue(
    filter.value,
  )})`;
}

function formatRisonValue(value: ListFilterValue): string {
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
  if (!isRecord(payload) || !Array.isArray(payload['result'])) {
    throw new Error('Superset list response must include a result array');
  }

  return payload['result']
    .filter(isRecord)
    .map(item => item as SupersetListItem);
}

function extractSupersetCount(payload: unknown, fallback: number): number {
  if (
    !isRecord(payload) ||
    typeof payload['count'] !== 'number' ||
    !Number.isSafeInteger(payload['count']) ||
    payload['count'] < fallback
  ) {
    return fallback;
  }
  return payload['count'];
}

function toDashboardListItem(
  item: SupersetListItem,
): DashboardListItem | undefined {
  if (!isSupersetId(item.id)) {
    return undefined;
  }

  return omitUndefined<DashboardListItem>({
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
  });
}

function toChartListItem(item: SupersetListItem): ChartListItem | undefined {
  if (!isSupersetId(item.id)) {
    return undefined;
  }

  return omitUndefined<ChartListItem>({
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
  });
}

function toDatasetListItem(item: SupersetListItem): DatasetListItem | undefined {
  if (!isSupersetId(item.id)) {
    return undefined;
  }

  return omitUndefined<DatasetListItem>({
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
      isSupersetId(item.database_id)
        ? item.database_id
        : isSupersetId(item.database?.id)
          ? item.database.id
          : undefined,
    uuid: typeof item.uuid === 'string' ? item.uuid : undefined,
    url: typeof item.url === 'string' ? item.url : undefined,
  });
}

function toDatabaseListItem(item: SupersetListItem): DatabaseListItem | undefined {
  if (!isSupersetId(item.id)) {
    return undefined;
  }

  return omitUndefined<DatabaseListItem>({
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
    cacheTimeout: isCacheTimeout(item.cache_timeout)
      ? item.cache_timeout
      : undefined,
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
  });
}

function toSavedQueryListItem(
  item: SupersetListItem,
): SavedQueryListItem | undefined {
  if (!isSupersetId(item.id)) {
    return undefined;
  }

  return omitUndefined<SavedQueryListItem>({
    id: item.id,
    uuid: typeof item.uuid === 'string' ? item.uuid : undefined,
    label: typeof item.label === 'string' ? item.label : undefined,
    sql: typeof item.sql === 'string' ? item.sql : undefined,
    dbId: isSupersetId(item.db_id) ? item.db_id : undefined,
    schema: typeof item.schema === 'string' ? item.schema : undefined,
    catalog: typeof item.catalog === 'string' ? item.catalog : undefined,
    description:
      typeof item.description === 'string' ? item.description : undefined,
    changedOn: typeof item.changed_on === 'string' ? item.changed_on : undefined,
    createdOn: typeof item.created_on === 'string' ? item.created_on : undefined,
    lastRun: typeof item.last_run === 'string' ? item.last_run : undefined,
  });
}

function toAnnotationLayerListItem(
  item: SupersetListItem,
): AnnotationLayerListItem | undefined {
  if (!isSupersetId(item.id)) {
    return undefined;
  }

  return omitUndefined<AnnotationLayerListItem>({
    id: item.id,
    name: typeof item.name === 'string' ? item.name : undefined,
    descr: typeof item.descr === 'string' ? item.descr : undefined,
    changedOn: typeof item.changed_on === 'string' ? item.changed_on : undefined,
    createdOn: typeof item.created_on === 'string' ? item.created_on : undefined,
  });
}

function toAnnotationListItem(
  item: SupersetListItem,
  fallbackLayerId: number,
): AnnotationListItem | undefined {
  if (!isSupersetId(item.id)) {
    return undefined;
  }

  return omitUndefined<AnnotationListItem>({
    id: item.id,
    shortDescr:
      typeof item.short_descr === 'string' ? item.short_descr : undefined,
    longDescr: typeof item.long_descr === 'string' ? item.long_descr : undefined,
    startDttm: typeof item.start_dttm === 'string' ? item.start_dttm : undefined,
    endDttm: typeof item.end_dttm === 'string' ? item.end_dttm : undefined,
    jsonMetadata:
      typeof item.json_metadata === 'string' ? item.json_metadata : undefined,
    layerId: isSupersetId(item.layer_id) ? item.layer_id : fallbackLayerId,
  });
}

function toQueryListItem(item: SupersetListItem): QueryListItem | undefined {
  if (!isSupersetId(item.id)) {
    return undefined;
  }

  return omitUndefined<QueryListItem>({
    id: item.id,
    sql: typeof item.sql === 'string' ? item.sql : undefined,
    executedSql:
      typeof item.executed_sql === 'string' ? item.executed_sql : undefined,
    status: typeof item.status === 'string' ? item.status : undefined,
    startTime: isNonNegativeFiniteNumber(item.start_time)
      ? item.start_time
      : undefined,
    endTime: isNonNegativeFiniteNumber(item.end_time)
      ? item.end_time
      : undefined,
    rows: isNonNegativeInteger(item.rows) ? item.rows : undefined,
    databaseId:
      isSupersetId(item.database_id)
        ? item.database_id
        : isSupersetId(item.database?.id)
          ? item.database.id
          : undefined,
    schema: typeof item.schema === 'string' ? item.schema : undefined,
    catalog: typeof item.catalog === 'string' ? item.catalog : undefined,
    tabName: typeof item.tab_name === 'string' ? item.tab_name : undefined,
    errorMessage:
      typeof item.error_message === 'string' ? item.error_message : undefined,
    clientId: typeof item.client_id === 'string' ? item.client_id : undefined,
    limit: isNonNegativeInteger(item.limit) ? item.limit : undefined,
    progress: isNonNegativeFiniteNumber(item.progress)
      ? item.progress
      : undefined,
    changedOn: typeof item.changed_on === 'string' ? item.changed_on : undefined,
    userId: isSupersetId(item.user_id)
      ? item.user_id
      : isSupersetId(item.user?.id)
        ? item.user.id
        : undefined,
  });
}

function toReportListItem(item: SupersetListItem): ReportListItem | undefined {
  if (!isSupersetId(item.id)) {
    return undefined;
  }

  return omitUndefined<ReportListItem>({
    id: item.id,
    name: typeof item.name === 'string' ? item.name : undefined,
    description:
      typeof item.description === 'string' ? item.description : undefined,
    type: typeof item.type === 'string' ? item.type : undefined,
    active: typeof item.active === 'boolean' ? item.active : undefined,
    crontab: typeof item.crontab === 'string' ? item.crontab : undefined,
    dashboardId:
      isSupersetId(item.dashboard_id) ? item.dashboard_id : undefined,
    chartId: isSupersetId(item.chart_id) ? item.chart_id : undefined,
    lastEvalDttm:
      typeof item.last_eval_dttm === 'string' ? item.last_eval_dttm : undefined,
    lastEvalDttmHumanized:
      typeof item.last_eval_dttm_humanized === 'string'
        ? item.last_eval_dttm_humanized
        : undefined,
    lastState:
      typeof item.last_state === 'string' ? item.last_state : undefined,
    creationMethod:
      typeof item.creation_method === 'string'
        ? item.creation_method
        : undefined,
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
  });
}

function toRoleListItem(item: SupersetListItem): RoleListItem | undefined {
  if (!isSupersetId(item.id)) {
    return undefined;
  }

  return omitUndefined<RoleListItem>({
    id: item.id,
    name: typeof item.name === 'string' ? item.name : undefined,
  });
}

function toRlsListItem(item: SupersetListItem): RlsListItem | undefined {
  if (!isSupersetId(item.id)) {
    return undefined;
  }

  return omitUndefined<RlsListItem>({
    id: item.id,
    name: typeof item.name === 'string' ? item.name : undefined,
    filterType:
      typeof item.filter_type === 'string' ? item.filter_type : undefined,
    tables: mapRlsRefs(item.tables, toRlsTableRef),
    roles: mapRlsRefs(item.roles, toRlsRoleRef),
    clause: typeof item.clause === 'string' ? item.clause : undefined,
    groupKey: typeof item.group_key === 'string' ? item.group_key : undefined,
    changedOn:
      typeof item.changed_on === 'string'
        ? item.changed_on
        : typeof item.changed_on_delta_humanized === 'string'
          ? item.changed_on_delta_humanized
          : undefined,
  });
}

function mapRlsRefs<T>(
  value: unknown,
  mapper: (value: unknown) => T | undefined,
): T[] | undefined {
  if (!Array.isArray(value)) {
    return undefined;
  }

  return value.map(mapper).filter(isDefined);
}

function toRlsTableRef(value: unknown): RlsTableRef | undefined {
  if (!isRecord(value)) {
    return undefined;
  }

  const ref: RlsTableRef = {};
  if (isSupersetId(value['id'])) {
    ref.id = value['id'];
  }
  if (typeof value['table_name'] === 'string') {
    ref.tableName = value['table_name'];
  }
  return Object.keys(ref).length > 0 ? ref : undefined;
}

function toRlsRoleRef(value: unknown): RlsRoleRef | undefined {
  if (!isRecord(value)) {
    return undefined;
  }

  const ref: RlsRoleRef = {};
  if (isSupersetId(value['id'])) {
    ref.id = value['id'];
  }
  if (typeof value['name'] === 'string') {
    ref.name = value['name'];
  }
  return Object.keys(ref).length > 0 ? ref : undefined;
}

function toTagListItem(item: SupersetListItem): TagListItem | undefined {
  if (!isSupersetId(item.id)) {
    return undefined;
  }

  return omitUndefined<TagListItem>({
    id: item.id,
    name: typeof item.name === 'string' ? item.name : undefined,
    type: typeof item.type === 'string' ? item.type : undefined,
    description:
      typeof item.description === 'string' ? item.description : undefined,
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
  });
}

function toTaskListItem(item: SupersetListItem): TaskListItem | undefined {
  if (!isSupersetId(item.id)) {
    return undefined;
  }

  return omitUndefined<TaskListItem>({
    id: item.id,
    uuid: typeof item.uuid === 'string' ? item.uuid : undefined,
    taskType: typeof item.task_type === 'string' ? item.task_type : undefined,
    taskKey: typeof item.task_key === 'string' ? item.task_key : undefined,
    taskName: typeof item.task_name === 'string' ? item.task_name : undefined,
    status: typeof item.status === 'string' ? item.status : undefined,
    scope: typeof item.scope === 'string' ? item.scope : undefined,
    changedOn: typeof item.changed_on === 'string' ? item.changed_on : undefined,
    createdOn: typeof item.created_on === 'string' ? item.created_on : undefined,
  });
}

function omitUndefined<T extends object>(
  value: Record<string, unknown>,
): T {
  return Object.fromEntries(
    Object.entries(value).filter(([, entry]) => entry !== undefined),
  ) as T;
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
  return requestedColumnsOrDefault(request, [
    'id',
    'dashboard_title',
    'slug',
    'description',
    'certified_by',
    'certification_details',
    'url',
    'changed_on',
    'changed_on_humanized',
  ]);
}

function requestedAnnotationLayerColumns(
  request: AnnotationLayerListRequest,
): string[] {
  return requestedColumnsOrDefault(request, ['id', 'name', 'descr']);
}

function requestedAnnotationColumns(request: AnnotationListRequest): string[] {
  return requestedColumnsOrDefault(request, [
    'id',
    'short_descr',
    'start_dttm',
    'end_dttm',
    'layer_id',
  ]);
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
  return requestedColumnsOrDefault(request, [
    'id',
    'slice_name',
    'viz_type',
    'description',
    'certified_by',
    'certification_details',
    'url',
    'changed_on',
    'changed_on_humanized',
  ]);
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
  return requestedColumnsOrDefault(request, [
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
  ]);
}

function requestedDatabaseColumns(request: DatabaseListRequest): string[] {
  return requestedColumnsOrDefault(request, [
    'id',
    'uuid',
    'database_name',
    'backend',
    'expose_in_sqllab',
    'allow_file_upload',
    'changed_on',
    'changed_on_humanized',
  ]);
}

function requestedQueryColumns(request: QueryListRequest): string[] {
  return requestedColumnsOrDefault(request, [
    'id',
    'status',
    'start_time',
    'database_id',
    'schema',
  ]);
}

function requestedSavedQueryColumns(request: SavedQueryListRequest): string[] {
  return requestedColumnsOrDefault(request, [
    'id',
    'label',
    'db_id',
    'schema',
    'uuid',
  ]);
}

function requestedReportColumns(request: ReportListRequest): string[] {
  return requestedColumnsOrDefault(request, [
    'id',
    'name',
    'type',
    'active',
    'crontab',
  ]);
}

function requestedRoleColumns(request: RoleListRequest): string[] {
  return requestedColumnsOrDefault(request, ['id', 'name']);
}

function requestedRlsColumns(request: RlsListRequest): string[] {
  return requestedColumnsOrDefault(request, [
    'id',
    'name',
    'filter_type',
    'clause',
  ]);
}

function requestedTagColumns(request: TagListRequest): string[] {
  return requestedColumnsOrDefault(request, ['id', 'name', 'type']);
}

function requestedTaskColumns(request: TaskListRequest): string[] {
  return requestedColumnsOrDefault(request, [
    'id',
    'uuid',
    'task_type',
    'status',
    'changed_on',
  ]);
}

function requestedColumnsOrDefault(
  request: ListColumnRequest,
  defaultColumns: string[],
): string[] {
  return isListColumnArray(request.selectColumns) &&
    request.selectColumns.length > 0
    ? request.selectColumns
    : defaultColumns;
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

function queryColumnsLoaded(queries: QueryListItem[]): string[] {
  const loaded = new Set<string>(['id']);
  for (const query of queries) {
    if (query.sql !== undefined) loaded.add('sql');
    if (query.executedSql !== undefined) loaded.add('executed_sql');
    if (query.status !== undefined) loaded.add('status');
    if (query.startTime !== undefined) loaded.add('start_time');
    if (query.endTime !== undefined) loaded.add('end_time');
    if (query.rows !== undefined) loaded.add('rows');
    if (query.databaseId !== undefined) loaded.add('database_id');
    if (query.schema !== undefined) loaded.add('schema');
    if (query.catalog !== undefined) loaded.add('catalog');
    if (query.tabName !== undefined) loaded.add('tab_name');
    if (query.errorMessage !== undefined) loaded.add('error_message');
    if (query.clientId !== undefined) loaded.add('client_id');
    if (query.limit !== undefined) loaded.add('limit');
    if (query.progress !== undefined) loaded.add('progress');
    if (query.changedOn !== undefined) loaded.add('changed_on');
    if (query.userId !== undefined) loaded.add('user_id');
  }
  return [...loaded];
}

function savedQueryColumnsLoaded(savedQueries: SavedQueryListItem[]): string[] {
  const loaded = new Set<string>(['id']);
  for (const savedQuery of savedQueries) {
    if (savedQuery.uuid !== undefined) loaded.add('uuid');
    if (savedQuery.label !== undefined) loaded.add('label');
    if (savedQuery.sql !== undefined) loaded.add('sql');
    if (savedQuery.dbId !== undefined) loaded.add('db_id');
    if (savedQuery.schema !== undefined) loaded.add('schema');
    if (savedQuery.catalog !== undefined) loaded.add('catalog');
    if (savedQuery.description !== undefined) loaded.add('description');
    if (savedQuery.changedOn !== undefined) loaded.add('changed_on');
    if (savedQuery.createdOn !== undefined) loaded.add('created_on');
    if (savedQuery.lastRun !== undefined) loaded.add('last_run');
  }
  return [...loaded];
}

function annotationLayerColumnsLoaded(
  annotationLayers: AnnotationLayerListItem[],
): string[] {
  const loaded = new Set<string>(['id']);
  for (const annotationLayer of annotationLayers) {
    if (annotationLayer.name !== undefined) loaded.add('name');
    if (annotationLayer.descr !== undefined) loaded.add('descr');
    if (annotationLayer.changedOn !== undefined) loaded.add('changed_on');
    if (annotationLayer.createdOn !== undefined) loaded.add('created_on');
  }
  return [...loaded];
}

function annotationColumnsLoaded(annotations: AnnotationListItem[]): string[] {
  const loaded = new Set<string>(['id']);
  for (const annotation of annotations) {
    if (annotation.shortDescr !== undefined) loaded.add('short_descr');
    if (annotation.longDescr !== undefined) loaded.add('long_descr');
    if (annotation.startDttm !== undefined) loaded.add('start_dttm');
    if (annotation.endDttm !== undefined) loaded.add('end_dttm');
    if (annotation.jsonMetadata !== undefined) loaded.add('json_metadata');
    if (annotation.layerId !== undefined) loaded.add('layer_id');
  }
  return [...loaded];
}

function reportColumnsLoaded(reports: ReportListItem[]): string[] {
  const loaded = new Set<string>(['id']);
  for (const report of reports) {
    if (report.name !== undefined) loaded.add('name');
    if (report.description !== undefined) loaded.add('description');
    if (report.type !== undefined) loaded.add('type');
    if (report.active !== undefined) loaded.add('active');
    if (report.crontab !== undefined) loaded.add('crontab');
    if (report.dashboardId !== undefined) loaded.add('dashboard_id');
    if (report.chartId !== undefined) loaded.add('chart_id');
    if (report.lastEvalDttm !== undefined) loaded.add('last_eval_dttm');
    if (report.lastEvalDttmHumanized !== undefined) {
      loaded.add('last_eval_dttm_humanized');
    }
    if (report.lastState !== undefined) loaded.add('last_state');
    if (report.creationMethod !== undefined) loaded.add('creation_method');
    if (report.changedOn !== undefined) loaded.add('changed_on');
    if (report.changedOnHumanized !== undefined) {
      loaded.add('changed_on_humanized');
    }
    if (report.createdOn !== undefined) loaded.add('created_on');
    if (report.createdOnHumanized !== undefined) {
      loaded.add('created_on_humanized');
    }
  }
  return [...loaded];
}

function roleColumnsLoaded(roles: RoleListItem[]): string[] {
  const loaded = new Set<string>(['id']);
  for (const role of roles) {
    if (role.name !== undefined) loaded.add('name');
  }
  return [...loaded];
}

function rlsColumnsLoaded(rlsFilters: RlsListItem[]): string[] {
  const loaded = new Set<string>(['id']);
  for (const rlsFilter of rlsFilters) {
    if (rlsFilter.name !== undefined) loaded.add('name');
    if (rlsFilter.filterType !== undefined) loaded.add('filter_type');
    if (rlsFilter.tables !== undefined) loaded.add('tables');
    if (rlsFilter.roles !== undefined) loaded.add('roles');
    if (rlsFilter.clause !== undefined) loaded.add('clause');
    if (rlsFilter.groupKey !== undefined) loaded.add('group_key');
    if (rlsFilter.changedOn !== undefined) loaded.add('changed_on');
  }
  return [...loaded];
}

function tagColumnsLoaded(tags: TagListItem[]): string[] {
  const loaded = new Set<string>(['id']);
  for (const tag of tags) {
    if (tag.name !== undefined) loaded.add('name');
    if (tag.type !== undefined) loaded.add('type');
    if (tag.description !== undefined) loaded.add('description');
    if (tag.changedOn !== undefined) loaded.add('changed_on');
    if (tag.changedOnHumanized !== undefined) loaded.add('changed_on_humanized');
    if (tag.createdOn !== undefined) loaded.add('created_on');
    if (tag.createdOnHumanized !== undefined) loaded.add('created_on_humanized');
  }
  return [...loaded];
}

function taskColumnsLoaded(tasks: TaskListItem[]): string[] {
  const loaded = new Set<string>(['id']);
  for (const task of tasks) {
    if (task.uuid !== undefined) loaded.add('uuid');
    if (task.taskType !== undefined) loaded.add('task_type');
    if (task.taskKey !== undefined) loaded.add('task_key');
    if (task.taskName !== undefined) loaded.add('task_name');
    if (task.status !== undefined) loaded.add('status');
    if (task.scope !== undefined) loaded.add('scope');
    if (task.changedOn !== undefined) loaded.add('changed_on');
    if (task.createdOn !== undefined) loaded.add('created_on');
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
    ...emptyListResponseMetadata(
      request,
      requestedDashboardColumns(request),
      warnings,
    ),
  };
}

function emptyAnnotationLayerListResponse(
  request: AnnotationLayerListRequest,
  warnings: string[],
): AnnotationLayerListResponse {
  return {
    contractVersion: ANNOTATION_LAYER_LIST_CONTRACT_VERSION,
    annotationLayers: [],
    ...emptyListResponseMetadata(
      request,
      requestedAnnotationLayerColumns(request),
      warnings,
    ),
  };
}

function emptyAnnotationListResponse(
  request: AnnotationListRequest,
  warnings: string[],
): AnnotationListResponse {
  return {
    contractVersion: ANNOTATION_LIST_CONTRACT_VERSION,
    annotations: [],
    layerId: request.layerId,
    ...emptyListResponseMetadata(
      request,
      requestedAnnotationColumns(request),
      warnings,
    ),
  };
}

function emptyChartListResponse(
  request: ChartListRequest,
  warnings: string[],
): ChartListResponse {
  return {
    contractVersion: CHART_LIST_CONTRACT_VERSION,
    charts: [],
    ...emptyListResponseMetadata(
      request,
      requestedChartColumns(request),
      warnings,
    ),
  };
}

function emptyDatasetListResponse(
  request: DatasetListRequest,
  warnings: string[],
): DatasetListResponse {
  return {
    contractVersion: DATASET_LIST_CONTRACT_VERSION,
    datasets: [],
    ...emptyListResponseMetadata(
      request,
      requestedDatasetColumns(request),
      warnings,
    ),
  };
}

function emptyDatabaseListResponse(
  request: DatabaseListRequest,
  warnings: string[],
): DatabaseListResponse {
  return {
    contractVersion: DATABASE_LIST_CONTRACT_VERSION,
    databases: [],
    ...emptyListResponseMetadata(
      request,
      requestedDatabaseColumns(request),
      warnings,
    ),
  };
}

function emptyQueryListResponse(
  request: QueryListRequest,
  warnings: string[],
): QueryListResponse {
  return {
    contractVersion: QUERY_LIST_CONTRACT_VERSION,
    queries: [],
    ...emptyListResponseMetadata(
      request,
      requestedQueryColumns(request),
      warnings,
    ),
  };
}

function emptySavedQueryListResponse(
  request: SavedQueryListRequest,
  warnings: string[],
): SavedQueryListResponse {
  return {
    contractVersion: SAVED_QUERY_LIST_CONTRACT_VERSION,
    savedQueries: [],
    ...emptyListResponseMetadata(
      request,
      requestedSavedQueryColumns(request),
      warnings,
    ),
  };
}

function emptyReportListResponse(
  request: ReportListRequest,
  warnings: string[],
): ReportListResponse {
  return {
    contractVersion: REPORT_LIST_CONTRACT_VERSION,
    reports: [],
    ...emptyListResponseMetadata(
      request,
      requestedReportColumns(request),
      warnings,
    ),
  };
}

function emptyRoleListResponse(
  request: RoleListRequest,
  warnings: string[],
): RoleListResponse {
  return {
    contractVersion: ROLE_LIST_CONTRACT_VERSION,
    roles: [],
    ...emptyListResponseMetadata(
      request,
      requestedRoleColumns(request),
      warnings,
    ),
  };
}

function emptyRlsListResponse(
  request: RlsListRequest,
  warnings: string[],
): RlsListResponse {
  return {
    contractVersion: RLS_LIST_CONTRACT_VERSION,
    rlsFilters: [],
    ...emptyListResponseMetadata(
      request,
      requestedRlsColumns(request),
      warnings,
    ),
  };
}

function emptyTagListResponse(
  request: TagListRequest,
  warnings: string[],
): TagListResponse {
  return {
    contractVersion: TAG_LIST_CONTRACT_VERSION,
    tags: [],
    ...emptyListResponseMetadata(
      request,
      requestedTagColumns(request),
      warnings,
    ),
  };
}

function emptyTaskListResponse(
  request: TaskListRequest,
  warnings: string[],
): TaskListResponse {
  return {
    contractVersion: TASK_LIST_CONTRACT_VERSION,
    tasks: [],
    ...emptyListResponseMetadata(
      request,
      requestedTaskColumns(request),
      warnings,
    ),
  };
}

function emptyListResponseMetadata(
  request: ListPaginationRequest,
  columnsRequested: string[],
  warnings: string[],
): ListResponseMetadata {
  return listResponseMetadata(request, 0, 0, columnsRequested, [], warnings);
}

function listResponseMetadata(
  request: ListPaginationRequest,
  count: number,
  totalCount: number,
  columnsRequested: string[],
  columnsLoaded: string[],
  warnings: string[],
): ListResponseMetadata {
  const totalPages = Math.ceil(totalCount / request.pageSize);

  return {
    count,
    totalCount,
    page: request.page,
    pageSize: request.pageSize,
    totalPages,
    hasNext: request.page < totalPages,
    hasPrevious: request.page > 1,
    columnsRequested,
    columnsLoaded,
    warnings,
  };
}

function toAssetSearchResult(
  assetType: SearchableAssetType,
  item: SupersetListItem,
  query: string,
): AssetSearchResult | undefined {
  if (!isSupersetId(item.id)) {
    return undefined;
  }

  const name = extractAssetName(assetType, item);
  const description = cleanAssetText(
    item.description,
    MAX_ASSET_DESCRIPTION_LENGTH,
  );
  const certified = hasCertification(item.certified_by);

  return {
    assetType,
    id: item.id,
    uuid: cleanAssetText(item.uuid, MAX_ASSET_TEXT_LENGTH),
    name,
    description,
    certified,
    relevanceScore: scoreAsset(name, description, query) + (certified ? 0.2 : 0),
    relevanceReason: cleanAssetText(
      buildRelevanceReason(name, description, query),
      MAX_ASSET_TEXT_LENGTH,
    ),
    owners: extractNameList(item.owners),
    tags: extractNameList(item.tags),
  };
}

function extractAssetName(
  assetType: SearchableAssetType,
  item: SupersetListItem,
): string {
  if (assetType === 'chart' && typeof item.slice_name === 'string') {
    return cleanAssetText(item.slice_name, MAX_ASSET_TEXT_LENGTH);
  }
  if (assetType === 'dashboard' && typeof item.dashboard_title === 'string') {
    return cleanAssetText(item.dashboard_title, MAX_ASSET_TEXT_LENGTH);
  }
  if (assetType === 'dataset' && typeof item.table_name === 'string') {
    return cleanAssetText(item.table_name, MAX_ASSET_TEXT_LENGTH);
  }
  return cleanAssetText(item.name, MAX_ASSET_TEXT_LENGTH);
}

function hasCertification(value: unknown): boolean {
  return typeof value === 'string' && value.trim() !== '';
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

function extractNameList(values: unknown): string[] {
  if (!Array.isArray(values)) {
    return [];
  }

  return values.flatMap(value => {
    const name = extractCleanName(value);
    return name === undefined ? [] : [name];
  });
}

function extractCleanName(value: unknown): string | undefined {
  if (typeof value === 'string') {
    return normalizeName(value);
  }
  if (isRecord(value)) {
    return normalizeName(
      value['name'] ?? value['username'] ?? value['first_name'],
    );
  }
  return undefined;
}

function normalizeName(value: unknown): string | undefined {
  if (!isCleanString(value)) {
    return undefined;
  }
  return cleanAssetText(value, MAX_ASSET_LIST_VALUE_LENGTH);
}

function isDefined<T>(value: T | undefined): value is T {
  return value !== undefined;
}

function isSupersetId(value: unknown): value is number {
  return isNonNegativeInteger(value);
}

function hasValidAuthorizationIds(request: unknown): boolean {
  if (!isRecord(request)) {
    return false;
  }

  const { principal, resource } = request;
  if (!isRecord(principal) || !isRecord(resource)) {
    return false;
  }

  return (
    isOptionalSupersetId(principal['userId']) &&
    isOptionalSupersetId(resource['id'])
  );
}

function hasValidAuthorizationRequestShape(
  request: unknown,
): request is PermissionCheckRequest {
  if (!isRecord(request)) {
    return false;
  }

  const { principal, resource } = request;
  return (
    hasOnlyKeys(request, [
      'contractVersion',
      'principal',
      'resource',
      'action',
    ]) &&
    request['contractVersion'] === AUTHORIZATION_CONTRACT_VERSION &&
    isRecord(principal) &&
    hasOnlyKeys(principal, ['type', 'userId', 'username', 'roles']) &&
    isRecord(resource) &&
    hasOnlyKeys(resource, ['type', 'id', 'uuid']) &&
    isPrincipalType(principal['type']) &&
    isOptionalCleanString(principal['username']) &&
    isOptionalCleanStringArray(principal['roles']) &&
    isResourceType(resource['type']) &&
    isOptionalCleanString(resource['uuid']) &&
    isPermissionAction(request['action'])
  );
}

function isPrincipalType(value: unknown): boolean {
  return value === 'user' || value === 'guest' || value === 'service';
}

function isResourceType(value: unknown): boolean {
  return (
    value === 'chart' ||
    value === 'dashboard' ||
    value === 'database' ||
    value === 'dataset' ||
    value === 'query'
  );
}

function isPermissionAction(value: unknown): boolean {
  return (
    value === 'create' ||
    value === 'delete' ||
    value === 'read' ||
    value === 'write'
  );
}

function hasOnlyKeys(
  value: Record<string, unknown>,
  allowedKeys: readonly string[],
): boolean {
  return Object.keys(value).every(key => allowedKeys.includes(key));
}

function isOptionalSupersetId(value: unknown): boolean {
  return value === undefined || isSupersetId(value);
}

function hasValidListPagination(
  request: unknown,
): request is ListPaginationRequest {
  return (
    isRecord(request) &&
    isPositiveInteger(request['page']) &&
    isListPageSize(request['pageSize'])
  );
}

function withFallbackListPagination<T extends ListPaginationRequest>(
  request: unknown,
): T {
  const record = isRecord(request) ? request : {};
  return {
    ...record,
    page: isPositiveInteger(record['page']) ? record['page'] : 1,
    pageSize: isListPageSize(record['pageSize']) ? record['pageSize'] : 100,
    selectColumns: isListColumnArray(record['selectColumns'])
      ? record['selectColumns']
      : [],
  } as unknown as T;
}

function hasValidListColumns(request: unknown): request is ListColumnRequest {
  return isRecord(request) && isListColumnArray(request['selectColumns']);
}

function hasValidAnnotationLayerId(
  request: unknown,
): request is AnnotationListRequest {
  return isRecord(request) && isPositiveInteger(request['layerId']);
}

function withFallbackAnnotationLayerId(request: unknown): AnnotationListRequest {
  const record = isRecord(request) ? request : {};
  return {
    ...withFallbackListPagination<AnnotationListRequest>(record),
    layerId: isNonNegativeInteger(record['layerId']) ? record['layerId'] : 0,
  } as AnnotationListRequest;
}

function isPositiveInteger(value: unknown): value is number {
  return isInteger(value) && value >= 1;
}

function isListPageSize(value: unknown): value is number {
  return isInteger(value) && value >= 1 && value <= 100;
}

function hasValidListOrdering(request: unknown): request is ListOrderingRequest {
  return (
    isRecord(request) &&
    isListOrderDirection(request['orderDirection']) &&
    isOptionalListOrderColumn(request['orderColumn'])
  );
}

function isListOrderDirection(value: unknown): value is 'asc' | 'desc' {
  return value === 'asc' || value === 'desc';
}

function isOptionalListOrderColumn(value: unknown): boolean {
  return (
    value === undefined ||
    (typeof value === 'string' &&
      (value === '' || isRisonToken(value)))
  );
}

function hasValidListFilters(request: unknown): request is ListFilterRequest {
  return (
    isRecord(request) &&
    Array.isArray(request['filters']) &&
    request['filters'].every(isListFilter) &&
    hasValidListSearch(request)
  );
}

function hasValidListSearch(request: Record<string, unknown>): boolean {
  const search = request['search'];
  return (
    search === undefined ||
    (isRisonScalarString(search) && (search === '' || search.trim() !== ''))
  );
}

function hasValidOwnershipFlags(
  request: unknown,
  requiresOwnedByMe: boolean,
): boolean {
  if (!isRecord(request) || typeof request['createdByMe'] !== 'boolean') {
    return false;
  }
  return (
    !requiresOwnedByMe || typeof request['ownedByMe'] === 'boolean'
  );
}

function hasExpectedContractVersion(
  request: unknown,
  contractVersion: string,
): boolean {
  return isRecord(request) && request['contractVersion'] === contractVersion;
}

function isListFilter(value: unknown): boolean {
  return (
    isRecord(value) &&
    isRisonToken(value['col']) &&
    isRisonToken(value['opr']) &&
    isListFilterValue(value['value'])
  );
}

function isRisonToken(value: unknown): value is string {
  return typeof value === 'string' && /^[A-Za-z0-9_]+$/.test(value);
}

function isListFilterValue(value: unknown): boolean {
  if (Array.isArray(value)) {
    return isHomogeneousListFilterArray(value);
  }
  return isListFilterScalar(value);
}

function isHomogeneousListFilterArray(value: unknown[]): boolean {
  if (value.length === 0) {
    return true;
  }
  if (!isListFilterScalar(value[0])) {
    return false;
  }

  const scalarType = typeof value[0];
  return value.every(
    item => isListFilterScalar(item) && typeof item === scalarType,
  );
}

function isListFilterScalar(value: unknown): boolean {
  return (
    isRisonScalarString(value) ||
    typeof value === 'boolean' ||
    (typeof value === 'number' && Number.isFinite(value))
  );
}

function isRisonScalarString(value: unknown): value is string {
  return typeof value === 'string' && !/[\u0000-\u001f\u007f]/.test(value);
}

function externalErrorMessage(error: unknown): string {
  return externalMessage(
    error instanceof Error ? error.message : String(error),
    'dependency request failed',
  );
}

function optionalExternalMessage(value: unknown): string | undefined {
  if (typeof value !== 'string') {
    return undefined;
  }

  const message = externalMessage(value, '');
  return message === '' ? undefined : message;
}

function externalMessage(value: string, fallback: string): string {
  const message = value
    .replace(CONTROL_CHARACTER_PATTERN, ' ')
    .replace(/\s+/g, ' ')
    .trim();

  if (message.length === 0) {
    return fallback;
  }

  return message.slice(0, MAX_EXTERNAL_MESSAGE_LENGTH);
}

function cleanAssetText(value: unknown, maxLength: number): string {
  if (typeof value !== 'string') {
    return '';
  }

  return value
    .replace(CONTROL_CHARACTER_PATTERN, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .slice(0, maxLength);
}

function cleanMetadataKey(value: string): string | undefined {
  const key = value
    .replace(CONTROL_CHARACTER_PATTERN, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .slice(0, MAX_METADATA_KEY_LENGTH);

  return key.length === 0 ? undefined : key;
}

function isListColumnArray(value: unknown): value is string[] {
  return Array.isArray(value) && value.every(isRisonToken);
}

function isCleanString(value: unknown): value is string {
  return (
    typeof value === 'string' &&
    value.trim() !== '' &&
    !/[\u0000-\u001f\u007f]/.test(value)
  );
}

function isOptionalCleanString(value: unknown): boolean {
  return value === undefined || isCleanString(value);
}

function isOptionalCleanStringArray(value: unknown): boolean {
  return (
    value === undefined ||
    (Array.isArray(value) && value.every(isCleanString))
  );
}

function isAssetSearchLimit(value: unknown): value is number {
  return isInteger(value) && value >= 1 && value <= 100;
}

function hasValidAssetSearchQuery(value: string): boolean {
  return (
    value.length <= MAX_ASSET_TEXT_LENGTH &&
    value.trim() !== '' &&
    isRisonScalarString(value)
  );
}

function hasValidAssetSearchRequestShape(
  request: unknown,
): request is AssetSearchRequest {
  return (
    isRecord(request) &&
    hasOnlyKeys(request, [
      'contractVersion',
      'query',
      'assetTypes',
      'includeCertifiedOnly',
      'limit',
    ]) &&
    request['contractVersion'] === ASSET_SEARCH_CONTRACT_VERSION &&
    typeof request['query'] === 'string' &&
    Array.isArray(request['assetTypes']) &&
    request['assetTypes'].every(isAssetType) &&
    typeof request['includeCertifiedOnly'] === 'boolean'
  );
}

function isAssetType(value: unknown): value is AssetType {
  return (
    value === 'chart' ||
    value === 'dashboard' ||
    value === 'dataset' ||
    value === 'metric'
  );
}

function isCacheTimeout(value: unknown): value is number {
  return isInteger(value) && value >= -1;
}

function isInteger(value: unknown): value is number {
  return typeof value === 'number' && Number.isSafeInteger(value);
}

function isNonNegativeInteger(value: unknown): value is number {
  return isInteger(value) && value >= 0;
}

function isNonNegativeFiniteNumber(value: unknown): value is number {
  return typeof value === 'number' && Number.isFinite(value) && value >= 0;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

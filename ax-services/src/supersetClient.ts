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
  AnnotationFilterValue,
  AnnotationListItem,
  AnnotationListRequest,
  AnnotationListResponse,
} from './contracts/annotationList';
import {
  ANNOTATION_LAYER_LIST_CONTRACT_VERSION,
  AnnotationLayerFilterValue,
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
  QUERY_LIST_CONTRACT_VERSION,
  QueryFilterValue,
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
  ReportFilterValue,
  ReportListItem,
  ReportListRequest,
  ReportListResponse,
} from './contracts/reportList';
import {
  ROLE_LIST_CONTRACT_VERSION,
  RoleFilterValue,
  RoleListItem,
  RoleListRequest,
  RoleListResponse,
} from './contracts/roleList';
import {
  RLS_LIST_CONTRACT_VERSION,
  RlsFilterValue,
  RlsListItem,
  RlsListRequest,
  RlsListResponse,
  RlsRoleRef,
  RlsTableRef,
} from './contracts/rlsList';
import {
  SAVED_QUERY_LIST_CONTRACT_VERSION,
  SavedQueryFilterValue,
  SavedQueryListItem,
  SavedQueryListRequest,
  SavedQueryListResponse,
} from './contracts/savedQueryList';
import {
  TAG_LIST_CONTRACT_VERSION,
  TagFilterValue,
  TagListItem,
  TagListRequest,
  TagListResponse,
} from './contracts/tagList';
import {
  TASK_LIST_CONTRACT_VERSION,
  TaskFilterValue,
  TaskListItem,
  TaskListRequest,
  TaskListResponse,
} from './contracts/taskList';
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

export class SupersetClient
  implements
    SupersetHealthClient,
    SupersetMetadataClient,
    SupersetAnnotationListClient,
    SupersetAnnotationLayerListClient,
    SupersetAssetSearchClient,
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
        error: error instanceof Error ? error.message : String(error),
        url: this.metadataUrl,
      };
    }
  }

  async listAnnotationLayers(
    request: AnnotationLayerListRequest,
    correlationId?: string,
  ): Promise<AnnotationLayerListResponse> {
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
      const totalPages = Math.ceil(totalCount / request.pageSize);

      return {
        contractVersion: ANNOTATION_LAYER_LIST_CONTRACT_VERSION,
        annotationLayers,
        count: annotationLayers.length,
        totalCount,
        page: request.page,
        pageSize: request.pageSize,
        totalPages,
        hasNext: request.page < totalPages,
        hasPrevious: request.page > 1,
        columnsRequested: requestedAnnotationLayerColumns(request),
        columnsLoaded: annotationLayerColumnsLoaded(annotationLayers),
        warnings: [],
      };
    } catch (error) {
      return emptyAnnotationLayerListResponse(request, [
        `annotation layer list failed: ${
          error instanceof Error ? error.message : String(error)
        }`,
      ]);
    }
  }

  async listAnnotations(
    request: AnnotationListRequest,
    correlationId?: string,
  ): Promise<AnnotationListResponse> {
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
      const totalPages = Math.ceil(totalCount / request.pageSize);

      return {
        contractVersion: ANNOTATION_LIST_CONTRACT_VERSION,
        annotations,
        count: annotations.length,
        totalCount,
        page: request.page,
        pageSize: request.pageSize,
        totalPages,
        hasNext: request.page < totalPages,
        hasPrevious: request.page > 1,
        layerId: request.layerId,
        columnsRequested: requestedAnnotationColumns(request),
        columnsLoaded: annotationColumnsLoaded(annotations),
        warnings: [],
      };
    } catch (error) {
      return emptyAnnotationListResponse(request, [
        `annotation list failed: ${
          error instanceof Error ? error.message : String(error)
        }`,
      ]);
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
      if (payload.contractVersion !== AUTHORIZATION_CONTRACT_VERSION) {
        return {
          contractVersion: AUTHORIZATION_CONTRACT_VERSION,
          allowed: false,
          error: 'authorization response contract version mismatch',
          statusCode: response.status,
        };
      }

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

  async listQueries(
    request: QueryListRequest,
    correlationId?: string,
  ): Promise<QueryListResponse> {
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
      const totalPages = Math.ceil(totalCount / request.pageSize);

      return {
        contractVersion: QUERY_LIST_CONTRACT_VERSION,
        queries,
        count: queries.length,
        totalCount,
        page: request.page,
        pageSize: request.pageSize,
        totalPages,
        hasNext: request.page < totalPages,
        hasPrevious: request.page > 1,
        columnsRequested: requestedQueryColumns(request),
        columnsLoaded: queryColumnsLoaded(queries),
        warnings: [],
      };
    } catch (error) {
      return emptyQueryListResponse(request, [
        `query list failed: ${
          error instanceof Error ? error.message : String(error)
        }`,
      ]);
    }
  }

  async listSavedQueries(
    request: SavedQueryListRequest,
    correlationId?: string,
  ): Promise<SavedQueryListResponse> {
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
      const totalPages = Math.ceil(totalCount / request.pageSize);

      return {
        contractVersion: SAVED_QUERY_LIST_CONTRACT_VERSION,
        savedQueries,
        count: savedQueries.length,
        totalCount,
        page: request.page,
        pageSize: request.pageSize,
        totalPages,
        hasNext: request.page < totalPages,
        hasPrevious: request.page > 1,
        columnsRequested: requestedSavedQueryColumns(request),
        columnsLoaded: savedQueryColumnsLoaded(savedQueries),
        warnings: [],
      };
    } catch (error) {
      return emptySavedQueryListResponse(request, [
        `saved query list failed: ${
          error instanceof Error ? error.message : String(error)
        }`,
      ]);
    }
  }

  async listReports(
    request: ReportListRequest,
    correlationId?: string,
  ): Promise<ReportListResponse> {
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
      const totalPages = Math.ceil(totalCount / request.pageSize);

      return {
        contractVersion: REPORT_LIST_CONTRACT_VERSION,
        reports,
        count: reports.length,
        totalCount,
        page: request.page,
        pageSize: request.pageSize,
        totalPages,
        hasNext: request.page < totalPages,
        hasPrevious: request.page > 1,
        columnsRequested: requestedReportColumns(request),
        columnsLoaded: reportColumnsLoaded(reports),
        warnings: [],
      };
    } catch (error) {
      return emptyReportListResponse(request, [
        `report list failed: ${
          error instanceof Error ? error.message : String(error)
        }`,
      ]);
    }
  }

  async listRoles(
    request: RoleListRequest,
    correlationId?: string,
  ): Promise<RoleListResponse> {
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
      const roles = extractSupersetResults(payload).map(toRoleListItem).filter(isDefined);
      const totalCount = extractSupersetCount(payload, roles.length);
      const totalPages = Math.ceil(totalCount / request.pageSize);

      return {
        contractVersion: ROLE_LIST_CONTRACT_VERSION,
        roles,
        count: roles.length,
        totalCount,
        page: request.page,
        pageSize: request.pageSize,
        totalPages,
        hasNext: request.page < totalPages,
        hasPrevious: request.page > 1,
        columnsRequested: requestedRoleColumns(request),
        columnsLoaded: roleColumnsLoaded(roles),
        warnings: [],
      };
    } catch (error) {
      return emptyRoleListResponse(request, [
        `role list failed: ${
          error instanceof Error ? error.message : String(error)
        }`,
      ]);
    }
  }

  async listRlsFilters(
    request: RlsListRequest,
    correlationId?: string,
  ): Promise<RlsListResponse> {
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
      const totalPages = Math.ceil(totalCount / request.pageSize);

      return {
        contractVersion: RLS_LIST_CONTRACT_VERSION,
        rlsFilters,
        count: rlsFilters.length,
        totalCount,
        page: request.page,
        pageSize: request.pageSize,
        totalPages,
        hasNext: request.page < totalPages,
        hasPrevious: request.page > 1,
        columnsRequested: requestedRlsColumns(request),
        columnsLoaded: rlsColumnsLoaded(rlsFilters),
        warnings: [],
      };
    } catch (error) {
      return emptyRlsListResponse(request, [
        `RLS filter list failed: ${
          error instanceof Error ? error.message : String(error)
        }`,
      ]);
    }
  }

  async listTags(
    request: TagListRequest,
    correlationId?: string,
  ): Promise<TagListResponse> {
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
      const tags = extractSupersetResults(payload).map(toTagListItem).filter(isDefined);
      const totalCount = extractSupersetCount(payload, tags.length);
      const totalPages = Math.ceil(totalCount / request.pageSize);

      return {
        contractVersion: TAG_LIST_CONTRACT_VERSION,
        tags,
        count: tags.length,
        totalCount,
        page: request.page,
        pageSize: request.pageSize,
        totalPages,
        hasNext: request.page < totalPages,
        hasPrevious: request.page > 1,
        columnsRequested: requestedTagColumns(request),
        columnsLoaded: tagColumnsLoaded(tags),
        warnings: [],
      };
    } catch (error) {
      return emptyTagListResponse(request, [
        `tag list failed: ${
          error instanceof Error ? error.message : String(error)
        }`,
      ]);
    }
  }

  async listTasks(
    request: TaskListRequest,
    correlationId?: string,
  ): Promise<TaskListResponse> {
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
      const totalPages = Math.ceil(totalCount / request.pageSize);

      return {
        contractVersion: TASK_LIST_CONTRACT_VERSION,
        tasks,
        count: tasks.length,
        totalCount,
        page: request.page,
        pageSize: request.pageSize,
        totalPages,
        hasNext: request.page < totalPages,
        hasPrevious: request.page > 1,
        columnsRequested: requestedTaskColumns(request),
        columnsLoaded: taskColumnsLoaded(tasks),
        warnings: [],
      };
    } catch (error) {
      return emptyTaskListResponse(request, [
        `task list failed: ${
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

  private buildAnnotationLayerListUrl(
    request: AnnotationLayerListRequest,
  ): string {
    const url = new URL(
      `${this.config.supersetBaseUrl}${this.config.supersetAssetSearchPaths.annotationLayer}`,
    );
    url.searchParams.set('q', buildAnnotationLayerListQuery(request));
    return url.toString();
  }

  private buildAnnotationListUrl(request: AnnotationListRequest): string {
    const basePath = this.config.supersetAssetSearchPaths.annotationLayer.replace(
      /\/$/,
      '',
    );
    const url = new URL(
      `${this.config.supersetBaseUrl}${basePath}/${request.layerId}/annotation/`,
    );
    url.searchParams.set('q', buildAnnotationListQuery(request));
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

  private buildQueryListUrl(request: QueryListRequest): string {
    const url = new URL(
      `${this.config.supersetBaseUrl}${this.config.supersetAssetSearchPaths.query}`,
    );
    url.searchParams.set('q', buildQueryListQuery(request));
    return url.toString();
  }

  private buildSavedQueryListUrl(request: SavedQueryListRequest): string {
    const url = new URL(
      `${this.config.supersetBaseUrl}${this.config.supersetAssetSearchPaths.savedQuery}`,
    );
    url.searchParams.set('q', buildSavedQueryListQuery(request));
    return url.toString();
  }

  private buildReportListUrl(request: ReportListRequest): string {
    const url = new URL(
      `${this.config.supersetBaseUrl}${this.config.supersetAssetSearchPaths.report}`,
    );
    url.searchParams.set('q', buildReportListQuery(request));
    return url.toString();
  }

  private buildRoleListUrl(request: RoleListRequest): string {
    const url = new URL(
      `${this.config.supersetBaseUrl}${this.config.supersetAssetSearchPaths.role}`,
    );
    url.searchParams.set('q', buildRoleListQuery(request));
    return url.toString();
  }

  private buildRlsListUrl(request: RlsListRequest): string {
    const url = new URL(
      `${this.config.supersetBaseUrl}${this.config.supersetAssetSearchPaths.rls}`,
    );
    url.searchParams.set('q', buildRlsListQuery(request));
    return url.toString();
  }

  private buildTagListUrl(request: TagListRequest): string {
    const url = new URL(
      `${this.config.supersetBaseUrl}${this.config.supersetAssetSearchPaths.tag}`,
    );
    url.searchParams.set('q', buildTagListQuery(request));
    return url.toString();
  }

  private buildTaskListUrl(request: TaskListRequest): string {
    const url = new URL(
      `${this.config.supersetBaseUrl}${this.config.supersetAssetSearchPaths.task}`,
    );
    url.searchParams.set('q', buildTaskListQuery(request));
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
    `filters:!(${filters.map(formatAnnotationLayerFilter).join(',')})`,
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
    `filters:!(${filters.map(formatAnnotationFilter).join(',')})`,
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
    `filters:!(${filters.map(formatQueryFilter).join(',')})`,
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
    `filters:!(${filters.map(formatSavedQueryFilter).join(',')})`,
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
    `filters:!(${filters.map(formatReportFilter).join(',')})`,
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
    `filters:!(${filters.map(formatRoleFilter).join(',')})`,
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
    `filters:!(${filters.map(formatRlsFilter).join(',')})`,
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
    `filters:!(${filters.map(formatTagFilter).join(',')})`,
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
    `filters:!(${filters.map(formatTaskFilter).join(',')})`,
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

function formatAnnotationLayerFilter(filter: {
  col: string;
  opr: string;
  value: AnnotationLayerFilterValue;
}): string {
  return `(col:${filter.col},opr:${filter.opr},value:${formatAnnotationLayerRisonValue(
    filter.value,
  )})`;
}

function formatAnnotationFilter(filter: {
  col: string;
  opr: string;
  value: AnnotationFilterValue;
}): string {
  return `(col:${filter.col},opr:${filter.opr},value:${formatAnnotationRisonValue(
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

function formatQueryFilter(filter: {
  col: string;
  opr: string;
  value: QueryFilterValue;
}): string {
  return `(col:${filter.col},opr:${filter.opr},value:${formatQueryRisonValue(
    filter.value,
  )})`;
}

function formatSavedQueryFilter(filter: {
  col: string;
  opr: string;
  value: SavedQueryFilterValue;
}): string {
  return `(col:${filter.col},opr:${filter.opr},value:${formatSavedQueryRisonValue(
    filter.value,
  )})`;
}

function formatReportFilter(filter: {
  col: string;
  opr: string;
  value: ReportFilterValue;
}): string {
  return `(col:${filter.col},opr:${filter.opr},value:${formatReportRisonValue(
    filter.value,
  )})`;
}

function formatRoleFilter(filter: {
  col: string;
  opr: string;
  value: RoleFilterValue;
}): string {
  return `(col:${filter.col},opr:${filter.opr},value:${formatRoleRisonValue(
    filter.value,
  )})`;
}

function formatRlsFilter(filter: {
  col: string;
  opr: string;
  value: RlsFilterValue;
}): string {
  return `(col:${filter.col},opr:${filter.opr},value:${formatRlsRisonValue(
    filter.value,
  )})`;
}

function formatTagFilter(filter: {
  col: string;
  opr: string;
  value: TagFilterValue;
}): string {
  return `(col:${filter.col},opr:${filter.opr},value:${formatTagRisonValue(
    filter.value,
  )})`;
}

function formatTaskFilter(filter: {
  col: string;
  opr: string;
  value: TaskFilterValue;
}): string {
  return `(col:${filter.col},opr:${filter.opr},value:${formatTaskRisonValue(
    filter.value,
  )})`;
}

function formatRisonValue(value: DashboardFilterValue): string {
  if (Array.isArray(value)) {
    return `!(${value.map(formatScalarRisonValue).join(',')})`;
  }
  return formatScalarRisonValue(value);
}

function formatAnnotationLayerRisonValue(
  value: AnnotationLayerFilterValue,
): string {
  if (Array.isArray(value)) {
    return `!(${value.map(formatScalarRisonValue).join(',')})`;
  }
  return formatScalarRisonValue(value);
}

function formatAnnotationRisonValue(value: AnnotationFilterValue): string {
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

function formatQueryRisonValue(value: QueryFilterValue): string {
  if (Array.isArray(value)) {
    return `!(${value.map(formatScalarRisonValue).join(',')})`;
  }
  return formatScalarRisonValue(value);
}

function formatSavedQueryRisonValue(value: SavedQueryFilterValue): string {
  if (Array.isArray(value)) {
    return `!(${value.map(formatScalarRisonValue).join(',')})`;
  }
  return formatScalarRisonValue(value);
}

function formatReportRisonValue(value: ReportFilterValue): string {
  if (Array.isArray(value)) {
    return `!(${value.map(formatScalarRisonValue).join(',')})`;
  }
  return formatScalarRisonValue(value);
}

function formatRoleRisonValue(value: RoleFilterValue): string {
  if (Array.isArray(value)) {
    return `!(${value.map(formatScalarRisonValue).join(',')})`;
  }
  return formatScalarRisonValue(value);
}

function formatRlsRisonValue(value: RlsFilterValue): string {
  if (Array.isArray(value)) {
    return `!(${value.map(formatScalarRisonValue).join(',')})`;
  }
  return formatScalarRisonValue(value);
}

function formatTagRisonValue(value: TagFilterValue): string {
  if (Array.isArray(value)) {
    return `!(${value.map(formatScalarRisonValue).join(',')})`;
  }
  return formatScalarRisonValue(value);
}

function formatTaskRisonValue(value: TaskFilterValue): string {
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

function toSavedQueryListItem(
  item: SupersetListItem,
): SavedQueryListItem | undefined {
  if (typeof item.id !== 'number') {
    return undefined;
  }

  return {
    id: item.id,
    uuid: typeof item.uuid === 'string' ? item.uuid : undefined,
    label: typeof item.label === 'string' ? item.label : undefined,
    sql: typeof item.sql === 'string' ? item.sql : undefined,
    dbId: typeof item.db_id === 'number' ? item.db_id : undefined,
    schema: typeof item.schema === 'string' ? item.schema : undefined,
    catalog: typeof item.catalog === 'string' ? item.catalog : undefined,
    description:
      typeof item.description === 'string' ? item.description : undefined,
    changedOn: typeof item.changed_on === 'string' ? item.changed_on : undefined,
    createdOn: typeof item.created_on === 'string' ? item.created_on : undefined,
    lastRun: typeof item.last_run === 'string' ? item.last_run : undefined,
  };
}

function toAnnotationLayerListItem(
  item: SupersetListItem,
): AnnotationLayerListItem | undefined {
  if (typeof item.id !== 'number') {
    return undefined;
  }

  return {
    id: item.id,
    name: typeof item.name === 'string' ? item.name : undefined,
    descr: typeof item.descr === 'string' ? item.descr : undefined,
    changedOn: typeof item.changed_on === 'string' ? item.changed_on : undefined,
    createdOn: typeof item.created_on === 'string' ? item.created_on : undefined,
  };
}

function toAnnotationListItem(
  item: SupersetListItem,
  fallbackLayerId: number,
): AnnotationListItem | undefined {
  if (typeof item.id !== 'number') {
    return undefined;
  }

  return {
    id: item.id,
    shortDescr:
      typeof item.short_descr === 'string' ? item.short_descr : undefined,
    longDescr: typeof item.long_descr === 'string' ? item.long_descr : undefined,
    startDttm: typeof item.start_dttm === 'string' ? item.start_dttm : undefined,
    endDttm: typeof item.end_dttm === 'string' ? item.end_dttm : undefined,
    jsonMetadata:
      typeof item.json_metadata === 'string' ? item.json_metadata : undefined,
    layerId: typeof item.layer_id === 'number' ? item.layer_id : fallbackLayerId,
  };
}

function toQueryListItem(item: SupersetListItem): QueryListItem | undefined {
  if (typeof item.id !== 'number') {
    return undefined;
  }

  return {
    id: item.id,
    sql: typeof item.sql === 'string' ? item.sql : undefined,
    executedSql:
      typeof item.executed_sql === 'string' ? item.executed_sql : undefined,
    status: typeof item.status === 'string' ? item.status : undefined,
    startTime: typeof item.start_time === 'number' ? item.start_time : undefined,
    endTime: typeof item.end_time === 'number' ? item.end_time : undefined,
    rows: typeof item.rows === 'number' ? item.rows : undefined,
    databaseId:
      typeof item.database_id === 'number'
        ? item.database_id
        : item.database?.id,
    schema: typeof item.schema === 'string' ? item.schema : undefined,
    catalog: typeof item.catalog === 'string' ? item.catalog : undefined,
    tabName: typeof item.tab_name === 'string' ? item.tab_name : undefined,
    errorMessage:
      typeof item.error_message === 'string' ? item.error_message : undefined,
    clientId: typeof item.client_id === 'string' ? item.client_id : undefined,
    limit: typeof item.limit === 'number' ? item.limit : undefined,
    progress: typeof item.progress === 'number' ? item.progress : undefined,
    changedOn: typeof item.changed_on === 'string' ? item.changed_on : undefined,
    userId: typeof item.user_id === 'number' ? item.user_id : item.user?.id,
  };
}

function toReportListItem(item: SupersetListItem): ReportListItem | undefined {
  if (typeof item.id !== 'number') {
    return undefined;
  }

  return {
    id: item.id,
    name: typeof item.name === 'string' ? item.name : undefined,
    description:
      typeof item.description === 'string' ? item.description : undefined,
    type: typeof item.type === 'string' ? item.type : undefined,
    active: typeof item.active === 'boolean' ? item.active : undefined,
    crontab: typeof item.crontab === 'string' ? item.crontab : undefined,
    dashboardId:
      typeof item.dashboard_id === 'number' ? item.dashboard_id : undefined,
    chartId: typeof item.chart_id === 'number' ? item.chart_id : undefined,
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
  };
}

function toRoleListItem(item: SupersetListItem): RoleListItem | undefined {
  if (typeof item.id !== 'number') {
    return undefined;
  }

  return {
    id: item.id,
    name: typeof item.name === 'string' ? item.name : undefined,
  };
}

function toRlsListItem(item: SupersetListItem): RlsListItem | undefined {
  if (typeof item.id !== 'number') {
    return undefined;
  }

  return {
    id: item.id,
    name: typeof item.name === 'string' ? item.name : undefined,
    filterType:
      typeof item.filter_type === 'string' ? item.filter_type : undefined,
    tables: item.tables?.map(toRlsTableRef).filter(isDefined),
    roles: item.roles?.map(toRlsRoleRef).filter(isDefined),
    clause: typeof item.clause === 'string' ? item.clause : undefined,
    groupKey: typeof item.group_key === 'string' ? item.group_key : undefined,
    changedOn:
      typeof item.changed_on === 'string'
        ? item.changed_on
        : typeof item.changed_on_delta_humanized === 'string'
          ? item.changed_on_delta_humanized
          : undefined,
  };
}

function toRlsTableRef(value: unknown): RlsTableRef | undefined {
  if (!isRecord(value)) {
    return undefined;
  }

  const ref: RlsTableRef = {};
  if (typeof value.id === 'number') {
    ref.id = value.id;
  }
  if (typeof value.table_name === 'string') {
    ref.tableName = value.table_name;
  }
  return Object.keys(ref).length > 0 ? ref : undefined;
}

function toRlsRoleRef(value: unknown): RlsRoleRef | undefined {
  if (!isRecord(value)) {
    return undefined;
  }

  const ref: RlsRoleRef = {};
  if (typeof value.id === 'number') {
    ref.id = value.id;
  }
  if (typeof value.name === 'string') {
    ref.name = value.name;
  }
  return Object.keys(ref).length > 0 ? ref : undefined;
}

function toTagListItem(item: SupersetListItem): TagListItem | undefined {
  if (typeof item.id !== 'number') {
    return undefined;
  }

  return {
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
  };
}

function toTaskListItem(item: SupersetListItem): TaskListItem | undefined {
  if (typeof item.id !== 'number') {
    return undefined;
  }

  return {
    id: item.id,
    uuid: typeof item.uuid === 'string' ? item.uuid : undefined,
    taskType: typeof item.task_type === 'string' ? item.task_type : undefined,
    taskKey: typeof item.task_key === 'string' ? item.task_key : undefined,
    taskName: typeof item.task_name === 'string' ? item.task_name : undefined,
    status: typeof item.status === 'string' ? item.status : undefined,
    scope: typeof item.scope === 'string' ? item.scope : undefined,
    changedOn: typeof item.changed_on === 'string' ? item.changed_on : undefined,
    createdOn: typeof item.created_on === 'string' ? item.created_on : undefined,
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

function requestedAnnotationLayerColumns(
  request: AnnotationLayerListRequest,
): string[] {
  return request.selectColumns.length > 0
    ? request.selectColumns
    : ['id', 'name', 'descr'];
}

function requestedAnnotationColumns(request: AnnotationListRequest): string[] {
  return request.selectColumns.length > 0
    ? request.selectColumns
    : ['id', 'short_descr', 'start_dttm', 'end_dttm', 'layer_id'];
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

function requestedQueryColumns(request: QueryListRequest): string[] {
  return request.selectColumns.length > 0
    ? request.selectColumns
    : ['id', 'status', 'start_time', 'database_id', 'schema'];
}

function requestedSavedQueryColumns(request: SavedQueryListRequest): string[] {
  return request.selectColumns.length > 0
    ? request.selectColumns
    : ['id', 'label', 'db_id', 'schema', 'uuid'];
}

function requestedReportColumns(request: ReportListRequest): string[] {
  return request.selectColumns.length > 0
    ? request.selectColumns
    : ['id', 'name', 'type', 'active', 'crontab'];
}

function requestedRoleColumns(request: RoleListRequest): string[] {
  return request.selectColumns.length > 0 ? request.selectColumns : ['id', 'name'];
}

function requestedRlsColumns(request: RlsListRequest): string[] {
  return request.selectColumns.length > 0
    ? request.selectColumns
    : ['id', 'name', 'filter_type', 'clause'];
}

function requestedTagColumns(request: TagListRequest): string[] {
  return request.selectColumns.length > 0
    ? request.selectColumns
    : ['id', 'name', 'type'];
}

function requestedTaskColumns(request: TaskListRequest): string[] {
  return request.selectColumns.length > 0
    ? request.selectColumns
    : ['id', 'uuid', 'task_type', 'status', 'changed_on'];
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

function emptyAnnotationLayerListResponse(
  request: AnnotationLayerListRequest,
  warnings: string[],
): AnnotationLayerListResponse {
  return {
    contractVersion: ANNOTATION_LAYER_LIST_CONTRACT_VERSION,
    annotationLayers: [],
    count: 0,
    totalCount: 0,
    page: request.page,
    pageSize: request.pageSize,
    totalPages: 0,
    hasNext: false,
    hasPrevious: request.page > 1,
    columnsRequested: requestedAnnotationLayerColumns(request),
    columnsLoaded: [],
    warnings,
  };
}

function emptyAnnotationListResponse(
  request: AnnotationListRequest,
  warnings: string[],
): AnnotationListResponse {
  return {
    contractVersion: ANNOTATION_LIST_CONTRACT_VERSION,
    annotations: [],
    count: 0,
    totalCount: 0,
    page: request.page,
    pageSize: request.pageSize,
    totalPages: 0,
    hasNext: false,
    hasPrevious: request.page > 1,
    layerId: request.layerId,
    columnsRequested: requestedAnnotationColumns(request),
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

function emptyQueryListResponse(
  request: QueryListRequest,
  warnings: string[],
): QueryListResponse {
  return {
    contractVersion: QUERY_LIST_CONTRACT_VERSION,
    queries: [],
    count: 0,
    totalCount: 0,
    page: request.page,
    pageSize: request.pageSize,
    totalPages: 0,
    hasNext: false,
    hasPrevious: request.page > 1,
    columnsRequested: requestedQueryColumns(request),
    columnsLoaded: [],
    warnings,
  };
}

function emptySavedQueryListResponse(
  request: SavedQueryListRequest,
  warnings: string[],
): SavedQueryListResponse {
  return {
    contractVersion: SAVED_QUERY_LIST_CONTRACT_VERSION,
    savedQueries: [],
    count: 0,
    totalCount: 0,
    page: request.page,
    pageSize: request.pageSize,
    totalPages: 0,
    hasNext: false,
    hasPrevious: request.page > 1,
    columnsRequested: requestedSavedQueryColumns(request),
    columnsLoaded: [],
    warnings,
  };
}

function emptyReportListResponse(
  request: ReportListRequest,
  warnings: string[],
): ReportListResponse {
  return {
    contractVersion: REPORT_LIST_CONTRACT_VERSION,
    reports: [],
    count: 0,
    totalCount: 0,
    page: request.page,
    pageSize: request.pageSize,
    totalPages: 0,
    hasNext: false,
    hasPrevious: request.page > 1,
    columnsRequested: requestedReportColumns(request),
    columnsLoaded: [],
    warnings,
  };
}

function emptyRoleListResponse(
  request: RoleListRequest,
  warnings: string[],
): RoleListResponse {
  return {
    contractVersion: ROLE_LIST_CONTRACT_VERSION,
    roles: [],
    count: 0,
    totalCount: 0,
    page: request.page,
    pageSize: request.pageSize,
    totalPages: 0,
    hasNext: false,
    hasPrevious: request.page > 1,
    columnsRequested: requestedRoleColumns(request),
    columnsLoaded: [],
    warnings,
  };
}

function emptyRlsListResponse(
  request: RlsListRequest,
  warnings: string[],
): RlsListResponse {
  return {
    contractVersion: RLS_LIST_CONTRACT_VERSION,
    rlsFilters: [],
    count: 0,
    totalCount: 0,
    page: request.page,
    pageSize: request.pageSize,
    totalPages: 0,
    hasNext: false,
    hasPrevious: request.page > 1,
    columnsRequested: requestedRlsColumns(request),
    columnsLoaded: [],
    warnings,
  };
}

function emptyTagListResponse(
  request: TagListRequest,
  warnings: string[],
): TagListResponse {
  return {
    contractVersion: TAG_LIST_CONTRACT_VERSION,
    tags: [],
    count: 0,
    totalCount: 0,
    page: request.page,
    pageSize: request.pageSize,
    totalPages: 0,
    hasNext: false,
    hasPrevious: request.page > 1,
    columnsRequested: requestedTagColumns(request),
    columnsLoaded: [],
    warnings,
  };
}

function emptyTaskListResponse(
  request: TaskListRequest,
  warnings: string[],
): TaskListResponse {
  return {
    contractVersion: TASK_LIST_CONTRACT_VERSION,
    tasks: [],
    count: 0,
    totalCount: 0,
    page: request.page,
    pageSize: request.pageSize,
    totalPages: 0,
    hasNext: false,
    hasPrevious: request.page > 1,
    columnsRequested: requestedTaskColumns(request),
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

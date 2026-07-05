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
    const invalidRequestResponse = invalidListRequestResponse(
      request,
      'annotation layer',
      ANNOTATION_LAYER_LIST_CONTRACT_VERSION,
      emptyAnnotationLayerListResponse,
    );
    if (invalidRequestResponse !== undefined) {
      return invalidRequestResponse;
    }

    return this.fetchListResource({
      request,
      correlationId,
      url: this.buildAnnotationLayerListUrl(request),
      resourceLabel: 'annotation layer',
      emptyResponse: emptyAnnotationLayerListResponse,
      toItem: toAnnotationLayerListItem,
      buildResponse: (annotationLayers, totalCount) => ({
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
      }),
    });
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

    const invalidRequestResponse = invalidListRequestResponse(
      request,
      'annotation',
      ANNOTATION_LIST_CONTRACT_VERSION,
      emptyAnnotationListResponse,
    );
    if (invalidRequestResponse !== undefined) {
      return invalidRequestResponse;
    }

    return this.fetchListResource({
      request,
      correlationId,
      url: this.buildAnnotationListUrl(request),
      resourceLabel: 'annotation',
      emptyResponse: emptyAnnotationListResponse,
      toItem: item => toAnnotationListItem(item, request.layerId),
      buildResponse: (annotations, totalCount) => ({
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
      }),
    });
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
    const invalidRequestResponse = invalidListRequestResponse(
      request,
      'dashboard',
      DASHBOARD_LIST_CONTRACT_VERSION,
      emptyDashboardListResponse,
      { requiresOwnedByMeFlag: true },
    );
    if (invalidRequestResponse !== undefined) {
      return invalidRequestResponse;
    }

    return this.fetchListResource({
      request,
      correlationId,
      url: this.buildDashboardListUrl(request),
      resourceLabel: 'dashboard',
      emptyResponse: emptyDashboardListResponse,
      toItem: toDashboardListItem,
      buildResponse: (dashboards, totalCount) => ({
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
      }),
    });
  }

  async listCharts(
    request: ChartListRequest,
    correlationId?: string,
  ): Promise<ChartListResponse> {
    const invalidRequestResponse = invalidListRequestResponse(
      request,
      'chart',
      CHART_LIST_CONTRACT_VERSION,
      emptyChartListResponse,
      { requiresOwnedByMeFlag: true },
    );
    if (invalidRequestResponse !== undefined) {
      return invalidRequestResponse;
    }

    return this.fetchListResource({
      request,
      correlationId,
      url: this.buildChartListUrl(request),
      resourceLabel: 'chart',
      emptyResponse: emptyChartListResponse,
      toItem: toChartListItem,
      buildResponse: (charts, totalCount) => ({
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
      }),
    });
  }

  async listDatasets(
    request: DatasetListRequest,
    correlationId?: string,
  ): Promise<DatasetListResponse> {
    const invalidRequestResponse = invalidListRequestResponse(
      request,
      'dataset',
      DATASET_LIST_CONTRACT_VERSION,
      emptyDatasetListResponse,
      { requiresOwnedByMeFlag: true },
    );
    if (invalidRequestResponse !== undefined) {
      return invalidRequestResponse;
    }

    return this.fetchListResource({
      request,
      correlationId,
      url: this.buildDatasetListUrl(request),
      resourceLabel: 'dataset',
      emptyResponse: emptyDatasetListResponse,
      toItem: toDatasetListItem,
      buildResponse: (datasets, totalCount) => ({
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
      }),
    });
  }

  async listDatabases(
    request: DatabaseListRequest,
    correlationId?: string,
  ): Promise<DatabaseListResponse> {
    const invalidRequestResponse = invalidListRequestResponse(
      request,
      'database',
      DATABASE_LIST_CONTRACT_VERSION,
      emptyDatabaseListResponse,
      { requiresOwnedByMeFlag: false },
    );
    if (invalidRequestResponse !== undefined) {
      return invalidRequestResponse;
    }

    return this.fetchListResource({
      request,
      correlationId,
      url: this.buildDatabaseListUrl(request),
      resourceLabel: 'database',
      emptyResponse: emptyDatabaseListResponse,
      toItem: toDatabaseListItem,
      buildResponse: (databases, totalCount) => ({
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
      }),
    });
  }

  private async fetchListResource<
    TRequest extends ListPaginationRequest,
    TItem,
    TResponse,
  >({
    request,
    correlationId,
    url,
    resourceLabel,
    emptyResponse,
    toItem,
    buildResponse,
  }: {
    request: TRequest;
    correlationId: string | undefined;
    url: string;
    resourceLabel: string;
    emptyResponse: EmptyListResponseFactory<TRequest, TResponse>;
    toItem: (item: SupersetListItem) => TItem | undefined;
    buildResponse: (items: TItem[], totalCount: number) => TResponse;
  }): Promise<TResponse> {
    try {
      const response = await fetch(url, {
        headers: this.buildHeaders(correlationId),
        signal: AbortSignal.timeout(this.config.supersetTimeoutMs),
      });

      if (!response.ok) {
        return emptyResponse(request, [
          `${resourceLabel} list returned status ${response.status} from Superset`,
        ]);
      }

      const payload = (await response.json()) as unknown;
      const items = extractSupersetResults(payload).map(toItem).filter(isDefined);
      const totalCount = extractSupersetCount(payload, items.length);

      return buildResponse(items, totalCount);
    } catch (error) {
      return emptyResponse(request, [
        `${resourceLabel} list failed: ${externalErrorMessage(error)}`,
      ]);
    }
  }

  async listQueries(
    request: QueryListRequest,
    correlationId?: string,
  ): Promise<QueryListResponse> {
    const invalidRequestResponse = invalidListRequestResponse(
      request,
      'query',
      QUERY_LIST_CONTRACT_VERSION,
      emptyQueryListResponse,
    );
    if (invalidRequestResponse !== undefined) {
      return invalidRequestResponse;
    }

    return this.fetchListResource({
      request,
      correlationId,
      url: this.buildQueryListUrl(request),
      resourceLabel: 'query',
      emptyResponse: emptyQueryListResponse,
      toItem: toQueryListItem,
      buildResponse: (queries, totalCount) => ({
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
      }),
    });
  }

  async listSavedQueries(
    request: SavedQueryListRequest,
    correlationId?: string,
  ): Promise<SavedQueryListResponse> {
    const invalidRequestResponse = invalidListRequestResponse(
      request,
      'saved query',
      SAVED_QUERY_LIST_CONTRACT_VERSION,
      emptySavedQueryListResponse,
    );
    if (invalidRequestResponse !== undefined) {
      return invalidRequestResponse;
    }

    return this.fetchListResource({
      request,
      correlationId,
      url: this.buildSavedQueryListUrl(request),
      resourceLabel: 'saved query',
      emptyResponse: emptySavedQueryListResponse,
      toItem: toSavedQueryListItem,
      buildResponse: (savedQueries, totalCount) => ({
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
      }),
    });
  }

  async listReports(
    request: ReportListRequest,
    correlationId?: string,
  ): Promise<ReportListResponse> {
    const invalidRequestResponse = invalidListRequestResponse(
      request,
      'report',
      REPORT_LIST_CONTRACT_VERSION,
      emptyReportListResponse,
    );
    if (invalidRequestResponse !== undefined) {
      return invalidRequestResponse;
    }

    return this.fetchListResource({
      request,
      correlationId,
      url: this.buildReportListUrl(request),
      resourceLabel: 'report',
      emptyResponse: emptyReportListResponse,
      toItem: toReportListItem,
      buildResponse: (reports, totalCount) => ({
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
      }),
    });
  }

  async listRoles(
    request: RoleListRequest,
    correlationId?: string,
  ): Promise<RoleListResponse> {
    const invalidRequestResponse = invalidListRequestResponse(
      request,
      'role',
      ROLE_LIST_CONTRACT_VERSION,
      emptyRoleListResponse,
    );
    if (invalidRequestResponse !== undefined) {
      return invalidRequestResponse;
    }

    return this.fetchListResource({
      request,
      correlationId,
      url: this.buildRoleListUrl(request),
      resourceLabel: 'role',
      emptyResponse: emptyRoleListResponse,
      toItem: toRoleListItem,
      buildResponse: (roles, totalCount) => ({
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
      }),
    });
  }

  async listRlsFilters(
    request: RlsListRequest,
    correlationId?: string,
  ): Promise<RlsListResponse> {
    const invalidRequestResponse = invalidListRequestResponse(
      request,
      'RLS filter',
      RLS_LIST_CONTRACT_VERSION,
      emptyRlsListResponse,
    );
    if (invalidRequestResponse !== undefined) {
      return invalidRequestResponse;
    }

    return this.fetchListResource({
      request,
      correlationId,
      url: this.buildRlsListUrl(request),
      resourceLabel: 'RLS filter',
      emptyResponse: emptyRlsListResponse,
      toItem: toRlsListItem,
      buildResponse: (rlsFilters, totalCount) => ({
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
      }),
    });
  }

  async listTags(
    request: TagListRequest,
    correlationId?: string,
  ): Promise<TagListResponse> {
    const invalidRequestResponse = invalidListRequestResponse(
      request,
      'tag',
      TAG_LIST_CONTRACT_VERSION,
      emptyTagListResponse,
    );
    if (invalidRequestResponse !== undefined) {
      return invalidRequestResponse;
    }

    return this.fetchListResource({
      request,
      correlationId,
      url: this.buildTagListUrl(request),
      resourceLabel: 'tag',
      emptyResponse: emptyTagListResponse,
      toItem: toTagListItem,
      buildResponse: (tags, totalCount) => ({
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
      }),
    });
  }

  async listTasks(
    request: TaskListRequest,
    correlationId?: string,
  ): Promise<TaskListResponse> {
    const invalidRequestResponse = invalidListRequestResponse(
      request,
      'task',
      TASK_LIST_CONTRACT_VERSION,
      emptyTaskListResponse,
    );
    if (invalidRequestResponse !== undefined) {
      return invalidRequestResponse;
    }

    return this.fetchListResource({
      request,
      correlationId,
      url: this.buildTaskListUrl(request),
      resourceLabel: 'task',
      emptyResponse: emptyTaskListResponse,
      toItem: toTaskListItem,
      buildResponse: (tasks, totalCount) => ({
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
      }),
    });
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

interface SupersetListQueryRequest extends ListPaginationRequest {
  filters: ListFilter[];
  search?: string;
  orderColumn?: string;
  orderDirection: string;
}

interface ListColumnRequest {
  selectColumns?: unknown;
}

type LoadedColumnName = string | readonly string[];

type LoadedColumnSpec<T> = readonly [keyof T, LoadedColumnName];

type EmptyListResponseFactory<
  TRequest extends ListPaginationRequest,
  TResponse,
> = (request: TRequest, warnings: string[]) => TResponse;

interface ListRequestValidationOptions {
  requiresOwnedByMeFlag?: boolean;
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
  return buildSupersetPagedListQuery(request, 'name');
}

function buildAnnotationListQuery(request: AnnotationListRequest): string {
  return buildSupersetPagedListQuery(request, 'short_descr');
}

function buildDashboardListQuery(request: DashboardListRequest): string {
  return buildSupersetPagedListQuery(request, 'dashboard_title');
}

function buildChartListQuery(request: ChartListRequest): string {
  return buildSupersetPagedListQuery(request, 'slice_name');
}

function buildDatasetListQuery(request: DatasetListRequest): string {
  return buildSupersetPagedListQuery(request, 'table_name');
}

function buildDatabaseListQuery(request: DatabaseListRequest): string {
  return buildSupersetPagedListQuery(request, 'database_name');
}

function buildQueryListQuery(request: QueryListRequest): string {
  return buildSupersetPagedListQuery(request, 'sql');
}

function buildSavedQueryListQuery(request: SavedQueryListRequest): string {
  return buildSupersetPagedListQuery(request, 'label');
}

function buildReportListQuery(request: ReportListRequest): string {
  return buildSupersetPagedListQuery(request, 'name');
}

function buildRoleListQuery(request: RoleListRequest): string {
  return buildSupersetPagedListQuery(request, 'name');
}

function buildRlsListQuery(request: RlsListRequest): string {
  return buildSupersetPagedListQuery(request, 'name');
}

function buildTagListQuery(request: TagListRequest): string {
  return buildSupersetPagedListQuery(request, 'name');
}

function buildTaskListQuery(request: TaskListRequest): string {
  return buildSupersetPagedListQuery(request, 'task_name');
}

function buildSupersetPagedListQuery(
  request: SupersetListQueryRequest,
  searchColumn: string,
): string {
  const filters = [...request.filters];
  if (request.search !== undefined && request.search !== '') {
    filters.push({
      col: searchColumn,
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
  return loadedColumns(dashboards, [
    ['dashboardTitle', 'dashboard_title'],
    ['slug', 'slug'],
    ['description', 'description'],
    ['certifiedBy', 'certified_by'],
    ['certificationDetails', 'certification_details'],
    ['published', 'published'],
    ['uuid', 'uuid'],
    ['url', 'url'],
    ['changedOn', 'changed_on'],
    ['changedOnHumanized', 'changed_on_humanized'],
  ]);
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
  return loadedColumns(charts, [
    ['sliceName', 'slice_name'],
    ['vizType', 'viz_type'],
    ['description', 'description'],
    ['certifiedBy', 'certified_by'],
    ['certificationDetails', 'certification_details'],
    ['uuid', 'uuid'],
    ['url', 'url'],
    ['changedOn', 'changed_on'],
    ['changedOnHumanized', 'changed_on_humanized'],
  ]);
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

function loadedColumns<T extends object>(
  items: T[],
  specs: readonly LoadedColumnSpec<T>[],
): string[] {
  const loaded = new Set<string>(['id']);
  for (const item of items) {
    for (const [field, columnNames] of specs) {
      if (item[field] !== undefined) {
        for (const columnName of arrayColumnNames(columnNames)) {
          loaded.add(columnName);
        }
      }
    }
  }
  return [...loaded];
}

function arrayColumnNames(columnNames: LoadedColumnName): readonly string[] {
  return typeof columnNames === 'string' ? [columnNames] : columnNames;
}

function datasetColumnsLoaded(datasets: DatasetListItem[]): string[] {
  return loadedColumns(datasets, [
    ['tableName', 'table_name'],
    ['schema', 'schema'],
    ['databaseName', ['database_name', 'database']],
    ['description', 'description'],
    ['certifiedBy', 'certified_by'],
    ['certificationDetails', 'certification_details'],
    ['changedOn', 'changed_on'],
    ['changedOnHumanized', 'changed_on_humanized'],
    ['isVirtual', 'is_virtual'],
    ['databaseId', 'database_id'],
    ['uuid', 'uuid'],
    ['url', 'url'],
  ]);
}

function databaseColumnsLoaded(databases: DatabaseListItem[]): string[] {
  return loadedColumns(databases, [
    ['uuid', 'uuid'],
    ['databaseName', 'database_name'],
    ['backend', 'backend'],
    ['exposeInSqllab', 'expose_in_sqllab'],
    ['allowCtas', 'allow_ctas'],
    ['allowCvas', 'allow_cvas'],
    ['allowDml', 'allow_dml'],
    ['allowFileUpload', 'allow_file_upload'],
    ['allowRunAsync', 'allow_run_async'],
    ['cacheTimeout', 'cache_timeout'],
    ['configurationMethod', 'configuration_method'],
    ['forceCtasSchema', 'force_ctas_schema'],
    ['impersonateUser', 'impersonate_user'],
    ['isManagedExternally', 'is_managed_externally'],
    ['externalUrl', 'external_url'],
    ['extra', 'extra'],
    ['changedOn', 'changed_on'],
    ['changedOnHumanized', 'changed_on_humanized'],
    ['createdOn', 'created_on'],
    ['createdOnHumanized', 'created_on_humanized'],
  ]);
}

function queryColumnsLoaded(queries: QueryListItem[]): string[] {
  return loadedColumns(queries, [
    ['sql', 'sql'],
    ['executedSql', 'executed_sql'],
    ['status', 'status'],
    ['startTime', 'start_time'],
    ['endTime', 'end_time'],
    ['rows', 'rows'],
    ['databaseId', 'database_id'],
    ['schema', 'schema'],
    ['catalog', 'catalog'],
    ['tabName', 'tab_name'],
    ['errorMessage', 'error_message'],
    ['clientId', 'client_id'],
    ['limit', 'limit'],
    ['progress', 'progress'],
    ['changedOn', 'changed_on'],
    ['userId', 'user_id'],
  ]);
}

function savedQueryColumnsLoaded(savedQueries: SavedQueryListItem[]): string[] {
  return loadedColumns(savedQueries, [
    ['uuid', 'uuid'],
    ['label', 'label'],
    ['sql', 'sql'],
    ['dbId', 'db_id'],
    ['schema', 'schema'],
    ['catalog', 'catalog'],
    ['description', 'description'],
    ['changedOn', 'changed_on'],
    ['createdOn', 'created_on'],
    ['lastRun', 'last_run'],
  ]);
}

function annotationLayerColumnsLoaded(
  annotationLayers: AnnotationLayerListItem[],
): string[] {
  return loadedColumns(annotationLayers, [
    ['name', 'name'],
    ['descr', 'descr'],
    ['changedOn', 'changed_on'],
    ['createdOn', 'created_on'],
  ]);
}

function annotationColumnsLoaded(annotations: AnnotationListItem[]): string[] {
  return loadedColumns(annotations, [
    ['shortDescr', 'short_descr'],
    ['longDescr', 'long_descr'],
    ['startDttm', 'start_dttm'],
    ['endDttm', 'end_dttm'],
    ['jsonMetadata', 'json_metadata'],
    ['layerId', 'layer_id'],
  ]);
}

function reportColumnsLoaded(reports: ReportListItem[]): string[] {
  return loadedColumns(reports, [
    ['name', 'name'],
    ['description', 'description'],
    ['type', 'type'],
    ['active', 'active'],
    ['crontab', 'crontab'],
    ['dashboardId', 'dashboard_id'],
    ['chartId', 'chart_id'],
    ['lastEvalDttm', 'last_eval_dttm'],
    ['lastEvalDttmHumanized', 'last_eval_dttm_humanized'],
    ['lastState', 'last_state'],
    ['creationMethod', 'creation_method'],
    ['changedOn', 'changed_on'],
    ['changedOnHumanized', 'changed_on_humanized'],
    ['createdOn', 'created_on'],
    ['createdOnHumanized', 'created_on_humanized'],
  ]);
}

function roleColumnsLoaded(roles: RoleListItem[]): string[] {
  return loadedColumns(roles, [['name', 'name']]);
}

function rlsColumnsLoaded(rlsFilters: RlsListItem[]): string[] {
  return loadedColumns(rlsFilters, [
    ['name', 'name'],
    ['filterType', 'filter_type'],
    ['tables', 'tables'],
    ['roles', 'roles'],
    ['clause', 'clause'],
    ['groupKey', 'group_key'],
    ['changedOn', 'changed_on'],
  ]);
}

function tagColumnsLoaded(tags: TagListItem[]): string[] {
  return loadedColumns(tags, [
    ['name', 'name'],
    ['type', 'type'],
    ['description', 'description'],
    ['changedOn', 'changed_on'],
    ['changedOnHumanized', 'changed_on_humanized'],
    ['createdOn', 'created_on'],
    ['createdOnHumanized', 'created_on_humanized'],
  ]);
}

function taskColumnsLoaded(tasks: TaskListItem[]): string[] {
  return loadedColumns(tasks, [
    ['uuid', 'uuid'],
    ['taskType', 'task_type'],
    ['taskKey', 'task_key'],
    ['taskName', 'task_name'],
    ['status', 'status'],
    ['scope', 'scope'],
    ['changedOn', 'changed_on'],
    ['createdOn', 'created_on'],
  ]);
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

function invalidListRequestResponse<
  TRequest extends ListPaginationRequest,
  TResponse,
>(
  request: TRequest,
  resourceName: string,
  contractVersion: string,
  emptyResponse: EmptyListResponseFactory<TRequest, TResponse>,
  options: ListRequestValidationOptions = {},
): TResponse | undefined {
  if (!hasValidListPagination(request)) {
    return emptyResponse(withFallbackListPagination<TRequest>(request), [
      `${resourceName} list request contains invalid pagination`,
    ]);
  }
  if (!hasValidListColumns(request)) {
    return emptyResponse(request, [
      `${resourceName} list request contains invalid columns`,
    ]);
  }
  if (!hasValidListOrdering(request)) {
    return emptyResponse(request, [
      `${resourceName} list request contains invalid ordering`,
    ]);
  }
  if (!hasValidListFilters(request)) {
    return emptyResponse(request, [
      `${resourceName} list request contains invalid filters`,
    ]);
  }
  if (!hasExpectedContractVersion(request, contractVersion)) {
    return emptyResponse(request, [
      `${resourceName} list request contains invalid contract version`,
    ]);
  }
  if (
    options.requiresOwnedByMeFlag !== undefined &&
    !hasValidOwnershipFlags(request, options.requiresOwnedByMeFlag)
  ) {
    return emptyResponse(request, [
      `${resourceName} list request contains invalid ownership flags`,
    ]);
  }
  return undefined;
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

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
import { randomUUID } from 'crypto';

import Fastify, { FastifyInstance } from 'fastify';

import { ServiceConfig } from './config';
import {
  AnnotationListRequest,
  AnnotationListResponse,
  annotationListRequestSchema,
  annotationListResponseSchema,
} from './contracts/annotationList';
import {
  AnnotationLayerListRequest,
  AnnotationLayerListResponse,
  annotationLayerListRequestSchema,
  annotationLayerListResponseSchema,
} from './contracts/annotationLayerList';
import {
  AssetSearchRequest,
  AssetSearchResponse,
  assetSearchRequestSchema,
  assetSearchResponseSchema,
} from './contracts/assetSearch';
import {
  PermissionCheckRequest,
  PermissionCheckResult,
  permissionCheckRequestSchema,
  permissionCheckResponseSchema,
} from './contracts/authorization';
import {
  ChartListRequest,
  ChartListResponse,
  chartListRequestSchema,
  chartListResponseSchema,
} from './contracts/chartList';
import {
  DashboardListRequest,
  DashboardListResponse,
  dashboardListRequestSchema,
  dashboardListResponseSchema,
} from './contracts/dashboardList';
import {
  DatabaseListRequest,
  DatabaseListResponse,
  databaseListRequestSchema,
  databaseListResponseSchema,
} from './contracts/databaseList';
import {
  DatasetListRequest,
  DatasetListResponse,
  datasetListRequestSchema,
  datasetListResponseSchema,
} from './contracts/datasetList';
import {
  QueryListRequest,
  QueryListResponse,
  queryListRequestSchema,
  queryListResponseSchema,
} from './contracts/queryList';
import {
  HealthResponseContract,
  healthResponseSchema,
  MetadataResponseContract,
  metadataResponseSchema,
  MetricsResponseContract,
  metricsResponseSchema,
  ReadinessResponseContract,
  readinessResponseSchema,
  RUNTIME_CONTRACT_VERSION,
} from './contracts/runtime';
import {
  ReportListRequest,
  ReportListResponse,
  reportListRequestSchema,
  reportListResponseSchema,
} from './contracts/reportList';
import {
  RoleListRequest,
  RoleListResponse,
  roleListRequestSchema,
  roleListResponseSchema,
} from './contracts/roleList';
import {
  RlsListRequest,
  RlsListResponse,
  rlsListRequestSchema,
  rlsListResponseSchema,
} from './contracts/rlsList';
import {
  SavedQueryListRequest,
  SavedQueryListResponse,
  savedQueryListRequestSchema,
  savedQueryListResponseSchema,
} from './contracts/savedQueryList';
import {
  TagListRequest,
  TagListResponse,
  tagListRequestSchema,
  tagListResponseSchema,
} from './contracts/tagList';
import {
  TaskListRequest,
  TaskListResponse,
  taskListRequestSchema,
  taskListResponseSchema,
} from './contracts/taskList';
import { ServiceMetrics } from './metrics';
import {
  SupersetHealthClient,
  SupersetMetadataClient,
  SupersetAnnotationListClient,
  SupersetAnnotationLayerListClient,
  SupersetAssetSearchClient,
  SupersetChartListClient,
  SupersetDashboardListClient,
  SupersetDatabaseListClient,
  SupersetDatasetListClient,
  SupersetQueryListClient,
  SupersetPermissionClient,
  SupersetReportListClient,
  SupersetRoleListClient,
  SupersetRlsListClient,
  SupersetSavedQueryListClient,
  SupersetTagListClient,
  SupersetTaskListClient,
} from './supersetClient';

const MAX_REQUEST_ID_LENGTH = 128;
const UNSAFE_REQUEST_ID_PATTERN = /[\s\u0000-\u001f\u007f]/;

export function normalizeRequestIdHeader(
  value: string | string[] | undefined,
): string | undefined {
  const candidate = Array.isArray(value) ? value[0] : value;
  if (candidate === undefined) {
    return undefined;
  }

  const requestId = candidate.trim();
  if (
    requestId === '' ||
    requestId.length > MAX_REQUEST_ID_LENGTH ||
    UNSAFE_REQUEST_ID_PATTERN.test(requestId)
  ) {
    return undefined;
  }

  return requestId;
}

export function buildServer(
  config: ServiceConfig,
  supersetClient: SupersetHealthClient &
    SupersetMetadataClient &
    SupersetAnnotationListClient &
    SupersetAnnotationLayerListClient &
    SupersetAssetSearchClient &
    SupersetPermissionClient &
    SupersetDashboardListClient &
    SupersetChartListClient &
    SupersetDatabaseListClient &
    SupersetDatasetListClient &
    SupersetQueryListClient &
    SupersetReportListClient &
    SupersetRoleListClient &
    SupersetRlsListClient &
    SupersetSavedQueryListClient &
    SupersetTagListClient &
    SupersetTaskListClient,
): FastifyInstance {
  const metrics = new ServiceMetrics();
  const serviceStartTime = process.hrtime.bigint();
  const server = Fastify({
    logger: config.logLevel === 'silent' ? false : { level: config.logLevel },
    genReqId(request) {
      return (
        normalizeRequestIdHeader(request.headers['x-request-id']) ||
        randomUUID()
      );
    },
  });

  server.addHook('onRequest', async (request, reply) => {
    reply.header('x-request-id', request.id);
    metrics.startRequest(request);
  });

  server.addHook('onResponse', async (request, reply) => {
    metrics.recordResponse(request, reply);
  });

  server.get(
    '/health',
    {
      schema: {
        response: {
          200: healthResponseSchema,
        },
      },
    },
    async (): Promise<HealthResponseContract> => ({
      contractVersion: RUNTIME_CONTRACT_VERSION,
      service: 'ax-services',
      status: 'ok',
      timestamp: new Date().toISOString(),
      version: process.env['npm_package_version'] || '0.0.1',
      nodeVersion: process.version,
      platform: process.platform,
      uptimeSeconds: Number(process.hrtime.bigint() - serviceStartTime) / 1e9,
    }),
  );

  server.get(
    '/ready',
    {
      schema: {
        response: {
          200: readinessResponseSchema,
          503: readinessResponseSchema,
        },
      },
    },
    async (request, reply): Promise<ReadinessResponseContract> => {
      const superset = await supersetClient.checkHealth(request.id);
      const ready = superset.ok;

      return reply.status(ready ? 200 : 503).send({
        contractVersion: RUNTIME_CONTRACT_VERSION,
        service: 'ax-services',
        status: ready ? 'ready' : 'not_ready',
        dependencies: {
          superset,
        },
      });
    },
  );

  server.get(
    '/metadata',
    {
      schema: {
        response: {
          200: metadataResponseSchema,
          503: metadataResponseSchema,
        },
      },
    },
    async (request, reply): Promise<MetadataResponseContract> => {
      const supersetMetadata = await supersetClient.probeMetadata(request.id);
      const ready = supersetMetadata.ok;

      return reply.status(ready ? 200 : 503).send({
        contractVersion: RUNTIME_CONTRACT_VERSION,
        service: 'ax-services',
        status: ready ? 'ok' : 'not_ready',
        dependencies: {
          supersetMetadata,
        },
      });
    },
  );

  server.get(
    '/metrics',
    {
      schema: {
        response: {
          200: metricsResponseSchema,
        },
      },
    },
    async (): Promise<MetricsResponseContract> => metrics.snapshot(),
  );

  server.post<{
    Body: AnnotationListRequest;
    Reply: AnnotationListResponse;
  }>(
    '/mcp/annotations/list',
    {
      schema: {
        body: annotationListRequestSchema,
        response: {
          200: annotationListResponseSchema,
        },
      },
    },
    async (request): Promise<AnnotationListResponse> =>
      supersetClient.listAnnotations(request.body, request.id),
  );

  server.post<{
    Body: AnnotationLayerListRequest;
    Reply: AnnotationLayerListResponse;
  }>(
    '/mcp/annotation-layers/list',
    {
      schema: {
        body: annotationLayerListRequestSchema,
        response: {
          200: annotationLayerListResponseSchema,
        },
      },
    },
    async (request): Promise<AnnotationLayerListResponse> =>
      supersetClient.listAnnotationLayers(request.body, request.id),
  );

  server.post<{
    Body: AssetSearchRequest;
    Reply: AssetSearchResponse;
  }>(
    '/mcp/assets/search',
    {
      schema: {
        body: assetSearchRequestSchema,
        response: {
          200: assetSearchResponseSchema,
        },
      },
    },
    async (request): Promise<AssetSearchResponse> =>
      supersetClient.searchAssets(request.body, request.id),
  );

  server.post<{
    Body: PermissionCheckRequest;
    Reply: PermissionCheckResult;
  }>(
    '/mcp/permissions/check',
    {
      schema: {
        body: permissionCheckRequestSchema,
        response: {
          200: permissionCheckResponseSchema,
        },
      },
    },
    async (request): Promise<PermissionCheckResult> =>
      supersetClient.checkPermission(request.body, request.id),
  );

  server.post<{
    Body: DashboardListRequest;
    Reply: DashboardListResponse;
  }>(
    '/mcp/dashboards/list',
    {
      schema: {
        body: dashboardListRequestSchema,
        response: {
          200: dashboardListResponseSchema,
        },
      },
    },
    async (request): Promise<DashboardListResponse> =>
      supersetClient.listDashboards(request.body, request.id),
  );

  server.post<{
    Body: ChartListRequest;
    Reply: ChartListResponse;
  }>(
    '/mcp/charts/list',
    {
      schema: {
        body: chartListRequestSchema,
        response: {
          200: chartListResponseSchema,
        },
      },
    },
    async (request): Promise<ChartListResponse> =>
      supersetClient.listCharts(request.body, request.id),
  );

  server.post<{
    Body: DatabaseListRequest;
    Reply: DatabaseListResponse;
  }>(
    '/mcp/databases/list',
    {
      schema: {
        body: databaseListRequestSchema,
        response: {
          200: databaseListResponseSchema,
        },
      },
    },
    async (request): Promise<DatabaseListResponse> =>
      supersetClient.listDatabases(request.body, request.id),
  );

  server.post<{
    Body: DatasetListRequest;
    Reply: DatasetListResponse;
  }>(
    '/mcp/datasets/list',
    {
      schema: {
        body: datasetListRequestSchema,
        response: {
          200: datasetListResponseSchema,
        },
      },
    },
    async (request): Promise<DatasetListResponse> =>
      supersetClient.listDatasets(request.body, request.id),
  );

  server.post<{
    Body: QueryListRequest;
    Reply: QueryListResponse;
  }>(
    '/mcp/queries/list',
    {
      schema: {
        body: queryListRequestSchema,
        response: {
          200: queryListResponseSchema,
        },
      },
    },
    async (request): Promise<QueryListResponse> =>
      supersetClient.listQueries(request.body, request.id),
  );

  server.post<{
    Body: ReportListRequest;
    Reply: ReportListResponse;
  }>(
    '/mcp/reports/list',
    {
      schema: {
        body: reportListRequestSchema,
        response: {
          200: reportListResponseSchema,
        },
      },
    },
    async (request): Promise<ReportListResponse> =>
      supersetClient.listReports(request.body, request.id),
  );

  server.post<{
    Body: RoleListRequest;
    Reply: RoleListResponse;
  }>(
    '/mcp/roles/list',
    {
      schema: {
        body: roleListRequestSchema,
        response: {
          200: roleListResponseSchema,
        },
      },
    },
    async (request): Promise<RoleListResponse> =>
      supersetClient.listRoles(request.body, request.id),
  );

  server.post<{
    Body: RlsListRequest;
    Reply: RlsListResponse;
  }>(
    '/mcp/rls-filters/list',
    {
      schema: {
        body: rlsListRequestSchema,
        response: {
          200: rlsListResponseSchema,
        },
      },
    },
    async (request): Promise<RlsListResponse> =>
      supersetClient.listRlsFilters(request.body, request.id),
  );

  server.post<{
    Body: SavedQueryListRequest;
    Reply: SavedQueryListResponse;
  }>(
    '/mcp/saved-queries/list',
    {
      schema: {
        body: savedQueryListRequestSchema,
        response: {
          200: savedQueryListResponseSchema,
        },
      },
    },
    async (request): Promise<SavedQueryListResponse> =>
      supersetClient.listSavedQueries(request.body, request.id),
  );

  server.post<{
    Body: TagListRequest;
    Reply: TagListResponse;
  }>(
    '/mcp/tags/list',
    {
      schema: {
        body: tagListRequestSchema,
        response: {
          200: tagListResponseSchema,
        },
      },
    },
    async (request): Promise<TagListResponse> =>
      supersetClient.listTags(request.body, request.id),
  );

  server.post<{
    Body: TaskListRequest;
    Reply: TaskListResponse;
  }>(
    '/mcp/tasks/list',
    {
      schema: {
        body: taskListRequestSchema,
        response: {
          200: taskListResponseSchema,
        },
      },
    },
    async (request): Promise<TaskListResponse> =>
      supersetClient.listTasks(request.body, request.id),
  );

  return server;
}

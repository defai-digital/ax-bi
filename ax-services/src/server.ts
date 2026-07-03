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
import { normalizeRequestIdHeader } from './requestId';
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

export { normalizeRequestIdHeader } from './requestId';

const DEFAULT_RUNTIME_VERSION = '0.0.1';
const MAX_RUNTIME_VERSION_LENGTH = 128;
const CONTROL_CHARACTER_PATTERN = /[\u0000-\u001f\u007f]/;

type ContractRouteHandler<Body, Reply> = (
  body: Body,
  requestId: string,
) => Promise<Reply>;

function runtimeVersion(): string {
  const version = process.env['npm_package_version']?.trim();

  if (
    version === undefined ||
    version.length === 0 ||
    version.length > MAX_RUNTIME_VERSION_LENGTH ||
    CONTROL_CHARACTER_PATTERN.test(version)
  ) {
    return DEFAULT_RUNTIME_VERSION;
  }

  return version;
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
      version: runtimeVersion(),
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

  function registerContractPostRoute<Body, Reply>(
    path: string,
    bodySchema: unknown,
    responseSchema: unknown,
    handler: ContractRouteHandler<Body, Reply>,
  ): void {
    server.post(
      path,
      {
        schema: {
          body: bodySchema,
          response: {
            200: responseSchema,
          },
        },
      },
      async (request): Promise<Reply> => {
        const response = await handler(request.body as Body, request.id);
        return response;
      },
    );
  }

  registerContractPostRoute<AnnotationListRequest, AnnotationListResponse>(
    '/mcp/annotations/list',
    annotationListRequestSchema,
    annotationListResponseSchema,
    (body, requestId) => supersetClient.listAnnotations(body, requestId),
  );

  registerContractPostRoute<
    AnnotationLayerListRequest,
    AnnotationLayerListResponse
  >(
    '/mcp/annotation-layers/list',
    annotationLayerListRequestSchema,
    annotationLayerListResponseSchema,
    (body, requestId) => supersetClient.listAnnotationLayers(body, requestId),
  );

  registerContractPostRoute<AssetSearchRequest, AssetSearchResponse>(
    '/mcp/assets/search',
    assetSearchRequestSchema,
    assetSearchResponseSchema,
    (body, requestId) => supersetClient.searchAssets(body, requestId),
  );

  registerContractPostRoute<PermissionCheckRequest, PermissionCheckResult>(
    '/mcp/permissions/check',
    permissionCheckRequestSchema,
    permissionCheckResponseSchema,
    (body, requestId) => supersetClient.checkPermission(body, requestId),
  );

  registerContractPostRoute<DashboardListRequest, DashboardListResponse>(
    '/mcp/dashboards/list',
    dashboardListRequestSchema,
    dashboardListResponseSchema,
    (body, requestId) => supersetClient.listDashboards(body, requestId),
  );

  registerContractPostRoute<ChartListRequest, ChartListResponse>(
    '/mcp/charts/list',
    chartListRequestSchema,
    chartListResponseSchema,
    (body, requestId) => supersetClient.listCharts(body, requestId),
  );

  registerContractPostRoute<DatabaseListRequest, DatabaseListResponse>(
    '/mcp/databases/list',
    databaseListRequestSchema,
    databaseListResponseSchema,
    (body, requestId) => supersetClient.listDatabases(body, requestId),
  );

  registerContractPostRoute<DatasetListRequest, DatasetListResponse>(
    '/mcp/datasets/list',
    datasetListRequestSchema,
    datasetListResponseSchema,
    (body, requestId) => supersetClient.listDatasets(body, requestId),
  );

  registerContractPostRoute<QueryListRequest, QueryListResponse>(
    '/mcp/queries/list',
    queryListRequestSchema,
    queryListResponseSchema,
    (body, requestId) => supersetClient.listQueries(body, requestId),
  );

  registerContractPostRoute<ReportListRequest, ReportListResponse>(
    '/mcp/reports/list',
    reportListRequestSchema,
    reportListResponseSchema,
    (body, requestId) => supersetClient.listReports(body, requestId),
  );

  registerContractPostRoute<RoleListRequest, RoleListResponse>(
    '/mcp/roles/list',
    roleListRequestSchema,
    roleListResponseSchema,
    (body, requestId) => supersetClient.listRoles(body, requestId),
  );

  registerContractPostRoute<RlsListRequest, RlsListResponse>(
    '/mcp/rls-filters/list',
    rlsListRequestSchema,
    rlsListResponseSchema,
    (body, requestId) => supersetClient.listRlsFilters(body, requestId),
  );

  registerContractPostRoute<SavedQueryListRequest, SavedQueryListResponse>(
    '/mcp/saved-queries/list',
    savedQueryListRequestSchema,
    savedQueryListResponseSchema,
    (body, requestId) => supersetClient.listSavedQueries(body, requestId),
  );

  registerContractPostRoute<TagListRequest, TagListResponse>(
    '/mcp/tags/list',
    tagListRequestSchema,
    tagListResponseSchema,
    (body, requestId) => supersetClient.listTags(body, requestId),
  );

  registerContractPostRoute<TaskListRequest, TaskListResponse>(
    '/mcp/tasks/list',
    taskListRequestSchema,
    taskListResponseSchema,
    (body, requestId) => supersetClient.listTasks(body, requestId),
  );

  return server;
}

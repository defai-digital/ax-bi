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
  AssetSearchRequest,
  AssetSearchResponse,
  assetSearchRequestSchema,
  assetSearchResponseSchema,
} from './contracts/assetSearch';
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
import { ServiceMetrics } from './metrics';
import {
  SupersetHealthClient,
  SupersetMetadataClient,
  SupersetAssetSearchClient,
  SupersetChartListClient,
  SupersetDashboardListClient,
} from './supersetClient';

export function buildServer(
  config: ServiceConfig,
  supersetClient: SupersetHealthClient &
    SupersetMetadataClient &
    SupersetAssetSearchClient &
    SupersetDashboardListClient &
    SupersetChartListClient,
): FastifyInstance {
  const metrics = new ServiceMetrics();
  const serviceStartTime = process.hrtime.bigint();
  const server = Fastify({
    logger: config.logLevel !== 'silent',
    genReqId(request) {
      const requestId = request.headers['x-request-id'];
      if (Array.isArray(requestId)) {
        return requestId[0] || randomUUID();
      }
      return requestId || randomUUID();
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
      version: process.env.npm_package_version || '0.0.1',
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

  return server;
}

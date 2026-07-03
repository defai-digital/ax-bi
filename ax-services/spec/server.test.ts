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
import { expect, test } from '@jest/globals';

import { buildConfig } from '../src/config';
import { buildServer, normalizeRequestIdHeader } from '../src/server';
import {
  ANNOTATION_LIST_CONTRACT_VERSION,
  AnnotationListResponse,
} from '../src/contracts/annotationList';
import {
  ANNOTATION_LAYER_LIST_CONTRACT_VERSION,
  AnnotationLayerListResponse,
} from '../src/contracts/annotationLayerList';
import {
  ASSET_SEARCH_CONTRACT_VERSION,
  AssetSearchResponse,
} from '../src/contracts/assetSearch';
import {
  AUTHORIZATION_CONTRACT_VERSION,
  PermissionCheckResult,
} from '../src/contracts/authorization';
import {
  CHART_LIST_CONTRACT_VERSION,
  ChartListResponse,
} from '../src/contracts/chartList';
import {
  DASHBOARD_LIST_CONTRACT_VERSION,
  DashboardListResponse,
} from '../src/contracts/dashboardList';
import {
  DATABASE_LIST_CONTRACT_VERSION,
  DatabaseListResponse,
} from '../src/contracts/databaseList';
import {
  DATASET_LIST_CONTRACT_VERSION,
  DatasetListResponse,
} from '../src/contracts/datasetList';
import {
  QUERY_LIST_CONTRACT_VERSION,
  QueryListResponse,
} from '../src/contracts/queryList';
import {
  REPORT_LIST_CONTRACT_VERSION,
  ReportListResponse,
} from '../src/contracts/reportList';
import {
  ROLE_LIST_CONTRACT_VERSION,
  RoleListResponse,
} from '../src/contracts/roleList';
import {
  RLS_LIST_CONTRACT_VERSION,
  RlsListResponse,
} from '../src/contracts/rlsList';
import {
  SAVED_QUERY_LIST_CONTRACT_VERSION,
  SavedQueryListResponse,
} from '../src/contracts/savedQueryList';
import {
  TAG_LIST_CONTRACT_VERSION,
  TagListResponse,
} from '../src/contracts/tagList';
import {
  TASK_LIST_CONTRACT_VERSION,
  TaskListResponse,
} from '../src/contracts/taskList';
import {
  DependencyHealth,
  DependencyMetadata,
  SupersetAnnotationListClient,
  SupersetAnnotationLayerListClient,
  SupersetAssetSearchClient,
  SupersetChartListClient,
  SupersetDashboardListClient,
  SupersetDatabaseListClient,
  SupersetDatasetListClient,
  SupersetQueryListClient,
  SupersetHealthClient,
  SupersetMetadataClient,
  SupersetPermissionClient,
  SupersetReportListClient,
  SupersetRoleListClient,
  SupersetRlsListClient,
  SupersetSavedQueryListClient,
  SupersetTagListClient,
  SupersetTaskListClient,
} from '../src/supersetClient';

const uuidPattern =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

const config = buildConfig({
  AX_SERVICES_LOG_LEVEL: 'silent',
});

function makeSupersetClient({
  health = {
    ok: true,
    statusCode: 200,
    url: 'http://127.0.0.1:8088/health',
  },
  metadata = {
    ok: true,
    statusCode: 200,
    url: 'http://127.0.0.1:8088/api/v1/dashboard/_info',
    keyCount: 2,
    keys: ['permissions', 'result'],
  },
  onHealth,
  onMetadata,
  onListAnnotations,
  onListAnnotationLayers,
  onCheckPermission,
  onSearch,
  onListCharts,
  onListDashboards,
  onListDatabases,
  onListDatasets,
  onListQueries,
  onListReports,
  onListRoles,
  onListRlsFilters,
  onListSavedQueries,
  onListTags,
  onListTasks,
  search = {
    contractVersion: ASSET_SEARCH_CONTRACT_VERSION,
    assets: [],
    warnings: [],
  },
  permissionCheck = {
    contractVersion: AUTHORIZATION_CONTRACT_VERSION,
    allowed: false,
  },
  annotationLayerList = {
    contractVersion: ANNOTATION_LAYER_LIST_CONTRACT_VERSION,
    annotationLayers: [],
    count: 0,
    totalCount: 0,
    page: 1,
    pageSize: 10,
    totalPages: 0,
    hasNext: false,
    hasPrevious: false,
    columnsRequested: [],
    columnsLoaded: [],
    warnings: [],
  },
  annotationList = {
    contractVersion: ANNOTATION_LIST_CONTRACT_VERSION,
    annotations: [],
    count: 0,
    totalCount: 0,
    page: 1,
    pageSize: 10,
    totalPages: 0,
    hasNext: false,
    hasPrevious: false,
    layerId: 1,
    columnsRequested: [],
    columnsLoaded: [],
    warnings: [],
  },
  chartList = {
    contractVersion: CHART_LIST_CONTRACT_VERSION,
    charts: [],
    count: 0,
    totalCount: 0,
    page: 1,
    pageSize: 10,
    totalPages: 0,
    hasNext: false,
    hasPrevious: false,
    columnsRequested: [],
    columnsLoaded: [],
    warnings: [],
  },
  dashboardList = {
    contractVersion: DASHBOARD_LIST_CONTRACT_VERSION,
    dashboards: [],
    count: 0,
    totalCount: 0,
    page: 1,
    pageSize: 10,
    totalPages: 0,
    hasNext: false,
    hasPrevious: false,
    columnsRequested: [],
    columnsLoaded: [],
    warnings: [],
  },
  databaseList = {
    contractVersion: DATABASE_LIST_CONTRACT_VERSION,
    databases: [],
    count: 0,
    totalCount: 0,
    page: 1,
    pageSize: 10,
    totalPages: 0,
    hasNext: false,
    hasPrevious: false,
    columnsRequested: [],
    columnsLoaded: [],
    warnings: [],
  },
  datasetList = {
    contractVersion: DATASET_LIST_CONTRACT_VERSION,
    datasets: [],
    count: 0,
    totalCount: 0,
    page: 1,
    pageSize: 10,
    totalPages: 0,
    hasNext: false,
    hasPrevious: false,
    columnsRequested: [],
    columnsLoaded: [],
    warnings: [],
  },
  queryList = {
    contractVersion: QUERY_LIST_CONTRACT_VERSION,
    queries: [],
    count: 0,
    totalCount: 0,
    page: 1,
    pageSize: 10,
    totalPages: 0,
    hasNext: false,
    hasPrevious: false,
    columnsRequested: [],
    columnsLoaded: [],
    warnings: [],
  },
  savedQueryList = {
    contractVersion: SAVED_QUERY_LIST_CONTRACT_VERSION,
    savedQueries: [],
    count: 0,
    totalCount: 0,
    page: 1,
    pageSize: 10,
    totalPages: 0,
    hasNext: false,
    hasPrevious: false,
    columnsRequested: [],
    columnsLoaded: [],
    warnings: [],
  },
  reportList = {
    contractVersion: REPORT_LIST_CONTRACT_VERSION,
    reports: [],
    count: 0,
    totalCount: 0,
    page: 1,
    pageSize: 10,
    totalPages: 0,
    hasNext: false,
    hasPrevious: false,
    columnsRequested: [],
    columnsLoaded: [],
    warnings: [],
  },
  roleList = {
    contractVersion: ROLE_LIST_CONTRACT_VERSION,
    roles: [],
    count: 0,
    totalCount: 0,
    page: 1,
    pageSize: 10,
    totalPages: 0,
    hasNext: false,
    hasPrevious: false,
    columnsRequested: [],
    columnsLoaded: [],
    warnings: [],
  },
  rlsList = {
    contractVersion: RLS_LIST_CONTRACT_VERSION,
    rlsFilters: [],
    count: 0,
    totalCount: 0,
    page: 1,
    pageSize: 10,
    totalPages: 0,
    hasNext: false,
    hasPrevious: false,
    columnsRequested: [],
    columnsLoaded: [],
    warnings: [],
  },
  tagList = {
    contractVersion: TAG_LIST_CONTRACT_VERSION,
    tags: [],
    count: 0,
    totalCount: 0,
    page: 1,
    pageSize: 10,
    totalPages: 0,
    hasNext: false,
    hasPrevious: false,
    columnsRequested: [],
    columnsLoaded: [],
    warnings: [],
  },
  taskList = {
    contractVersion: TASK_LIST_CONTRACT_VERSION,
    tasks: [],
    count: 0,
    totalCount: 0,
    page: 1,
    pageSize: 10,
    totalPages: 0,
    hasNext: false,
    hasPrevious: false,
    columnsRequested: [],
    columnsLoaded: [],
    warnings: [],
  },
}: {
  health?: DependencyHealth;
  metadata?: DependencyMetadata;
  search?: AssetSearchResponse;
  permissionCheck?: PermissionCheckResult;
  annotationList?: AnnotationListResponse;
  annotationLayerList?: AnnotationLayerListResponse;
  chartList?: ChartListResponse;
  dashboardList?: DashboardListResponse;
  databaseList?: DatabaseListResponse;
  datasetList?: DatasetListResponse;
  queryList?: QueryListResponse;
  reportList?: ReportListResponse;
  roleList?: RoleListResponse;
  rlsList?: RlsListResponse;
  savedQueryList?: SavedQueryListResponse;
  tagList?: TagListResponse;
  taskList?: TaskListResponse;
  onHealth?: (correlationId?: string) => void;
  onMetadata?: (correlationId?: string) => void;
  onListAnnotations?: (correlationId?: string) => void;
  onListAnnotationLayers?: (correlationId?: string) => void;
  onCheckPermission?: (correlationId?: string) => void;
  onSearch?: (correlationId?: string) => void;
  onListCharts?: (correlationId?: string) => void;
  onListDashboards?: (correlationId?: string) => void;
  onListDatabases?: (correlationId?: string) => void;
  onListDatasets?: (correlationId?: string) => void;
  onListQueries?: (correlationId?: string) => void;
  onListReports?: (correlationId?: string) => void;
  onListRoles?: (correlationId?: string) => void;
  onListRlsFilters?: (correlationId?: string) => void;
  onListSavedQueries?: (correlationId?: string) => void;
  onListTags?: (correlationId?: string) => void;
  onListTasks?: (correlationId?: string) => void;
} = {}): SupersetHealthClient &
  SupersetMetadataClient &
  SupersetAnnotationListClient &
  SupersetAnnotationLayerListClient &
  SupersetAssetSearchClient &
  SupersetPermissionClient &
  SupersetChartListClient &
  SupersetDashboardListClient &
  SupersetDatabaseListClient &
  SupersetDatasetListClient &
  SupersetQueryListClient &
  SupersetReportListClient &
  SupersetRoleListClient &
  SupersetRlsListClient &
  SupersetSavedQueryListClient &
  SupersetTagListClient &
  SupersetTaskListClient {
  return {
    async checkHealth(correlationId) {
      onHealth?.(correlationId);
      return health;
    },
    async probeMetadata(correlationId) {
      onMetadata?.(correlationId);
      return metadata;
    },
    async searchAssets(_request, correlationId) {
      onSearch?.(correlationId);
      return search;
    },
    async checkPermission(_request, correlationId) {
      onCheckPermission?.(correlationId);
      return permissionCheck;
    },
    async listAnnotations(_request, correlationId) {
      onListAnnotations?.(correlationId);
      return annotationList;
    },
    async listAnnotationLayers(_request, correlationId) {
      onListAnnotationLayers?.(correlationId);
      return annotationLayerList;
    },
    async listCharts(_request, correlationId) {
      onListCharts?.(correlationId);
      return chartList;
    },
    async listDashboards(_request, correlationId) {
      onListDashboards?.(correlationId);
      return dashboardList;
    },
    async listDatabases(_request, correlationId) {
      onListDatabases?.(correlationId);
      return databaseList;
    },
    async listDatasets(_request, correlationId) {
      onListDatasets?.(correlationId);
      return datasetList;
    },
    async listQueries(_request, correlationId) {
      onListQueries?.(correlationId);
      return queryList;
    },
    async listReports(_request, correlationId) {
      onListReports?.(correlationId);
      return reportList;
    },
    async listRoles(_request, correlationId) {
      onListRoles?.(correlationId);
      return roleList;
    },
    async listRlsFilters(_request, correlationId) {
      onListRlsFilters?.(correlationId);
      return rlsList;
    },
    async listSavedQueries(_request, correlationId) {
      onListSavedQueries?.(correlationId);
      return savedQueryList;
    },
    async listTags(_request, correlationId) {
      onListTags?.(correlationId);
      return tagList;
    },
    async listTasks(_request, correlationId) {
      onListTasks?.(correlationId);
      return taskList;
    },
  };
}

test('health endpoint returns service metadata', async () => {
  const server = buildServer(config, makeSupersetClient());

  const response = await server.inject({
    method: 'GET',
    url: '/health',
  });

  expect(response.statusCode).toBe(200);
  expect(response.headers['x-request-id']).toBeDefined();
  expect(response.json()).toEqual({
    contractVersion: 'runtime.v1',
    service: 'ax-services',
    status: 'ok',
    timestamp: expect.any(String),
    version: expect.any(String),
    nodeVersion: expect.stringMatching(/^v\d+\./),
    platform: expect.any(String),
    uptimeSeconds: expect.any(Number),
  });
});

test('health endpoint sanitizes package version metadata', async () => {
  const previousVersion = process.env['npm_package_version'];

  try {
    process.env['npm_package_version'] = '  1.2.3-build.4  ';
    const server = buildServer(config, makeSupersetClient());

    const response = await server.inject({
      method: 'GET',
      url: '/health',
    });

    expect(response.statusCode).toBe(200);
    expect(response.json().version).toBe('1.2.3-build.4');

    process.env['npm_package_version'] = '1.2.3\nextra';
    const unsafeResponse = await server.inject({
      method: 'GET',
      url: '/health',
    });

    expect(unsafeResponse.statusCode).toBe(200);
    expect(unsafeResponse.json().version).toBe('0.0.1');

    process.env['npm_package_version'] = '1'.repeat(129);
    const longResponse = await server.inject({
      method: 'GET',
      url: '/health',
    });

    expect(longResponse.statusCode).toBe(200);
    expect(longResponse.json().version).toBe('0.0.1');
  } finally {
    if (previousVersion === undefined) {
      delete process.env['npm_package_version'];
    } else {
      process.env['npm_package_version'] = previousVersion;
    }
  }
});

test('ready endpoint returns ok when Superset is reachable', async () => {
  const seenRequestIds: string[] = [];
  const server = buildServer(
    config,
    makeSupersetClient({
      onHealth(correlationId) {
        if (correlationId) {
          seenRequestIds.push(correlationId);
        }
      },
    }),
  );

  const response = await server.inject({
    method: 'GET',
    url: '/ready',
    headers: {
      'x-request-id': 'request-123',
    },
  });

  expect(response.statusCode).toBe(200);
  expect(response.headers['x-request-id']).toBe('request-123');
  expect(seenRequestIds).toEqual(['request-123']);
  expect(response.json()).toEqual({
    contractVersion: 'runtime.v1',
    service: 'ax-services',
    status: 'ready',
    dependencies: {
      superset: {
        ok: true,
        statusCode: 200,
        url: 'http://127.0.0.1:8088/health',
      },
    },
  });
});

test('request ID normalization trims valid IDs and rejects unsafe IDs', () => {
  expect(normalizeRequestIdHeader('  request-123  ')).toBe('request-123');
  expect(normalizeRequestIdHeader('request_abc.~123')).toBe('request_abc.~123');
  expect(normalizeRequestIdHeader(['request-abc'])).toBe('request-abc');
  expect(normalizeRequestIdHeader(undefined)).toBeUndefined();
  expect(
    normalizeRequestIdHeader(['request-abc', 'request-def']),
  ).toBeUndefined();
  expect(normalizeRequestIdHeader('   ')).toBeUndefined();
  expect(normalizeRequestIdHeader('x'.repeat(129))).toBeUndefined();
  expect(normalizeRequestIdHeader('request\n123')).toBeUndefined();
  expect(normalizeRequestIdHeader('request 123')).toBeUndefined();
  expect(normalizeRequestIdHeader('request,123')).toBeUndefined();
  expect(normalizeRequestIdHeader('request:123')).toBeUndefined();
  expect(normalizeRequestIdHeader('request/123')).toBeUndefined();
});

test('server applies configured Fastify log level', async () => {
  const server = buildServer(
    buildConfig({
      AX_SERVICES_LOG_LEVEL: 'warn',
    }),
    makeSupersetClient(),
  );

  expect(server.log.level).toBe('warn');

  await server.close();
});

test('ready endpoint replaces unsafe request IDs before echoing or forwarding', async () => {
  const seenRequestIds: string[] = [];
  const server = buildServer(
    config,
    makeSupersetClient({
      onHealth(correlationId) {
        if (correlationId) {
          seenRequestIds.push(correlationId);
        }
      },
    }),
  );
  const unsafeRequestId = 'x'.repeat(129);

  const response = await server.inject({
    method: 'GET',
    url: '/ready',
    headers: {
      'x-request-id': unsafeRequestId,
    },
  });

  expect(response.statusCode).toBe(200);
  expect(response.headers['x-request-id']).toEqual(
    expect.stringMatching(uuidPattern),
  );
  expect(response.headers['x-request-id']).not.toBe(unsafeRequestId);
  expect(seenRequestIds).toEqual([response.headers['x-request-id']]);
});

test('ready endpoint returns unavailable when Superset is unreachable', async () => {
  const server = buildServer(
    config,
    makeSupersetClient({
      health: {
        ok: false,
        error: 'connect ECONNREFUSED',
        url: 'http://127.0.0.1:8088/health',
      },
    }),
  );

  const response = await server.inject({
    method: 'GET',
    url: '/ready',
  });

  expect(response.statusCode).toBe(503);
  expect(response.json()).toEqual({
    contractVersion: 'runtime.v1',
    service: 'ax-services',
    status: 'not_ready',
    dependencies: {
      superset: {
        ok: false,
        error: 'connect ECONNREFUSED',
        url: 'http://127.0.0.1:8088/health',
      },
    },
  });
});

test('metadata endpoint returns sanitized Superset metadata probe', async () => {
  const seenRequestIds: string[] = [];
  const server = buildServer(
    config,
    makeSupersetClient({
      metadata: {
        ok: true,
        statusCode: 200,
        url: 'http://127.0.0.1:8088/api/v1/dashboard/_info',
        keyCount: 3,
        keys: ['edit_columns', 'permissions', 'result'],
      },
      onMetadata(correlationId) {
        if (correlationId) {
          seenRequestIds.push(correlationId);
        }
      },
    }),
  );

  const response = await server.inject({
    method: 'GET',
    url: '/metadata',
    headers: {
      'x-request-id': 'request-metadata',
    },
  });

  expect(response.statusCode).toBe(200);
  expect(response.headers['x-request-id']).toBe('request-metadata');
  expect(seenRequestIds).toEqual(['request-metadata']);
  expect(response.json()).toEqual({
    contractVersion: 'runtime.v1',
    service: 'ax-services',
    status: 'ok',
    dependencies: {
      supersetMetadata: {
        ok: true,
        statusCode: 200,
        url: 'http://127.0.0.1:8088/api/v1/dashboard/_info',
        keyCount: 3,
        keys: ['edit_columns', 'permissions', 'result'],
      },
    },
  });
});

test('metadata endpoint returns unavailable when Superset metadata is unreachable', async () => {
  const server = buildServer(
    config,
    makeSupersetClient({
      metadata: {
        ok: false,
        error: 'metadata timeout',
        url: 'http://127.0.0.1:8088/api/v1/dashboard/_info',
      },
    }),
  );

  const response = await server.inject({
    method: 'GET',
    url: '/metadata',
  });

  expect(response.statusCode).toBe(503);
  expect(response.json()).toEqual({
    contractVersion: 'runtime.v1',
    service: 'ax-services',
    status: 'not_ready',
    dependencies: {
      supersetMetadata: {
        ok: false,
        error: 'metadata timeout',
        url: 'http://127.0.0.1:8088/api/v1/dashboard/_info',
      },
    },
  });
});

test('metrics endpoint returns request counters by route', async () => {
  const server = buildServer(
    config,
    makeSupersetClient({
      health: {
        ok: false,
        error: 'connect ECONNREFUSED',
        url: 'http://127.0.0.1:8088/health',
      },
    }),
  );

  await server.inject({
    method: 'GET',
    url: '/health',
  });
  await server.inject({
    method: 'GET',
    url: '/ready',
  });

  const response = await server.inject({
    method: 'GET',
    url: '/metrics',
  });

  expect(response.statusCode).toBe(200);
  expect(response.json()).toMatchObject({
    contractVersion: 'runtime.v1',
    service: 'ax-services',
    status: 'ok',
    requests: {
      total: 2,
      errorCount: 1,
      routes: {
        'GET /health': {
          count: 1,
          errorCount: 0,
        },
        'GET /ready': {
          count: 1,
          errorCount: 1,
        },
      },
    },
  });
  expect(response.json().uptimeSeconds).toBeGreaterThanOrEqual(0);
  expect(response.json().requests.averageDurationMs).toBeGreaterThanOrEqual(0);
  expect(
    response.json().requests.routes['GET /health'].averageDurationMs,
  ).toBeGreaterThanOrEqual(0);
});

test('metrics endpoint aggregates unmatched routes under one key', async () => {
  const server = buildServer(config, makeSupersetClient());

  await server.inject({
    method: 'GET',
    url: '/missing?token=first',
  });
  await server.inject({
    method: 'GET',
    url: '/another-missing?token=second',
  });

  const response = await server.inject({
    method: 'GET',
    url: '/metrics',
  });
  const routes = response.json().requests.routes;

  expect(response.statusCode).toBe(200);
  expect(routes).toMatchObject({
    'GET <unmatched>': {
      count: 2,
      errorCount: 0,
    },
  });
  expect(Object.keys(routes)).not.toContain('GET /another-missing');
  expect(Object.keys(routes)).not.toContain('GET /missing?token=first');
  expect(Object.keys(routes)).not.toContain('GET /another-missing?token=second');
});

test('asset search endpoint delegates to Superset client', async () => {
  const seenRequestIds: string[] = [];
  const server = buildServer(
    config,
    makeSupersetClient({
      search: {
        contractVersion: ASSET_SEARCH_CONTRACT_VERSION,
        assets: [
          {
            assetType: 'dataset',
            id: 1,
            uuid: 'dataset-uuid',
            name: 'sales_fact',
            certified: false,
            relevanceScore: 1,
            owners: [],
            tags: [],
          },
        ],
        warnings: [],
      },
      onSearch(correlationId) {
        if (correlationId) {
          seenRequestIds.push(correlationId);
        }
      },
    }),
  );

  const response = await server.inject({
    method: 'POST',
    url: '/mcp/assets/search',
    headers: {
      'x-request-id': 'request-search',
    },
    payload: {
      contractVersion: ASSET_SEARCH_CONTRACT_VERSION,
      query: 'sales',
      assetTypes: ['dataset'],
      includeCertifiedOnly: false,
      limit: 10,
    },
  });

  expect(response.statusCode).toBe(200);
  expect(response.headers['x-request-id']).toBe('request-search');
  expect(seenRequestIds).toEqual(['request-search']);
  expect(response.json()).toEqual({
    contractVersion: ASSET_SEARCH_CONTRACT_VERSION,
    assets: [
      {
        assetType: 'dataset',
        id: 1,
        uuid: 'dataset-uuid',
        name: 'sales_fact',
        certified: false,
        relevanceScore: 1,
        owners: [],
        tags: [],
      },
    ],
    warnings: [],
  });
});

test('asset search endpoint rejects unsafe query values', async () => {
  const seenRequestIds: string[] = [];
  const server = buildServer(
    config,
    makeSupersetClient({
      onSearch(correlationId) {
        if (correlationId) {
          seenRequestIds.push(correlationId);
        }
      },
    }),
  );

  for (const query of ['   ', 'sales\nregion']) {
    const response = await server.inject({
      method: 'POST',
      url: '/mcp/assets/search',
      payload: {
        contractVersion: ASSET_SEARCH_CONTRACT_VERSION,
        query,
        assetTypes: ['dataset'],
        includeCertifiedOnly: false,
        limit: 10,
      },
    });

    expect(response.statusCode).toBe(400);
  }
  expect(seenRequestIds).toEqual([]);
});

test('permission check endpoint delegates to Superset client', async () => {
  const seenRequestIds: string[] = [];
  const server = buildServer(
    config,
    makeSupersetClient({
      permissionCheck: {
        contractVersion: AUTHORIZATION_CONTRACT_VERSION,
        allowed: true,
        reason: 'allowed by Superset',
      },
      onCheckPermission(correlationId) {
        if (correlationId) {
          seenRequestIds.push(correlationId);
        }
      },
    }),
  );

  const response = await server.inject({
    method: 'POST',
    url: '/mcp/permissions/check',
    headers: {
      'x-request-id': 'request-permission',
    },
    payload: {
      contractVersion: AUTHORIZATION_CONTRACT_VERSION,
      principal: {
        type: 'service',
      },
      resource: {
        type: 'dashboard',
        id: 5,
      },
      action: 'read',
    },
  });

  expect(response.statusCode).toBe(200);
  expect(response.headers['x-request-id']).toBe('request-permission');
  expect(seenRequestIds).toEqual(['request-permission']);
  expect(response.json()).toEqual({
    contractVersion: AUTHORIZATION_CONTRACT_VERSION,
    allowed: true,
    reason: 'allowed by Superset',
  });
});

test('permission check endpoint rejects unsafe authorization strings', async () => {
  const seenRequestIds: string[] = [];
  const server = buildServer(
    config,
    makeSupersetClient({
      onCheckPermission(correlationId) {
        if (correlationId) {
          seenRequestIds.push(correlationId);
        }
      },
    }),
  );

  for (const payload of [
    {
      contractVersion: AUTHORIZATION_CONTRACT_VERSION,
      principal: {
        type: 'user',
        username: 'admin\nroot',
      },
      resource: {
        type: 'dashboard',
        id: 5,
      },
      action: 'read',
    },
    {
      contractVersion: AUTHORIZATION_CONTRACT_VERSION,
      principal: {
        type: 'service',
        roles: ['Admin', '   '],
      },
      resource: {
        type: 'dashboard',
        id: 5,
      },
      action: 'read',
    },
    {
      contractVersion: AUTHORIZATION_CONTRACT_VERSION,
      principal: {
        type: 'service',
      },
      resource: {
        type: 'dashboard',
        uuid: '',
      },
      action: 'read',
    },
  ]) {
    const response = await server.inject({
      method: 'POST',
      url: '/mcp/permissions/check',
      payload,
    });

    expect(response.statusCode).toBe(400);
  }
  expect(seenRequestIds).toEqual([]);
});

test('permission check endpoint returns fail-closed details', async () => {
  const server = buildServer(
    config,
    makeSupersetClient({
      permissionCheck: {
        contractVersion: AUTHORIZATION_CONTRACT_VERSION,
        allowed: false,
        statusCode: 503,
        error: 'connect failed',
      },
    }),
  );

  const response = await server.inject({
    method: 'POST',
    url: '/mcp/permissions/check',
    payload: {
      contractVersion: AUTHORIZATION_CONTRACT_VERSION,
      principal: {
        type: 'service',
      },
      resource: {
        type: 'dashboard',
        id: 5,
      },
      action: 'read',
    },
  });

  expect(response.statusCode).toBe(200);
  expect(response.json()).toEqual({
    contractVersion: AUTHORIZATION_CONTRACT_VERSION,
    allowed: false,
    statusCode: 503,
    error: 'connect failed',
  });
});

test('annotation layer list endpoint delegates to Superset client', async () => {
  const seenRequestIds: string[] = [];
  const server = buildServer(
    config,
    makeSupersetClient({
      annotationLayerList: {
        contractVersion: ANNOTATION_LAYER_LIST_CONTRACT_VERSION,
        annotationLayers: [
          {
            id: 5,
            name: 'Release markers',
            descr: 'Production release windows',
          },
        ],
        count: 1,
        totalCount: 1,
        page: 1,
        pageSize: 10,
        totalPages: 1,
        hasNext: false,
        hasPrevious: false,
        columnsRequested: ['id', 'name'],
        columnsLoaded: ['id', 'name', 'descr'],
        warnings: [],
      },
      onListAnnotationLayers(correlationId) {
        if (correlationId) {
          seenRequestIds.push(correlationId);
        }
      },
    }),
  );

  const response = await server.inject({
    method: 'POST',
    url: '/mcp/annotation-layers/list',
    headers: {
      'x-request-id': 'request-annotation-layers',
    },
    payload: {
      contractVersion: ANNOTATION_LAYER_LIST_CONTRACT_VERSION,
      filters: [],
      selectColumns: ['id', 'name'],
      search: 'release',
      orderDirection: 'asc',
      page: 1,
      pageSize: 10,
    },
  });

  expect(response.statusCode).toBe(200);
  expect(response.headers['x-request-id']).toBe('request-annotation-layers');
  expect(seenRequestIds).toEqual(['request-annotation-layers']);
  expect(response.json()).toEqual({
    contractVersion: ANNOTATION_LAYER_LIST_CONTRACT_VERSION,
    annotationLayers: [
      {
        id: 5,
        name: 'Release markers',
        descr: 'Production release windows',
      },
    ],
    count: 1,
    totalCount: 1,
    page: 1,
    pageSize: 10,
    totalPages: 1,
    hasNext: false,
    hasPrevious: false,
    columnsRequested: ['id', 'name'],
    columnsLoaded: ['id', 'name', 'descr'],
    warnings: [],
  });
});

test('annotation list endpoint delegates to Superset client', async () => {
  const seenRequestIds: string[] = [];
  const server = buildServer(
    config,
    makeSupersetClient({
      annotationList: {
        contractVersion: ANNOTATION_LIST_CONTRACT_VERSION,
        annotations: [
          {
            id: 7,
            shortDescr: 'Deploy',
            longDescr: 'Production deploy',
            layerId: 5,
          },
        ],
        count: 1,
        totalCount: 1,
        page: 1,
        pageSize: 10,
        totalPages: 1,
        hasNext: false,
        hasPrevious: false,
        layerId: 5,
        columnsRequested: ['id', 'short_descr', 'layer_id'],
        columnsLoaded: ['id', 'short_descr', 'long_descr', 'layer_id'],
        warnings: [],
      },
      onListAnnotations(correlationId) {
        if (correlationId) {
          seenRequestIds.push(correlationId);
        }
      },
    }),
  );

  const response = await server.inject({
    method: 'POST',
    url: '/mcp/annotations/list',
    headers: {
      'x-request-id': 'request-annotations',
    },
    payload: {
      contractVersion: ANNOTATION_LIST_CONTRACT_VERSION,
      layerId: 5,
      filters: [],
      selectColumns: ['id', 'short_descr', 'layer_id'],
      search: 'deploy',
      orderDirection: 'asc',
      page: 1,
      pageSize: 10,
    },
  });

  expect(response.statusCode).toBe(200);
  expect(response.headers['x-request-id']).toBe('request-annotations');
  expect(seenRequestIds).toEqual(['request-annotations']);
  expect(response.json()).toEqual({
    contractVersion: ANNOTATION_LIST_CONTRACT_VERSION,
    annotations: [
      {
        id: 7,
        shortDescr: 'Deploy',
        longDescr: 'Production deploy',
        layerId: 5,
      },
    ],
    count: 1,
    totalCount: 1,
    page: 1,
    pageSize: 10,
    totalPages: 1,
    hasNext: false,
    hasPrevious: false,
    layerId: 5,
    columnsRequested: ['id', 'short_descr', 'layer_id'],
    columnsLoaded: ['id', 'short_descr', 'long_descr', 'layer_id'],
    warnings: [],
  });
});

test('dashboard list endpoint delegates to Superset client', async () => {
  const seenRequestIds: string[] = [];
  const server = buildServer(
    config,
    makeSupersetClient({
      dashboardList: {
        contractVersion: DASHBOARD_LIST_CONTRACT_VERSION,
        dashboards: [
          {
            id: 7,
            dashboardTitle: 'Sales dashboard',
            slug: 'sales',
            url: '/superset/dashboard/7/',
          },
        ],
        count: 1,
        totalCount: 1,
        page: 1,
        pageSize: 10,
        totalPages: 1,
        hasNext: false,
        hasPrevious: false,
        columnsRequested: ['id', 'dashboard_title'],
        columnsLoaded: ['id', 'dashboard_title', 'slug', 'url'],
        warnings: [],
      },
      onListDashboards(correlationId) {
        if (correlationId) {
          seenRequestIds.push(correlationId);
        }
      },
    }),
  );

  const response = await server.inject({
    method: 'POST',
    url: '/mcp/dashboards/list',
    headers: {
      'x-request-id': 'request-dashboard-list',
    },
    payload: {
      contractVersion: DASHBOARD_LIST_CONTRACT_VERSION,
      filters: [],
      selectColumns: ['id', 'dashboard_title'],
      search: 'sales',
      orderDirection: 'asc',
      page: 1,
      pageSize: 10,
      createdByMe: false,
      ownedByMe: false,
    },
  });

  expect(response.statusCode).toBe(200);
  expect(response.headers['x-request-id']).toBe('request-dashboard-list');
  expect(seenRequestIds).toEqual(['request-dashboard-list']);
  expect(response.json()).toEqual({
    contractVersion: DASHBOARD_LIST_CONTRACT_VERSION,
    dashboards: [
      {
        id: 7,
        dashboardTitle: 'Sales dashboard',
        slug: 'sales',
        url: '/superset/dashboard/7/',
      },
    ],
    count: 1,
    totalCount: 1,
    page: 1,
    pageSize: 10,
    totalPages: 1,
    hasNext: false,
    hasPrevious: false,
    columnsRequested: ['id', 'dashboard_title'],
    columnsLoaded: ['id', 'dashboard_title', 'slug', 'url'],
    warnings: [],
  });
});

test('dashboard list endpoint rejects unsafe requested columns', async () => {
  const seenRequestIds: string[] = [];
  const server = buildServer(
    config,
    makeSupersetClient({
      onListDashboards(correlationId) {
        if (correlationId) {
          seenRequestIds.push(correlationId);
        }
      },
    }),
  );

  const response = await server.inject({
    method: 'POST',
    url: '/mcp/dashboards/list',
    payload: {
      contractVersion: DASHBOARD_LIST_CONTRACT_VERSION,
      filters: [],
      selectColumns: ['id', 'dashboard_title),page_size:100'],
      orderDirection: 'asc',
      page: 1,
      pageSize: 10,
      createdByMe: false,
      ownedByMe: false,
    },
  });

  expect(response.statusCode).toBe(400);
  expect(seenRequestIds).toEqual([]);
});

test('dashboard list endpoint rejects unsafe ordering columns', async () => {
  const seenRequestIds: string[] = [];
  const server = buildServer(
    config,
    makeSupersetClient({
      onListDashboards(correlationId) {
        if (correlationId) {
          seenRequestIds.push(correlationId);
        }
      },
    }),
  );

  const response = await server.inject({
    method: 'POST',
    url: '/mcp/dashboards/list',
    payload: {
      contractVersion: DASHBOARD_LIST_CONTRACT_VERSION,
      filters: [],
      selectColumns: ['id', 'dashboard_title'],
      orderColumn: 'dashboard_title),page_size:100',
      orderDirection: 'asc',
      page: 1,
      pageSize: 10,
      createdByMe: false,
      ownedByMe: false,
    },
  });

  expect(response.statusCode).toBe(400);
  expect(seenRequestIds).toEqual([]);
});

test('dashboard list endpoint rejects unsafe search values', async () => {
  const seenRequestIds: string[] = [];
  const server = buildServer(
    config,
    makeSupersetClient({
      onListDashboards(correlationId) {
        if (correlationId) {
          seenRequestIds.push(correlationId);
        }
      },
    }),
  );

  for (const search of ['   ', 'sales\nregion']) {
    const response = await server.inject({
      method: 'POST',
      url: '/mcp/dashboards/list',
      payload: {
        contractVersion: DASHBOARD_LIST_CONTRACT_VERSION,
        filters: [],
        selectColumns: ['id', 'dashboard_title'],
        search,
        orderDirection: 'asc',
        page: 1,
        pageSize: 10,
        createdByMe: false,
        ownedByMe: false,
      },
    });

    expect(response.statusCode).toBe(400);
  }
  expect(seenRequestIds).toEqual([]);
});

test('dashboard list endpoint rejects unsafe filter values', async () => {
  const seenRequestIds: string[] = [];
  const server = buildServer(
    config,
    makeSupersetClient({
      onListDashboards(correlationId) {
        if (correlationId) {
          seenRequestIds.push(correlationId);
        }
      },
    }),
  );

  for (const value of ['sales\nregion', ['sales', 'north\rregion']]) {
    const response = await server.inject({
      method: 'POST',
      url: '/mcp/dashboards/list',
      payload: {
        contractVersion: DASHBOARD_LIST_CONTRACT_VERSION,
        filters: [{ col: 'dashboard_title', opr: 'ct', value }],
        selectColumns: ['id', 'dashboard_title'],
        orderDirection: 'asc',
        page: 1,
        pageSize: 10,
        createdByMe: false,
        ownedByMe: false,
      },
    });

    expect(response.statusCode).toBe(400);
  }
  expect(seenRequestIds).toEqual([]);
});

test('chart list endpoint delegates to Superset client', async () => {
  const seenRequestIds: string[] = [];
  const server = buildServer(
    config,
    makeSupersetClient({
      chartList: {
        contractVersion: CHART_LIST_CONTRACT_VERSION,
        charts: [
          {
            id: 9,
            sliceName: 'Sales by region',
            vizType: 'bar',
            url: '/explore/?slice_id=9',
          },
        ],
        count: 1,
        totalCount: 1,
        page: 1,
        pageSize: 10,
        totalPages: 1,
        hasNext: false,
        hasPrevious: false,
        columnsRequested: ['id', 'slice_name'],
        columnsLoaded: ['id', 'slice_name', 'viz_type', 'url'],
        warnings: [],
      },
      onListCharts(correlationId) {
        if (correlationId) {
          seenRequestIds.push(correlationId);
        }
      },
    }),
  );

  const response = await server.inject({
    method: 'POST',
    url: '/mcp/charts/list',
    headers: {
      'x-request-id': 'request-chart-list',
    },
    payload: {
      contractVersion: CHART_LIST_CONTRACT_VERSION,
      filters: [],
      selectColumns: ['id', 'slice_name'],
      search: 'sales',
      orderDirection: 'asc',
      page: 1,
      pageSize: 10,
      createdByMe: false,
      ownedByMe: false,
    },
  });

  expect(response.statusCode).toBe(200);
  expect(response.headers['x-request-id']).toBe('request-chart-list');
  expect(seenRequestIds).toEqual(['request-chart-list']);
  expect(response.json()).toEqual({
    contractVersion: CHART_LIST_CONTRACT_VERSION,
    charts: [
      {
        id: 9,
        sliceName: 'Sales by region',
        vizType: 'bar',
        url: '/explore/?slice_id=9',
      },
    ],
    count: 1,
    totalCount: 1,
    page: 1,
    pageSize: 10,
    totalPages: 1,
    hasNext: false,
    hasPrevious: false,
    columnsRequested: ['id', 'slice_name'],
    columnsLoaded: ['id', 'slice_name', 'viz_type', 'url'],
    warnings: [],
  });
});

test('database list endpoint delegates to Superset client', async () => {
  const seenRequestIds: string[] = [];
  const server = buildServer(
    config,
    makeSupersetClient({
      databaseList: {
        contractVersion: DATABASE_LIST_CONTRACT_VERSION,
        databases: [
          {
            id: 13,
            databaseName: 'examples',
            backend: 'postgresql',
            exposeInSqllab: true,
          },
        ],
        count: 1,
        totalCount: 1,
        page: 1,
        pageSize: 10,
        totalPages: 1,
        hasNext: false,
        hasPrevious: false,
        columnsRequested: ['id', 'database_name'],
        columnsLoaded: ['id', 'database_name', 'backend', 'expose_in_sqllab'],
        warnings: [],
      },
      onListDatabases(correlationId) {
        if (correlationId) {
          seenRequestIds.push(correlationId);
        }
      },
    }),
  );

  const response = await server.inject({
    method: 'POST',
    url: '/mcp/databases/list',
    headers: {
      'x-request-id': 'request-database-list',
    },
    payload: {
      contractVersion: DATABASE_LIST_CONTRACT_VERSION,
      filters: [],
      selectColumns: ['id', 'database_name'],
      search: 'examples',
      orderDirection: 'asc',
      page: 1,
      pageSize: 10,
      createdByMe: false,
    },
  });

  expect(response.statusCode).toBe(200);
  expect(response.headers['x-request-id']).toBe('request-database-list');
  expect(seenRequestIds).toEqual(['request-database-list']);
  expect(response.json()).toEqual({
    contractVersion: DATABASE_LIST_CONTRACT_VERSION,
    databases: [
      {
        id: 13,
        databaseName: 'examples',
        backend: 'postgresql',
        exposeInSqllab: true,
      },
    ],
    count: 1,
    totalCount: 1,
    page: 1,
    pageSize: 10,
    totalPages: 1,
    hasNext: false,
    hasPrevious: false,
    columnsRequested: ['id', 'database_name'],
    columnsLoaded: ['id', 'database_name', 'backend', 'expose_in_sqllab'],
    warnings: [],
  });
});

test('dataset list endpoint delegates to Superset client', async () => {
  const seenRequestIds: string[] = [];
  const server = buildServer(
    config,
    makeSupersetClient({
      datasetList: {
        contractVersion: DATASET_LIST_CONTRACT_VERSION,
        datasets: [
          {
            id: 11,
            tableName: 'sales_fact',
            schema: 'public',
            databaseName: 'examples',
            url: '/explore/?datasource_type=table&datasource_id=11',
          },
        ],
        count: 1,
        totalCount: 1,
        page: 1,
        pageSize: 10,
        totalPages: 1,
        hasNext: false,
        hasPrevious: false,
        columnsRequested: ['id', 'table_name'],
        columnsLoaded: ['id', 'table_name', 'schema', 'database_name', 'url'],
        warnings: [],
      },
      onListDatasets(correlationId) {
        if (correlationId) {
          seenRequestIds.push(correlationId);
        }
      },
    }),
  );

  const response = await server.inject({
    method: 'POST',
    url: '/mcp/datasets/list',
    headers: {
      'x-request-id': 'request-dataset-list',
    },
    payload: {
      contractVersion: DATASET_LIST_CONTRACT_VERSION,
      filters: [],
      selectColumns: ['id', 'table_name'],
      search: 'sales',
      orderDirection: 'asc',
      page: 1,
      pageSize: 10,
      createdByMe: false,
      ownedByMe: false,
    },
  });

  expect(response.statusCode).toBe(200);
  expect(response.headers['x-request-id']).toBe('request-dataset-list');
  expect(seenRequestIds).toEqual(['request-dataset-list']);
  expect(response.json()).toEqual({
    contractVersion: DATASET_LIST_CONTRACT_VERSION,
    datasets: [
      {
        id: 11,
        tableName: 'sales_fact',
        schema: 'public',
        databaseName: 'examples',
        url: '/explore/?datasource_type=table&datasource_id=11',
      },
    ],
    count: 1,
    totalCount: 1,
    page: 1,
    pageSize: 10,
    totalPages: 1,
    hasNext: false,
    hasPrevious: false,
    columnsRequested: ['id', 'table_name'],
    columnsLoaded: ['id', 'table_name', 'schema', 'database_name', 'url'],
    warnings: [],
  });
});

test('saved query list endpoint delegates to Superset client', async () => {
  const seenRequestIds: string[] = [];
  const server = buildServer(
    config,
    makeSupersetClient({
      savedQueryList: {
        contractVersion: SAVED_QUERY_LIST_CONTRACT_VERSION,
        savedQueries: [
          {
            id: 17,
            label: 'Revenue query',
            dbId: 3,
            schema: 'public',
          },
        ],
        count: 1,
        totalCount: 1,
        page: 1,
        pageSize: 10,
        totalPages: 1,
        hasNext: false,
        hasPrevious: false,
        columnsRequested: ['id', 'label'],
        columnsLoaded: ['id', 'label', 'db_id', 'schema'],
        warnings: [],
      },
      onListSavedQueries(correlationId) {
        if (correlationId) {
          seenRequestIds.push(correlationId);
        }
      },
    }),
  );

  const response = await server.inject({
    method: 'POST',
    url: '/mcp/saved-queries/list',
    headers: {
      'x-request-id': 'request-saved-query-list',
    },
    payload: {
      contractVersion: SAVED_QUERY_LIST_CONTRACT_VERSION,
      filters: [],
      selectColumns: ['id', 'label'],
      search: 'revenue',
      orderDirection: 'asc',
      page: 1,
      pageSize: 10,
    },
  });

  expect(response.statusCode).toBe(200);
  expect(response.headers['x-request-id']).toBe('request-saved-query-list');
  expect(seenRequestIds).toEqual(['request-saved-query-list']);
  expect(response.json()).toEqual({
    contractVersion: SAVED_QUERY_LIST_CONTRACT_VERSION,
    savedQueries: [
      {
        id: 17,
        label: 'Revenue query',
        dbId: 3,
        schema: 'public',
      },
    ],
    count: 1,
    totalCount: 1,
    page: 1,
    pageSize: 10,
    totalPages: 1,
    hasNext: false,
    hasPrevious: false,
    columnsRequested: ['id', 'label'],
    columnsLoaded: ['id', 'label', 'db_id', 'schema'],
    warnings: [],
  });
});

test('query list endpoint delegates to Superset client', async () => {
  const seenRequestIds: string[] = [];
  const server = buildServer(
    config,
    makeSupersetClient({
      queryList: {
        contractVersion: QUERY_LIST_CONTRACT_VERSION,
        queries: [
          {
            id: 11,
            sql: 'SELECT 1',
            status: 'success',
            databaseId: 3,
            schema: 'public',
          },
        ],
        count: 1,
        totalCount: 1,
        page: 1,
        pageSize: 10,
        totalPages: 1,
        hasNext: false,
        hasPrevious: false,
        columnsRequested: ['id', 'status'],
        columnsLoaded: ['id', 'sql', 'status', 'database_id', 'schema'],
        warnings: [],
      },
      onListQueries(correlationId) {
        if (correlationId) {
          seenRequestIds.push(correlationId);
        }
      },
    }),
  );

  const response = await server.inject({
    method: 'POST',
    url: '/mcp/queries/list',
    headers: {
      'x-request-id': 'request-query-list',
    },
    payload: {
      contractVersion: QUERY_LIST_CONTRACT_VERSION,
      filters: [],
      selectColumns: ['id', 'status'],
      search: 'select',
      orderDirection: 'desc',
      page: 1,
      pageSize: 10,
    },
  });

  expect(response.statusCode).toBe(200);
  expect(response.headers['x-request-id']).toBe('request-query-list');
  expect(seenRequestIds).toEqual(['request-query-list']);
  expect(response.json()).toEqual({
    contractVersion: QUERY_LIST_CONTRACT_VERSION,
    queries: [
      {
        id: 11,
        sql: 'SELECT 1',
        status: 'success',
        databaseId: 3,
        schema: 'public',
      },
    ],
    count: 1,
    totalCount: 1,
    page: 1,
    pageSize: 10,
    totalPages: 1,
    hasNext: false,
    hasPrevious: false,
    columnsRequested: ['id', 'status'],
    columnsLoaded: ['id', 'sql', 'status', 'database_id', 'schema'],
    warnings: [],
  });
});

test('report list endpoint delegates to Superset client', async () => {
  const seenRequestIds: string[] = [];
  const server = buildServer(
    config,
    makeSupersetClient({
      reportList: {
        contractVersion: REPORT_LIST_CONTRACT_VERSION,
        reports: [
          {
            id: 23,
            name: 'Daily report',
            type: 'Report',
            active: true,
            crontab: '0 9 * * *',
          },
        ],
        count: 1,
        totalCount: 1,
        page: 1,
        pageSize: 10,
        totalPages: 1,
        hasNext: false,
        hasPrevious: false,
        columnsRequested: ['id', 'name'],
        columnsLoaded: ['id', 'name', 'type', 'active', 'crontab'],
        warnings: [],
      },
      onListReports(correlationId) {
        if (correlationId) {
          seenRequestIds.push(correlationId);
        }
      },
    }),
  );

  const response = await server.inject({
    method: 'POST',
    url: '/mcp/reports/list',
    headers: {
      'x-request-id': 'request-report-list',
    },
    payload: {
      contractVersion: REPORT_LIST_CONTRACT_VERSION,
      filters: [],
      selectColumns: ['id', 'name'],
      search: 'daily',
      orderDirection: 'asc',
      page: 1,
      pageSize: 10,
    },
  });

  expect(response.statusCode).toBe(200);
  expect(response.headers['x-request-id']).toBe('request-report-list');
  expect(seenRequestIds).toEqual(['request-report-list']);
  expect(response.json()).toEqual({
    contractVersion: REPORT_LIST_CONTRACT_VERSION,
    reports: [
      {
        id: 23,
        name: 'Daily report',
        type: 'Report',
        active: true,
        crontab: '0 9 * * *',
      },
    ],
    count: 1,
    totalCount: 1,
    page: 1,
    pageSize: 10,
    totalPages: 1,
    hasNext: false,
    hasPrevious: false,
    columnsRequested: ['id', 'name'],
    columnsLoaded: ['id', 'name', 'type', 'active', 'crontab'],
    warnings: [],
  });
});

test('role list endpoint delegates to Superset client', async () => {
  const seenRequestIds: string[] = [];
  const server = buildServer(
    config,
    makeSupersetClient({
      roleList: {
        contractVersion: ROLE_LIST_CONTRACT_VERSION,
        roles: [
          {
            id: 31,
            name: 'Admin',
          },
        ],
        count: 1,
        totalCount: 1,
        page: 1,
        pageSize: 10,
        totalPages: 1,
        hasNext: false,
        hasPrevious: false,
        columnsRequested: ['id', 'name'],
        columnsLoaded: ['id', 'name'],
        warnings: [],
      },
      onListRoles(correlationId) {
        if (correlationId) {
          seenRequestIds.push(correlationId);
        }
      },
    }),
  );

  const response = await server.inject({
    method: 'POST',
    url: '/mcp/roles/list',
    headers: {
      'x-request-id': 'request-role-list',
    },
    payload: {
      contractVersion: ROLE_LIST_CONTRACT_VERSION,
      filters: [],
      selectColumns: ['id', 'name'],
      search: 'admin',
      orderDirection: 'asc',
      page: 1,
      pageSize: 10,
    },
  });

  expect(response.statusCode).toBe(200);
  expect(response.headers['x-request-id']).toBe('request-role-list');
  expect(seenRequestIds).toEqual(['request-role-list']);
  expect(response.json()).toEqual({
    contractVersion: ROLE_LIST_CONTRACT_VERSION,
    roles: [
      {
        id: 31,
        name: 'Admin',
      },
    ],
    count: 1,
    totalCount: 1,
    page: 1,
    pageSize: 10,
    totalPages: 1,
    hasNext: false,
    hasPrevious: false,
    columnsRequested: ['id', 'name'],
    columnsLoaded: ['id', 'name'],
    warnings: [],
  });
});

test('RLS filter list endpoint delegates to Superset client', async () => {
  const seenRequestIds: string[] = [];
  const server = buildServer(
    config,
    makeSupersetClient({
      rlsList: {
        contractVersion: RLS_LIST_CONTRACT_VERSION,
        rlsFilters: [
          {
            id: 42,
            name: 'regional_sales',
            filterType: 'Regular',
            tables: [{ id: 7, tableName: 'sales' }],
            roles: [{ id: 3, name: 'Alpha' }],
            clause: 'region = "EMEA"',
          },
        ],
        count: 1,
        totalCount: 1,
        page: 1,
        pageSize: 10,
        totalPages: 1,
        hasNext: false,
        hasPrevious: false,
        columnsRequested: ['id', 'name', 'filter_type', 'tables', 'roles'],
        columnsLoaded: ['id', 'name', 'filter_type', 'tables', 'roles'],
        warnings: [],
      },
      onListRlsFilters(correlationId) {
        if (correlationId) {
          seenRequestIds.push(correlationId);
        }
      },
    }),
  );

  const response = await server.inject({
    method: 'POST',
    url: '/mcp/rls-filters/list',
    headers: {
      'x-request-id': 'request-rls-list',
    },
    payload: {
      contractVersion: RLS_LIST_CONTRACT_VERSION,
      filters: [],
      selectColumns: ['id', 'name', 'filter_type', 'tables', 'roles'],
      search: 'regional',
      orderDirection: 'asc',
      page: 1,
      pageSize: 10,
    },
  });

  expect(response.statusCode).toBe(200);
  expect(response.headers['x-request-id']).toBe('request-rls-list');
  expect(seenRequestIds).toEqual(['request-rls-list']);
  expect(response.json()).toEqual({
    contractVersion: RLS_LIST_CONTRACT_VERSION,
    rlsFilters: [
      {
        id: 42,
        name: 'regional_sales',
        filterType: 'Regular',
        tables: [{ id: 7, tableName: 'sales' }],
        roles: [{ id: 3, name: 'Alpha' }],
        clause: 'region = "EMEA"',
      },
    ],
    count: 1,
    totalCount: 1,
    page: 1,
    pageSize: 10,
    totalPages: 1,
    hasNext: false,
    hasPrevious: false,
    columnsRequested: ['id', 'name', 'filter_type', 'tables', 'roles'],
    columnsLoaded: ['id', 'name', 'filter_type', 'tables', 'roles'],
    warnings: [],
  });
});

test('tag list endpoint delegates to Superset client', async () => {
  const seenRequestIds: string[] = [];
  const server = buildServer(
    config,
    makeSupersetClient({
      tagList: {
        contractVersion: TAG_LIST_CONTRACT_VERSION,
        tags: [
          {
            id: 19,
            name: 'finance',
            type: 'custom',
          },
        ],
        count: 1,
        totalCount: 1,
        page: 1,
        pageSize: 10,
        totalPages: 1,
        hasNext: false,
        hasPrevious: false,
        columnsRequested: ['id', 'name'],
        columnsLoaded: ['id', 'name', 'type'],
        warnings: [],
      },
      onListTags(correlationId) {
        if (correlationId) {
          seenRequestIds.push(correlationId);
        }
      },
    }),
  );

  const response = await server.inject({
    method: 'POST',
    url: '/mcp/tags/list',
    headers: {
      'x-request-id': 'request-tag-list',
    },
    payload: {
      contractVersion: TAG_LIST_CONTRACT_VERSION,
      filters: [],
      selectColumns: ['id', 'name'],
      search: 'finance',
      orderDirection: 'asc',
      page: 1,
      pageSize: 10,
    },
  });

  expect(response.statusCode).toBe(200);
  expect(response.headers['x-request-id']).toBe('request-tag-list');
  expect(seenRequestIds).toEqual(['request-tag-list']);
  expect(response.json()).toEqual({
    contractVersion: TAG_LIST_CONTRACT_VERSION,
    tags: [
      {
        id: 19,
        name: 'finance',
        type: 'custom',
      },
    ],
    count: 1,
    totalCount: 1,
    page: 1,
    pageSize: 10,
    totalPages: 1,
    hasNext: false,
    hasPrevious: false,
    columnsRequested: ['id', 'name'],
    columnsLoaded: ['id', 'name', 'type'],
    warnings: [],
  });
});

test('task list endpoint delegates to Superset client', async () => {
  const seenRequestIds: string[] = [];
  const server = buildServer(
    config,
    makeSupersetClient({
      taskList: {
        contractVersion: TASK_LIST_CONTRACT_VERSION,
        tasks: [
          {
            id: 31,
            uuid: 'task-uuid',
            taskType: 'sql_execution',
            taskKey: 'task-key',
            taskName: 'Refresh cache',
            status: 'success',
            scope: 'private',
          },
        ],
        count: 1,
        totalCount: 1,
        page: 1,
        pageSize: 10,
        totalPages: 1,
        hasNext: false,
        hasPrevious: false,
        columnsRequested: ['id', 'task_name'],
        columnsLoaded: [
          'id',
          'uuid',
          'task_type',
          'task_key',
          'task_name',
          'status',
          'scope',
        ],
        warnings: [],
      },
      onListTasks(correlationId) {
        if (correlationId) {
          seenRequestIds.push(correlationId);
        }
      },
    }),
  );

  const response = await server.inject({
    method: 'POST',
    url: '/mcp/tasks/list',
    headers: {
      'x-request-id': 'request-task-list',
    },
    payload: {
      contractVersion: TASK_LIST_CONTRACT_VERSION,
      filters: [],
      selectColumns: ['id', 'task_name'],
      search: 'refresh',
      orderDirection: 'asc',
      page: 1,
      pageSize: 10,
    },
  });

  expect(response.statusCode).toBe(200);
  expect(response.headers['x-request-id']).toBe('request-task-list');
  expect(seenRequestIds).toEqual(['request-task-list']);
  expect(response.json()).toEqual({
    contractVersion: TASK_LIST_CONTRACT_VERSION,
    tasks: [
      {
        id: 31,
        uuid: 'task-uuid',
        taskType: 'sql_execution',
        taskKey: 'task-key',
        taskName: 'Refresh cache',
        status: 'success',
        scope: 'private',
      },
    ],
    count: 1,
    totalCount: 1,
    page: 1,
    pageSize: 10,
    totalPages: 1,
    hasNext: false,
    hasPrevious: false,
    columnsRequested: ['id', 'task_name'],
    columnsLoaded: [
      'id',
      'uuid',
      'task_type',
      'task_key',
      'task_name',
      'status',
      'scope',
    ],
    warnings: [],
  });
});

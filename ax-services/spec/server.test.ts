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
import { buildServer } from '../src/server';
import {
  ASSET_SEARCH_CONTRACT_VERSION,
  AssetSearchResponse,
} from '../src/contracts/assetSearch';
import {
  DependencyHealth,
  DependencyMetadata,
  SupersetAssetSearchClient,
  SupersetHealthClient,
  SupersetMetadataClient,
} from '../src/supersetClient';

const config = {
  ...buildConfig({}),
  logLevel: 'silent',
};

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
  onSearch,
  search = {
    contractVersion: ASSET_SEARCH_CONTRACT_VERSION,
    assets: [],
    warnings: [],
  },
}: {
  health?: DependencyHealth;
  metadata?: DependencyMetadata;
  search?: AssetSearchResponse;
  onHealth?: (correlationId?: string) => void;
  onMetadata?: (correlationId?: string) => void;
  onSearch?: (correlationId?: string) => void;
} = {}): SupersetHealthClient & SupersetMetadataClient & SupersetAssetSearchClient {
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
  });
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

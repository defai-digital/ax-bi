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
import { afterEach, expect, test } from '@jest/globals';

import { buildConfig } from '../src/config';
import { ANNOTATION_LIST_CONTRACT_VERSION } from '../src/contracts/annotationList';
import { ANNOTATION_LAYER_LIST_CONTRACT_VERSION } from '../src/contracts/annotationLayerList';
import { ASSET_SEARCH_CONTRACT_VERSION } from '../src/contracts/assetSearch';
import { AUTHORIZATION_CONTRACT_VERSION } from '../src/contracts/authorization';
import { CHART_LIST_CONTRACT_VERSION } from '../src/contracts/chartList';
import { DASHBOARD_LIST_CONTRACT_VERSION } from '../src/contracts/dashboardList';
import { DATABASE_LIST_CONTRACT_VERSION } from '../src/contracts/databaseList';
import { DATASET_LIST_CONTRACT_VERSION } from '../src/contracts/datasetList';
import { QUERY_LIST_CONTRACT_VERSION } from '../src/contracts/queryList';
import { REPORT_LIST_CONTRACT_VERSION } from '../src/contracts/reportList';
import { ROLE_LIST_CONTRACT_VERSION } from '../src/contracts/roleList';
import { RLS_LIST_CONTRACT_VERSION } from '../src/contracts/rlsList';
import { SAVED_QUERY_LIST_CONTRACT_VERSION } from '../src/contracts/savedQueryList';
import { TAG_LIST_CONTRACT_VERSION } from '../src/contracts/tagList';
import { TASK_LIST_CONTRACT_VERSION } from '../src/contracts/taskList';
import { SupersetClient } from '../src/supersetClient';

const originalFetch = global.fetch;

afterEach(() => {
  global.fetch = originalFetch;
});

type ClientRequest<TMethod extends keyof SupersetClient> =
  SupersetClient[TMethod] extends (
    request: infer TRequest,
    ...args: unknown[]
  ) => unknown
    ? TRequest
    : never;

function requestFor<TMethod extends keyof SupersetClient>(
  _method: TMethod,
  request: unknown,
): ClientRequest<TMethod> {
  return request as ClientRequest<TMethod>;
}

test('checkHealth returns Superset status and forwards request ID', async () => {
  let seenInput: RequestInfo | URL | undefined;
  let seenInit: RequestInit | undefined;
  global.fetch = async (input, init) => {
    seenInput = input;
    seenInit = init;
    return new Response('OK', { status: 200 });
  };
  const client = new SupersetClient(buildConfig({}));

  const result = await client.checkHealth('request-abc');

  expect(result).toEqual({
    ok: true,
    statusCode: 200,
    url: 'http://127.0.0.1:8088/health',
  });
  expect(seenInput).toBe('http://127.0.0.1:8088/health');
  expect(seenInit?.headers).toEqual({
    'x-request-id': 'request-abc',
  });
});

test('checkHealth bounds and sanitizes dependency errors', async () => {
  global.fetch = async () => {
    throw new Error(`  connect\n${'x'.repeat(300)}  `);
  };
  const client = new SupersetClient(buildConfig({}));

  const result = await client.checkHealth();

  expect(result.ok).toBe(false);
  expect(result.error).toBeDefined();
  expect(result.error).not.toContain('\n');
  expect(result.error?.startsWith('connect ')).toBe(true);
  expect(result.error?.length).toBeLessThanOrEqual(256);
});

test('checkHealth normalizes direct caller request IDs before forwarding', async () => {
  const seenInits: RequestInit[] = [];
  global.fetch = async (_input, init) => {
    seenInits.push(init ?? {});
    return new Response('OK', { status: 200 });
  };
  const client = new SupersetClient(buildConfig({}));

  await client.checkHealth('  request-abc  ');
  await client.checkHealth('request abc');
  await client.checkHealth('request,abc');

  expect(seenInits[0]?.headers).toEqual({
    'x-request-id': 'request-abc',
  });
  expect(seenInits[1]?.headers).toEqual({});
  expect(seenInits[2]?.headers).toEqual({});
});

test('checkPermission posts authorization request to Superset', async () => {
  let seenInput: RequestInfo | URL | undefined;
  let seenInit: RequestInit | undefined;
  global.fetch = async (input, init) => {
    seenInput = input;
    seenInit = init;
    return Response.json(
      {
        contractVersion: AUTHORIZATION_CONTRACT_VERSION,
        allowed: true,
        reason: 'allowed by Superset',
      },
      { status: 200 },
    );
  };
  const client = new SupersetClient(
    buildConfig({
      AX_SUPERSET_INTERNAL_TOKEN: 'token-123',
    }),
  );

  const result = await client.checkPermission(
    {
      contractVersion: AUTHORIZATION_CONTRACT_VERSION,
      principal: {
        type: 'user',
        userId: 7,
      },
      resource: {
        type: 'dataset',
        id: 42,
      },
      action: 'read',
    },
    'request-abc',
  );

  expect(result).toEqual({
    contractVersion: AUTHORIZATION_CONTRACT_VERSION,
    allowed: true,
    reason: 'allowed by Superset',
    statusCode: 200,
  });
  expect(seenInput).toBe(
    'http://127.0.0.1:8088/api/v1/security/permissions/check',
  );
  expect(seenInit).toEqual(
    expect.objectContaining({
      method: 'POST',
      headers: {
        authorization: 'Bearer token-123',
        'content-type': 'application/json',
        'x-request-id': 'request-abc',
      },
    }),
  );
  expect(JSON.parse(String(seenInit?.body))).toEqual({
    contractVersion: AUTHORIZATION_CONTRACT_VERSION,
    principal: {
      type: 'user',
      userId: 7,
    },
    resource: {
      type: 'dataset',
      id: 42,
    },
    action: 'read',
  });
});

test('checkPermission sanitizes upstream denial reasons', async () => {
  global.fetch = async () =>
    Response.json(
      {
        contractVersion: AUTHORIZATION_CONTRACT_VERSION,
        allowed: false,
        reason: ` denied\n${'x'.repeat(300)} `,
      },
      { status: 200 },
    );
  const client = new SupersetClient(buildConfig({}));

  const result = await client.checkPermission({
    contractVersion: AUTHORIZATION_CONTRACT_VERSION,
    principal: {
      type: 'user',
      userId: 7,
    },
    resource: {
      type: 'dataset',
      id: 42,
    },
    action: 'read',
  });

  expect(result.allowed).toBe(false);
  expect(result.reason).toBeDefined();
  expect(result.reason).not.toContain('\n');
  expect(result.reason?.startsWith('denied ')).toBe(true);
  expect(result.reason?.length).toBeLessThanOrEqual(256);
});

test('checkPermission fails closed when Superset cannot be reached', async () => {
  global.fetch = async () => {
    throw new Error('connect failed');
  };
  const client = new SupersetClient(buildConfig({}));

  const result = await client.checkPermission({
    contractVersion: AUTHORIZATION_CONTRACT_VERSION,
    principal: {
      type: 'service',
    },
    resource: {
      type: 'dashboard',
      id: 5,
    },
    action: 'read',
  });

  expect(result).toEqual({
    contractVersion: AUTHORIZATION_CONTRACT_VERSION,
    allowed: false,
    error: 'connect failed',
  });
});

test('checkPermission fails closed for invalid numeric identifiers', async () => {
  let fetchCalled = false;
  global.fetch = async () => {
    fetchCalled = true;
    throw new Error('unexpected fetch');
  };
  const client = new SupersetClient(buildConfig({}));

  const result = await client.checkPermission({
    contractVersion: AUTHORIZATION_CONTRACT_VERSION,
    principal: {
      type: 'user',
      userId: -1,
    },
    resource: {
      type: 'dashboard',
      id: 5.5,
    },
    action: 'read',
  });

  expect(result).toEqual({
    contractVersion: AUTHORIZATION_CONTRACT_VERSION,
    allowed: false,
    error: 'authorization request contains invalid numeric identifier',
  });
  expect(fetchCalled).toBe(false);
});

test('checkPermission fails closed for unsafe numeric identifiers', async () => {
  let fetchCalled = false;
  global.fetch = async () => {
    fetchCalled = true;
    throw new Error('unexpected fetch');
  };
  const client = new SupersetClient(buildConfig({}));

  const result = await client.checkPermission({
    contractVersion: AUTHORIZATION_CONTRACT_VERSION,
    principal: {
      type: 'user',
      userId: Number.MAX_SAFE_INTEGER + 1,
    },
    resource: {
      type: 'dashboard',
      id: 5,
    },
    action: 'read',
  });

  expect(result).toEqual({
    contractVersion: AUTHORIZATION_CONTRACT_VERSION,
    allowed: false,
    error: 'authorization request contains invalid numeric identifier',
  });
  expect(fetchCalled).toBe(false);
});

test('checkPermission fails closed for invalid request shapes', async () => {
  let fetchCalled = false;
  global.fetch = async () => {
    fetchCalled = true;
    throw new Error('unexpected fetch');
  };
  const client = new SupersetClient(buildConfig({}));

  const result = await client.checkPermission(requestFor('checkPermission', {
    contractVersion: AUTHORIZATION_CONTRACT_VERSION,
    principal: {
      type: 'service',
      roles: ['Admin', 7],
    },
    resource: {
      type: 'dashboard',
      id: 5,
    },
    action: 'read',
  }));

  expect(result).toEqual({
    contractVersion: AUTHORIZATION_CONTRACT_VERSION,
    allowed: false,
    error: 'authorization request contains invalid request shape',
  });
  expect(fetchCalled).toBe(false);
});

test('checkPermission fails closed for extra authorization fields', async () => {
  let fetchCalled = false;
  global.fetch = async () => {
    fetchCalled = true;
    throw new Error('unexpected fetch');
  };
  const client = new SupersetClient(buildConfig({}));

  for (const request of [
    {
      contractVersion: AUTHORIZATION_CONTRACT_VERSION,
      principal: {
        type: 'service',
      },
      resource: {
        type: 'dashboard',
        id: 5,
      },
      action: 'read',
      tenant: 'ax',
    },
    {
      contractVersion: AUTHORIZATION_CONTRACT_VERSION,
      principal: {
        type: 'service',
        tenant: 'ax',
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
        id: 5,
        slug: 'sales',
      },
      action: 'read',
    },
  ]) {
    const result = await client.checkPermission(
      requestFor('checkPermission', request),
    );

    expect(result).toEqual({
      contractVersion: AUTHORIZATION_CONTRACT_VERSION,
      allowed: false,
      error: 'authorization request contains invalid request shape',
    });
  }

  expect(fetchCalled).toBe(false);
});

test('checkPermission fails closed for unsafe authorization strings', async () => {
  let fetchCalled = false;
  global.fetch = async () => {
    fetchCalled = true;
    throw new Error('unexpected fetch');
  };
  const client = new SupersetClient(buildConfig({}));

  for (const request of [
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
    const result = await client.checkPermission(
      requestFor('checkPermission', request),
    );

    expect(result).toEqual({
      contractVersion: AUTHORIZATION_CONTRACT_VERSION,
      allowed: false,
      error: 'authorization request contains invalid request shape',
    });
  }

  expect(fetchCalled).toBe(false);
});

test('checkPermission fails closed for wrong authorization request contract version', async () => {
  let fetchCalled = false;
  global.fetch = async () => {
    fetchCalled = true;
    throw new Error('unexpected fetch');
  };
  const client = new SupersetClient(buildConfig({}));

  const result = await client.checkPermission(
    requestFor('checkPermission', {
      contractVersion: 'authorization.v0',
      principal: {
        type: 'service',
      },
      resource: {
        type: 'dashboard',
        id: 5,
      },
      action: 'read',
    }),
  );

  expect(result).toEqual({
    contractVersion: AUTHORIZATION_CONTRACT_VERSION,
    allowed: false,
    error: 'authorization request contains invalid request shape',
  });
  expect(fetchCalled).toBe(false);
});

test('checkPermission fails closed for non-success Superset responses', async () => {
  global.fetch = async () =>
    Response.json(
      {
        contractVersion: AUTHORIZATION_CONTRACT_VERSION,
        allowed: true,
        reason: 'misleading upstream body',
      },
      { status: 500 },
    );
  const client = new SupersetClient(buildConfig({}));

  const result = await client.checkPermission({
    contractVersion: AUTHORIZATION_CONTRACT_VERSION,
    principal: {
      type: 'service',
    },
    resource: {
      type: 'dashboard',
      id: 5,
    },
    action: 'read',
  });

  expect(result).toEqual({
    contractVersion: AUTHORIZATION_CONTRACT_VERSION,
    allowed: false,
    statusCode: 500,
  });
});

test('checkPermission fails closed for missing authorization contract version', async () => {
  global.fetch = async () =>
    Response.json(
      {
        allowed: true,
        reason: 'missing contract version',
      },
      { status: 200 },
    );
  const client = new SupersetClient(buildConfig({}));

  const result = await client.checkPermission({
    contractVersion: AUTHORIZATION_CONTRACT_VERSION,
    principal: {
      type: 'service',
    },
    resource: {
      type: 'dashboard',
      id: 5,
    },
    action: 'read',
  });

  expect(result).toEqual({
    contractVersion: AUTHORIZATION_CONTRACT_VERSION,
    allowed: false,
    error: 'authorization response contract version mismatch',
    statusCode: 200,
  });
});

test('checkPermission fails closed for wrong authorization contract version', async () => {
  global.fetch = async () =>
    Response.json(
      {
        contractVersion: 'authorization.v0',
        allowed: true,
        reason: 'old contract version',
      },
      { status: 200 },
    );
  const client = new SupersetClient(buildConfig({}));

  const result = await client.checkPermission({
    contractVersion: AUTHORIZATION_CONTRACT_VERSION,
    principal: {
      type: 'service',
    },
    resource: {
      type: 'dashboard',
      id: 5,
    },
    action: 'read',
  });

  expect(result).toEqual({
    contractVersion: AUTHORIZATION_CONTRACT_VERSION,
    allowed: false,
    error: 'authorization response contract version mismatch',
    statusCode: 200,
  });
});

test('checkPermission fails closed for non-object authorization responses', async () => {
  global.fetch = async () => Response.json(null, { status: 200 });
  const client = new SupersetClient(buildConfig({}));

  const result = await client.checkPermission({
    contractVersion: AUTHORIZATION_CONTRACT_VERSION,
    principal: {
      type: 'service',
    },
    resource: {
      type: 'dashboard',
      id: 5,
    },
    action: 'read',
  });

  expect(result).toEqual({
    contractVersion: AUTHORIZATION_CONTRACT_VERSION,
    allowed: false,
    error: 'authorization response contract version mismatch',
    statusCode: 200,
  });
});

test('checkPermission fails closed for malformed authorization allowed fields', async () => {
  global.fetch = async () =>
    Response.json(
      {
        contractVersion: AUTHORIZATION_CONTRACT_VERSION,
        allowed: 'true',
        reason: 'malformed upstream response',
      },
      { status: 200 },
    );
  const client = new SupersetClient(buildConfig({}));

  const result = await client.checkPermission({
    contractVersion: AUTHORIZATION_CONTRACT_VERSION,
    principal: {
      type: 'service',
    },
    resource: {
      type: 'dashboard',
      id: 5,
    },
    action: 'read',
  });

  expect(result).toEqual({
    contractVersion: AUTHORIZATION_CONTRACT_VERSION,
    allowed: false,
    error: 'authorization response allowed field must be boolean',
    statusCode: 200,
  });
});

test('probeMetadata returns sanitized Superset metadata summary', async () => {
  let seenInput: RequestInfo | URL | undefined;
  let seenInit: RequestInit | undefined;
  global.fetch = async (input, init) => {
    seenInput = input;
    seenInit = init;
    return Response.json(
      {
        permissions: ['can_read'],
        result: {
          add_columns: ['dashboard_title'],
        },
        edit_columns: ['slug'],
      },
      { status: 200 },
    );
  };
  const client = new SupersetClient(
    buildConfig({
      AX_SUPERSET_INTERNAL_TOKEN: 'token-123',
      AX_SUPERSET_METADATA_PATH: '/api/v1/dashboard/_info',
    }),
  );

  const result = await client.probeMetadata('request-abc');

  expect(result).toEqual({
    ok: true,
    statusCode: 200,
    url: 'http://127.0.0.1:8088/api/v1/dashboard/_info',
    keyCount: 3,
    keys: ['edit_columns', 'permissions', 'result'],
  });
  expect(seenInput).toBe('http://127.0.0.1:8088/api/v1/dashboard/_info');
  expect(seenInit?.headers).toEqual({
    authorization: 'Bearer token-123',
    'x-request-id': 'request-abc',
  });
});

test('probeMetadata bounds and sanitizes metadata keys', async () => {
  const payload: Record<string, unknown> = {
    ' aaa\nscope ': true,
    ' ': true,
    clean: true,
    [`long-${'x'.repeat(200)}`]: true,
  };
  for (let index = 0; index < 120; index += 1) {
    payload[`key-${index.toString().padStart(3, '0')}`] = true;
  }
  global.fetch = async () => Response.json(payload, { status: 200 });
  const client = new SupersetClient(buildConfig({}));

  const result = await client.probeMetadata();

  expect(result.ok).toBe(true);
  expect(result.keyCount).toBe(100);
  expect(result.keys).toHaveLength(100);
  expect(result.keys).toContain('aaa scope');
  expect(result.keys).not.toContain('');
  expect(result.keys?.every(key => !key.includes('\n'))).toBe(true);
  expect(result.keys?.every(key => key.length <= 128)).toBe(true);
});

test('probeMetadata reports non-success Superset responses without parsing body', async () => {
  global.fetch = async () =>
    new Response('<h1>service unavailable</h1>', {
      status: 503,
      headers: {
        'content-type': 'text/html',
      },
    });
  const client = new SupersetClient(buildConfig({}));

  const result = await client.probeMetadata();

  expect(result).toEqual({
    ok: false,
    statusCode: 503,
    url: 'http://127.0.0.1:8088/api/v1/dashboard/_info',
    keyCount: 0,
    keys: [],
  });
});

test('probeMetadata reports successful array payloads as unhealthy', async () => {
  global.fetch = async () => Response.json(['permissions'], { status: 200 });
  const client = new SupersetClient(buildConfig({}));

  const result = await client.probeMetadata();

  expect(result).toEqual({
    ok: false,
    statusCode: 200,
    error: 'metadata response must be a JSON object',
    url: 'http://127.0.0.1:8088/api/v1/dashboard/_info',
    keyCount: 0,
    keys: [],
  });
});

test('probeMetadata reports successful primitive payloads as unhealthy', async () => {
  global.fetch = async () => Response.json('ok', { status: 200 });
  const client = new SupersetClient(buildConfig({}));

  const result = await client.probeMetadata();

  expect(result).toEqual({
    ok: false,
    statusCode: 200,
    error: 'metadata response must be a JSON object',
    url: 'http://127.0.0.1:8088/api/v1/dashboard/_info',
    keyCount: 0,
    keys: [],
  });
});

test('probeMetadata returns an error result when fetch fails', async () => {
  global.fetch = async () => {
    throw new Error('metadata failed');
  };
  const client = new SupersetClient(buildConfig({}));

  const result = await client.probeMetadata();

  expect(result).toEqual({
    ok: false,
    error: 'metadata failed',
    url: 'http://127.0.0.1:8088/api/v1/dashboard/_info',
  });
});

test('searchAssets queries Superset list APIs and ranks normalized results', async () => {
  const seenInputs: string[] = [];
  const seenInits: RequestInit[] = [];
  global.fetch = async (input, init) => {
    seenInputs.push(String(input));
    seenInits.push(init ?? {});

    if (String(input).includes('/api/v1/chart/')) {
      return Response.json({
        result: [
          {
            id: 2,
            uuid: 'chart-uuid',
            slice_name: 'Sales by region',
            description: 'Regional sales view',
            certified_by: 'Analytics',
            owners: [{ username: 'owner1' }],
            tags: [{ name: 'finance' }],
          },
        ],
      });
    }

    return Response.json({
      result: [
        {
          id: 1,
          uuid: 'dataset-uuid',
          table_name: 'sales_fact',
          description: 'Orders and revenue',
          owners: ['owner2'],
          tags: ['gold'],
        },
      ],
    });
  };
  const client = new SupersetClient(
    buildConfig({
      AX_SUPERSET_INTERNAL_TOKEN: 'token-123',
    }),
  );

  const result = await client.searchAssets(
    {
      contractVersion: ASSET_SEARCH_CONTRACT_VERSION,
      query: 'sales',
      assetTypes: ['dataset', 'chart'],
      includeCertifiedOnly: false,
      limit: 10,
    },
    'request-search',
  );

  expect(result).toEqual({
    contractVersion: ASSET_SEARCH_CONTRACT_VERSION,
    assets: [
      {
        assetType: 'chart',
        id: 2,
        uuid: 'chart-uuid',
        name: 'Sales by region',
        description: 'Regional sales view',
        certified: true,
        relevanceScore: 1.7,
        relevanceReason: "name matches 'sales', description matches 'sales'",
        owners: ['owner1'],
        tags: ['finance'],
      },
      {
        assetType: 'dataset',
        id: 1,
        uuid: 'dataset-uuid',
        name: 'sales_fact',
        description: 'Orders and revenue',
        certified: false,
        relevanceScore: 1,
        relevanceReason: "name matches 'sales'",
        owners: ['owner2'],
        tags: ['gold'],
      },
    ],
    warnings: [],
  });
  expect(seenInputs).toHaveLength(2);
  expect(seenInits).toHaveLength(2);
  expect(seenInputs[0]).toContain('/api/v1/dataset/');
  expect(seenInputs[0]).toContain('q=');
  expect(seenInputs[1]).toContain('/api/v1/chart/');
  const firstInit = seenInits[0];
  expect(firstInit).toBeDefined();
  expect(firstInit?.headers).toEqual({
    authorization: 'Bearer token-123',
    'x-request-id': 'request-search',
  });
});

test('searchAssets ignores malformed certification metadata', async () => {
  global.fetch = async () =>
    Response.json({
      result: [
        {
          id: 2,
          uuid: 'chart-uuid',
          slice_name: 'Sales by region',
          certified_by: { name: 'Analytics' },
        },
      ],
    });
  const client = new SupersetClient(buildConfig({}));

  const result = await client.searchAssets({
    contractVersion: ASSET_SEARCH_CONTRACT_VERSION,
    query: 'sales',
    assetTypes: ['chart'],
    includeCertifiedOnly: false,
    limit: 10,
  });

  expect(result).toEqual({
    contractVersion: ASSET_SEARCH_CONTRACT_VERSION,
    assets: [
      {
        assetType: 'chart',
        id: 2,
        uuid: 'chart-uuid',
        name: 'Sales by region',
        description: '',
        certified: false,
        relevanceScore: 1,
        relevanceReason: "name matches 'sales'",
        owners: [],
        tags: [],
      },
    ],
    warnings: [],
  });
});

test('searchAssets normalizes malformed owner and tag metadata', async () => {
  global.fetch = async () =>
    Response.json({
      result: [
        {
          id: 2,
          uuid: 'chart-uuid',
          slice_name: 'Sales by region',
          owners: { username: 'owner1' },
          tags: ['   ', { name: ' finance ' }, { name: 'gold\n' }],
        },
      ],
    });
  const client = new SupersetClient(buildConfig({}));

  const result = await client.searchAssets({
    contractVersion: ASSET_SEARCH_CONTRACT_VERSION,
    query: 'sales',
    assetTypes: ['chart'],
    includeCertifiedOnly: false,
    limit: 10,
  });

  expect(result).toEqual({
    contractVersion: ASSET_SEARCH_CONTRACT_VERSION,
    assets: [
      {
        assetType: 'chart',
        id: 2,
        uuid: 'chart-uuid',
        name: 'Sales by region',
        description: '',
        certified: false,
        relevanceScore: 1,
        relevanceReason: "name matches 'sales'",
        owners: [],
        tags: ['finance'],
      },
    ],
    warnings: [],
  });
});

test('searchAssets sanitizes bounded result metadata', async () => {
  global.fetch = async () =>
    Response.json({
      result: [
        {
          id: 2,
          uuid: ` chart\n${'u'.repeat(300)} `,
          slice_name: ` Sales\n${'x'.repeat(300)} `,
          description: ` Regional\n${'d'.repeat(1100)} `,
          owners: [` owner-${'o'.repeat(200)} `],
          tags: [` tag-${'t'.repeat(200)} `],
        },
      ],
    });
  const client = new SupersetClient(buildConfig({}));

  const result = await client.searchAssets({
    contractVersion: ASSET_SEARCH_CONTRACT_VERSION,
    query: 'sales',
    assetTypes: ['chart'],
    includeCertifiedOnly: false,
    limit: 10,
  });

  expect(result.assets).toHaveLength(1);
  const [asset] = result.assets;
  expect(asset?.uuid).not.toContain('\n');
  expect(asset?.uuid.startsWith('chart ')).toBe(true);
  expect(asset?.uuid.length).toBeLessThanOrEqual(256);
  expect(asset?.name).not.toContain('\n');
  expect(asset?.name.startsWith('Sales ')).toBe(true);
  expect(asset?.name.length).toBeLessThanOrEqual(256);
  expect(asset?.description).not.toContain('\n');
  expect(asset?.description?.startsWith('Regional ')).toBe(true);
  expect(asset?.description?.length).toBeLessThanOrEqual(1024);
  expect(asset?.owners).toEqual([`owner-${'o'.repeat(122)}`]);
  expect(asset?.tags).toEqual([`tag-${'t'.repeat(124)}`]);
  expect(result.warnings).toEqual([]);
});

test('searchAssets records status warnings for non-json error responses', async () => {
  global.fetch = async () =>
    new Response('upstream timeout', {
      status: 504,
      headers: {
        'content-type': 'text/plain',
      },
    });
  const client = new SupersetClient(buildConfig({}));

  const result = await client.searchAssets({
    contractVersion: ASSET_SEARCH_CONTRACT_VERSION,
    query: 'sales',
    assetTypes: ['dashboard'],
    includeCertifiedOnly: false,
    limit: 10,
  });

  expect(result).toEqual({
    contractVersion: ASSET_SEARCH_CONTRACT_VERSION,
    assets: [],
    warnings: ['dashboard search returned status 504 from Superset'],
  });
});

test('searchAssets records warnings for malformed successful Superset list responses', async () => {
  global.fetch = async () => Response.json({ count: 1 }, { status: 200 });
  const client = new SupersetClient(buildConfig({}));

  const result = await client.searchAssets({
    contractVersion: ASSET_SEARCH_CONTRACT_VERSION,
    query: 'sales',
    assetTypes: ['dashboard'],
    includeCertifiedOnly: false,
    limit: 10,
  });

  expect(result).toEqual({
    contractVersion: ASSET_SEARCH_CONTRACT_VERSION,
    assets: [],
    warnings: [
      'dashboard search failed: Superset list response must include a result array',
    ],
  });
});

test('searchAssets deduplicates requested asset types before querying Superset', async () => {
  const seenInputs: string[] = [];
  global.fetch = async input => {
    seenInputs.push(String(input));
    return Response.json({
      result: [
        {
          id: 1,
          uuid: 'dashboard-uuid',
          dashboard_title: 'Sales dashboard',
          certified_by: null,
        },
      ],
    });
  };
  const client = new SupersetClient(buildConfig({}));

  const result = await client.searchAssets({
    contractVersion: ASSET_SEARCH_CONTRACT_VERSION,
    query: 'sales',
    assetTypes: ['dashboard', 'dashboard'],
    includeCertifiedOnly: false,
    limit: 10,
  });

  expect(seenInputs).toHaveLength(1);
  expect(seenInputs[0]).toContain('/api/v1/dashboard/');
  expect(result.assets).toHaveLength(1);
  expect(result.warnings).toEqual([]);
});

test('searchAssets rejects invalid limits before querying Superset', async () => {
  let fetchCalled = false;
  global.fetch = async () => {
    fetchCalled = true;
    throw new Error('unexpected fetch');
  };
  const client = new SupersetClient(buildConfig({}));

  const result = await client.searchAssets({
    contractVersion: ASSET_SEARCH_CONTRACT_VERSION,
    query: 'sales',
    assetTypes: ['dashboard'],
    includeCertifiedOnly: false,
    limit: 10.5,
  });

  expect(result).toEqual({
    contractVersion: ASSET_SEARCH_CONTRACT_VERSION,
    assets: [],
    warnings: ['asset search request contains invalid limit'],
  });
  expect(fetchCalled).toBe(false);
});

test('searchAssets rejects blank queries before querying Superset', async () => {
  let fetchCalled = false;
  global.fetch = async () => {
    fetchCalled = true;
    throw new Error('unexpected fetch');
  };
  const client = new SupersetClient(buildConfig({}));

  const result = await client.searchAssets({
    contractVersion: ASSET_SEARCH_CONTRACT_VERSION,
    query: '   ',
    assetTypes: ['dashboard'],
    includeCertifiedOnly: false,
    limit: 10,
  });

  expect(result).toEqual({
    contractVersion: ASSET_SEARCH_CONTRACT_VERSION,
    assets: [],
    warnings: ['asset search request contains invalid query'],
  });
  expect(fetchCalled).toBe(false);
});

test('searchAssets rejects control characters before querying Superset', async () => {
  let fetchCalled = false;
  global.fetch = async () => {
    fetchCalled = true;
    throw new Error('unexpected fetch');
  };
  const client = new SupersetClient(buildConfig({}));

  const result = await client.searchAssets({
    contractVersion: ASSET_SEARCH_CONTRACT_VERSION,
    query: 'sales\nregion',
    assetTypes: ['dashboard'],
    includeCertifiedOnly: false,
    limit: 10,
  });

  expect(result).toEqual({
    contractVersion: ASSET_SEARCH_CONTRACT_VERSION,
    assets: [],
    warnings: ['asset search request contains invalid query'],
  });
  expect(fetchCalled).toBe(false);
});

test('searchAssets rejects overlong queries before querying Superset', async () => {
  let fetchCalled = false;
  global.fetch = async () => {
    fetchCalled = true;
    throw new Error('unexpected fetch');
  };
  const client = new SupersetClient(buildConfig({}));

  const result = await client.searchAssets({
    contractVersion: ASSET_SEARCH_CONTRACT_VERSION,
    query: 's'.repeat(257),
    assetTypes: ['dashboard'],
    includeCertifiedOnly: false,
    limit: 10,
  });

  expect(result).toEqual({
    contractVersion: ASSET_SEARCH_CONTRACT_VERSION,
    assets: [],
    warnings: ['asset search request contains invalid query'],
  });
  expect(fetchCalled).toBe(false);
});

test('searchAssets rejects invalid request shapes before querying Superset', async () => {
  let fetchCalled = false;
  global.fetch = async () => {
    fetchCalled = true;
    throw new Error('unexpected fetch');
  };
  const client = new SupersetClient(buildConfig({}));

  const result = await client.searchAssets(
    requestFor('searchAssets', {
      contractVersion: ASSET_SEARCH_CONTRACT_VERSION,
      query: 'sales',
      assetTypes: 'dashboard',
      includeCertifiedOnly: false,
      limit: 10,
    }),
  );

  expect(result).toEqual({
    contractVersion: ASSET_SEARCH_CONTRACT_VERSION,
    assets: [],
    warnings: ['asset search request contains invalid request shape'],
  });
  expect(fetchCalled).toBe(false);
});

test('searchAssets rejects extra request fields before querying Superset', async () => {
  let fetchCalled = false;
  global.fetch = async () => {
    fetchCalled = true;
    throw new Error('unexpected fetch');
  };
  const client = new SupersetClient(buildConfig({}));

  const result = await client.searchAssets(
    requestFor('searchAssets', {
      contractVersion: ASSET_SEARCH_CONTRACT_VERSION,
      query: 'sales',
      assetTypes: ['dashboard'],
      includeCertifiedOnly: false,
      limit: 10,
      tenant: 'ax',
    }),
  );

  expect(result).toEqual({
    contractVersion: ASSET_SEARCH_CONTRACT_VERSION,
    assets: [],
    warnings: ['asset search request contains invalid request shape'],
  });
  expect(fetchCalled).toBe(false);
});

test('searchAssets rejects wrong request contract versions before querying Superset', async () => {
  let fetchCalled = false;
  global.fetch = async () => {
    fetchCalled = true;
    throw new Error('unexpected fetch');
  };
  const client = new SupersetClient(buildConfig({}));

  const result = await client.searchAssets(
    requestFor('searchAssets', {
      contractVersion: 'asset-search.v0',
      query: 'sales',
      assetTypes: ['dashboard'],
      includeCertifiedOnly: false,
      limit: 10,
    }),
  );

  expect(result).toEqual({
    contractVersion: ASSET_SEARCH_CONTRACT_VERSION,
    assets: [],
    warnings: ['asset search request contains invalid request shape'],
  });
  expect(fetchCalled).toBe(false);
});

test('searchAssets records warnings for unsupported and failed search paths', async () => {
  global.fetch = async () => {
    throw new Error('search failed');
  };
  const client = new SupersetClient(buildConfig({}));

  const result = await client.searchAssets({
    contractVersion: ASSET_SEARCH_CONTRACT_VERSION,
    query: 'sales',
    assetTypes: ['metric', 'dashboard'],
    includeCertifiedOnly: false,
    limit: 10,
  });

  expect(result).toEqual({
    contractVersion: ASSET_SEARCH_CONTRACT_VERSION,
    assets: [],
    warnings: [
      'Metric search is not supported by the TypeScript path.',
      'dashboard search failed: search failed',
    ],
  });
});

type ListContractCase = {
  name: string;
  request: Record<string, unknown>;
  warning: string;
  method: ListMethodName;
};

type ListMethodName =
  | 'listAnnotationLayers'
  | 'listAnnotations'
  | 'listCharts'
  | 'listDashboards'
  | 'listDatabases'
  | 'listDatasets'
  | 'listQueries'
  | 'listReports'
  | 'listRoles'
  | 'listRlsFilters'
  | 'listSavedQueries'
  | 'listTags'
  | 'listTasks';

type ListMethod = (
  request: Record<string, unknown>,
) => Promise<{ warnings: string[] }>;

function callListMethod(
  client: SupersetClient,
  method: ListMethodName,
  request: Record<string, unknown>,
): Promise<{ warnings: string[] }> {
  return (client[method] as unknown as ListMethod)(request);
}

const validListRequest = {
  filters: [],
  selectColumns: [],
  orderDirection: 'asc',
  page: 1,
  pageSize: 10,
} satisfies Record<string, unknown>;

const listContractVersionCases: ListContractCase[] = [
  {
    name: 'annotation layer list',
    request: {
      ...validListRequest,
      contractVersion: 'annotation-layer-list.v0',
    },
    warning: 'annotation layer list request contains invalid contract version',
    method: 'listAnnotationLayers',
  },
  {
    name: 'annotation list',
    request: {
      ...validListRequest,
      contractVersion: 'annotation-list.v0',
      layerId: 5,
    },
    warning: 'annotation list request contains invalid contract version',
    method: 'listAnnotations',
  },
  {
    name: 'dashboard list',
    request: {
      ...validListRequest,
      contractVersion: 'dashboard-list.v0',
      createdByMe: false,
      ownedByMe: false,
    },
    warning: 'dashboard list request contains invalid contract version',
    method: 'listDashboards',
  },
  {
    name: 'chart list',
    request: {
      ...validListRequest,
      contractVersion: 'chart-list.v0',
    },
    warning: 'chart list request contains invalid contract version',
    method: 'listCharts',
  },
  {
    name: 'dataset list',
    request: {
      ...validListRequest,
      contractVersion: 'dataset-list.v0',
    },
    warning: 'dataset list request contains invalid contract version',
    method: 'listDatasets',
  },
  {
    name: 'database list',
    request: {
      ...validListRequest,
      contractVersion: 'database-list.v0',
    },
    warning: 'database list request contains invalid contract version',
    method: 'listDatabases',
  },
  {
    name: 'query list',
    request: {
      ...validListRequest,
      contractVersion: 'query-list.v0',
    },
    warning: 'query list request contains invalid contract version',
    method: 'listQueries',
  },
  {
    name: 'saved query list',
    request: {
      ...validListRequest,
      contractVersion: 'saved-query-list.v0',
    },
    warning: 'saved query list request contains invalid contract version',
    method: 'listSavedQueries',
  },
  {
    name: 'report list',
    request: {
      ...validListRequest,
      contractVersion: 'report-list.v0',
    },
    warning: 'report list request contains invalid contract version',
    method: 'listReports',
  },
  {
    name: 'role list',
    request: {
      ...validListRequest,
      contractVersion: 'role-list.v0',
    },
    warning: 'role list request contains invalid contract version',
    method: 'listRoles',
  },
  {
    name: 'RLS filter list',
    request: {
      ...validListRequest,
      contractVersion: 'rls-list.v0',
    },
    warning: 'RLS filter list request contains invalid contract version',
    method: 'listRlsFilters',
  },
  {
    name: 'tag list',
    request: {
      ...validListRequest,
      contractVersion: 'tag-list.v0',
    },
    warning: 'tag list request contains invalid contract version',
    method: 'listTags',
  },
  {
    name: 'task list',
    request: {
      ...validListRequest,
      contractVersion: 'task-list.v0',
    },
    warning: 'task list request contains invalid contract version',
    method: 'listTasks',
  },
];

for (const { name, request, warning, method } of listContractVersionCases) {
  test(`${name} rejects wrong request contract versions before querying Superset`, async () => {
    let fetchCalled = false;
    global.fetch = async () => {
      fetchCalled = true;
      throw new Error('unexpected fetch');
    };
    const client = new SupersetClient(buildConfig({}));

    const result = await callListMethod(client, method, request);

    expect(result.warnings).toContain(warning);
    expect(fetchCalled).toBe(false);
  });
}

type OwnershipFlagCase = {
  name: string;
  request: Record<string, unknown>;
  warning: string;
  method: ListMethodName;
};

const ownershipFlagCases: OwnershipFlagCase[] = [
  {
    name: 'dashboard list',
    request: {
      ...validListRequest,
      contractVersion: DASHBOARD_LIST_CONTRACT_VERSION,
      createdByMe: 'false',
      ownedByMe: false,
    },
    warning: 'dashboard list request contains invalid ownership flags',
    method: 'listDashboards',
  },
  {
    name: 'chart list',
    request: {
      ...validListRequest,
      contractVersion: CHART_LIST_CONTRACT_VERSION,
      createdByMe: false,
    },
    warning: 'chart list request contains invalid ownership flags',
    method: 'listCharts',
  },
  {
    name: 'dataset list',
    request: {
      ...validListRequest,
      contractVersion: DATASET_LIST_CONTRACT_VERSION,
      createdByMe: false,
      ownedByMe: 'false',
    },
    warning: 'dataset list request contains invalid ownership flags',
    method: 'listDatasets',
  },
  {
    name: 'database list',
    request: {
      ...validListRequest,
      contractVersion: DATABASE_LIST_CONTRACT_VERSION,
    },
    warning: 'database list request contains invalid ownership flags',
    method: 'listDatabases',
  },
];

for (const { name, request, warning, method } of ownershipFlagCases) {
  test(`${name} rejects invalid ownership flags before querying Superset`, async () => {
    let fetchCalled = false;
    global.fetch = async () => {
      fetchCalled = true;
      throw new Error('unexpected fetch');
    };
    const client = new SupersetClient(buildConfig({}));

    const result = await callListMethod(client, method, request);

    expect(result.warnings).toContain(warning);
    expect(fetchCalled).toBe(false);
  });
}

test('listAnnotationLayers maps Superset annotation layer list responses', async () => {
  let seenInput: RequestInfo | URL | undefined;
  let seenInit: RequestInit | undefined;
  global.fetch = async (input, init) => {
    seenInput = input;
    seenInit = init;
    return Response.json({
      count: 6,
      result: [
        {
          id: 5,
          name: 'Release markers',
          descr: 'Production release windows',
          changed_on: '2026-01-05T00:00:00',
          created_on: '2026-01-01T00:00:00',
        },
      ],
    });
  };
  const client = new SupersetClient(
    buildConfig({
      AX_SUPERSET_INTERNAL_TOKEN: 'token-123',
    }),
  );

  const result = await client.listAnnotationLayers(
    {
      contractVersion: ANNOTATION_LAYER_LIST_CONTRACT_VERSION,
      filters: [{ col: 'name', opr: 'ct', value: 'release' }],
      selectColumns: ['id', 'name'],
      search: 'markers',
      orderColumn: 'name',
      orderDirection: 'desc',
      page: 2,
      pageSize: 5,
    },
    'request-annotation-layers',
  );

  expect(result).toEqual({
    contractVersion: ANNOTATION_LAYER_LIST_CONTRACT_VERSION,
    annotationLayers: [
      {
        id: 5,
        name: 'Release markers',
        descr: 'Production release windows',
        changedOn: '2026-01-05T00:00:00',
        createdOn: '2026-01-01T00:00:00',
      },
    ],
    count: 1,
    totalCount: 6,
    page: 2,
    pageSize: 5,
    totalPages: 2,
    hasNext: false,
    hasPrevious: true,
    columnsRequested: ['id', 'name'],
    columnsLoaded: ['id', 'name', 'descr', 'changed_on', 'created_on'],
    warnings: [],
  });
  expect(String(seenInput)).toContain('/api/v1/annotation_layer/');
  expect(String(seenInput)).toContain('q=');
  expect(decodeURIComponent(String(seenInput))).toContain('page:1');
  expect(decodeURIComponent(String(seenInput))).toContain("value:'markers'");
  expect(seenInit?.headers).toEqual({
    authorization: 'Bearer token-123',
    'x-request-id': 'request-annotation-layers',
  });
});

test('listAnnotationLayers records warnings for failed Superset responses', async () => {
  global.fetch = async () =>
    new Response('upstream timeout', {
      status: 504,
      headers: {
        'content-type': 'text/plain',
      },
    });
  const client = new SupersetClient(buildConfig({}));

  const result = await client.listAnnotationLayers({
    contractVersion: ANNOTATION_LAYER_LIST_CONTRACT_VERSION,
    filters: [],
    selectColumns: [],
    orderDirection: 'asc',
    page: 1,
    pageSize: 10,
  });

  expect(result).toEqual({
    contractVersion: ANNOTATION_LAYER_LIST_CONTRACT_VERSION,
    annotationLayers: [],
    count: 0,
    totalCount: 0,
    page: 1,
    pageSize: 10,
    totalPages: 0,
    hasNext: false,
    hasPrevious: false,
    columnsRequested: ['id', 'name', 'descr'],
    columnsLoaded: [],
    warnings: ['annotation layer list returned status 504 from Superset'],
  });
});

test('listAnnotations maps Superset annotation list responses', async () => {
  let seenInput: RequestInfo | URL | undefined;
  let seenInit: RequestInit | undefined;
  global.fetch = async (input, init) => {
    seenInput = input;
    seenInit = init;
    return Response.json({
      count: 4,
      result: [
        {
          id: 7,
          short_descr: 'Deploy',
          long_descr: 'Production deploy',
          start_dttm: '2026-01-05T00:00:00',
          end_dttm: '2026-01-05T01:00:00',
          json_metadata: '{"env":"prod"}',
        },
      ],
    });
  };
  const client = new SupersetClient(
    buildConfig({
      AX_SUPERSET_INTERNAL_TOKEN: 'token-123',
    }),
  );

  const result = await client.listAnnotations(
    {
      contractVersion: ANNOTATION_LIST_CONTRACT_VERSION,
      layerId: 5,
      filters: [{ col: 'short_descr', opr: 'ct', value: 'deploy' }],
      selectColumns: ['id', 'short_descr', 'layer_id'],
      search: 'release',
      orderColumn: 'short_descr',
      orderDirection: 'desc',
      page: 2,
      pageSize: 2,
    },
    'request-annotations',
  );

  expect(result).toEqual({
    contractVersion: ANNOTATION_LIST_CONTRACT_VERSION,
    annotations: [
      {
        id: 7,
        shortDescr: 'Deploy',
        longDescr: 'Production deploy',
        startDttm: '2026-01-05T00:00:00',
        endDttm: '2026-01-05T01:00:00',
        jsonMetadata: '{"env":"prod"}',
        layerId: 5,
      },
    ],
    count: 1,
    totalCount: 4,
    page: 2,
    pageSize: 2,
    totalPages: 2,
    hasNext: false,
    hasPrevious: true,
    layerId: 5,
    columnsRequested: ['id', 'short_descr', 'layer_id'],
    columnsLoaded: [
      'id',
      'short_descr',
      'long_descr',
      'start_dttm',
      'end_dttm',
      'json_metadata',
      'layer_id',
    ],
    warnings: [],
  });
  expect(String(seenInput)).toContain('/api/v1/annotation_layer/5/annotation/');
  expect(String(seenInput)).toContain('q=');
  expect(decodeURIComponent(String(seenInput))).toContain('page:1');
  expect(decodeURIComponent(String(seenInput))).toContain("value:'release'");
  expect(seenInit?.headers).toEqual({
    authorization: 'Bearer token-123',
    'x-request-id': 'request-annotations',
  });
});

test('listAnnotations records warnings for failed Superset responses', async () => {
  global.fetch = async () =>
    new Response('missing layer', {
      status: 404,
      headers: {
        'content-type': 'text/plain',
      },
    });
  const client = new SupersetClient(buildConfig({}));

  const result = await client.listAnnotations({
    contractVersion: ANNOTATION_LIST_CONTRACT_VERSION,
    layerId: 5,
    filters: [],
    selectColumns: [],
    orderDirection: 'asc',
    page: 1,
    pageSize: 10,
  });

  expect(result).toEqual({
    contractVersion: ANNOTATION_LIST_CONTRACT_VERSION,
    annotations: [],
    count: 0,
    totalCount: 0,
    page: 1,
    pageSize: 10,
    totalPages: 0,
    hasNext: false,
    hasPrevious: false,
    layerId: 5,
    columnsRequested: ['id', 'short_descr', 'start_dttm', 'end_dttm', 'layer_id'],
    columnsLoaded: [],
    warnings: ['annotation list returned status 404 from Superset'],
  });
});

test('listAnnotations rejects invalid layer IDs before querying Superset', async () => {
  let fetchCalled = false;
  global.fetch = async () => {
    fetchCalled = true;
    throw new Error('unexpected fetch');
  };
  const client = new SupersetClient(buildConfig({}));

  const result = await client.listAnnotations({
    contractVersion: ANNOTATION_LIST_CONTRACT_VERSION,
    layerId: 5.5,
    filters: [],
    selectColumns: [],
    orderDirection: 'asc',
    page: 1,
    pageSize: 10,
  });

  expect(result).toEqual({
    contractVersion: ANNOTATION_LIST_CONTRACT_VERSION,
    annotations: [],
    count: 0,
    totalCount: 0,
    page: 1,
    pageSize: 10,
    totalPages: 0,
    hasNext: false,
    hasPrevious: false,
    layerId: 0,
    columnsRequested: ['id', 'short_descr', 'start_dttm', 'end_dttm', 'layer_id'],
    columnsLoaded: [],
    warnings: ['annotation list request contains invalid layer id'],
  });
  expect(fetchCalled).toBe(false);
});

test('listAnnotations rejects malformed requests before querying Superset', async () => {
  let fetchCalled = false;
  global.fetch = async () => {
    fetchCalled = true;
    throw new Error('unexpected fetch');
  };
  const client = new SupersetClient(buildConfig({}));

  const result = await client.listAnnotations(
    requestFor('listAnnotations', null),
  );

  expect(result).toEqual({
    contractVersion: ANNOTATION_LIST_CONTRACT_VERSION,
    annotations: [],
    count: 0,
    totalCount: 0,
    page: 1,
    pageSize: 100,
    totalPages: 0,
    hasNext: false,
    hasPrevious: false,
    layerId: 0,
    columnsRequested: ['id', 'short_descr', 'start_dttm', 'end_dttm', 'layer_id'],
    columnsLoaded: [],
    warnings: ['annotation list request contains invalid layer id'],
  });
  expect(fetchCalled).toBe(false);
});

test('listDashboards maps Superset dashboard list responses', async () => {
  let seenInput: RequestInfo | URL | undefined;
  let seenInit: RequestInit | undefined;
  global.fetch = async (input, init) => {
    seenInput = input;
    seenInit = init;
    return Response.json({
      count: 11,
      result: [
        {
          id: 7,
          dashboard_title: 'Sales dashboard',
          slug: 'sales',
          description: 'Executive sales',
          certified_by: 'BI',
          certification_details: 'Reviewed',
          published: true,
          uuid: 'dashboard-uuid',
          url: '/superset/dashboard/7/',
          changed_on: '2026-01-01T00:00:00',
          changed_on_humanized: '1 day ago',
        },
      ],
    });
  };
  const client = new SupersetClient(
    buildConfig({
      AX_SUPERSET_INTERNAL_TOKEN: 'token-123',
    }),
  );

  const result = await client.listDashboards(
    {
      contractVersion: DASHBOARD_LIST_CONTRACT_VERSION,
      filters: [{ col: 'published', opr: 'eq', value: true }],
      selectColumns: ['id', 'dashboard_title'],
      search: 'sales',
      orderColumn: 'dashboard_title',
      orderDirection: 'desc',
      page: 2,
      pageSize: 10,
      createdByMe: false,
      ownedByMe: false,
    },
    'request-dashboards',
  );

  expect(result).toEqual({
    contractVersion: DASHBOARD_LIST_CONTRACT_VERSION,
    dashboards: [
      {
        id: 7,
        dashboardTitle: 'Sales dashboard',
        slug: 'sales',
        description: 'Executive sales',
        certifiedBy: 'BI',
        certificationDetails: 'Reviewed',
        published: true,
        uuid: 'dashboard-uuid',
        url: '/superset/dashboard/7/',
        changedOn: '2026-01-01T00:00:00',
        changedOnHumanized: '1 day ago',
      },
    ],
    count: 1,
    totalCount: 11,
    page: 2,
    pageSize: 10,
    totalPages: 2,
    hasNext: false,
    hasPrevious: true,
    columnsRequested: ['id', 'dashboard_title'],
    columnsLoaded: [
      'id',
      'dashboard_title',
      'slug',
      'description',
      'certified_by',
      'certification_details',
      'published',
      'uuid',
      'url',
      'changed_on',
      'changed_on_humanized',
    ],
    warnings: [],
  });
  expect(String(seenInput)).toContain('/api/v1/dashboard/');
  expect(String(seenInput)).toContain('q=');
  expect(decodeURIComponent(String(seenInput))).toContain('page:1');
  expect(decodeURIComponent(String(seenInput))).toContain(
    "value:'sales'",
  );
  expect(seenInit?.headers).toEqual({
    authorization: 'Bearer token-123',
    'x-request-id': 'request-dashboards',
  });
});

test('listDashboards ignores Superset counts lower than mapped results', async () => {
  global.fetch = async () =>
    Response.json({
      count: 0,
      result: [
        {
          id: 7,
          dashboard_title: 'Sales dashboard',
        },
      ],
    });
  const client = new SupersetClient(buildConfig({}));

  const result = await client.listDashboards({
    contractVersion: DASHBOARD_LIST_CONTRACT_VERSION,
    filters: [],
    selectColumns: [],
    orderDirection: 'asc',
    page: 1,
    pageSize: 10,
    createdByMe: false,
    ownedByMe: false,
  });

  expect(result.totalCount).toBe(1);
  expect(result.totalPages).toBe(1);
  expect(result.hasNext).toBe(false);
});

test('listDashboards ignores fractional Superset counts', async () => {
  global.fetch = async () =>
    Response.json({
      count: 1.5,
      result: [
        {
          id: 7,
          dashboard_title: 'Sales dashboard',
        },
      ],
    });
  const client = new SupersetClient(buildConfig({}));

  const result = await client.listDashboards({
    contractVersion: DASHBOARD_LIST_CONTRACT_VERSION,
    filters: [],
    selectColumns: [],
    orderDirection: 'asc',
    page: 1,
    pageSize: 10,
    createdByMe: false,
    ownedByMe: false,
  });

  expect(result.totalCount).toBe(1);
  expect(result.totalPages).toBe(1);
  expect(result.hasNext).toBe(false);
});

test('listDashboards ignores unsafe Superset counts', async () => {
  global.fetch = async () =>
    Response.json({
      count: Number.MAX_SAFE_INTEGER + 1,
      result: [
        {
          id: 7,
          dashboard_title: 'Sales dashboard',
        },
      ],
    });
  const client = new SupersetClient(buildConfig({}));

  const result = await client.listDashboards({
    contractVersion: DASHBOARD_LIST_CONTRACT_VERSION,
    filters: [],
    selectColumns: [],
    orderDirection: 'asc',
    page: 1,
    pageSize: 10,
    createdByMe: false,
    ownedByMe: false,
  });

  expect(result.totalCount).toBe(1);
  expect(result.totalPages).toBe(1);
  expect(result.hasNext).toBe(false);
});

test('listDashboards does not report previous pages for empty result sets', async () => {
  global.fetch = async () =>
    Response.json({
      count: 0,
      result: [],
    });
  const client = new SupersetClient(buildConfig({}));

  const result = await client.listDashboards({
    contractVersion: DASHBOARD_LIST_CONTRACT_VERSION,
    filters: [],
    selectColumns: [],
    orderDirection: 'asc',
    page: 2,
    pageSize: 10,
    createdByMe: false,
    ownedByMe: false,
  });

  expect(result.totalCount).toBe(0);
  expect(result.totalPages).toBe(0);
  expect(result.hasNext).toBe(false);
  expect(result.hasPrevious).toBe(false);
});

test('listDashboards rejects invalid pagination before querying Superset', async () => {
  let fetchCalled = false;
  global.fetch = async () => {
    fetchCalled = true;
    throw new Error('unexpected fetch');
  };
  const client = new SupersetClient(buildConfig({}));

  const result = await client.listDashboards({
    contractVersion: DASHBOARD_LIST_CONTRACT_VERSION,
    filters: [],
    selectColumns: [],
    orderDirection: 'asc',
    page: 1,
    pageSize: 10.5,
    createdByMe: false,
    ownedByMe: false,
  });

  expect(result).toEqual({
    contractVersion: DASHBOARD_LIST_CONTRACT_VERSION,
    dashboards: [],
    count: 0,
    totalCount: 0,
    page: 1,
    pageSize: 100,
    totalPages: 0,
    hasNext: false,
    hasPrevious: false,
    columnsRequested: [
      'id',
      'dashboard_title',
      'slug',
      'description',
      'certified_by',
      'certification_details',
      'url',
      'changed_on',
      'changed_on_humanized',
    ],
    columnsLoaded: [],
    warnings: ['dashboard list request contains invalid pagination'],
  });
  expect(fetchCalled).toBe(false);
});

test('listDashboards rejects malformed requests before querying Superset', async () => {
  let fetchCalled = false;
  global.fetch = async () => {
    fetchCalled = true;
    throw new Error('unexpected fetch');
  };
  const client = new SupersetClient(buildConfig({}));

  const result = await client.listDashboards(
    requestFor('listDashboards', null),
  );

  expect(result).toEqual({
    contractVersion: DASHBOARD_LIST_CONTRACT_VERSION,
    dashboards: [],
    count: 0,
    totalCount: 0,
    page: 1,
    pageSize: 100,
    totalPages: 0,
    hasNext: false,
    hasPrevious: false,
    columnsRequested: [
      'id',
      'dashboard_title',
      'slug',
      'description',
      'certified_by',
      'certification_details',
      'url',
      'changed_on',
      'changed_on_humanized',
    ],
    columnsLoaded: [],
    warnings: ['dashboard list request contains invalid pagination'],
  });
  expect(fetchCalled).toBe(false);
});

test('listDashboards rejects unsafe pagination before querying Superset', async () => {
  let fetchCalled = false;
  global.fetch = async () => {
    fetchCalled = true;
    throw new Error('unexpected fetch');
  };
  const client = new SupersetClient(buildConfig({}));

  const result = await client.listDashboards({
    contractVersion: DASHBOARD_LIST_CONTRACT_VERSION,
    filters: [],
    selectColumns: [],
    orderDirection: 'asc',
    page: Number.MAX_SAFE_INTEGER + 1,
    pageSize: 10,
    createdByMe: false,
    ownedByMe: false,
  });

  expect(result).toEqual({
    contractVersion: DASHBOARD_LIST_CONTRACT_VERSION,
    dashboards: [],
    count: 0,
    totalCount: 0,
    page: 1,
    pageSize: 10,
    totalPages: 0,
    hasNext: false,
    hasPrevious: false,
    columnsRequested: [
      'id',
      'dashboard_title',
      'slug',
      'description',
      'certified_by',
      'certification_details',
      'url',
      'changed_on',
      'changed_on_humanized',
    ],
    columnsLoaded: [],
    warnings: ['dashboard list request contains invalid pagination'],
  });
  expect(fetchCalled).toBe(false);
});

test('listDashboards rejects invalid columns before querying Superset', async () => {
  let fetchCalled = false;
  global.fetch = async () => {
    fetchCalled = true;
    throw new Error('unexpected fetch');
  };
  const client = new SupersetClient(buildConfig({}));

  const result = await client.listDashboards({
    contractVersion: DASHBOARD_LIST_CONTRACT_VERSION,
    filters: [],
    selectColumns: ['id', 'dashboard_title),page_size:100'],
    orderDirection: 'asc',
    page: 1,
    pageSize: 10,
    createdByMe: false,
    ownedByMe: false,
  });

  expect(result).toEqual({
    contractVersion: DASHBOARD_LIST_CONTRACT_VERSION,
    dashboards: [],
    count: 0,
    totalCount: 0,
    page: 1,
    pageSize: 10,
    totalPages: 0,
    hasNext: false,
    hasPrevious: false,
    columnsRequested: [
      'id',
      'dashboard_title',
      'slug',
      'description',
      'certified_by',
      'certification_details',
      'url',
      'changed_on',
      'changed_on_humanized',
    ],
    columnsLoaded: [],
    warnings: ['dashboard list request contains invalid columns'],
  });
  expect(fetchCalled).toBe(false);
});

test('listDashboards rejects invalid ordering before querying Superset', async () => {
  let fetchCalled = false;
  global.fetch = async () => {
    fetchCalled = true;
    throw new Error('unexpected fetch');
  };
  const client = new SupersetClient(buildConfig({}));

  const result = await client.listDashboards({
    contractVersion: DASHBOARD_LIST_CONTRACT_VERSION,
    filters: [],
    selectColumns: [],
    orderColumn: 'dashboard_title),page_size:100',
    orderDirection: 'asc',
    page: 1,
    pageSize: 10,
    createdByMe: false,
    ownedByMe: false,
  });

  expect(result).toEqual({
    contractVersion: DASHBOARD_LIST_CONTRACT_VERSION,
    dashboards: [],
    count: 0,
    totalCount: 0,
    page: 1,
    pageSize: 10,
    totalPages: 0,
    hasNext: false,
    hasPrevious: false,
    columnsRequested: [
      'id',
      'dashboard_title',
      'slug',
      'description',
      'certified_by',
      'certification_details',
      'url',
      'changed_on',
      'changed_on_humanized',
    ],
    columnsLoaded: [],
    warnings: ['dashboard list request contains invalid ordering'],
  });
  expect(fetchCalled).toBe(false);
});

test('listDashboards rejects invalid filters before querying Superset', async () => {
  let fetchCalled = false;
  global.fetch = async () => {
    fetchCalled = true;
    throw new Error('unexpected fetch');
  };
  const client = new SupersetClient(buildConfig({}));

  const result = await client.listDashboards({
    contractVersion: DASHBOARD_LIST_CONTRACT_VERSION,
    filters: [
      {
        col: 'published),page_size:100',
        opr: 'eq',
        value: true,
      },
    ],
    selectColumns: [],
    orderDirection: 'asc',
    page: 1,
    pageSize: 10,
    createdByMe: false,
    ownedByMe: false,
  });

  expect(result).toEqual({
    contractVersion: DASHBOARD_LIST_CONTRACT_VERSION,
    dashboards: [],
    count: 0,
    totalCount: 0,
    page: 1,
    pageSize: 10,
    totalPages: 0,
    hasNext: false,
    hasPrevious: false,
    columnsRequested: [
      'id',
      'dashboard_title',
      'slug',
      'description',
      'certified_by',
      'certification_details',
      'url',
      'changed_on',
      'changed_on_humanized',
    ],
    columnsLoaded: [],
    warnings: ['dashboard list request contains invalid filters'],
  });
  expect(fetchCalled).toBe(false);
});

test('listDashboards rejects invalid search values before querying Superset', async () => {
  let fetchCalled = false;
  global.fetch = async () => {
    fetchCalled = true;
    throw new Error('unexpected fetch');
  };
  const client = new SupersetClient(buildConfig({}));

  for (const search of ['sales\nregion', '   ', { query: 'sales' }]) {
    const result = await client.listDashboards(
      requestFor('listDashboards', {
        contractVersion: DASHBOARD_LIST_CONTRACT_VERSION,
        filters: [],
        selectColumns: [],
        search,
        orderDirection: 'asc',
        page: 1,
        pageSize: 10,
        createdByMe: false,
        ownedByMe: false,
      }),
    );

    expect(result.warnings).toEqual([
      'dashboard list request contains invalid filters',
    ]);
  }
  expect(fetchCalled).toBe(false);
});

test('listDashboards rejects control characters in filter values', async () => {
  let fetchCalled = false;
  global.fetch = async () => {
    fetchCalled = true;
    throw new Error('unexpected fetch');
  };
  const client = new SupersetClient(buildConfig({}));

  const result = await client.listDashboards({
    contractVersion: DASHBOARD_LIST_CONTRACT_VERSION,
    filters: [
      {
        col: 'dashboard_title',
        opr: 'ct',
        value: 'sales\nregion',
      },
    ],
    selectColumns: [],
    orderDirection: 'asc',
    page: 1,
    pageSize: 10,
    createdByMe: false,
    ownedByMe: false,
  });

  expect(result).toEqual({
    contractVersion: DASHBOARD_LIST_CONTRACT_VERSION,
    dashboards: [],
    count: 0,
    totalCount: 0,
    page: 1,
    pageSize: 10,
    totalPages: 0,
    hasNext: false,
    hasPrevious: false,
    columnsRequested: [
      'id',
      'dashboard_title',
      'slug',
      'description',
      'certified_by',
      'certification_details',
      'url',
      'changed_on',
      'changed_on_humanized',
    ],
    columnsLoaded: [],
    warnings: ['dashboard list request contains invalid filters'],
  });
  expect(fetchCalled).toBe(false);
});

test('listDashboards rejects mixed-type filter arrays before querying Superset', async () => {
  let fetchCalled = false;
  global.fetch = async () => {
    fetchCalled = true;
    throw new Error('unexpected fetch');
  };
  const client = new SupersetClient(buildConfig({}));

  const result = await client.listDashboards(
    requestFor('listDashboards', {
      contractVersion: DASHBOARD_LIST_CONTRACT_VERSION,
      filters: [
        {
          col: 'published',
          opr: 'in',
          value: [true, 'false'],
        },
      ],
      selectColumns: [],
      orderDirection: 'asc',
      page: 1,
      pageSize: 10,
      createdByMe: false,
      ownedByMe: false,
    }),
  );

  expect(result).toEqual({
    contractVersion: DASHBOARD_LIST_CONTRACT_VERSION,
    dashboards: [],
    count: 0,
    totalCount: 0,
    page: 1,
    pageSize: 10,
    totalPages: 0,
    hasNext: false,
    hasPrevious: false,
    columnsRequested: [
      'id',
      'dashboard_title',
      'slug',
      'description',
      'certified_by',
      'certification_details',
      'url',
      'changed_on',
      'changed_on_humanized',
    ],
    columnsLoaded: [],
    warnings: ['dashboard list request contains invalid filters'],
  });
  expect(fetchCalled).toBe(false);
});

test('listDashboards skips invalid Superset item IDs', async () => {
  global.fetch = async () =>
    Response.json({
      count: 3,
      result: [
        {
          id: 7,
          dashboard_title: 'Sales dashboard',
        },
        {
          id: -1,
          dashboard_title: 'Invalid negative ID',
        },
        {
          id: 2.5,
          dashboard_title: 'Invalid fractional ID',
        },
      ],
    });
  const client = new SupersetClient(buildConfig({}));

  const result = await client.listDashboards({
    contractVersion: DASHBOARD_LIST_CONTRACT_VERSION,
    filters: [],
    selectColumns: [],
    orderDirection: 'asc',
    page: 1,
    pageSize: 10,
    createdByMe: false,
    ownedByMe: false,
  });

  expect(result.dashboards).toEqual([
    {
      id: 7,
      dashboardTitle: 'Sales dashboard',
    },
  ]);
  expect(result.count).toBe(1);
  expect(result.totalCount).toBe(3);
});

test('listDashboards records warnings for failed Superset list responses', async () => {
  global.fetch = async () =>
    new Response('upstream timeout', {
      status: 504,
      headers: {
        'content-type': 'text/plain',
      },
    });
  const client = new SupersetClient(buildConfig({}));

  const result = await client.listDashboards({
    contractVersion: DASHBOARD_LIST_CONTRACT_VERSION,
    filters: [],
    selectColumns: [],
    orderDirection: 'asc',
    page: 1,
    pageSize: 10,
    createdByMe: false,
    ownedByMe: false,
  });

  expect(result).toEqual({
    contractVersion: DASHBOARD_LIST_CONTRACT_VERSION,
    dashboards: [],
    count: 0,
    totalCount: 0,
    page: 1,
    pageSize: 10,
    totalPages: 0,
    hasNext: false,
    hasPrevious: false,
    columnsRequested: [
      'id',
      'dashboard_title',
      'slug',
      'description',
      'certified_by',
      'certification_details',
      'url',
      'changed_on',
      'changed_on_humanized',
    ],
    columnsLoaded: [],
    warnings: ['dashboard list returned status 504 from Superset'],
  });
});

test('listDashboards records warnings for malformed successful Superset list responses', async () => {
  global.fetch = async () => Response.json({ count: 1 }, { status: 200 });
  const client = new SupersetClient(buildConfig({}));

  const result = await client.listDashboards({
    contractVersion: DASHBOARD_LIST_CONTRACT_VERSION,
    filters: [],
    selectColumns: [],
    orderDirection: 'asc',
    page: 1,
    pageSize: 10,
    createdByMe: false,
    ownedByMe: false,
  });

  expect(result).toEqual({
    contractVersion: DASHBOARD_LIST_CONTRACT_VERSION,
    dashboards: [],
    count: 0,
    totalCount: 0,
    page: 1,
    pageSize: 10,
    totalPages: 0,
    hasNext: false,
    hasPrevious: false,
    columnsRequested: [
      'id',
      'dashboard_title',
      'slug',
      'description',
      'certified_by',
      'certification_details',
      'url',
      'changed_on',
      'changed_on_humanized',
    ],
    columnsLoaded: [],
    warnings: [
      'dashboard list failed: Superset list response must include a result array',
    ],
  });
});

test('listCharts maps Superset chart list responses', async () => {
  let seenInput: RequestInfo | URL | undefined;
  let seenInit: RequestInit | undefined;
  global.fetch = async (input, init) => {
    seenInput = input;
    seenInit = init;
    return Response.json({
      count: 12,
      result: [
        {
          id: 9,
          slice_name: 'Sales by region',
          viz_type: 'bar',
          description: 'Regional sales',
          certified_by: 'BI',
          certification_details: 'Reviewed',
          uuid: 'chart-uuid',
          url: '/explore/?slice_id=9',
          changed_on: '2026-01-02T00:00:00',
          changed_on_humanized: '2 days ago',
        },
      ],
    });
  };
  const client = new SupersetClient(
    buildConfig({
      AX_SUPERSET_INTERNAL_TOKEN: 'token-123',
    }),
  );

  const result = await client.listCharts(
    {
      contractVersion: CHART_LIST_CONTRACT_VERSION,
      filters: [{ col: 'viz_type', opr: 'eq', value: 'bar' }],
      selectColumns: ['id', 'slice_name'],
      search: 'sales',
      orderColumn: 'slice_name',
      orderDirection: 'desc',
      page: 2,
      pageSize: 10,
      createdByMe: false,
      ownedByMe: false,
    },
    'request-charts',
  );

  expect(result).toEqual({
    contractVersion: CHART_LIST_CONTRACT_VERSION,
    charts: [
      {
        id: 9,
        sliceName: 'Sales by region',
        vizType: 'bar',
        description: 'Regional sales',
        certifiedBy: 'BI',
        certificationDetails: 'Reviewed',
        uuid: 'chart-uuid',
        url: '/explore/?slice_id=9',
        changedOn: '2026-01-02T00:00:00',
        changedOnHumanized: '2 days ago',
      },
    ],
    count: 1,
    totalCount: 12,
    page: 2,
    pageSize: 10,
    totalPages: 2,
    hasNext: false,
    hasPrevious: true,
    columnsRequested: ['id', 'slice_name'],
    columnsLoaded: [
      'id',
      'slice_name',
      'viz_type',
      'description',
      'certified_by',
      'certification_details',
      'uuid',
      'url',
      'changed_on',
      'changed_on_humanized',
    ],
    warnings: [],
  });
  expect(String(seenInput)).toContain('/api/v1/chart/');
  expect(String(seenInput)).toContain('q=');
  expect(decodeURIComponent(String(seenInput))).toContain('page:1');
  expect(decodeURIComponent(String(seenInput))).toContain("value:'sales'");
  expect(seenInit?.headers).toEqual({
    authorization: 'Bearer token-123',
    'x-request-id': 'request-charts',
  });
});

test('listCharts records warnings for failed Superset list responses', async () => {
  global.fetch = async () =>
    new Response('upstream timeout', {
      status: 504,
      headers: {
        'content-type': 'text/plain',
      },
    });
  const client = new SupersetClient(buildConfig({}));

  const result = await client.listCharts({
    contractVersion: CHART_LIST_CONTRACT_VERSION,
    filters: [],
    selectColumns: [],
    orderDirection: 'asc',
    page: 1,
    pageSize: 10,
    createdByMe: false,
    ownedByMe: false,
  });

  expect(result).toEqual({
    contractVersion: CHART_LIST_CONTRACT_VERSION,
    charts: [],
    count: 0,
    totalCount: 0,
    page: 1,
    pageSize: 10,
    totalPages: 0,
    hasNext: false,
    hasPrevious: false,
    columnsRequested: [
      'id',
      'slice_name',
      'viz_type',
      'description',
      'certified_by',
      'certification_details',
      'url',
      'changed_on',
      'changed_on_humanized',
    ],
    columnsLoaded: [],
    warnings: ['chart list returned status 504 from Superset'],
  });
});

test('listDatasets maps Superset dataset list responses', async () => {
  let seenInput: RequestInfo | URL | undefined;
  let seenInit: RequestInit | undefined;
  global.fetch = async (input, init) => {
    seenInput = input;
    seenInit = init;
    return Response.json({
      count: 13,
      result: [
        {
          id: 11,
          table_name: 'sales_fact',
          schema: 'public',
          database: {
            id: 3,
            database_name: 'examples',
          },
          description: 'Orders and revenue',
          certified_by: 'BI',
          certification_details: 'Reviewed',
          changed_on: '2026-01-03T00:00:00',
          changed_on_humanized: '3 days ago',
          is_virtual: false,
          uuid: 'dataset-uuid',
          url: '/explore/?datasource_type=table&datasource_id=11',
        },
      ],
    });
  };
  const client = new SupersetClient(
    buildConfig({
      AX_SUPERSET_INTERNAL_TOKEN: 'token-123',
    }),
  );

  const result = await client.listDatasets(
    {
      contractVersion: DATASET_LIST_CONTRACT_VERSION,
      filters: [{ col: 'schema', opr: 'eq', value: 'public' }],
      selectColumns: ['id', 'table_name'],
      search: 'sales',
      orderColumn: 'table_name',
      orderDirection: 'desc',
      page: 2,
      pageSize: 10,
      createdByMe: false,
      ownedByMe: false,
    },
    'request-datasets',
  );

  expect(result).toEqual({
    contractVersion: DATASET_LIST_CONTRACT_VERSION,
    datasets: [
      {
        id: 11,
        tableName: 'sales_fact',
        schema: 'public',
        databaseName: 'examples',
        description: 'Orders and revenue',
        certifiedBy: 'BI',
        certificationDetails: 'Reviewed',
        changedOn: '2026-01-03T00:00:00',
        changedOnHumanized: '3 days ago',
        isVirtual: false,
        databaseId: 3,
        uuid: 'dataset-uuid',
        url: '/explore/?datasource_type=table&datasource_id=11',
      },
    ],
    count: 1,
    totalCount: 13,
    page: 2,
    pageSize: 10,
    totalPages: 2,
    hasNext: false,
    hasPrevious: true,
    columnsRequested: ['id', 'table_name'],
    columnsLoaded: [
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
      'is_virtual',
      'database_id',
      'uuid',
      'url',
    ],
    warnings: [],
  });
  expect(String(seenInput)).toContain('/api/v1/dataset/');
  expect(String(seenInput)).toContain('q=');
  expect(decodeURIComponent(String(seenInput))).toContain('page:1');
  expect(decodeURIComponent(String(seenInput))).toContain("value:'sales'");
  expect(seenInit?.headers).toEqual({
    authorization: 'Bearer token-123',
    'x-request-id': 'request-datasets',
  });
});

test('listDatasets ignores invalid related database IDs', async () => {
  global.fetch = async () =>
    Response.json({
      count: 2,
      result: [
        {
          id: 11,
          table_name: 'sales_fact',
          database_id: -3,
          database: {
            id: 2.5,
            database_name: 'examples',
          },
        },
        {
          id: 12,
          table_name: 'inventory_fact',
          database_id: 4,
        },
      ],
    });
  const client = new SupersetClient(buildConfig({}));

  const result = await client.listDatasets({
    contractVersion: DATASET_LIST_CONTRACT_VERSION,
    filters: [],
    selectColumns: [],
    orderDirection: 'asc',
    page: 1,
    pageSize: 10,
    createdByMe: false,
    ownedByMe: false,
  });

  expect(result.datasets).toEqual([
    {
      id: 11,
      tableName: 'sales_fact',
      databaseName: 'examples',
      isVirtual: false,
    },
    {
      id: 12,
      tableName: 'inventory_fact',
      isVirtual: false,
      databaseId: 4,
    },
  ]);
});

test('listDatasets records warnings for failed Superset list responses', async () => {
  global.fetch = async () =>
    new Response('upstream timeout', {
      status: 504,
      headers: {
        'content-type': 'text/plain',
      },
    });
  const client = new SupersetClient(buildConfig({}));

  const result = await client.listDatasets({
    contractVersion: DATASET_LIST_CONTRACT_VERSION,
    filters: [],
    selectColumns: [],
    orderDirection: 'asc',
    page: 1,
    pageSize: 10,
    createdByMe: false,
    ownedByMe: false,
  });

  expect(result).toEqual({
    contractVersion: DATASET_LIST_CONTRACT_VERSION,
    datasets: [],
    count: 0,
    totalCount: 0,
    page: 1,
    pageSize: 10,
    totalPages: 0,
    hasNext: false,
    hasPrevious: false,
    columnsRequested: [
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
    ],
    columnsLoaded: [],
    warnings: ['dataset list returned status 504 from Superset'],
  });
});

test('listDatabases maps Superset database list responses', async () => {
  let seenInput: RequestInfo | URL | undefined;
  let seenInit: RequestInit | undefined;
  global.fetch = async (input, init) => {
    seenInput = input;
    seenInit = init;
    return Response.json({
      count: 14,
      result: [
        {
          id: 13,
          uuid: 'database-uuid',
          database_name: 'examples',
          backend: 'postgresql',
          expose_in_sqllab: true,
          allow_ctas: false,
          allow_cvas: true,
          allow_dml: false,
          allow_file_upload: true,
          allow_run_async: false,
          cache_timeout: 300,
          configuration_method: 'sqlalchemy_form',
          force_ctas_schema: 'tmp',
          impersonate_user: true,
          is_managed_externally: false,
          external_url: 'https://example.test/database/13',
          extra: {
            metadata_params: {},
          },
          changed_on: '2026-01-04T00:00:00',
          changed_on_humanized: '4 days ago',
          created_on: '2026-01-01T00:00:00',
          created_on_humanized: '1 week ago',
        },
      ],
    });
  };
  const client = new SupersetClient(
    buildConfig({
      AX_SUPERSET_INTERNAL_TOKEN: 'token-123',
    }),
  );

  const result = await client.listDatabases(
    {
      contractVersion: DATABASE_LIST_CONTRACT_VERSION,
      filters: [{ col: 'expose_in_sqllab', opr: 'eq', value: true }],
      selectColumns: ['id', 'database_name'],
      search: 'examples',
      orderColumn: 'database_name',
      orderDirection: 'desc',
      page: 2,
      pageSize: 10,
      createdByMe: false,
    },
    'request-databases',
  );

  expect(result).toEqual({
    contractVersion: DATABASE_LIST_CONTRACT_VERSION,
    databases: [
      {
        id: 13,
        uuid: 'database-uuid',
        databaseName: 'examples',
        backend: 'postgresql',
        exposeInSqllab: true,
        allowCtas: false,
        allowCvas: true,
        allowDml: false,
        allowFileUpload: true,
        allowRunAsync: false,
        cacheTimeout: 300,
        configurationMethod: 'sqlalchemy_form',
        forceCtasSchema: 'tmp',
        impersonateUser: true,
        isManagedExternally: false,
        externalUrl: 'https://example.test/database/13',
        extra: {
          metadata_params: {},
        },
        changedOn: '2026-01-04T00:00:00',
        changedOnHumanized: '4 days ago',
        createdOn: '2026-01-01T00:00:00',
        createdOnHumanized: '1 week ago',
      },
    ],
    count: 1,
    totalCount: 14,
    page: 2,
    pageSize: 10,
    totalPages: 2,
    hasNext: false,
    hasPrevious: true,
    columnsRequested: ['id', 'database_name'],
    columnsLoaded: [
      'id',
      'uuid',
      'database_name',
      'backend',
      'expose_in_sqllab',
      'allow_ctas',
      'allow_cvas',
      'allow_dml',
      'allow_file_upload',
      'allow_run_async',
      'cache_timeout',
      'configuration_method',
      'force_ctas_schema',
      'impersonate_user',
      'is_managed_externally',
      'external_url',
      'extra',
      'changed_on',
      'changed_on_humanized',
      'created_on',
      'created_on_humanized',
    ],
    warnings: [],
  });
  expect(String(seenInput)).toContain('/api/v1/database/');
  expect(String(seenInput)).toContain('q=');
  expect(decodeURIComponent(String(seenInput))).toContain('page:1');
  expect(decodeURIComponent(String(seenInput))).toContain("value:'examples'");
  expect(seenInit?.headers).toEqual({
    authorization: 'Bearer token-123',
    'x-request-id': 'request-databases',
  });
});

test('listDatabases validates cache timeout values', async () => {
  global.fetch = async () =>
    Response.json({
      count: 4,
      result: [
        {
          id: 13,
          database_name: 'disabled-cache',
          cache_timeout: -1,
        },
        {
          id: 14,
          database_name: 'fractional-cache',
          cache_timeout: 10.5,
        },
        {
          id: 15,
          database_name: 'invalid-negative-cache',
          cache_timeout: -2,
        },
        {
          id: 16,
          database_name: 'normal-cache',
          cache_timeout: 300,
        },
      ],
    });
  const client = new SupersetClient(buildConfig({}));

  const result = await client.listDatabases({
    contractVersion: DATABASE_LIST_CONTRACT_VERSION,
    filters: [],
    selectColumns: [],
    orderDirection: 'asc',
    page: 1,
    pageSize: 10,
    createdByMe: false,
  });

  expect(result.databases).toEqual([
    {
      id: 13,
      databaseName: 'disabled-cache',
      cacheTimeout: -1,
    },
    {
      id: 14,
      databaseName: 'fractional-cache',
    },
    {
      id: 15,
      databaseName: 'invalid-negative-cache',
    },
    {
      id: 16,
      databaseName: 'normal-cache',
      cacheTimeout: 300,
    },
  ]);
  expect(result.columnsLoaded).toContain('cache_timeout');
});

test('listDatabases records warnings for failed Superset list responses', async () => {
  global.fetch = async () =>
    new Response('upstream timeout', {
      status: 504,
      headers: {
        'content-type': 'text/plain',
      },
    });
  const client = new SupersetClient(buildConfig({}));

  const result = await client.listDatabases({
    contractVersion: DATABASE_LIST_CONTRACT_VERSION,
    filters: [],
    selectColumns: [],
    orderDirection: 'asc',
    page: 1,
    pageSize: 10,
    createdByMe: false,
  });

  expect(result).toEqual({
    contractVersion: DATABASE_LIST_CONTRACT_VERSION,
    databases: [],
    count: 0,
    totalCount: 0,
    page: 1,
    pageSize: 10,
    totalPages: 0,
    hasNext: false,
    hasPrevious: false,
    columnsRequested: [
      'id',
      'uuid',
      'database_name',
      'backend',
      'expose_in_sqllab',
      'allow_file_upload',
      'changed_on',
      'changed_on_humanized',
    ],
    columnsLoaded: [],
    warnings: ['database list returned status 504 from Superset'],
  });
});

test('listQueries maps Superset query list responses', async () => {
  let seenInput: RequestInfo | URL | undefined;
  let seenInit: RequestInit | undefined;
  global.fetch = async (input, init) => {
    seenInput = input;
    seenInit = init;
    return Response.json({
      count: 4,
      result: [
        {
          id: 11,
          sql: 'SELECT * FROM sales',
          executed_sql: 'SELECT * FROM sales LIMIT 1000',
          status: 'success',
          start_time: 1700000000,
          end_time: 1700000001,
          rows: 10,
          database: {
            id: 3,
            database_name: 'examples',
          },
          schema: 'public',
          catalog: 'analytics',
          tab_name: 'SQL Lab',
          error_message: '',
          client_id: 'query-client-id',
          limit: 1000,
          progress: 100,
          changed_on: '2026-01-05T00:00:00',
          user: {
            id: 42,
          },
        },
      ],
    });
  };
  const client = new SupersetClient(
    buildConfig({
      AX_SUPERSET_INTERNAL_TOKEN: 'token-123',
    }),
  );

  const result = await client.listQueries(
    {
      contractVersion: QUERY_LIST_CONTRACT_VERSION,
      filters: [{ col: 'status', opr: 'eq', value: 'success' }],
      selectColumns: ['id', 'status', 'database_id', 'schema'],
      search: 'sales',
      orderColumn: 'changed_on',
      orderDirection: 'desc',
      page: 2,
      pageSize: 2,
    },
    'request-queries',
  );

  expect(result).toEqual({
    contractVersion: QUERY_LIST_CONTRACT_VERSION,
    queries: [
      {
        id: 11,
        sql: 'SELECT * FROM sales',
        executedSql: 'SELECT * FROM sales LIMIT 1000',
        status: 'success',
        startTime: 1700000000,
        endTime: 1700000001,
        rows: 10,
        databaseId: 3,
        schema: 'public',
        catalog: 'analytics',
        tabName: 'SQL Lab',
        errorMessage: '',
        clientId: 'query-client-id',
        limit: 1000,
        progress: 100,
        changedOn: '2026-01-05T00:00:00',
        userId: 42,
      },
    ],
    count: 1,
    totalCount: 4,
    page: 2,
    pageSize: 2,
    totalPages: 2,
    hasNext: false,
    hasPrevious: true,
    columnsRequested: ['id', 'status', 'database_id', 'schema'],
    columnsLoaded: [
      'id',
      'sql',
      'executed_sql',
      'status',
      'start_time',
      'end_time',
      'rows',
      'database_id',
      'schema',
      'catalog',
      'tab_name',
      'error_message',
      'client_id',
      'limit',
      'progress',
      'changed_on',
      'user_id',
    ],
    warnings: [],
  });
  expect(String(seenInput)).toContain('/api/v1/query/');
  expect(String(seenInput)).toContain('q=');
  expect(decodeURIComponent(String(seenInput))).toContain('page:1');
  expect(decodeURIComponent(String(seenInput))).toContain("value:'sales'");
  expect(seenInit?.headers).toEqual({
    authorization: 'Bearer token-123',
    'x-request-id': 'request-queries',
  });
});

test('listQueries ignores invalid numeric metrics', async () => {
  global.fetch = async () =>
    Response.json({
      count: 1,
      result: [
        {
          id: 11,
          status: 'success',
          start_time: -1,
          end_time: Number.POSITIVE_INFINITY,
          rows: 10.5,
          limit: -100,
          progress: Number.NaN,
        },
      ],
    });
  const client = new SupersetClient(buildConfig({}));

  const result = await client.listQueries({
    contractVersion: QUERY_LIST_CONTRACT_VERSION,
    filters: [],
    selectColumns: [],
    orderDirection: 'asc',
    page: 1,
    pageSize: 10,
  });

  expect(result.queries).toEqual([
    {
      id: 11,
      status: 'success',
    },
  ]);
  expect(result.columnsLoaded).toEqual(['id', 'status']);
});

test('listQueries records warnings for failed Superset list responses', async () => {
  global.fetch = async () =>
    new Response('upstream timeout', {
      status: 504,
      headers: {
        'content-type': 'text/plain',
      },
    });
  const client = new SupersetClient(buildConfig({}));

  const result = await client.listQueries({
    contractVersion: QUERY_LIST_CONTRACT_VERSION,
    filters: [],
    selectColumns: [],
    orderDirection: 'desc',
    page: 1,
    pageSize: 25,
  });

  expect(result).toEqual({
    contractVersion: QUERY_LIST_CONTRACT_VERSION,
    queries: [],
    count: 0,
    totalCount: 0,
    page: 1,
    pageSize: 25,
    totalPages: 0,
    hasNext: false,
    hasPrevious: false,
    columnsRequested: ['id', 'status', 'start_time', 'database_id', 'schema'],
    columnsLoaded: [],
    warnings: ['query list returned status 504 from Superset'],
  });
});

test('listSavedQueries maps Superset saved query list responses', async () => {
  let seenInput: RequestInfo | URL | undefined;
  let seenInit: RequestInit | undefined;
  global.fetch = async (input, init) => {
    seenInput = input;
    seenInit = init;
    return Response.json({
      count: 15,
      result: [
        {
          id: 17,
          uuid: 'saved-query-uuid',
          label: 'Revenue query',
          sql: 'select * from sales',
          db_id: 3,
          schema: 'public',
          catalog: 'analytics',
          description: 'Revenue analysis',
          changed_on: '2026-01-05T00:00:00',
          created_on: '2026-01-01T00:00:00',
          last_run: '2026-01-06T00:00:00',
        },
      ],
    });
  };
  const client = new SupersetClient(
    buildConfig({
      AX_SUPERSET_INTERNAL_TOKEN: 'token-123',
    }),
  );

  const result = await client.listSavedQueries(
    {
      contractVersion: SAVED_QUERY_LIST_CONTRACT_VERSION,
      filters: [{ col: 'schema', opr: 'eq', value: 'public' }],
      selectColumns: ['id', 'label'],
      search: 'revenue',
      orderColumn: 'label',
      orderDirection: 'desc',
      page: 2,
      pageSize: 10,
    },
    'request-saved-queries',
  );

  expect(result).toEqual({
    contractVersion: SAVED_QUERY_LIST_CONTRACT_VERSION,
    savedQueries: [
      {
        id: 17,
        uuid: 'saved-query-uuid',
        label: 'Revenue query',
        sql: 'select * from sales',
        dbId: 3,
        schema: 'public',
        catalog: 'analytics',
        description: 'Revenue analysis',
        changedOn: '2026-01-05T00:00:00',
        createdOn: '2026-01-01T00:00:00',
        lastRun: '2026-01-06T00:00:00',
      },
    ],
    count: 1,
    totalCount: 15,
    page: 2,
    pageSize: 10,
    totalPages: 2,
    hasNext: false,
    hasPrevious: true,
    columnsRequested: ['id', 'label'],
    columnsLoaded: [
      'id',
      'uuid',
      'label',
      'sql',
      'db_id',
      'schema',
      'catalog',
      'description',
      'changed_on',
      'created_on',
      'last_run',
    ],
    warnings: [],
  });
  expect(String(seenInput)).toContain('/api/v1/saved_query/');
  expect(String(seenInput)).toContain('q=');
  expect(decodeURIComponent(String(seenInput))).toContain('page:1');
  expect(decodeURIComponent(String(seenInput))).toContain("value:'revenue'");
  expect(seenInit?.headers).toEqual({
    authorization: 'Bearer token-123',
    'x-request-id': 'request-saved-queries',
  });
});

test('listSavedQueries records warnings for failed Superset list responses', async () => {
  global.fetch = async () =>
    new Response('upstream timeout', {
      status: 504,
      headers: {
        'content-type': 'text/plain',
      },
    });
  const client = new SupersetClient(buildConfig({}));

  const result = await client.listSavedQueries({
    contractVersion: SAVED_QUERY_LIST_CONTRACT_VERSION,
    filters: [],
    selectColumns: [],
    orderDirection: 'asc',
    page: 1,
    pageSize: 10,
  });

  expect(result).toEqual({
    contractVersion: SAVED_QUERY_LIST_CONTRACT_VERSION,
    savedQueries: [],
    count: 0,
    totalCount: 0,
    page: 1,
    pageSize: 10,
    totalPages: 0,
    hasNext: false,
    hasPrevious: false,
    columnsRequested: ['id', 'label', 'db_id', 'schema', 'uuid'],
    columnsLoaded: [],
    warnings: ['saved query list returned status 504 from Superset'],
  });
});

test('listReports maps Superset report list responses', async () => {
  let seenInput: RequestInfo | URL | undefined;
  let seenInit: RequestInit | undefined;
  global.fetch = async (input, init) => {
    seenInput = input;
    seenInit = init;
    return Response.json({
      count: 21,
      result: [
        {
          id: 23,
          name: 'Daily sales report',
          description: 'Sends sales summary',
          type: 'Report',
          active: true,
          crontab: '0 9 * * *',
          dashboard_id: 7,
          chart_id: 11,
          last_eval_dttm: '2026-01-08T00:00:00',
          last_eval_dttm_humanized: 'a day ago',
          last_state: 'Success',
          creation_method: 'alerts_reports',
          changed_on: '2026-01-07T00:00:00',
          changed_on_humanized: '2 days ago',
          created_on: '2026-01-01T00:00:00',
          created_on_humanized: '8 days ago',
        },
      ],
    });
  };
  const client = new SupersetClient(
    buildConfig({
      AX_SUPERSET_INTERNAL_TOKEN: 'token-123',
    }),
  );

  const result = await client.listReports(
    {
      contractVersion: REPORT_LIST_CONTRACT_VERSION,
      filters: [{ col: 'active', opr: 'eq', value: true }],
      selectColumns: ['id', 'name'],
      search: 'daily',
      orderColumn: 'name',
      orderDirection: 'desc',
      page: 2,
      pageSize: 10,
    },
    'request-reports',
  );

  expect(result).toEqual({
    contractVersion: REPORT_LIST_CONTRACT_VERSION,
    reports: [
      {
        id: 23,
        name: 'Daily sales report',
        description: 'Sends sales summary',
        type: 'Report',
        active: true,
        crontab: '0 9 * * *',
        dashboardId: 7,
        chartId: 11,
        lastEvalDttm: '2026-01-08T00:00:00',
        lastEvalDttmHumanized: 'a day ago',
        lastState: 'Success',
        creationMethod: 'alerts_reports',
        changedOn: '2026-01-07T00:00:00',
        changedOnHumanized: '2 days ago',
        createdOn: '2026-01-01T00:00:00',
        createdOnHumanized: '8 days ago',
      },
    ],
    count: 1,
    totalCount: 21,
    page: 2,
    pageSize: 10,
    totalPages: 3,
    hasNext: true,
    hasPrevious: true,
    columnsRequested: ['id', 'name'],
    columnsLoaded: [
      'id',
      'name',
      'description',
      'type',
      'active',
      'crontab',
      'dashboard_id',
      'chart_id',
      'last_eval_dttm',
      'last_eval_dttm_humanized',
      'last_state',
      'creation_method',
      'changed_on',
      'changed_on_humanized',
      'created_on',
      'created_on_humanized',
    ],
    warnings: [],
  });
  expect(String(seenInput)).toContain('/api/v1/report/');
  expect(String(seenInput)).toContain('q=');
  expect(decodeURIComponent(String(seenInput))).toContain('page:1');
  expect(decodeURIComponent(String(seenInput))).toContain("value:'daily'");
  expect(seenInit?.headers).toEqual({
    authorization: 'Bearer token-123',
    'x-request-id': 'request-reports',
  });
});

test('listReports records warnings for failed Superset list responses', async () => {
  global.fetch = async () =>
    new Response('upstream timeout', {
      status: 504,
      headers: {
        'content-type': 'text/plain',
      },
    });
  const client = new SupersetClient(buildConfig({}));

  const result = await client.listReports({
    contractVersion: REPORT_LIST_CONTRACT_VERSION,
    filters: [],
    selectColumns: [],
    orderDirection: 'asc',
    page: 1,
    pageSize: 10,
  });

  expect(result).toEqual({
    contractVersion: REPORT_LIST_CONTRACT_VERSION,
    reports: [],
    count: 0,
    totalCount: 0,
    page: 1,
    pageSize: 10,
    totalPages: 0,
    hasNext: false,
    hasPrevious: false,
    columnsRequested: ['id', 'name', 'type', 'active', 'crontab'],
    columnsLoaded: [],
    warnings: ['report list returned status 504 from Superset'],
  });
});

test('listRoles maps Superset role list responses', async () => {
  let seenInput: RequestInfo | URL | undefined;
  let seenInit: RequestInit | undefined;
  global.fetch = async (input, init) => {
    seenInput = input;
    seenInit = init;
    return Response.json({
      count: 4,
      result: [
        {
          id: 31,
          name: 'Admin',
        },
      ],
    });
  };
  const client = new SupersetClient(
    buildConfig({
      AX_SUPERSET_INTERNAL_TOKEN: 'token-123',
    }),
  );

  const result = await client.listRoles(
    {
      contractVersion: ROLE_LIST_CONTRACT_VERSION,
      filters: [{ col: 'name', opr: 'ct', value: 'Admin' }],
      selectColumns: ['id', 'name'],
      search: 'admin',
      orderColumn: 'name',
      orderDirection: 'desc',
      page: 2,
      pageSize: 2,
    },
    'request-roles',
  );

  expect(result).toEqual({
    contractVersion: ROLE_LIST_CONTRACT_VERSION,
    roles: [
      {
        id: 31,
        name: 'Admin',
      },
    ],
    count: 1,
    totalCount: 4,
    page: 2,
    pageSize: 2,
    totalPages: 2,
    hasNext: false,
    hasPrevious: true,
    columnsRequested: ['id', 'name'],
    columnsLoaded: ['id', 'name'],
    warnings: [],
  });
  expect(String(seenInput)).toContain('/api/v1/role/');
  expect(String(seenInput)).toContain('q=');
  expect(decodeURIComponent(String(seenInput))).toContain('page:1');
  expect(decodeURIComponent(String(seenInput))).toContain("value:'admin'");
  expect(seenInit?.headers).toEqual({
    authorization: 'Bearer token-123',
    'x-request-id': 'request-roles',
  });
});

test('listRoles records warnings for failed Superset list responses', async () => {
  global.fetch = async () =>
    new Response('upstream timeout', {
      status: 504,
      headers: {
        'content-type': 'text/plain',
      },
    });
  const client = new SupersetClient(buildConfig({}));

  const result = await client.listRoles({
    contractVersion: ROLE_LIST_CONTRACT_VERSION,
    filters: [],
    selectColumns: [],
    orderDirection: 'asc',
    page: 1,
    pageSize: 10,
  });

  expect(result).toEqual({
    contractVersion: ROLE_LIST_CONTRACT_VERSION,
    roles: [],
    count: 0,
    totalCount: 0,
    page: 1,
    pageSize: 10,
    totalPages: 0,
    hasNext: false,
    hasPrevious: false,
    columnsRequested: ['id', 'name'],
    columnsLoaded: [],
    warnings: ['role list returned status 504 from Superset'],
  });
});

test('listRlsFilters maps Superset RLS filter list responses', async () => {
  let seenInput: RequestInfo | URL | undefined;
  let seenInit: RequestInit | undefined;
  global.fetch = async (input, init) => {
    seenInput = input;
    seenInit = init;
    return Response.json({
      count: 3,
      result: [
        {
          id: 42,
          name: 'regional_sales',
          filter_type: 'Regular',
          tables: [{ id: 7, table_name: 'sales' }],
          roles: [{ id: 3, name: 'Alpha' }],
          clause: 'region = "EMEA"',
          group_key: 'region',
          changed_on_delta_humanized: '1 hour ago',
        },
      ],
    });
  };
  const client = new SupersetClient(
    buildConfig({
      AX_SUPERSET_INTERNAL_TOKEN: 'token-123',
    }),
  );

  const result = await client.listRlsFilters(
    {
      contractVersion: RLS_LIST_CONTRACT_VERSION,
      filters: [{ col: 'filter_type', opr: 'eq', value: 'Regular' }],
      selectColumns: ['id', 'name', 'filter_type', 'tables', 'roles', 'clause'],
      search: 'regional',
      orderColumn: 'name',
      orderDirection: 'desc',
      page: 2,
      pageSize: 2,
    },
    'request-rls',
  );

  expect(result).toEqual({
    contractVersion: RLS_LIST_CONTRACT_VERSION,
    rlsFilters: [
      {
        id: 42,
        name: 'regional_sales',
        filterType: 'Regular',
        tables: [{ id: 7, tableName: 'sales' }],
        roles: [{ id: 3, name: 'Alpha' }],
        clause: 'region = "EMEA"',
        groupKey: 'region',
        changedOn: '1 hour ago',
      },
    ],
    count: 1,
    totalCount: 3,
    page: 2,
    pageSize: 2,
    totalPages: 2,
    hasNext: false,
    hasPrevious: true,
    columnsRequested: ['id', 'name', 'filter_type', 'tables', 'roles', 'clause'],
    columnsLoaded: [
      'id',
      'name',
      'filter_type',
      'tables',
      'roles',
      'clause',
      'group_key',
      'changed_on',
    ],
    warnings: [],
  });
  expect(String(seenInput)).toContain('/api/v1/rowlevelsecurity/');
  expect(String(seenInput)).toContain('q=');
  expect(decodeURIComponent(String(seenInput))).toContain('page:1');
  expect(decodeURIComponent(String(seenInput))).toContain("value:'regional'");
  expect(seenInit?.headers).toEqual({
    authorization: 'Bearer token-123',
    'x-request-id': 'request-rls',
  });
});

test('listRlsFilters ignores malformed relation metadata', async () => {
  global.fetch = async () =>
    Response.json({
      count: 1,
      result: [
        {
          id: 42,
          name: 'regional_sales',
          filter_type: 'Regular',
          tables: { id: 7, table_name: 'sales' },
          roles: { id: 3, name: 'Alpha' },
          clause: 'region = "EMEA"',
        },
      ],
    });
  const client = new SupersetClient(buildConfig({}));

  const result = await client.listRlsFilters({
    contractVersion: RLS_LIST_CONTRACT_VERSION,
    filters: [],
    selectColumns: [],
    orderDirection: 'asc',
    page: 1,
    pageSize: 10,
  });

  expect(result).toEqual({
    contractVersion: RLS_LIST_CONTRACT_VERSION,
    rlsFilters: [
      {
        id: 42,
        name: 'regional_sales',
        filterType: 'Regular',
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
    columnsRequested: ['id', 'name', 'filter_type', 'clause'],
    columnsLoaded: ['id', 'name', 'filter_type', 'clause'],
    warnings: [],
  });
});

test('listRlsFilters records warnings for failed Superset list responses', async () => {
  global.fetch = async () =>
    new Response('upstream timeout', {
      status: 504,
      headers: {
        'content-type': 'text/plain',
      },
    });
  const client = new SupersetClient(buildConfig({}));

  const result = await client.listRlsFilters({
    contractVersion: RLS_LIST_CONTRACT_VERSION,
    filters: [],
    selectColumns: [],
    orderDirection: 'asc',
    page: 1,
    pageSize: 10,
  });

  expect(result).toEqual({
    contractVersion: RLS_LIST_CONTRACT_VERSION,
    rlsFilters: [],
    count: 0,
    totalCount: 0,
    page: 1,
    pageSize: 10,
    totalPages: 0,
    hasNext: false,
    hasPrevious: false,
    columnsRequested: ['id', 'name', 'filter_type', 'clause'],
    columnsLoaded: [],
    warnings: ['RLS filter list returned status 504 from Superset'],
  });
});

test('listTags maps Superset tag list responses', async () => {
  let seenInput: RequestInfo | URL | undefined;
  let seenInit: RequestInit | undefined;
  global.fetch = async (input, init) => {
    seenInput = input;
    seenInit = init;
    return Response.json({
      count: 16,
      result: [
        {
          id: 19,
          name: 'finance',
          type: 'custom',
          description: 'Finance-owned assets',
          changed_on: '2026-01-07T00:00:00',
          changed_on_humanized: '1 hour ago',
          created_on: '2026-01-01T00:00:00',
          created_on_humanized: '1 week ago',
        },
      ],
    });
  };
  const client = new SupersetClient(
    buildConfig({
      AX_SUPERSET_INTERNAL_TOKEN: 'token-123',
    }),
  );

  const result = await client.listTags(
    {
      contractVersion: TAG_LIST_CONTRACT_VERSION,
      filters: [{ col: 'type', opr: 'eq', value: 'custom' }],
      selectColumns: ['id', 'name'],
      search: 'finance',
      orderColumn: 'name',
      orderDirection: 'desc',
      page: 2,
      pageSize: 10,
    },
    'request-tags',
  );

  expect(result).toEqual({
    contractVersion: TAG_LIST_CONTRACT_VERSION,
    tags: [
      {
        id: 19,
        name: 'finance',
        type: 'custom',
        description: 'Finance-owned assets',
        changedOn: '2026-01-07T00:00:00',
        changedOnHumanized: '1 hour ago',
        createdOn: '2026-01-01T00:00:00',
        createdOnHumanized: '1 week ago',
      },
    ],
    count: 1,
    totalCount: 16,
    page: 2,
    pageSize: 10,
    totalPages: 2,
    hasNext: false,
    hasPrevious: true,
    columnsRequested: ['id', 'name'],
    columnsLoaded: [
      'id',
      'name',
      'type',
      'description',
      'changed_on',
      'changed_on_humanized',
      'created_on',
      'created_on_humanized',
    ],
    warnings: [],
  });
  expect(String(seenInput)).toContain('/api/v1/tag/');
  expect(String(seenInput)).toContain('q=');
  expect(decodeURIComponent(String(seenInput))).toContain('page:1');
  expect(decodeURIComponent(String(seenInput))).toContain("value:'finance'");
  expect(seenInit?.headers).toEqual({
    authorization: 'Bearer token-123',
    'x-request-id': 'request-tags',
  });
});

test('listTags records warnings for failed Superset list responses', async () => {
  global.fetch = async () =>
    new Response('upstream timeout', {
      status: 504,
      headers: {
        'content-type': 'text/plain',
      },
    });
  const client = new SupersetClient(buildConfig({}));

  const result = await client.listTags({
    contractVersion: TAG_LIST_CONTRACT_VERSION,
    filters: [],
    selectColumns: [],
    orderDirection: 'asc',
    page: 1,
    pageSize: 10,
  });

  expect(result).toEqual({
    contractVersion: TAG_LIST_CONTRACT_VERSION,
    tags: [],
    count: 0,
    totalCount: 0,
    page: 1,
    pageSize: 10,
    totalPages: 0,
    hasNext: false,
    hasPrevious: false,
    columnsRequested: ['id', 'name', 'type'],
    columnsLoaded: [],
    warnings: ['tag list returned status 504 from Superset'],
  });
});

test('listTasks maps Superset task list responses', async () => {
  let seenInput: RequestInfo | URL | undefined;
  let seenInit: RequestInit | undefined;
  global.fetch = async (input, init) => {
    seenInput = input;
    seenInit = init;
    return Response.json({
      count: 12,
      result: [
        {
          id: 31,
          uuid: 'task-uuid',
          task_type: 'sql_execution',
          task_key: 'task-key',
          task_name: 'Refresh cache',
          status: 'success',
          scope: 'private',
          changed_on: '2026-01-07T00:00:00',
          created_on: '2026-01-01T00:00:00',
        },
      ],
    });
  };
  const client = new SupersetClient(
    buildConfig({
      AX_SUPERSET_INTERNAL_TOKEN: 'token-123',
    }),
  );

  const result = await client.listTasks(
    {
      contractVersion: TASK_LIST_CONTRACT_VERSION,
      filters: [{ col: 'status', opr: 'eq', value: 'success' }],
      selectColumns: ['id', 'task_name'],
      search: 'refresh',
      orderColumn: 'changed_on',
      orderDirection: 'desc',
      page: 2,
      pageSize: 10,
    },
    'request-tasks',
  );

  expect(result).toEqual({
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
        changedOn: '2026-01-07T00:00:00',
        createdOn: '2026-01-01T00:00:00',
      },
    ],
    count: 1,
    totalCount: 12,
    page: 2,
    pageSize: 10,
    totalPages: 2,
    hasNext: false,
    hasPrevious: true,
    columnsRequested: ['id', 'task_name'],
    columnsLoaded: [
      'id',
      'uuid',
      'task_type',
      'task_key',
      'task_name',
      'status',
      'scope',
      'changed_on',
      'created_on',
    ],
    warnings: [],
  });
  expect(String(seenInput)).toContain('/api/v1/task/');
  expect(String(seenInput)).toContain('q=');
  expect(decodeURIComponent(String(seenInput))).toContain('page:1');
  expect(decodeURIComponent(String(seenInput))).toContain('col:task_name');
  expect(decodeURIComponent(String(seenInput))).toContain("value:'refresh'");
  expect(seenInit?.headers).toEqual({
    authorization: 'Bearer token-123',
    'x-request-id': 'request-tasks',
  });
});

test('listTasks records warnings for failed Superset list responses', async () => {
  global.fetch = async () =>
    new Response('upstream timeout', {
      status: 504,
      headers: {
        'content-type': 'text/plain',
      },
    });
  const client = new SupersetClient(buildConfig({}));

  const result = await client.listTasks({
    contractVersion: TASK_LIST_CONTRACT_VERSION,
    filters: [],
    selectColumns: [],
    orderDirection: 'asc',
    page: 1,
    pageSize: 10,
  });

  expect(result).toEqual({
    contractVersion: TASK_LIST_CONTRACT_VERSION,
    tasks: [],
    count: 0,
    totalCount: 0,
    page: 1,
    pageSize: 10,
    totalPages: 0,
    hasNext: false,
    hasPrevious: false,
    columnsRequested: ['id', 'uuid', 'task_type', 'status', 'changed_on'],
    columnsLoaded: [],
    warnings: ['task list returned status 504 from Superset'],
  });
});

test('checkHealth returns an error result when fetch fails', async () => {
  global.fetch = async () => {
    throw new Error('connect failed');
  };
  const client = new SupersetClient(buildConfig({}));

  const result = await client.checkHealth();

  expect(result).toEqual({
    ok: false,
    error: 'connect failed',
    url: 'http://127.0.0.1:8088/health',
  });
});

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
import { ASSET_SEARCH_CONTRACT_VERSION } from '../src/contracts/assetSearch';
import { AUTHORIZATION_CONTRACT_VERSION } from '../src/contracts/authorization';
import { CHART_LIST_CONTRACT_VERSION } from '../src/contracts/chartList';
import { DASHBOARD_LIST_CONTRACT_VERSION } from '../src/contracts/dashboardList';
import { DATABASE_LIST_CONTRACT_VERSION } from '../src/contracts/databaseList';
import { DATASET_LIST_CONTRACT_VERSION } from '../src/contracts/datasetList';
import { SAVED_QUERY_LIST_CONTRACT_VERSION } from '../src/contracts/savedQueryList';
import { TAG_LIST_CONTRACT_VERSION } from '../src/contracts/tagList';
import { SupersetClient } from '../src/supersetClient';

const originalFetch = global.fetch;

afterEach(() => {
  global.fetch = originalFetch;
});

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
  expect(seenInputs[0]).toContain('/api/v1/dataset/');
  expect(seenInputs[0]).toContain('q=');
  expect(seenInputs[1]).toContain('/api/v1/chart/');
  expect(seenInits[0].headers).toEqual({
    authorization: 'Bearer token-123',
    'x-request-id': 'request-search',
  });
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

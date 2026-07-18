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
import rison from 'rison';
import { AxBIClient } from '@ax-bi/ui-core';
import { ASSET_SEARCH_PAGE_SIZE, searchAssets } from 'src/services/assetSearch';

const DASHBOARD_ROW = {
  id: 1,
  dashboard_title: 'Sales dashboard',
  url: '/ax-bi/dashboard/1/',
};
const CHART_ROW = { id: 2, slice_name: 'Sales chart' };
const DATASET_ROW = { id: 3, table_name: 'sales_table' };
const DATABASE_ROW = { id: 4, database_name: 'sales_db' };
const SAVED_QUERY_ROW = { id: 5, label: 'sales query' };

const ENDPOINT_ROWS: Record<string, unknown[]> = {
  '/api/v1/dashboard/': [DASHBOARD_ROW],
  '/api/v1/chart/': [CHART_ROW],
  '/api/v1/dataset/': [DATASET_ROW],
  '/api/v1/database/': [DATABASE_ROW],
  '/api/v1/saved_query/': [SAVED_QUERY_ROW],
};

interface DecodedQuery {
  filters: Array<{ col: string; opr: string; value: string }>;
  page_size: number;
  order_column: string;
  order_direction: string;
}

const decodeQuery = (endpoint: string): DecodedQuery => {
  const q = new URL(`http://localhost${endpoint}`).searchParams.get('q');
  return rison.decode(q ?? '') as DecodedQuery;
};

const getSpy = jest.spyOn(AxBIClient, 'get');

beforeEach(() => {
  getSpy.mockReset();
  getSpy.mockImplementation(async ({ endpoint }) => {
    const path = Object.keys(ENDPOINT_ROWS).find(prefix =>
      String(endpoint).startsWith(prefix),
    );
    return {
      json: { result: path ? ENDPOINT_ROWS[path] : [] },
      response: new Response(),
    };
  });
});

afterAll(() => {
  getSpy.mockRestore();
});

const calledEndpoints = () =>
  getSpy.mock.calls.map(([config]) => String(config.endpoint));

test('searches all five asset types and groups typed results', async () => {
  const results = await searchAssets('sales');

  expect(results.dashboards).toEqual([
    { id: 1, title: 'Sales dashboard', url: '/ax-bi/dashboard/1/' },
  ]);
  expect(results.charts).toEqual([
    { id: 2, title: 'Sales chart', url: undefined },
  ]);
  expect(results.datasets).toEqual([{ id: 3, title: 'sales_table' }]);
  expect(results.databases).toEqual([{ id: 4, title: 'sales_db' }]);
  expect(results.savedQueries).toEqual([{ id: 5, title: 'sales query' }]);
  expect(getSpy).toHaveBeenCalledTimes(5);
});

test('builds contains rison filters with the per-type column and page cap', async () => {
  await searchAssets('sales');

  const expectedColumns: Record<string, string> = {
    '/api/v1/dashboard/': 'dashboard_title',
    '/api/v1/chart/': 'slice_name',
    '/api/v1/dataset/': 'table_name',
    '/api/v1/database/': 'database_name',
    '/api/v1/saved_query/': 'label',
  };

  Object.entries(expectedColumns).forEach(([prefix, column]) => {
    const endpoint = calledEndpoints().find(url => url.startsWith(prefix));
    expect(endpoint).toBeDefined();
    const query = decodeQuery(endpoint!);
    expect(query.filters).toEqual([{ col: column, opr: 'ct', value: 'sales' }]);
    expect(query.page_size).toBe(ASSET_SEARCH_PAGE_SIZE);
    expect(query.order_column).toBe('changed_on_delta_humanized');
    expect(query.order_direction).toBe('desc');
  });
});

test('restricts the search to the requested types', async () => {
  const results = await searchAssets('sales', {
    types: ['dashboards', 'charts'],
  });

  const endpoints = calledEndpoints();
  expect(endpoints.some(url => url.startsWith('/api/v1/dashboard/'))).toBe(
    true,
  );
  expect(endpoints.some(url => url.startsWith('/api/v1/chart/'))).toBe(true);
  expect(endpoints).toHaveLength(2);
  expect(results.dashboards).toHaveLength(1);
  expect(results.charts).toHaveLength(1);
  expect(results.datasets).toEqual([]);
  expect(results.databases).toEqual([]);
  expect(results.savedQueries).toEqual([]);
});

test('contains a failing endpoint without rejecting the other types', async () => {
  getSpy.mockImplementation(async ({ endpoint }) => {
    if (String(endpoint).startsWith('/api/v1/chart/')) {
      throw new Error('Chart API down');
    }
    const path = Object.keys(ENDPOINT_ROWS).find(prefix =>
      String(endpoint).startsWith(prefix),
    );
    return {
      json: { result: path ? ENDPOINT_ROWS[path] : [] },
      response: new Response(),
    };
  });

  const results = await searchAssets('sales');

  expect(results.charts).toEqual([]);
  expect(results.dashboards).toHaveLength(1);
  expect(results.datasets).toHaveLength(1);
  expect(results.databases).toHaveLength(1);
  expect(results.savedQueries).toHaveLength(1);
});

test('honors a custom page size for every type', async () => {
  await searchAssets('sales', { pageSize: 3 });

  calledEndpoints().forEach(endpoint => {
    expect(decodeQuery(endpoint).page_size).toBe(3);
  });
});

test('returns empty groups and skips requests for a blank query', async () => {
  const results = await searchAssets('   ');

  expect(getSpy).not.toHaveBeenCalled();
  expect(results).toEqual({
    dashboards: [],
    charts: [],
    datasets: [],
    databases: [],
    savedQueries: [],
  });
});

test('skips requests when the signal is already aborted', async () => {
  const controller = new AbortController();
  controller.abort();

  const results = await searchAssets('sales', { signal: controller.signal });

  expect(getSpy).not.toHaveBeenCalled();
  expect(results.dashboards).toEqual([]);
});

test('rejects when the signal aborts mid-flight', async () => {
  getSpy.mockImplementation(
    ({ signal }) =>
      new Promise((_, reject) => {
        signal?.addEventListener('abort', () =>
          reject(new DOMException('Aborted', 'AbortError')),
        );
      }),
  );
  const controller = new AbortController();

  const promise = searchAssets('sales', { signal: controller.signal });
  controller.abort();

  await expect(promise).rejects.toThrow('Aborted');
});

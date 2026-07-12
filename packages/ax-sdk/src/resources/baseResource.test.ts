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

import { jest } from '@jest/globals';

import type { HttpClient } from '../transport/httpClient.js';
import { BaseResource } from './baseResource.js';
import { ChartsResource } from './charts.js';
import { DashboardsResource } from './dashboards.js';
import type { AxBIListEnvelope } from './types.js';

interface TestItem {
  id: number;
  name?: string;
}

class TestResource extends BaseResource<
  TestItem,
  { name: string },
  { name: string }
> {
  protected readonly basePath = '/api/v1/test';
  protected readonly searchColumn = 'name';
}

test('BaseResource reports zero total pages for empty list responses', async () => {
  const envelope: AxBIListEnvelope<TestItem> = {
    count: 0,
    ids: [],
    result: [],
  };
  const get = jest.fn(async () => envelope);
  const resource = new TestResource({ get } as unknown as HttpClient);

  await expect(resource.list({ page: 1, pageSize: 20 })).resolves.toEqual({
    results: [],
    count: 0,
    totalCount: 0,
    page: 1,
    pageSize: 20,
    totalPages: 0,
    hasNext: false,
    hasPrevious: false,
  });
});

test('BaseResource encodes item IDs before fetching a single item', async () => {
  const item: TestItem = { id: 7, name: 'encoded' };
  const get = jest.fn(async () => ({ id: item.id, result: item }));
  const resource = new TestResource({ get } as unknown as HttpClient);

  await expect(resource.getById('uuid/with?query=1')).resolves.toEqual(item);

  expect(get).toHaveBeenCalledWith('/api/v1/test/uuid%2Fwith%3Fquery%3D1');
});

test('BaseResource encodes item IDs before updating an item', async () => {
  const item: TestItem = { id: 7, name: 'updated' };
  const put = jest.fn(async () => ({ id: item.id, result: item }));
  const resource = new TestResource({ put } as unknown as HttpClient);

  await expect(
    resource.update('uuid/with?query=1', { name: 'updated' }),
  ).resolves.toEqual(item);

  expect(put).toHaveBeenCalledWith('/api/v1/test/uuid%2Fwith%3Fquery%3D1', {
    name: 'updated',
  });
});

test('BaseResource encodes item IDs before deleting an item', async () => {
  const deleteMock = jest.fn(async () => ({ message: 'OK' }));
  const resource = new TestResource({
    delete: deleteMock,
  } as unknown as HttpClient);

  await expect(resource.delete('uuid/with?query=1')).resolves.toBeUndefined();

  expect(deleteMock).toHaveBeenCalledWith(
    '/api/v1/test/uuid%2Fwith%3Fquery%3D1',
  );
});

test('DashboardsResource encodes item IDs before metadata and copy subpaths', async () => {
  const get = jest.fn(async () => ({ metadata: { chart_configuration: {} } }));
  const post = jest.fn(async () => ({ id: 8, dashboard_title: 'Copy' }));
  const resource = new DashboardsResource({
    get,
    post,
  } as unknown as HttpClient);

  await expect(resource.getMetadata('dash/one?x=1')).resolves.toEqual({
    metadata: { chart_configuration: {} },
  });
  await expect(resource.copy('dash/one?x=1')).resolves.toEqual({
    id: 8,
    dashboard_title: 'Copy',
  });

  expect(get).toHaveBeenCalledWith(
    '/api/v1/dashboard/dash%2Fone%3Fx%3D1/metadata',
  );
  expect(post).toHaveBeenCalledWith(
    '/api/v1/dashboard/dash%2Fone%3Fx%3D1/copy',
  );
});

test('ChartsResource encodes item IDs before chart data subpaths', async () => {
  const result = { data: [] };
  const get = jest.fn(async () => result);
  const resource = new ChartsResource({ get } as unknown as HttpClient);

  await expect(resource.getData('chart/one?x=1')).resolves.toEqual(result);

  expect(get).toHaveBeenCalledWith(
    '/api/v1/chart/chart%2Fone%3Fx%3D1/data',
  );
});

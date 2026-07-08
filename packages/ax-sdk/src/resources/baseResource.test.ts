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
import type { SupersetListEnvelope } from './types.js';

interface TestItem {
  id: number;
}

class TestResource extends BaseResource<TestItem> {
  protected readonly basePath = '/api/v1/test';
  protected readonly searchColumn = 'name';
}

describe('BaseResource', () => {
  test('reports zero total pages for empty list responses', async () => {
    const envelope: SupersetListEnvelope<TestItem> = {
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
});

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
import { paginate, type PaginatedResponse } from './pagination.js';

function makePage<T>(
  items: T[],
  page: number,
  pageSize: number,
  totalCount: number,
): PaginatedResponse<T> {
  const totalPages = Math.ceil(totalCount / pageSize);
  return {
    results: items,
    count: items.length,
    totalCount,
    page,
    pageSize,
    totalPages,
    hasNext: page < totalPages,
    hasPrevious: page > 1,
  };
}

describe('paginate', () => {
  test('yields all pages sequentially', async () => {
    const fetcher = jest.fn(
      async (page: number, _pageSize: number): Promise<PaginatedResponse<number>> => {
        if (page === 1) return makePage([1, 2, 3], 1, 3, 7);
        if (page === 2) return makePage([4, 5, 6], 2, 3, 7);
        return makePage([7], 3, 3, 7);
      },
    );

    const batches: number[][] = [];
    for await (const batch of paginate(fetcher, 3)) {
      batches.push(batch);
    }

    expect(batches).toEqual([[1, 2, 3], [4, 5, 6], [7]]);
    expect(fetcher).toHaveBeenCalledTimes(3);
  });

  test('handles single page', async () => {
    const fetcher = jest.fn(
      async (): Promise<PaginatedResponse<string>> =>
        makePage(['a', 'b'], 1, 10, 2),
    );

    const batches: string[][] = [];
    for await (const batch of paginate(fetcher, 10)) {
      batches.push(batch);
    }

    expect(batches).toEqual([['a', 'b']]);
    expect(fetcher).toHaveBeenCalledTimes(1);
  });

  test('handles empty results', async () => {
    const fetcher = jest.fn(
      async (): Promise<PaginatedResponse<string>> =>
        makePage([], 1, 10, 0),
    );

    const batches: string[][] = [];
    for await (const batch of paginate(fetcher, 10)) {
      batches.push(batch);
    }

    expect(batches).toEqual([]);
    expect(fetcher).toHaveBeenCalledTimes(1);
  });
});

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

/** Pagination metadata returned by list endpoints. */
export interface PaginatedResponse<T> {
  count: number;
  totalCount: number;
  page: number;
  pageSize: number;
  totalPages: number;
  hasNext: boolean;
  hasPrevious: boolean;
  /** The result items for this page. */
  results: T[];
}

/** Common filter operator used by list endpoints. */
export interface ListFilter {
  col: string;
  opr: string;
  value: string | number | boolean | string[] | number[] | boolean[];
}

/** Common parameters shared across all list endpoints. */
export interface ListParams {
  filters?: ListFilter[];
  selectColumns?: string[];
  search?: string;
  orderColumn?: string;
  orderDirection?: 'asc' | 'desc';
  page?: number;
  pageSize?: number;
}

/**
 * Async generator that paginates through all pages of a list endpoint.
 * Yields one batch (page) of results at a time.
 *
 * @param fetcher - Function that fetches a single page.
 * @param pageSize - Number of items per page (default 100).
 *
 * @example
 * ```ts
 * for await (const batch of paginate((page, pageSize) =>
 *   client.dashboards.list({ page, pageSize })
 * )) {
 *   console.log(`Got ${batch.length} dashboards`);
 * }
 * ```
 */
export async function* paginate<T>(
  fetcher: (page: number, pageSize: number) => Promise<PaginatedResponse<T>>,
  pageSize = 100,
): AsyncGenerator<T[]> {
  let page = 1;
  let totalPages = 1;

  while (page <= totalPages) {
    const response = await fetcher(page, pageSize);
    totalPages = response.totalPages;
    if (response.results.length > 0) {
      yield response.results;
    }
    page++;
  }
}

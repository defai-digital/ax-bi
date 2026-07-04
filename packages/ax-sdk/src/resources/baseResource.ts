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

import { HttpClient } from '../transport/httpClient.js';
import type { ListParams, PaginatedResponse } from '../shared/pagination.js';
import { paginate } from '../shared/pagination.js';
import type { SupersetListEnvelope, SupersetItemEnvelope, SupersetDeleteEnvelope } from './types.js';

/**
 * Base class for REST resource modules.
 * Provides standard CRUD operations mapped to Superset API conventions.
 */
export abstract class BaseResource<TItem> {
  protected abstract readonly basePath: string;
  /** The column name used for text search in the backend API (e.g. 'dashboard_title', 'slice_name'). */
  protected abstract readonly searchColumn: string;

  constructor(protected readonly http: HttpClient) {}

  /** List resources with optional filtering and pagination. */
  async list(params?: ListParams): Promise<PaginatedResponse<TItem>> {
    const query = this.buildListQuery(params);
    const envelope = await this.http.get<SupersetListEnvelope<TItem>>(this.basePath, query);
    return this.envelopeToPaginated(envelope, params);
  }

  /** Fetch a single resource by ID or UUID. */
  async getById(id: number | string): Promise<TItem> {
    const envelope = await this.http.get<SupersetItemEnvelope<TItem>>(`${this.basePath}/${id}`);
    return envelope.result;
  }

  /** Create a new resource. Returns the created item. */
  async create(data: unknown): Promise<TItem> {
    const envelope = await this.http.post<SupersetItemEnvelope<TItem>>(`${this.basePath}/`, data);
    return envelope.result;
  }

  /** Update an existing resource by ID or UUID. */
  async update(id: number | string, data: unknown): Promise<TItem> {
    const envelope = await this.http.put<SupersetItemEnvelope<TItem>>(
      `${this.basePath}/${id}`,
      data,
    );
    return envelope.result;
  }

  /** Delete a resource by ID or UUID. */
  async delete(id: number | string): Promise<void> {
    await this.http.delete<SupersetDeleteEnvelope>(`${this.basePath}/${id}`);
  }

  /**
   * Async iterator that paginates through all items.
   *
   * @example
   * ```ts
   * for await (const batch of resource.listAll({ search: 'sales' })) {
   *   for (const item of batch) { ... }
   * }
   * ```
   */
  listAll(params?: ListParams, pageSize = 100): AsyncGenerator<TItem[]> {
    return paginate<TItem>(
      (page, ps) => this.list({ ...params, page, pageSize: ps }),
      pageSize,
    );
  }

  private buildListQuery(
    params?: ListParams,
  ): Record<string, string | number | boolean | undefined> {
    if (!params) return {};

    const query: Record<string, string | number | boolean | undefined> = {
      page: params.page,
      page_size: params.pageSize,
    };

    if (params.search) {
      // Superset uses (filters:!((col:...,opr:ct,value:...)))
      // but also supports `q=(filters:...)&search=...`
      query['q'] = JSON.stringify({
        filters: [
          ...(params.filters ?? []),
          { col: this.searchColumn, opr: 'ct', value: params.search },
        ],
        order_column: params.orderColumn,
        order_direction: params.orderDirection,
        select_columns: params.selectColumns,
      });
    } else if (params.filters || params.orderColumn || params.selectColumns) {
      query['q'] = JSON.stringify({
        filters: params.filters,
        order_column: params.orderColumn,
        order_direction: params.orderDirection,
        select_columns: params.selectColumns,
      });
    }

    return query;
  }

  private envelopeToPaginated(
    envelope: SupersetListEnvelope<TItem>,
    params?: ListParams,
  ): PaginatedResponse<TItem> {
    const page = params?.page ?? 1;
    const pageSize = params?.pageSize ?? 20;
    const totalCount = envelope.count ?? envelope.result.length;
    const totalPages = Math.max(1, Math.ceil(totalCount / pageSize));

    return {
      results: envelope.result,
      count: envelope.result.length,
      totalCount,
      page,
      pageSize,
      totalPages,
      hasNext: page < totalPages,
      hasPrevious: page > 1,
    };
  }
}

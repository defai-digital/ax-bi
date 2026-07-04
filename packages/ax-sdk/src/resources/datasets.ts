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

import { BaseResource } from './baseResource.js';
import type { DatasetItem, CreateDatasetInput, UpdateDatasetInput } from './types.js';

/** CRUD operations for datasets (tables). */
export class DatasetsResource extends BaseResource<DatasetItem> {
  protected readonly basePath = '/api/v1/dataset';
  protected readonly searchColumn = 'table_name';

  /** Create a new dataset. */
  override async create(data: CreateDatasetInput): Promise<DatasetItem> {
    return super.create(data);
  }

  /** Update an existing dataset. */
  override async update(id: number | string, data: UpdateDatasetInput): Promise<DatasetItem> {
    return super.update(id, data);
  }

  /** Get the columns for a dataset. */
  async getColumns(id: number | string): Promise<NonNullable<DatasetItem['columns']>> {
    const item = await this.getById(id);
    return item.columns ?? [];
  }

  /** Get the metrics for a dataset. */
  async getMetrics(id: number | string): Promise<NonNullable<DatasetItem['metrics']>> {
    const item = await this.getById(id);
    return item.metrics ?? [];
  }

  /** Refresh dataset metadata from the underlying database table. */
  async refresh(id: number | string): Promise<{ message: string }> {
    return this.http.put<{ message: string }>(`${this.basePath}/${id}/refresh`);
  }

  /** Export one or more datasets as ZIP. */
  async export(ids: number[]): Promise<Blob> {
    const response = await this.http.request<Blob>({
      method: 'GET',
      path: `${this.basePath}/export/`,
      query: { q: JSON.stringify(ids) },
    });
    return response;
  }
}

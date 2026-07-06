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
import type { ChartItem, CreateChartInput, UpdateChartInput } from './types.js';

/** CRUD operations for charts (slices). */
export class ChartsResource extends BaseResource<
  ChartItem,
  CreateChartInput,
  UpdateChartInput
> {
  protected readonly basePath = '/api/v1/chart';
  protected readonly searchColumn = 'slice_name';

  /** Get chart data (query result) for a given chart. */
  async getData(id: number | string): Promise<Record<string, unknown>> {
    return this.http.get<Record<string, unknown>>(`${this.basePath}/${id}/data`);
  }

  /** Export one or more charts as ZIP. */
  async export(ids: number[]): Promise<Blob> {
    return this.exportZip(ids);
  }

  /** Get the chart's raw form data / viz config. */
  async getFormData(id: number | string): Promise<Record<string, unknown>> {
    const item = await this.getById(id);
    return {
      id: item.id,
      slice_name: item.slice_name,
      viz_type: item.viz_type,
      datasource_id: item.datasource_id,
      datasource_type: item.datasource_type,
    };
  }
}

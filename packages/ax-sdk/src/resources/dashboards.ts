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
import type { DashboardItem, CreateDashboardInput, UpdateDashboardInput } from './types.js';

/** CRUD operations for dashboards. */
export class DashboardsResource extends BaseResource<
  DashboardItem,
  CreateDashboardInput,
  UpdateDashboardInput
> {
  protected readonly basePath = '/api/v1/dashboard';
  protected readonly searchColumn = 'dashboard_title';

  /** Get the dashboard's JSON metadata (position, filters, etc.). */
  async getMetadata(id: number | string): Promise<{ metadata: Record<string, unknown> }> {
    return this.http.get<{ metadata: Record<string, unknown> }>(
      `${this.basePath}/${id}/metadata`,
    );
  }

  /** Export one or more dashboards as ZIP. */
  async export(ids: number[]): Promise<Blob> {
    return this.exportZip(ids);
  }

  /** Copy a dashboard by ID. Returns the new dashboard. */
  async copy(id: number | string): Promise<DashboardItem> {
    return this.http.post<DashboardItem>(`${this.basePath}/${id}/copy`);
  }
}

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
import type { DatabaseItem } from './types.js';

/** CRUD operations for database connections. */
export class DatabasesResource extends BaseResource<DatabaseItem> {
  protected readonly basePath = '/api/v1/database';

  /** Test a database connection before saving. */
  async testConnection(params: {
    sqlalchemy_uri: string;
    database_name?: string;
    extra?: string;
  }): Promise<{ message: string }> {
    return this.http.post<{ message: string }>(`${this.basePath}/validate_parameters`, params);
  }

  /** List schemas available in a database. */
  async getSchemas(id: number | string): Promise<{ result: string[] }> {
    return this.http.get<{ result: string[] }>(`${this.basePath}/${id}/schemas/`);
  }

  /** List tables in a database + schema. */
  async getTables(
    id: number | string,
    schema: string,
  ): Promise<{ result: Array<{ value: string; type: string }> }> {
    return this.http.get<{ result: Array<{ value: string; type: string }> }>(
      `${this.basePath}/${id}/tables/`,
      { schema_name: schema },
    );
  }

  /** List columns in a database table. */
  async getColumns(
    id: number | string,
    schema: string,
    tableName: string,
  ): Promise<{ result: Array<{ name: string; type: string; keys: string[] }> }> {
    return this.http.get<{
      result: Array<{ name: string; type: string; keys: string[] }>;
    }>(`${this.basePath}/${id}/table/${tableName}/${schema}`);
  }
}

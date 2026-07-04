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
import type { QueryItem } from './types.js';

/** Read-only operations for query history. */
export class QueriesResource extends BaseResource<QueryItem> {
  protected readonly basePath = '/api/v1/saved_query';

  /** Get the results of a previously executed query. */
  async getResults(key: string): Promise<Record<string, unknown>> {
    return this.http.get<Record<string, unknown>>(`/api/v1/sqllab/results/${key}`);
  }
}

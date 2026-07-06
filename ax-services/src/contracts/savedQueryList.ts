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
import {
  type ListFilter as SharedListFilter,
  type ListFilterValue as SharedListFilterValue,
  type ListRequestBase,
  type ListResponseBase,
  buildListRequestSchema,
  buildListResponseSchema,
} from './listColumn';

export const SAVED_QUERY_LIST_CONTRACT_VERSION = 'saved-query-list.v1';

export type SavedQueryFilterValue = SharedListFilterValue;

export type SavedQueryListFilter = SharedListFilter;

export type SavedQueryListRequest = ListRequestBase<typeof SAVED_QUERY_LIST_CONTRACT_VERSION>;

export interface SavedQueryListItem {
  id: number;
  uuid?: string;
  label?: string;
  sql?: string;
  dbId?: number;
  schema?: string;
  catalog?: string;
  description?: string;
  changedOn?: string;
  createdOn?: string;
  lastRun?: string;
}

export interface SavedQueryListResponse
  extends ListResponseBase<typeof SAVED_QUERY_LIST_CONTRACT_VERSION> {
  savedQueries: SavedQueryListItem[];
}

const savedQueryListItemSchema = {
  type: 'object',
  required: ['id'],
  additionalProperties: false,
  properties: {
    id: { type: 'integer', minimum: 0 },
    uuid: { type: 'string' },
    label: { type: 'string' },
    sql: { type: 'string' },
    dbId: { type: 'integer', minimum: 0 },
    schema: { type: 'string' },
    catalog: { type: 'string' },
    description: { type: 'string' },
    changedOn: { type: 'string' },
    createdOn: { type: 'string' },
    lastRun: { type: 'string' },
  },
} as const;

export const savedQueryListRequestSchema = buildListRequestSchema({
  schemaId: 'ax-services.saved-query-list.v1.request',
  contractVersion: SAVED_QUERY_LIST_CONTRACT_VERSION,
});

export const savedQueryListResponseSchema = buildListResponseSchema({
  schemaId: 'ax-services.saved-query-list.v1.response',
  contractVersion: SAVED_QUERY_LIST_CONTRACT_VERSION,
  collectionKey: 'savedQueries',
  itemSchema: savedQueryListItemSchema,
});

export const savedQueryListContractSchemas = {
  savedQueryListRequestSchema,
  savedQueryListResponseSchema,
} as const;

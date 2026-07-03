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
  listColumnSchema,
  listCountSchema,
  listFilterSchema,
  listOrderColumnSchema,
  listPageSchema,
  listPageSizeSchema,
  listSearchSchema,
  listTotalPagesSchema,
  warningSchema,
} from './listColumn';

export const SAVED_QUERY_LIST_CONTRACT_VERSION = 'saved-query-list.v1';

export type SavedQueryFilterValue =
  | string
  | number
  | boolean
  | string[]
  | number[]
  | boolean[];

export interface SavedQueryListFilter {
  col: string;
  opr: string;
  value: SavedQueryFilterValue;
}

export interface SavedQueryListRequest {
  contractVersion: typeof SAVED_QUERY_LIST_CONTRACT_VERSION;
  filters: SavedQueryListFilter[];
  selectColumns: string[];
  search?: string;
  orderColumn?: string;
  orderDirection: 'asc' | 'desc';
  page: number;
  pageSize: number;
}

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

export interface SavedQueryListResponse {
  contractVersion: typeof SAVED_QUERY_LIST_CONTRACT_VERSION;
  savedQueries: SavedQueryListItem[];
  count: number;
  totalCount: number;
  page: number;
  pageSize: number;
  totalPages: number;
  hasNext: boolean;
  hasPrevious: boolean;
  columnsRequested: string[];
  columnsLoaded: string[];
  warnings: string[];
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

export const savedQueryListRequestSchema = {
  $id: 'ax-services.saved-query-list.v1.request',
  type: 'object',
  required: [
    'contractVersion',
    'filters',
    'selectColumns',
    'orderDirection',
    'page',
    'pageSize',
  ],
  additionalProperties: false,
  properties: {
    contractVersion: { const: SAVED_QUERY_LIST_CONTRACT_VERSION },
    filters: {
      type: 'array',
      items: listFilterSchema,
    },
    selectColumns: listColumnSchema,
    search: listSearchSchema,
    orderColumn: listOrderColumnSchema,
    orderDirection: { enum: ['asc', 'desc'] },
    page: listPageSchema,
    pageSize: listPageSizeSchema,
  },
} as const;

export const savedQueryListResponseSchema = {
  $id: 'ax-services.saved-query-list.v1.response',
  type: 'object',
  required: [
    'contractVersion',
    'savedQueries',
    'count',
    'totalCount',
    'page',
    'pageSize',
    'totalPages',
    'hasNext',
    'hasPrevious',
    'columnsRequested',
    'columnsLoaded',
    'warnings',
  ],
  additionalProperties: false,
  properties: {
    contractVersion: { const: SAVED_QUERY_LIST_CONTRACT_VERSION },
    savedQueries: {
      type: 'array',
      items: savedQueryListItemSchema,
    },
    count: listCountSchema,
    totalCount: listCountSchema,
    page: listPageSchema,
    pageSize: listPageSizeSchema,
    totalPages: listTotalPagesSchema,
    hasNext: { type: 'boolean' },
    hasPrevious: { type: 'boolean' },
    columnsRequested: listColumnSchema,
    columnsLoaded: listColumnSchema,
    warnings: warningSchema,
  },
} as const;

export const savedQueryListContractSchemas = {
  savedQueryListRequestSchema,
  savedQueryListResponseSchema,
} as const;

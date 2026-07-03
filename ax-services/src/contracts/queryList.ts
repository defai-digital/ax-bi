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
import { listColumnSchema } from './listColumn';

export const QUERY_LIST_CONTRACT_VERSION = 'query-list.v1';

export type QueryFilterValue =
  | string
  | number
  | boolean
  | string[]
  | number[]
  | boolean[];

export interface QueryListFilter {
  col: string;
  opr: string;
  value: QueryFilterValue;
}

export interface QueryListRequest {
  contractVersion: typeof QUERY_LIST_CONTRACT_VERSION;
  filters: QueryListFilter[];
  selectColumns: string[];
  search?: string;
  orderColumn?: string;
  orderDirection: 'asc' | 'desc';
  page: number;
  pageSize: number;
}

export interface QueryListItem {
  id: number;
  sql?: string;
  executedSql?: string;
  status?: string;
  startTime?: number;
  endTime?: number;
  rows?: number;
  databaseId?: number;
  schema?: string;
  catalog?: string;
  tabName?: string;
  errorMessage?: string;
  clientId?: string;
  limit?: number;
  progress?: number;
  changedOn?: string;
  userId?: number;
}

export interface QueryListResponse {
  contractVersion: typeof QUERY_LIST_CONTRACT_VERSION;
  queries: QueryListItem[];
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

const queryFilterSchema = {
  type: 'object',
  required: ['col', 'opr', 'value'],
  additionalProperties: false,
  properties: {
    col: { type: 'string', pattern: '^[A-Za-z0-9_]+$' },
    opr: { type: 'string', pattern: '^[A-Za-z0-9_]+$' },
    value: {
      anyOf: [
        { type: 'string' },
        { type: 'number' },
        { type: 'boolean' },
        { type: 'array', items: { type: 'string' } },
        { type: 'array', items: { type: 'number' } },
        { type: 'array', items: { type: 'boolean' } },
      ],
    },
  },
} as const;

const queryListItemSchema = {
  type: 'object',
  required: ['id'],
  additionalProperties: false,
  properties: {
    id: { type: 'integer', minimum: 0 },
    sql: { type: 'string' },
    executedSql: { type: 'string' },
    status: { type: 'string' },
    startTime: { type: 'number', minimum: 0 },
    endTime: { type: 'number', minimum: 0 },
    rows: { type: 'integer', minimum: 0 },
    databaseId: { type: 'integer', minimum: 0 },
    schema: { type: 'string' },
    catalog: { type: 'string' },
    tabName: { type: 'string' },
    errorMessage: { type: 'string' },
    clientId: { type: 'string' },
    limit: { type: 'integer', minimum: 0 },
    progress: { type: 'number', minimum: 0 },
    changedOn: { type: 'string' },
    userId: { type: 'integer', minimum: 0 },
  },
} as const;

export const queryListRequestSchema = {
  $id: 'ax-services.query-list.v1.request',
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
    contractVersion: { const: QUERY_LIST_CONTRACT_VERSION },
    filters: {
      type: 'array',
      items: queryFilterSchema,
    },
    selectColumns: listColumnSchema,
    search: { type: 'string' },
    orderColumn: { type: 'string' },
    orderDirection: { enum: ['asc', 'desc'] },
    page: { type: 'integer', minimum: 1 },
    pageSize: { type: 'integer', minimum: 1, maximum: 100 },
  },
} as const;

export const queryListResponseSchema = {
  $id: 'ax-services.query-list.v1.response',
  type: 'object',
  required: [
    'contractVersion',
    'queries',
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
    contractVersion: { const: QUERY_LIST_CONTRACT_VERSION },
    queries: {
      type: 'array',
      items: queryListItemSchema,
    },
    count: { type: 'integer', minimum: 0 },
    totalCount: { type: 'integer', minimum: 0 },
    page: { type: 'integer', minimum: 1 },
    pageSize: { type: 'integer', minimum: 1, maximum: 100 },
    totalPages: { type: 'integer', minimum: 0 },
    hasNext: { type: 'boolean' },
    hasPrevious: { type: 'boolean' },
    columnsRequested: {
      type: 'array',
      items: { type: 'string' },
    },
    columnsLoaded: {
      type: 'array',
      items: { type: 'string' },
    },
    warnings: {
      type: 'array',
      items: { type: 'string' },
    },
  },
} as const;

export const queryListContractSchemas = {
  queryListRequestSchema,
  queryListResponseSchema,
} as const;

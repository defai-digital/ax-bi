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

export const RLS_LIST_CONTRACT_VERSION = 'rls-list.v1';

export type RlsFilterValue = SharedListFilterValue;

export type RlsListFilter = SharedListFilter;

export interface RlsListRequest {
  contractVersion: typeof RLS_LIST_CONTRACT_VERSION;
  filters: RlsListFilter[];
  selectColumns: string[];
  search?: string;
  orderColumn?: string;
  orderDirection: 'asc' | 'desc';
  page: number;
  pageSize: number;
}

export interface RlsTableRef {
  id?: number;
  tableName?: string;
}

export interface RlsRoleRef {
  id?: number;
  name?: string;
}

export interface RlsListItem {
  id: number;
  name?: string;
  filterType?: string;
  tables?: RlsTableRef[];
  roles?: RlsRoleRef[];
  clause?: string;
  groupKey?: string;
  changedOn?: string;
}

export interface RlsListResponse {
  contractVersion: typeof RLS_LIST_CONTRACT_VERSION;
  rlsFilters: RlsListItem[];
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

const rlsTableRefSchema = {
  type: 'object',
  additionalProperties: false,
  properties: {
    id: { type: 'integer', minimum: 0 },
    tableName: { type: 'string' },
  },
} as const;

const rlsRoleRefSchema = {
  type: 'object',
  additionalProperties: false,
  properties: {
    id: { type: 'integer', minimum: 0 },
    name: { type: 'string' },
  },
} as const;

const rlsListItemSchema = {
  type: 'object',
  required: ['id'],
  additionalProperties: false,
  properties: {
    id: { type: 'integer', minimum: 0 },
    name: { type: 'string' },
    filterType: { type: 'string' },
    tables: { type: 'array', items: rlsTableRefSchema },
    roles: { type: 'array', items: rlsRoleRefSchema },
    clause: { type: 'string' },
    groupKey: { type: 'string' },
    changedOn: { type: 'string' },
  },
} as const;

export const rlsListRequestSchema = {
  $id: 'ax-services.rls-list.v1.request',
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
    contractVersion: { const: RLS_LIST_CONTRACT_VERSION },
    filters: { type: 'array', items: listFilterSchema },
    selectColumns: listColumnSchema,
    search: listSearchSchema,
    orderColumn: listOrderColumnSchema,
    orderDirection: { enum: ['asc', 'desc'] },
    page: listPageSchema,
    pageSize: listPageSizeSchema,
  },
} as const;

export const rlsListResponseSchema = {
  $id: 'ax-services.rls-list.v1.response',
  type: 'object',
  required: [
    'contractVersion',
    'rlsFilters',
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
    contractVersion: { const: RLS_LIST_CONTRACT_VERSION },
    rlsFilters: { type: 'array', items: rlsListItemSchema },
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

export const rlsListContractSchemas = {
  rlsListRequestSchema,
  rlsListResponseSchema,
} as const;

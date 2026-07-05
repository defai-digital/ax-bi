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
  buildListRequestSchema,
  listColumnSchema,
  listCountSchema,
  listPageSchema,
  listPageSizeSchema,
  listTotalPagesSchema,
  warningSchema,
} from './listColumn';

export const ROLE_LIST_CONTRACT_VERSION = 'role-list.v1';

export type RoleFilterValue = SharedListFilterValue;

export type RoleListFilter = SharedListFilter;

export interface RoleListRequest {
  contractVersion: typeof ROLE_LIST_CONTRACT_VERSION;
  filters: RoleListFilter[];
  selectColumns: string[];
  search?: string;
  orderColumn?: string;
  orderDirection: 'asc' | 'desc';
  page: number;
  pageSize: number;
}

export interface RoleListItem {
  id: number;
  name?: string;
}

export interface RoleListResponse {
  contractVersion: typeof ROLE_LIST_CONTRACT_VERSION;
  roles: RoleListItem[];
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

const roleListItemSchema = {
  type: 'object',
  required: ['id'],
  additionalProperties: false,
  properties: {
    id: { type: 'integer', minimum: 0 },
    name: { type: 'string' },
  },
} as const;

export const roleListRequestSchema = buildListRequestSchema({
  schemaId: 'ax-services.role-list.v1.request',
  contractVersion: ROLE_LIST_CONTRACT_VERSION,
});

export const roleListResponseSchema = {
  $id: 'ax-services.role-list.v1.response',
  type: 'object',
  required: [
    'contractVersion',
    'roles',
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
    contractVersion: { const: ROLE_LIST_CONTRACT_VERSION },
    roles: {
      type: 'array',
      items: roleListItemSchema,
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

export const roleListContractSchemas = {
  roleListRequestSchema,
  roleListResponseSchema,
} as const;

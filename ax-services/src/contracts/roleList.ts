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
export const ROLE_LIST_CONTRACT_VERSION = 'role-list.v1';

export type RoleFilterValue =
  | string
  | number
  | boolean
  | string[]
  | number[]
  | boolean[];

export interface RoleListFilter {
  col: string;
  opr: string;
  value: RoleFilterValue;
}

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

const roleFilterSchema = {
  type: 'object',
  required: ['col', 'opr', 'value'],
  additionalProperties: false,
  properties: {
    col: { type: 'string' },
    opr: { type: 'string' },
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

const roleListItemSchema = {
  type: 'object',
  required: ['id'],
  additionalProperties: false,
  properties: {
    id: { type: 'number' },
    name: { type: 'string' },
  },
} as const;

export const roleListRequestSchema = {
  $id: 'ax-services.role-list.v1.request',
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
    contractVersion: { const: ROLE_LIST_CONTRACT_VERSION },
    filters: {
      type: 'array',
      items: roleFilterSchema,
    },
    selectColumns: {
      type: 'array',
      items: { type: 'string' },
    },
    search: { type: 'string' },
    orderColumn: { type: 'string' },
    orderDirection: { enum: ['asc', 'desc'] },
    page: { type: 'number', minimum: 1 },
    pageSize: { type: 'number', minimum: 1, maximum: 100 },
  },
} as const;

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
    count: { type: 'number' },
    totalCount: { type: 'number' },
    page: { type: 'number' },
    pageSize: { type: 'number' },
    totalPages: { type: 'number' },
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

export const roleListContractSchemas = {
  roleListRequestSchema,
  roleListResponseSchema,
} as const;

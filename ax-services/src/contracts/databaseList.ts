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
import { listColumnSchema, listOrderColumnSchema } from './listColumn';

export const DATABASE_LIST_CONTRACT_VERSION = 'database-list.v1';

export type DatabaseFilterValue =
  | string
  | number
  | boolean
  | string[]
  | number[]
  | boolean[];

export interface DatabaseListFilter {
  col: string;
  opr: string;
  value: DatabaseFilterValue;
}

export interface DatabaseListRequest {
  contractVersion: typeof DATABASE_LIST_CONTRACT_VERSION;
  filters: DatabaseListFilter[];
  selectColumns: string[];
  search?: string;
  orderColumn?: string;
  orderDirection: 'asc' | 'desc';
  page: number;
  pageSize: number;
  createdByMe: boolean;
}

export interface DatabaseListItem {
  id: number;
  uuid?: string;
  databaseName?: string;
  backend?: string;
  exposeInSqllab?: boolean;
  allowCtas?: boolean;
  allowCvas?: boolean;
  allowDml?: boolean;
  allowFileUpload?: boolean;
  allowRunAsync?: boolean;
  cacheTimeout?: number;
  configurationMethod?: string;
  forceCtasSchema?: string;
  impersonateUser?: boolean;
  isManagedExternally?: boolean;
  externalUrl?: string;
  extra?: Record<string, unknown>;
  changedOn?: string;
  changedOnHumanized?: string;
  createdOn?: string;
  createdOnHumanized?: string;
}

export interface DatabaseListResponse {
  contractVersion: typeof DATABASE_LIST_CONTRACT_VERSION;
  databases: DatabaseListItem[];
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

const databaseFilterSchema = {
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

const databaseListItemSchema = {
  type: 'object',
  required: ['id'],
  additionalProperties: false,
  properties: {
    id: { type: 'integer', minimum: 0 },
    uuid: { type: 'string' },
    databaseName: { type: 'string' },
    backend: { type: 'string' },
    exposeInSqllab: { type: 'boolean' },
    allowCtas: { type: 'boolean' },
    allowCvas: { type: 'boolean' },
    allowDml: { type: 'boolean' },
    allowFileUpload: { type: 'boolean' },
    allowRunAsync: { type: 'boolean' },
    cacheTimeout: { type: 'integer', minimum: -1 },
    configurationMethod: { type: 'string' },
    forceCtasSchema: { type: 'string' },
    impersonateUser: { type: 'boolean' },
    isManagedExternally: { type: 'boolean' },
    externalUrl: { type: 'string' },
    extra: {
      type: 'object',
      additionalProperties: true,
    },
    changedOn: { type: 'string' },
    changedOnHumanized: { type: 'string' },
    createdOn: { type: 'string' },
    createdOnHumanized: { type: 'string' },
  },
} as const;

export const databaseListRequestSchema = {
  $id: 'ax-services.database-list.v1.request',
  type: 'object',
  required: [
    'contractVersion',
    'filters',
    'selectColumns',
    'orderDirection',
    'page',
    'pageSize',
    'createdByMe',
  ],
  additionalProperties: false,
  properties: {
    contractVersion: { const: DATABASE_LIST_CONTRACT_VERSION },
    filters: {
      type: 'array',
      items: databaseFilterSchema,
    },
    selectColumns: listColumnSchema,
    search: { type: 'string' },
    orderColumn: listOrderColumnSchema,
    orderDirection: { enum: ['asc', 'desc'] },
    page: { type: 'integer', minimum: 1 },
    pageSize: { type: 'integer', minimum: 1, maximum: 100 },
    createdByMe: { type: 'boolean' },
  },
} as const;

export const databaseListResponseSchema = {
  $id: 'ax-services.database-list.v1.response',
  type: 'object',
  required: [
    'contractVersion',
    'databases',
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
    contractVersion: { const: DATABASE_LIST_CONTRACT_VERSION },
    databases: {
      type: 'array',
      items: databaseListItemSchema,
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

export const databaseListContractSchemas = {
  databaseListRequestSchema,
  databaseListResponseSchema,
} as const;

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

export const DATABASE_LIST_CONTRACT_VERSION = 'database-list.v1';

export type DatabaseFilterValue = SharedListFilterValue;

export type DatabaseListFilter = SharedListFilter;

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

export const databaseListRequestSchema = buildListRequestSchema({
  schemaId: 'ax-services.database-list.v1.request',
  contractVersion: DATABASE_LIST_CONTRACT_VERSION,
  extraRequired: ['createdByMe'],
  extraProperties: {
    createdByMe: { type: 'boolean' },
  },
});

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

export const databaseListContractSchemas = {
  databaseListRequestSchema,
  databaseListResponseSchema,
} as const;

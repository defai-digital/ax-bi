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
export const DATASET_LIST_CONTRACT_VERSION = 'dataset-list.v1';

export type DatasetFilterValue =
  | string
  | number
  | boolean
  | string[]
  | number[]
  | boolean[];

export interface DatasetListFilter {
  col: string;
  opr: string;
  value: DatasetFilterValue;
}

export interface DatasetListRequest {
  contractVersion: typeof DATASET_LIST_CONTRACT_VERSION;
  filters: DatasetListFilter[];
  selectColumns: string[];
  search?: string;
  orderColumn?: string;
  orderDirection: 'asc' | 'desc';
  page: number;
  pageSize: number;
  createdByMe: boolean;
  ownedByMe: boolean;
}

export interface DatasetListItem {
  id: number;
  tableName?: string;
  schema?: string;
  databaseName?: string;
  description?: string;
  certifiedBy?: string;
  certificationDetails?: string;
  changedOn?: string;
  changedOnHumanized?: string;
  isVirtual?: boolean;
  databaseId?: number;
  uuid?: string;
  url?: string;
}

export interface DatasetListResponse {
  contractVersion: typeof DATASET_LIST_CONTRACT_VERSION;
  datasets: DatasetListItem[];
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

const datasetFilterSchema = {
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

const datasetListItemSchema = {
  type: 'object',
  required: ['id'],
  additionalProperties: false,
  properties: {
    id: { type: 'integer', minimum: 0 },
    tableName: { type: 'string' },
    schema: { type: 'string' },
    databaseName: { type: 'string' },
    description: { type: 'string' },
    certifiedBy: { type: 'string' },
    certificationDetails: { type: 'string' },
    changedOn: { type: 'string' },
    changedOnHumanized: { type: 'string' },
    isVirtual: { type: 'boolean' },
    databaseId: { type: 'integer', minimum: 0 },
    uuid: { type: 'string' },
    url: { type: 'string' },
  },
} as const;

export const datasetListRequestSchema = {
  $id: 'ax-services.dataset-list.v1.request',
  type: 'object',
  required: [
    'contractVersion',
    'filters',
    'selectColumns',
    'orderDirection',
    'page',
    'pageSize',
    'createdByMe',
    'ownedByMe',
  ],
  additionalProperties: false,
  properties: {
    contractVersion: { const: DATASET_LIST_CONTRACT_VERSION },
    filters: {
      type: 'array',
      items: datasetFilterSchema,
    },
    selectColumns: {
      type: 'array',
      items: { type: 'string' },
    },
    search: { type: 'string' },
    orderColumn: { type: 'string' },
    orderDirection: { enum: ['asc', 'desc'] },
    page: { type: 'integer', minimum: 1 },
    pageSize: { type: 'integer', minimum: 1, maximum: 100 },
    createdByMe: { type: 'boolean' },
    ownedByMe: { type: 'boolean' },
  },
} as const;

export const datasetListResponseSchema = {
  $id: 'ax-services.dataset-list.v1.response',
  type: 'object',
  required: [
    'contractVersion',
    'datasets',
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
    contractVersion: { const: DATASET_LIST_CONTRACT_VERSION },
    datasets: {
      type: 'array',
      items: datasetListItemSchema,
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

export const datasetListContractSchemas = {
  datasetListRequestSchema,
  datasetListResponseSchema,
} as const;

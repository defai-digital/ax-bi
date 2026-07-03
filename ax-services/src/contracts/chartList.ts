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
  listFilterStringArraySchema,
  listFilterStringSchema,
  listOrderColumnSchema,
  listSearchSchema,
  warningSchema,
} from './listColumn';

export const CHART_LIST_CONTRACT_VERSION = 'chart-list.v1';

export type ChartFilterValue =
  | string
  | number
  | boolean
  | string[]
  | number[]
  | boolean[];

export interface ChartListFilter {
  col: string;
  opr: string;
  value: ChartFilterValue;
}

export interface ChartListRequest {
  contractVersion: typeof CHART_LIST_CONTRACT_VERSION;
  filters: ChartListFilter[];
  selectColumns: string[];
  search?: string;
  orderColumn?: string;
  orderDirection: 'asc' | 'desc';
  page: number;
  pageSize: number;
  createdByMe: boolean;
  ownedByMe: boolean;
}

export interface ChartListItem {
  id: number;
  sliceName?: string;
  vizType?: string;
  description?: string;
  certifiedBy?: string;
  certificationDetails?: string;
  uuid?: string;
  url?: string;
  changedOn?: string;
  changedOnHumanized?: string;
}

export interface ChartListResponse {
  contractVersion: typeof CHART_LIST_CONTRACT_VERSION;
  charts: ChartListItem[];
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

const chartFilterSchema = {
  type: 'object',
  required: ['col', 'opr', 'value'],
  additionalProperties: false,
  properties: {
    col: { type: 'string', pattern: '^[A-Za-z0-9_]+$' },
    opr: { type: 'string', pattern: '^[A-Za-z0-9_]+$' },
    value: {
      anyOf: [
        listFilterStringSchema,
        { type: 'number' },
        { type: 'boolean' },
        listFilterStringArraySchema,
        { type: 'array', items: { type: 'number' } },
        { type: 'array', items: { type: 'boolean' } },
      ],
    },
  },
} as const;

const chartListItemSchema = {
  type: 'object',
  required: ['id'],
  additionalProperties: false,
  properties: {
    id: { type: 'integer', minimum: 0 },
    sliceName: { type: 'string' },
    vizType: { type: 'string' },
    description: { type: 'string' },
    certifiedBy: { type: 'string' },
    certificationDetails: { type: 'string' },
    uuid: { type: 'string' },
    url: { type: 'string' },
    changedOn: { type: 'string' },
    changedOnHumanized: { type: 'string' },
  },
} as const;

export const chartListRequestSchema = {
  $id: 'ax-services.chart-list.v1.request',
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
    contractVersion: { const: CHART_LIST_CONTRACT_VERSION },
    filters: {
      type: 'array',
      items: chartFilterSchema,
    },
    selectColumns: listColumnSchema,
    search: listSearchSchema,
    orderColumn: listOrderColumnSchema,
    orderDirection: { enum: ['asc', 'desc'] },
    page: { type: 'integer', minimum: 1 },
    pageSize: { type: 'integer', minimum: 1, maximum: 100 },
    createdByMe: { type: 'boolean' },
    ownedByMe: { type: 'boolean' },
  },
} as const;

export const chartListResponseSchema = {
  $id: 'ax-services.chart-list.v1.response',
  type: 'object',
  required: [
    'contractVersion',
    'charts',
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
    contractVersion: { const: CHART_LIST_CONTRACT_VERSION },
    charts: {
      type: 'array',
      items: chartListItemSchema,
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
    warnings: warningSchema,
  },
} as const;

export const chartListContractSchemas = {
  chartListRequestSchema,
  chartListResponseSchema,
} as const;

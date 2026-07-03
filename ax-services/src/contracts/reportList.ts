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

export const REPORT_LIST_CONTRACT_VERSION = 'report-list.v1';

export type ReportFilterValue =
  | string
  | number
  | boolean
  | string[]
  | number[]
  | boolean[];

export interface ReportListFilter {
  col: string;
  opr: string;
  value: ReportFilterValue;
}

export interface ReportListRequest {
  contractVersion: typeof REPORT_LIST_CONTRACT_VERSION;
  filters: ReportListFilter[];
  selectColumns: string[];
  search?: string;
  orderColumn?: string;
  orderDirection: 'asc' | 'desc';
  page: number;
  pageSize: number;
}

export interface ReportListItem {
  id: number;
  name?: string;
  description?: string;
  type?: string;
  active?: boolean;
  crontab?: string;
  dashboardId?: number;
  chartId?: number;
  lastEvalDttm?: string;
  lastEvalDttmHumanized?: string;
  lastState?: string;
  creationMethod?: string;
  changedOn?: string;
  changedOnHumanized?: string;
  createdOn?: string;
  createdOnHumanized?: string;
}

export interface ReportListResponse {
  contractVersion: typeof REPORT_LIST_CONTRACT_VERSION;
  reports: ReportListItem[];
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

const reportFilterSchema = {
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

const reportListItemSchema = {
  type: 'object',
  required: ['id'],
  additionalProperties: false,
  properties: {
    id: { type: 'integer', minimum: 0 },
    name: { type: 'string' },
    description: { type: 'string' },
    type: { type: 'string' },
    active: { type: 'boolean' },
    crontab: { type: 'string' },
    dashboardId: { type: 'integer', minimum: 0 },
    chartId: { type: 'integer', minimum: 0 },
    lastEvalDttm: { type: 'string' },
    lastEvalDttmHumanized: { type: 'string' },
    lastState: { type: 'string' },
    creationMethod: { type: 'string' },
    changedOn: { type: 'string' },
    changedOnHumanized: { type: 'string' },
    createdOn: { type: 'string' },
    createdOnHumanized: { type: 'string' },
  },
} as const;

export const reportListRequestSchema = {
  $id: 'ax-services.report-list.v1.request',
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
    contractVersion: { const: REPORT_LIST_CONTRACT_VERSION },
    filters: {
      type: 'array',
      items: reportFilterSchema,
    },
    selectColumns: listColumnSchema,
    search: listSearchSchema,
    orderColumn: listOrderColumnSchema,
    orderDirection: { enum: ['asc', 'desc'] },
    page: { type: 'integer', minimum: 1 },
    pageSize: { type: 'integer', minimum: 1, maximum: 100 },
  },
} as const;

export const reportListResponseSchema = {
  $id: 'ax-services.report-list.v1.response',
  type: 'object',
  required: [
    'contractVersion',
    'reports',
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
    contractVersion: { const: REPORT_LIST_CONTRACT_VERSION },
    reports: {
      type: 'array',
      items: reportListItemSchema,
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

export const reportListContractSchemas = {
  reportListRequestSchema,
  reportListResponseSchema,
} as const;

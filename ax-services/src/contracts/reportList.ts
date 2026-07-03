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

export const REPORT_LIST_CONTRACT_VERSION = 'report-list.v1';

export type ReportFilterValue = SharedListFilterValue;

export type ReportListFilter = SharedListFilter;

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

export const reportListContractSchemas = {
  reportListRequestSchema,
  reportListResponseSchema,
} as const;

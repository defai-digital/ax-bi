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

export const DASHBOARD_LIST_CONTRACT_VERSION = 'dashboard-list.v1';

export type DashboardFilterValue = SharedListFilterValue;

export type DashboardListFilter = SharedListFilter;

export interface DashboardListRequest {
  contractVersion: typeof DASHBOARD_LIST_CONTRACT_VERSION;
  filters: DashboardListFilter[];
  selectColumns: string[];
  search?: string;
  orderColumn?: string;
  orderDirection: 'asc' | 'desc';
  page: number;
  pageSize: number;
  createdByMe: boolean;
  ownedByMe: boolean;
}

export interface DashboardListItem {
  id: number;
  dashboardTitle?: string;
  slug?: string;
  description?: string;
  certifiedBy?: string;
  certificationDetails?: string;
  published?: boolean;
  uuid?: string;
  url?: string;
  changedOn?: string;
  changedOnHumanized?: string;
}

export interface DashboardListResponse {
  contractVersion: typeof DASHBOARD_LIST_CONTRACT_VERSION;
  dashboards: DashboardListItem[];
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

const dashboardListItemSchema = {
  type: 'object',
  required: ['id'],
  additionalProperties: false,
  properties: {
    id: { type: 'integer', minimum: 0 },
    dashboardTitle: { type: 'string' },
    slug: { type: 'string' },
    description: { type: 'string' },
    certifiedBy: { type: 'string' },
    certificationDetails: { type: 'string' },
    published: { type: 'boolean' },
    uuid: { type: 'string' },
    url: { type: 'string' },
    changedOn: { type: 'string' },
    changedOnHumanized: { type: 'string' },
  },
} as const;

export const dashboardListRequestSchema = {
  $id: 'ax-services.dashboard-list.v1.request',
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
    contractVersion: { const: DASHBOARD_LIST_CONTRACT_VERSION },
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
    createdByMe: { type: 'boolean' },
    ownedByMe: { type: 'boolean' },
  },
} as const;

export const dashboardListResponseSchema = {
  $id: 'ax-services.dashboard-list.v1.response',
  type: 'object',
  required: [
    'contractVersion',
    'dashboards',
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
    contractVersion: { const: DASHBOARD_LIST_CONTRACT_VERSION },
    dashboards: {
      type: 'array',
      items: dashboardListItemSchema,
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

export const dashboardListContractSchemas = {
  dashboardListRequestSchema,
  dashboardListResponseSchema,
} as const;

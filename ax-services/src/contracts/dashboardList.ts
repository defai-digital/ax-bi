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
export const DASHBOARD_LIST_CONTRACT_VERSION = 'dashboard-list.v1';

export type DashboardFilterValue =
  | string
  | number
  | boolean
  | string[]
  | number[]
  | boolean[];

export interface DashboardListFilter {
  col: string;
  opr: string;
  value: DashboardFilterValue;
}

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

const dashboardFilterSchema = {
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

const dashboardListItemSchema = {
  type: 'object',
  required: ['id'],
  additionalProperties: false,
  properties: {
    id: { type: 'number' },
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
      items: dashboardFilterSchema,
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

export const dashboardListContractSchemas = {
  dashboardListRequestSchema,
  dashboardListResponseSchema,
} as const;

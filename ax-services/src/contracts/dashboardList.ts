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
  buildListResponseSchema,
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

export const dashboardListRequestSchema = buildListRequestSchema({
  schemaId: 'ax-services.dashboard-list.v1.request',
  contractVersion: DASHBOARD_LIST_CONTRACT_VERSION,
  extraRequired: ['createdByMe', 'ownedByMe'],
  extraProperties: {
    createdByMe: { type: 'boolean' },
    ownedByMe: { type: 'boolean' },
  },
});

export const dashboardListResponseSchema = buildListResponseSchema({
  schemaId: 'ax-services.dashboard-list.v1.response',
  contractVersion: DASHBOARD_LIST_CONTRACT_VERSION,
  collectionKey: 'dashboards',
  itemSchema: dashboardListItemSchema,
});

export const dashboardListContractSchemas = {
  dashboardListRequestSchema,
  dashboardListResponseSchema,
} as const;

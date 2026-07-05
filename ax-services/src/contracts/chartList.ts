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

export const CHART_LIST_CONTRACT_VERSION = 'chart-list.v1';

export type ChartFilterValue = SharedListFilterValue;

export type ChartListFilter = SharedListFilter;

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

export const chartListRequestSchema = buildListRequestSchema({
  schemaId: 'ax-services.chart-list.v1.request',
  contractVersion: CHART_LIST_CONTRACT_VERSION,
  extraRequired: ['createdByMe', 'ownedByMe'],
  extraProperties: {
    createdByMe: { type: 'boolean' },
    ownedByMe: { type: 'boolean' },
  },
});

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

export const chartListContractSchemas = {
  chartListRequestSchema,
  chartListResponseSchema,
} as const;

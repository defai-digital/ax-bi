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

export const DATASET_LIST_CONTRACT_VERSION = 'dataset-list.v1';

export type DatasetFilterValue = SharedListFilterValue;

export type DatasetListFilter = SharedListFilter;

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

export const datasetListRequestSchema = buildListRequestSchema({
  schemaId: 'ax-services.dataset-list.v1.request',
  contractVersion: DATASET_LIST_CONTRACT_VERSION,
  extraRequired: ['createdByMe', 'ownedByMe'],
  extraProperties: {
    createdByMe: { type: 'boolean' },
    ownedByMe: { type: 'boolean' },
  },
});

export const datasetListResponseSchema = buildListResponseSchema({
  schemaId: 'ax-services.dataset-list.v1.response',
  contractVersion: DATASET_LIST_CONTRACT_VERSION,
  collectionKey: 'datasets',
  itemSchema: datasetListItemSchema,
});

export const datasetListContractSchemas = {
  datasetListRequestSchema,
  datasetListResponseSchema,
} as const;

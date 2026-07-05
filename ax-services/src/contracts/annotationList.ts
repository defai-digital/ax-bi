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

export const ANNOTATION_LIST_CONTRACT_VERSION = 'annotation-list.v1';

export type AnnotationFilterValue = SharedListFilterValue;

export type AnnotationListFilter = SharedListFilter;

export interface AnnotationListRequest {
  contractVersion: typeof ANNOTATION_LIST_CONTRACT_VERSION;
  layerId: number;
  filters: AnnotationListFilter[];
  selectColumns: string[];
  search?: string;
  orderColumn?: string;
  orderDirection: 'asc' | 'desc';
  page: number;
  pageSize: number;
}

export interface AnnotationListItem {
  id: number;
  shortDescr?: string;
  longDescr?: string;
  startDttm?: string;
  endDttm?: string;
  jsonMetadata?: string;
  layerId?: number;
}

export interface AnnotationListResponse {
  contractVersion: typeof ANNOTATION_LIST_CONTRACT_VERSION;
  annotations: AnnotationListItem[];
  count: number;
  totalCount: number;
  page: number;
  pageSize: number;
  totalPages: number;
  hasNext: boolean;
  hasPrevious: boolean;
  layerId: number;
  columnsRequested: string[];
  columnsLoaded: string[];
  warnings: string[];
}

const annotationListItemSchema = {
  type: 'object',
  required: ['id'],
  additionalProperties: false,
  properties: {
    id: { type: 'integer', minimum: 0 },
    shortDescr: { type: 'string' },
    longDescr: { type: 'string' },
    startDttm: { type: 'string' },
    endDttm: { type: 'string' },
    jsonMetadata: { type: 'string' },
    layerId: { type: 'integer', minimum: 0 },
  },
} as const;

export const annotationListRequestSchema = buildListRequestSchema({
  schemaId: 'ax-services.annotation-list.v1.request',
  contractVersion: ANNOTATION_LIST_CONTRACT_VERSION,
  leadingRequired: ['layerId'],
  leadingProperties: {
    layerId: { type: 'integer', minimum: 1 },
  },
});

export const annotationListResponseSchema = {
  $id: 'ax-services.annotation-list.v1.response',
  type: 'object',
  required: [
    'contractVersion',
    'annotations',
    'count',
    'totalCount',
    'page',
    'pageSize',
    'totalPages',
    'hasNext',
    'hasPrevious',
    'layerId',
    'columnsRequested',
    'columnsLoaded',
    'warnings',
  ],
  additionalProperties: false,
  properties: {
    contractVersion: { const: ANNOTATION_LIST_CONTRACT_VERSION },
    annotations: {
      type: 'array',
      items: annotationListItemSchema,
    },
    count: listCountSchema,
    totalCount: listCountSchema,
    page: listPageSchema,
    pageSize: listPageSizeSchema,
    totalPages: listTotalPagesSchema,
    hasNext: { type: 'boolean' },
    hasPrevious: { type: 'boolean' },
    layerId: { type: 'integer', minimum: 0 },
    columnsRequested: listColumnSchema,
    columnsLoaded: listColumnSchema,
    warnings: warningSchema,
  },
} as const;

export const annotationListContractSchemas = {
  annotationListRequestSchema,
  annotationListResponseSchema,
} as const;

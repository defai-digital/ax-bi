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

export const ANNOTATION_LAYER_LIST_CONTRACT_VERSION =
  'annotation-layer-list.v1';

export type AnnotationLayerFilterValue = SharedListFilterValue;

export type AnnotationLayerListFilter = SharedListFilter;

export interface AnnotationLayerListRequest {
  contractVersion: typeof ANNOTATION_LAYER_LIST_CONTRACT_VERSION;
  filters: AnnotationLayerListFilter[];
  selectColumns: string[];
  search?: string;
  orderColumn?: string;
  orderDirection: 'asc' | 'desc';
  page: number;
  pageSize: number;
}

export interface AnnotationLayerListItem {
  id: number;
  name?: string;
  descr?: string;
  changedOn?: string;
  createdOn?: string;
}

export interface AnnotationLayerListResponse {
  contractVersion: typeof ANNOTATION_LAYER_LIST_CONTRACT_VERSION;
  annotationLayers: AnnotationLayerListItem[];
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

const annotationLayerListItemSchema = {
  type: 'object',
  required: ['id'],
  additionalProperties: false,
  properties: {
    id: { type: 'integer', minimum: 0 },
    name: { type: 'string' },
    descr: { type: 'string' },
    changedOn: { type: 'string' },
    createdOn: { type: 'string' },
  },
} as const;

export const annotationLayerListRequestSchema = buildListRequestSchema({
  schemaId: 'ax-services.annotation-layer-list.v1.request',
  contractVersion: ANNOTATION_LAYER_LIST_CONTRACT_VERSION,
});

export const annotationLayerListResponseSchema = buildListResponseSchema({
  schemaId: 'ax-services.annotation-layer-list.v1.response',
  contractVersion: ANNOTATION_LAYER_LIST_CONTRACT_VERSION,
  collectionKey: 'annotationLayers',
  itemSchema: annotationLayerListItemSchema,
});

export const annotationLayerListContractSchemas = {
  annotationLayerListRequestSchema,
  annotationLayerListResponseSchema,
} as const;

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

export const TAG_LIST_CONTRACT_VERSION = 'tag-list.v1';

export type TagFilterValue = SharedListFilterValue;

export type TagListFilter = SharedListFilter;

export interface TagListRequest {
  contractVersion: typeof TAG_LIST_CONTRACT_VERSION;
  filters: TagListFilter[];
  selectColumns: string[];
  search?: string;
  orderColumn?: string;
  orderDirection: 'asc' | 'desc';
  page: number;
  pageSize: number;
}

export interface TagListItem {
  id: number;
  name?: string;
  type?: string;
  description?: string;
  changedOn?: string;
  changedOnHumanized?: string;
  createdOn?: string;
  createdOnHumanized?: string;
}

export interface TagListResponse {
  contractVersion: typeof TAG_LIST_CONTRACT_VERSION;
  tags: TagListItem[];
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

const tagListItemSchema = {
  type: 'object',
  required: ['id'],
  additionalProperties: false,
  properties: {
    id: { type: 'integer', minimum: 0 },
    name: { type: 'string' },
    type: { type: 'string' },
    description: { type: 'string' },
    changedOn: { type: 'string' },
    changedOnHumanized: { type: 'string' },
    createdOn: { type: 'string' },
    createdOnHumanized: { type: 'string' },
  },
} as const;

export const tagListRequestSchema = buildListRequestSchema({
  schemaId: 'ax-services.tag-list.v1.request',
  contractVersion: TAG_LIST_CONTRACT_VERSION,
});

export const tagListResponseSchema = buildListResponseSchema({
  schemaId: 'ax-services.tag-list.v1.response',
  contractVersion: TAG_LIST_CONTRACT_VERSION,
  collectionKey: 'tags',
  itemSchema: tagListItemSchema,
});

export const tagListContractSchemas = {
  tagListRequestSchema,
  tagListResponseSchema,
} as const;

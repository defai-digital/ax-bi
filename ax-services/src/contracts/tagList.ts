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
export const TAG_LIST_CONTRACT_VERSION = 'tag-list.v1';

export type TagFilterValue =
  | string
  | number
  | boolean
  | string[]
  | number[]
  | boolean[];

export interface TagListFilter {
  col: string;
  opr: string;
  value: TagFilterValue;
}

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

const tagFilterSchema = {
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

export const tagListRequestSchema = {
  $id: 'ax-services.tag-list.v1.request',
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
    contractVersion: { const: TAG_LIST_CONTRACT_VERSION },
    filters: {
      type: 'array',
      items: tagFilterSchema,
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
  },
} as const;

export const tagListResponseSchema = {
  $id: 'ax-services.tag-list.v1.response',
  type: 'object',
  required: [
    'contractVersion',
    'tags',
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
    contractVersion: { const: TAG_LIST_CONTRACT_VERSION },
    tags: {
      type: 'array',
      items: tagListItemSchema,
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

export const tagListContractSchemas = {
  tagListRequestSchema,
  tagListResponseSchema,
} as const;

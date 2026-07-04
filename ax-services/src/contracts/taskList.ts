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

export const TASK_LIST_CONTRACT_VERSION = 'task-list.v1';

export type TaskFilterValue = SharedListFilterValue;

export type TaskListFilter = SharedListFilter;

export interface TaskListRequest {
  contractVersion: typeof TASK_LIST_CONTRACT_VERSION;
  filters: TaskListFilter[];
  selectColumns: string[];
  search?: string;
  orderColumn?: string;
  orderDirection: 'asc' | 'desc';
  page: number;
  pageSize: number;
}

export interface TaskListItem {
  id: number;
  uuid?: string;
  taskType?: string;
  taskKey?: string;
  taskName?: string;
  status?: string;
  scope?: string;
  changedOn?: string;
  createdOn?: string;
}

export interface TaskListResponse {
  contractVersion: typeof TASK_LIST_CONTRACT_VERSION;
  tasks: TaskListItem[];
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

const taskListItemSchema = {
  type: 'object',
  required: ['id'],
  additionalProperties: false,
  properties: {
    id: { type: 'integer', minimum: 0 },
    uuid: { type: 'string' },
    taskType: { type: 'string' },
    taskKey: { type: 'string' },
    taskName: { type: 'string' },
    status: { type: 'string' },
    scope: { type: 'string' },
    changedOn: { type: 'string' },
    createdOn: { type: 'string' },
  },
} as const;

export const taskListRequestSchema = {
  $id: 'ax-services.task-list.v1.request',
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
    contractVersion: { const: TASK_LIST_CONTRACT_VERSION },
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

export const taskListResponseSchema = {
  $id: 'ax-services.task-list.v1.response',
  type: 'object',
  required: [
    'contractVersion',
    'tasks',
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
    contractVersion: { const: TASK_LIST_CONTRACT_VERSION },
    tasks: {
      type: 'array',
      items: taskListItemSchema,
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

export const taskListContractSchemas = {
  taskListRequestSchema,
  taskListResponseSchema,
} as const;

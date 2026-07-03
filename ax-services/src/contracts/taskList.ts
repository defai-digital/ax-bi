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
import { listColumnSchema, listOrderColumnSchema } from './listColumn';

export const TASK_LIST_CONTRACT_VERSION = 'task-list.v1';

export type TaskFilterValue =
  | string
  | number
  | boolean
  | string[]
  | number[]
  | boolean[];

export interface TaskListFilter {
  col: string;
  opr: string;
  value: TaskFilterValue;
}

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

const taskFilterSchema = {
  type: 'object',
  required: ['col', 'opr', 'value'],
  additionalProperties: false,
  properties: {
    col: { type: 'string', pattern: '^[A-Za-z0-9_]+$' },
    opr: { type: 'string', pattern: '^[A-Za-z0-9_]+$' },
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
      items: taskFilterSchema,
    },
    selectColumns: listColumnSchema,
    search: { type: 'string' },
    orderColumn: listOrderColumnSchema,
    orderDirection: { enum: ['asc', 'desc'] },
    page: { type: 'integer', minimum: 1 },
    pageSize: { type: 'integer', minimum: 1, maximum: 100 },
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
    count: { type: 'integer', minimum: 0 },
    totalCount: { type: 'integer', minimum: 0 },
    page: { type: 'integer', minimum: 1 },
    pageSize: { type: 'integer', minimum: 1, maximum: 100 },
    totalPages: { type: 'integer', minimum: 0 },
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

export const taskListContractSchemas = {
  taskListRequestSchema,
  taskListResponseSchema,
} as const;

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
  type ListRequestBase,
  type ListResponseBase,
  buildListRequestSchema,
  buildListResponseSchema,
} from './listColumn';

export const TASK_LIST_CONTRACT_VERSION = 'task-list.v1';

export type TaskFilterValue = SharedListFilterValue;

export type TaskListFilter = SharedListFilter;

export type TaskListRequest = ListRequestBase<typeof TASK_LIST_CONTRACT_VERSION>;

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

export interface TaskListResponse
  extends ListResponseBase<typeof TASK_LIST_CONTRACT_VERSION> {
  tasks: TaskListItem[];
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

export const taskListRequestSchema = buildListRequestSchema({
  schemaId: 'ax-services.task-list.v1.request',
  contractVersion: TASK_LIST_CONTRACT_VERSION,
});

export const taskListResponseSchema = buildListResponseSchema({
  schemaId: 'ax-services.task-list.v1.response',
  contractVersion: TASK_LIST_CONTRACT_VERSION,
  collectionKey: 'tasks',
  itemSchema: taskListItemSchema,
});

export const taskListContractSchemas = {
  taskListRequestSchema,
  taskListResponseSchema,
} as const;

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
import { expect, test } from '@jest/globals';

import {
  annotationListContractSchemas,
  ANNOTATION_LIST_CONTRACT_VERSION,
} from '../src/contracts/annotationList';
import {
  annotationLayerListContractSchemas,
  ANNOTATION_LAYER_LIST_CONTRACT_VERSION,
} from '../src/contracts/annotationLayerList';
import {
  assetSearchContractSchemas,
  ASSET_SEARCH_CONTRACT_VERSION,
} from '../src/contracts/assetSearch';
import {
  authorizationContractSchemas,
  AUTHORIZATION_CONTRACT_VERSION,
  permissionCheckRequestSchema,
} from '../src/contracts/authorization';
import {
  chartListContractSchemas,
  CHART_LIST_CONTRACT_VERSION,
} from '../src/contracts/chartList';
import {
  dashboardListContractSchemas,
  DASHBOARD_LIST_CONTRACT_VERSION,
} from '../src/contracts/dashboardList';
import {
  databaseListContractSchemas,
  DATABASE_LIST_CONTRACT_VERSION,
} from '../src/contracts/databaseList';
import {
  datasetListContractSchemas,
  DATASET_LIST_CONTRACT_VERSION,
} from '../src/contracts/datasetList';
import {
  healthResponseSchema,
  metadataResponseSchema,
  metricsResponseSchema,
  readinessResponseSchema,
  RUNTIME_CONTRACT_VERSION,
  runtimeContractSchemas,
} from '../src/contracts/runtime';
import {
  queryListContractSchemas,
  QUERY_LIST_CONTRACT_VERSION,
} from '../src/contracts/queryList';
import {
  reportListContractSchemas,
  REPORT_LIST_CONTRACT_VERSION,
} from '../src/contracts/reportList';
import {
  roleListContractSchemas,
  ROLE_LIST_CONTRACT_VERSION,
} from '../src/contracts/roleList';
import {
  rlsListContractSchemas,
  RLS_LIST_CONTRACT_VERSION,
} from '../src/contracts/rlsList';
import {
  savedQueryListContractSchemas,
  SAVED_QUERY_LIST_CONTRACT_VERSION,
} from '../src/contracts/savedQueryList';
import {
  tagListContractSchemas,
  TAG_LIST_CONTRACT_VERSION,
} from '../src/contracts/tagList';
import {
  taskListContractSchemas,
  TASK_LIST_CONTRACT_VERSION,
} from '../src/contracts/taskList';

test('runtime contract version is explicit', () => {
  expect(RUNTIME_CONTRACT_VERSION).toBe('runtime.v1');
});

test('authorization contract version is explicit', () => {
  expect(AUTHORIZATION_CONTRACT_VERSION).toBe('authorization.v1');
});

test('asset search contract version is explicit', () => {
  expect(ASSET_SEARCH_CONTRACT_VERSION).toBe('asset-search.v1');
});

test('annotation list contract version is explicit', () => {
  expect(ANNOTATION_LIST_CONTRACT_VERSION).toBe('annotation-list.v1');
});

test('annotation layer list contract version is explicit', () => {
  expect(ANNOTATION_LAYER_LIST_CONTRACT_VERSION).toBe(
    'annotation-layer-list.v1',
  );
});

test('dashboard list contract version is explicit', () => {
  expect(DASHBOARD_LIST_CONTRACT_VERSION).toBe('dashboard-list.v1');
});

test('chart list contract version is explicit', () => {
  expect(CHART_LIST_CONTRACT_VERSION).toBe('chart-list.v1');
});

test('dataset list contract version is explicit', () => {
  expect(DATASET_LIST_CONTRACT_VERSION).toBe('dataset-list.v1');
});

test('database list contract version is explicit', () => {
  expect(DATABASE_LIST_CONTRACT_VERSION).toBe('database-list.v1');
});

test('query list contract version is explicit', () => {
  expect(QUERY_LIST_CONTRACT_VERSION).toBe('query-list.v1');
});

test('saved query list contract version is explicit', () => {
  expect(SAVED_QUERY_LIST_CONTRACT_VERSION).toBe('saved-query-list.v1');
});

test('report list contract version is explicit', () => {
  expect(REPORT_LIST_CONTRACT_VERSION).toBe('report-list.v1');
});

test('role list contract version is explicit', () => {
  expect(ROLE_LIST_CONTRACT_VERSION).toBe('role-list.v1');
});

test('RLS list contract version is explicit', () => {
  expect(RLS_LIST_CONTRACT_VERSION).toBe('rls-list.v1');
});

test('tag list contract version is explicit', () => {
  expect(TAG_LIST_CONTRACT_VERSION).toBe('tag-list.v1');
});

test('task list contract version is explicit', () => {
  expect(TASK_LIST_CONTRACT_VERSION).toBe('task-list.v1');
});

test('health response schema is stable', () => {
  expect(healthResponseSchema).toEqual({
    $id: 'ax-services.health.v1.response',
    type: 'object',
    required: [
      'contractVersion',
      'service',
      'status',
      'timestamp',
      'version',
      'nodeVersion',
      'platform',
      'uptimeSeconds',
    ],
    additionalProperties: false,
    properties: {
      contractVersion: { const: 'runtime.v1' },
      service: { const: 'ax-services' },
      status: { const: 'ok' },
      timestamp: { type: 'string' },
      version: { type: 'string' },
      nodeVersion: { type: 'string' },
      platform: { type: 'string' },
      uptimeSeconds: { type: 'number' },
    },
  });
});

test('readiness response schema is registered in runtime contracts', () => {
  expect(runtimeContractSchemas.readinessResponseSchema).toBe(
    readinessResponseSchema,
  );
  expect(readinessResponseSchema.properties.status).toEqual({
    enum: ['ready', 'not_ready'],
  });
});

test('metrics response schema is registered in runtime contracts', () => {
  expect(runtimeContractSchemas.metricsResponseSchema).toBe(metricsResponseSchema);
  expect(metricsResponseSchema.properties.requests.properties.routes).toEqual({
    type: 'object',
    additionalProperties: {
      type: 'object',
      required: ['count', 'errorCount', 'averageDurationMs', 'maxDurationMs'],
      additionalProperties: false,
      properties: {
        count: { type: 'number' },
        errorCount: { type: 'number' },
        averageDurationMs: { type: 'number' },
        maxDurationMs: { type: 'number' },
      },
    },
  });
});

test('metadata response schema is registered in runtime contracts', () => {
  expect(runtimeContractSchemas.metadataResponseSchema).toBe(
    metadataResponseSchema,
  );
  expect(
    metadataResponseSchema.properties.dependencies.properties.supersetMetadata
      .properties.keys,
  ).toEqual({
    type: 'array',
    items: { type: 'string' },
  });
});

test('permission check request schema is registered in authorization contracts', () => {
  expect(authorizationContractSchemas.permissionCheckRequestSchema).toBe(
    permissionCheckRequestSchema,
  );
  expect(
    permissionCheckRequestSchema.properties.principal.properties.userId,
  ).toEqual({
    type: 'integer',
    minimum: 0,
  });
  expect(permissionCheckRequestSchema.properties.resource.properties.id).toEqual({
    type: 'integer',
    minimum: 0,
  });
  expect(permissionCheckRequestSchema.properties.action).toEqual({
    enum: ['create', 'delete', 'read', 'write'],
  });
});

test('RLS list request schema is registered in RLS list contracts', () => {
  expect(rlsListContractSchemas.rlsListRequestSchema.properties.page).toEqual({
    type: 'integer',
    minimum: 1,
  });
  expect(
    rlsListContractSchemas.rlsListResponseSchema.properties.rlsFilters.items
      .properties.clause,
  ).toEqual({
    type: 'string',
  });
});

test('asset search request schema is registered in asset search contracts', () => {
  expect(assetSearchContractSchemas.assetSearchRequestSchema.properties.query).toEqual(
    {
      type: 'string',
    },
  );
  expect(
    assetSearchContractSchemas.assetSearchRequestSchema.properties.limit,
  ).toEqual({
    type: 'integer',
    minimum: 1,
    maximum: 100,
  });
  expect(
    assetSearchContractSchemas.assetSearchResponseSchema.properties.assets.items
      .properties.assetType,
  ).toEqual({
    enum: ['chart', 'dashboard', 'dataset', 'metric'],
  });
});

test('annotation list request schema is registered in annotation list contracts', () => {
  expect(
    annotationListContractSchemas.annotationListRequestSchema.properties.layerId,
  ).toEqual({
    type: 'integer',
    minimum: 1,
  });
  expect(
    annotationListContractSchemas.annotationListResponseSchema.properties.annotations
      .items.properties,
  ).toEqual({
    id: { type: 'integer', minimum: 0 },
    shortDescr: { type: 'string' },
    longDescr: { type: 'string' },
    startDttm: { type: 'string' },
    endDttm: { type: 'string' },
    jsonMetadata: { type: 'string' },
    layerId: { type: 'integer', minimum: 0 },
  });
});

test('role list request schema is registered in role list contracts', () => {
  expect(roleListContractSchemas.roleListRequestSchema.properties.page).toEqual({
    type: 'integer',
    minimum: 1,
  });
  expect(
    roleListContractSchemas.roleListResponseSchema.properties.roles.items.properties,
  ).toEqual({
    id: { type: 'integer', minimum: 0 },
    name: { type: 'string' },
  });
});

test('annotation layer list request schema is registered in annotation layer list contracts', () => {
  expect(
    annotationLayerListContractSchemas.annotationLayerListRequestSchema.properties
      .page,
  ).toEqual({
    type: 'integer',
    minimum: 1,
  });
  expect(
    annotationLayerListContractSchemas.annotationLayerListResponseSchema.properties
      .annotationLayers.items.properties.name,
  ).toEqual({
    type: 'string',
  });
});

test('dashboard list request schema is registered in dashboard list contracts', () => {
  expect(
    dashboardListContractSchemas.dashboardListRequestSchema.properties.page,
  ).toEqual({
    type: 'integer',
    minimum: 1,
  });
  expect(
    dashboardListContractSchemas.dashboardListRequestSchema.properties.filters
      .items.properties.col,
  ).toEqual({
    type: 'string',
    pattern: '^[A-Za-z0-9_]+$',
  });
  expect(
    dashboardListContractSchemas.dashboardListRequestSchema.properties.filters
      .items.properties.opr,
  ).toEqual({
    type: 'string',
    pattern: '^[A-Za-z0-9_]+$',
  });
  expect(
    dashboardListContractSchemas.dashboardListResponseSchema.properties.count,
  ).toEqual({
    type: 'integer',
    minimum: 0,
  });
  expect(
    dashboardListContractSchemas.dashboardListResponseSchema.properties.totalPages,
  ).toEqual({
    type: 'integer',
    minimum: 0,
  });
  expect(
    dashboardListContractSchemas.dashboardListResponseSchema.properties
      .dashboards.items.properties.dashboardTitle,
  ).toEqual({
    type: 'string',
  });
});

test('chart list request schema is registered in chart list contracts', () => {
  expect(chartListContractSchemas.chartListRequestSchema.properties.page).toEqual({
    type: 'integer',
    minimum: 1,
  });
  expect(
    chartListContractSchemas.chartListResponseSchema.properties.charts.items
      .properties.sliceName,
  ).toEqual({
    type: 'string',
  });
});

test('dataset list request schema is registered in dataset list contracts', () => {
  expect(
    datasetListContractSchemas.datasetListRequestSchema.properties.page,
  ).toEqual({
    type: 'integer',
    minimum: 1,
  });
  expect(
    datasetListContractSchemas.datasetListResponseSchema.properties.datasets.items
      .properties.tableName,
  ).toEqual({
    type: 'string',
  });
});

test('database list request schema is registered in database list contracts', () => {
  expect(
    databaseListContractSchemas.databaseListRequestSchema.properties.page,
  ).toEqual({
    type: 'integer',
    minimum: 1,
  });
  expect(
    databaseListContractSchemas.databaseListResponseSchema.properties.databases
      .items.properties.databaseName,
  ).toEqual({
    type: 'string',
  });
});

test('query list request schema is registered in query list contracts', () => {
  expect(queryListContractSchemas.queryListRequestSchema.properties.page).toEqual({
    type: 'integer',
    minimum: 1,
  });
  expect(
    queryListContractSchemas.queryListResponseSchema.properties.queries.items
      .properties.sql,
  ).toEqual({
    type: 'string',
  });
});

test('saved query list request schema is registered in saved query list contracts', () => {
  expect(
    savedQueryListContractSchemas.savedQueryListRequestSchema.properties.page,
  ).toEqual({
    type: 'integer',
    minimum: 1,
  });
  expect(
    savedQueryListContractSchemas.savedQueryListResponseSchema.properties
      .savedQueries.items.properties.label,
  ).toEqual({
    type: 'string',
  });
});

test('report list request schema is registered in report list contracts', () => {
  expect(reportListContractSchemas.reportListRequestSchema.properties.page).toEqual({
    type: 'integer',
    minimum: 1,
  });
  expect(
    reportListContractSchemas.reportListResponseSchema.properties.reports.items
      .properties.name,
  ).toEqual({
    type: 'string',
  });
});

test('tag list request schema is registered in tag list contracts', () => {
  expect(tagListContractSchemas.tagListRequestSchema.properties.page).toEqual({
    type: 'integer',
    minimum: 1,
  });
  expect(
    tagListContractSchemas.tagListResponseSchema.properties.tags.items.properties.name,
  ).toEqual({
    type: 'string',
  });
});

test('task list request schema is registered in task list contracts', () => {
  expect(taskListContractSchemas.taskListRequestSchema.properties.page).toEqual({
    type: 'integer',
    minimum: 1,
  });
  expect(
    taskListContractSchemas.taskListResponseSchema.properties.tasks.items.properties
      .taskName,
  ).toEqual({
    type: 'string',
  });
});

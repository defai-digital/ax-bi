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

test('runtime contract version is explicit', () => {
  expect(RUNTIME_CONTRACT_VERSION).toBe('runtime.v1');
});

test('authorization contract version is explicit', () => {
  expect(AUTHORIZATION_CONTRACT_VERSION).toBe('authorization.v1');
});

test('asset search contract version is explicit', () => {
  expect(ASSET_SEARCH_CONTRACT_VERSION).toBe('asset-search.v1');
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
  expect(permissionCheckRequestSchema.properties.action).toEqual({
    enum: ['create', 'delete', 'read', 'write'],
  });
});

test('asset search request schema is registered in asset search contracts', () => {
  expect(assetSearchContractSchemas.assetSearchRequestSchema.properties.query).toEqual(
    {
      type: 'string',
    },
  );
  expect(
    assetSearchContractSchemas.assetSearchResponseSchema.properties.assets.items
      .properties.assetType,
  ).toEqual({
    enum: ['chart', 'dashboard', 'dataset', 'metric'],
  });
});

test('dashboard list request schema is registered in dashboard list contracts', () => {
  expect(
    dashboardListContractSchemas.dashboardListRequestSchema.properties.page,
  ).toEqual({
    type: 'number',
    minimum: 1,
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
    type: 'number',
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
    type: 'number',
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
    type: 'number',
    minimum: 1,
  });
  expect(
    databaseListContractSchemas.databaseListResponseSchema.properties.databases
      .items.properties.databaseName,
  ).toEqual({
    type: 'string',
  });
});

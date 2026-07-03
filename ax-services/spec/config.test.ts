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

import { buildConfig } from '../src/config';

test('buildConfig returns service defaults', () => {
  const config = buildConfig({});

  expect(config.host).toBe('127.0.0.1');
  expect(config.port).toBe(5010);
  expect(config.supersetBaseUrl).toBe('http://127.0.0.1:8088');
  expect(config.supersetHealthPath).toBe('/health');
  expect(config.supersetMetadataPath).toBe('/api/v1/dashboard/_info');
  expect(config.supersetPermissionPath).toBe(
    '/api/v1/security/permissions/check',
  );
  expect(config.supersetAssetSearchPaths).toEqual({
    annotationLayer: '/api/v1/annotation_layer/',
    chart: '/api/v1/chart/',
    dashboard: '/api/v1/dashboard/',
    database: '/api/v1/database/',
    dataset: '/api/v1/dataset/',
    query: '/api/v1/query/',
    report: '/api/v1/report/',
    role: '/api/v1/role/',
    rls: '/api/v1/rowlevelsecurity/',
    savedQuery: '/api/v1/saved_query/',
    tag: '/api/v1/tag/',
    task: '/api/v1/task/',
  });
  expect(config.supersetTimeoutMs).toBe(2000);
  expect(config.supersetInternalToken).toBeUndefined();
  expect(config.logLevel).toBe('info');
});

test('buildConfig reads environment overrides', () => {
  const config = buildConfig({
    AX_SERVICES_HOST: '  0.0.0.0  ',
    AX_SERVICES_PORT: '6010',
    AX_SUPERSET_BASE_URL: 'https://superset.example.test/',
    AX_SUPERSET_HEALTH_PATH: 'healthz',
    AX_SUPERSET_METADATA_PATH: 'api/v1/chart/_info',
    AX_SUPERSET_PERMISSION_PATH: 'permissions/check',
    AX_SUPERSET_ANNOTATION_LAYER_LIST_PATH: 'annotation-layers',
    AX_SUPERSET_CHART_LIST_PATH: 'charts',
    AX_SUPERSET_DASHBOARD_LIST_PATH: 'dashboards',
    AX_SUPERSET_DATABASE_LIST_PATH: 'databases',
    AX_SUPERSET_DATASET_LIST_PATH: 'datasets',
    AX_SUPERSET_QUERY_LIST_PATH: 'queries',
    AX_SUPERSET_REPORT_LIST_PATH: 'reports',
    AX_SUPERSET_ROLE_LIST_PATH: 'roles',
    AX_SUPERSET_RLS_LIST_PATH: 'rls-filters',
    AX_SUPERSET_SAVED_QUERY_LIST_PATH: 'saved-queries',
    AX_SUPERSET_TAG_LIST_PATH: 'tags',
    AX_SUPERSET_TASK_LIST_PATH: 'tasks',
    AX_SUPERSET_TIMEOUT_MS: '1500',
    AX_SUPERSET_INTERNAL_TOKEN: '  token-123  ',
    AX_SERVICES_LOG_LEVEL: ' DEBUG ',
  });

  expect(config.host).toBe('0.0.0.0');
  expect(config.port).toBe(6010);
  expect(config.supersetBaseUrl).toBe('https://superset.example.test');
  expect(config.supersetHealthPath).toBe('/healthz');
  expect(config.supersetMetadataPath).toBe('/api/v1/chart/_info');
  expect(config.supersetPermissionPath).toBe('/permissions/check');
  expect(config.supersetAssetSearchPaths).toEqual({
    annotationLayer: '/annotation-layers',
    chart: '/charts',
    dashboard: '/dashboards',
    database: '/databases',
    dataset: '/datasets',
    query: '/queries',
    report: '/reports',
    role: '/roles',
    rls: '/rls-filters',
    savedQuery: '/saved-queries',
    tag: '/tags',
    task: '/tasks',
  });
  expect(config.supersetTimeoutMs).toBe(1500);
  expect(config.supersetInternalToken).toBe('token-123');
  expect(config.logLevel).toBe('debug');
});

test('buildConfig canonicalizes configured Superset paths', () => {
  const config = buildConfig({
    AX_SUPERSET_HEALTH_PATH: '  ///healthz  ',
    AX_SUPERSET_CHART_LIST_PATH: '  charts  ',
  });

  expect(config.supersetHealthPath).toBe('/healthz');
  expect(config.supersetAssetSearchPaths.chart).toBe('/charts');
});

test('buildConfig supports path-prefixed Superset base URLs', () => {
  const config = buildConfig({
    AX_SUPERSET_BASE_URL: 'https://example.test/superset/',
  });

  expect(config.supersetBaseUrl).toBe('https://example.test/superset');
});

test('buildConfig defaults blank host and log level values', () => {
  const config = buildConfig({
    AX_SERVICES_HOST: '   ',
    AX_SERVICES_LOG_LEVEL: '   ',
  });

  expect(config.host).toBe('127.0.0.1');
  expect(config.logLevel).toBe('info');
});

test('buildConfig rejects invalid numeric settings', () => {
  expect(() => buildConfig({ AX_SERVICES_PORT: 'abc' })).toThrow(
    'AX_SERVICES_PORT must be a positive integer',
  );
  expect(() => buildConfig({ AX_SERVICES_PORT: '65536' })).toThrow(
    'AX_SERVICES_PORT must be between 1 and 65535',
  );
  expect(() => buildConfig({ AX_SUPERSET_TIMEOUT_MS: '0' })).toThrow(
    'AX_SUPERSET_TIMEOUT_MS must be a positive integer',
  );
  expect(() =>
    buildConfig({ AX_SUPERSET_TIMEOUT_MS: '2147483648' }),
  ).toThrow('AX_SUPERSET_TIMEOUT_MS must be between 1 and 2147483647');
});

test('buildConfig accepts maximum supported Superset timeout', () => {
  const config = buildConfig({ AX_SUPERSET_TIMEOUT_MS: '2147483647' });

  expect(config.supersetTimeoutMs).toBe(2147483647);
});

test('buildConfig treats blank optional token as absent', () => {
  const config = buildConfig({ AX_SUPERSET_INTERNAL_TOKEN: '   ' });

  expect(config.supersetInternalToken).toBeUndefined();
});

test('buildConfig rejects invalid Superset URL', () => {
  expect(() => buildConfig({ AX_SUPERSET_BASE_URL: 'not a url' })).toThrow(
    'AX_SUPERSET_BASE_URL must be a valid HTTP(S) URL',
  );
});

test('buildConfig rejects unsupported Superset URL protocols', () => {
  expect(() =>
    buildConfig({ AX_SUPERSET_BASE_URL: 'ftp://superset.example.test' }),
  ).toThrow(
    'AX_SUPERSET_BASE_URL must be a valid HTTP(S) URL',
  );
});

test('buildConfig rejects Superset base URLs with query or fragment', () => {
  expect(() =>
    buildConfig({ AX_SUPERSET_BASE_URL: 'https://example.test?tenant=ax' }),
  ).toThrow('AX_SUPERSET_BASE_URL must be a valid HTTP(S) URL');
  expect(() =>
    buildConfig({ AX_SUPERSET_BASE_URL: 'https://example.test#dashboard' }),
  ).toThrow('AX_SUPERSET_BASE_URL must be a valid HTTP(S) URL');
});

test('buildConfig rejects blank Superset path overrides', () => {
  expect(() => buildConfig({ AX_SUPERSET_HEALTH_PATH: '   ' })).toThrow(
    'AX_SUPERSET_HEALTH_PATH must not be empty',
  );
});

test('buildConfig rejects ambiguous Superset path overrides', () => {
  const message =
    'AX_SUPERSET_HEALTH_PATH must be a URL path without query, fragment, backslash, or control characters';

  expect(() =>
    buildConfig({ AX_SUPERSET_HEALTH_PATH: '/health?verbose=true' }),
  ).toThrow(message);
  expect(() =>
    buildConfig({ AX_SUPERSET_HEALTH_PATH: '/health#ready' }),
  ).toThrow(message);
  expect(() =>
    buildConfig({ AX_SUPERSET_HEALTH_PATH: String.raw`api\v1\health` }),
  ).toThrow(message);
  expect(() =>
    buildConfig({ AX_SUPERSET_HEALTH_PATH: '/health\nready' }),
  ).toThrow(message);
});

test('buildConfig rejects unsupported log levels', () => {
  expect(() => buildConfig({ AX_SERVICES_LOG_LEVEL: 'verbose' })).toThrow(
    'AX_SERVICES_LOG_LEVEL must be one of: debug, info, warn, error, silent',
  );
});

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
  expect(config.port).toBe(31424);
  expect(config.axbiBaseUrl).toBe('http://127.0.0.1:31423');
  expect(config.axbiHealthPath).toBe('/health');
  expect(config.axbiMetadataPath).toBe('/api/v1/dashboard/_info');
  expect(config.axbiPermissionPath).toBe('/api/v1/security/permissions/check');
  expect(config.axbiAssetSearchPaths).toEqual({
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
  expect(config.axbiTimeoutMs).toBe(2000);
  expect(config.axbiInternalToken).toBeUndefined();
  expect(config.inboundToken).toBeUndefined();
  expect(config.logLevel).toBe('info');
});

test('buildConfig reads environment overrides', () => {
  const config = buildConfig({
    AX_SERVICES_HOST: '  0.0.0.0  ',
    AX_SERVICES_PORT: '6010',
    AXBI_BASE_URL: 'https://ax-bi.example.test/',
    AXBI_HEALTH_PATH: 'healthz',
    AXBI_METADATA_PATH: 'api/v1/chart/_info',
    AXBI_PERMISSION_PATH: 'permissions/check',
    AXBI_ANNOTATION_LAYER_LIST_PATH: 'annotation-layers',
    AXBI_CHART_LIST_PATH: 'charts',
    AXBI_DASHBOARD_LIST_PATH: 'dashboards',
    AXBI_DATABASE_LIST_PATH: 'databases',
    AXBI_DATASET_LIST_PATH: 'datasets',
    AXBI_QUERY_LIST_PATH: 'queries',
    AXBI_REPORT_LIST_PATH: 'reports',
    AXBI_ROLE_LIST_PATH: 'roles',
    AXBI_RLS_LIST_PATH: 'rls-filters',
    AXBI_SAVED_QUERY_LIST_PATH: 'saved-queries',
    AXBI_TAG_LIST_PATH: 'tags',
    AXBI_TASK_LIST_PATH: 'tasks',
    AXBI_TIMEOUT_MS: '1500',
    AXBI_INTERNAL_TOKEN: '  token-123  ',
    AX_SERVICES_INTERNAL_TOKEN: '  inbound-token-123  ',
    AX_SERVICES_LOG_LEVEL: ' DEBUG ',
  });

  expect(config.host).toBe('0.0.0.0');
  expect(config.port).toBe(6010);
  expect(config.axbiBaseUrl).toBe('https://ax-bi.example.test');
  expect(config.axbiHealthPath).toBe('/healthz');
  expect(config.axbiMetadataPath).toBe('/api/v1/chart/_info');
  expect(config.axbiPermissionPath).toBe('/permissions/check');
  expect(config.axbiAssetSearchPaths).toEqual({
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
  expect(config.axbiTimeoutMs).toBe(1500);
  expect(config.axbiInternalToken).toBe('token-123');
  expect(config.inboundToken).toBe('inbound-token-123');
  expect(config.logLevel).toBe('debug');
});

test('buildConfig canonicalizes configured AxBI paths', () => {
  const config = buildConfig({
    AXBI_HEALTH_PATH: '  ///healthz  ',
    AXBI_CHART_LIST_PATH: '  charts  ',
  });

  expect(config.axbiHealthPath).toBe('/healthz');
  expect(config.axbiAssetSearchPaths.chart).toBe('/charts');
});

test('buildConfig supports path-prefixed AxBI base URLs', () => {
  const config = buildConfig({
    AXBI_BASE_URL: 'https://example.test/ax-bi/',
  });

  expect(config.axbiBaseUrl).toBe('https://example.test/ax-bi');
});

test('buildConfig defaults blank host and log level values', () => {
  const config = buildConfig({
    AX_SERVICES_HOST: '   ',
    AX_SERVICES_LOG_LEVEL: '   ',
  });

  expect(config.host).toBe('127.0.0.1');
  expect(config.logLevel).toBe('info');
});

test('buildConfig accepts hostnames and IP listener addresses', () => {
  expect(
    buildConfig({
      AX_SERVICES_HOST: ' service.internal ',
      AX_SERVICES_INTERNAL_TOKEN: 'inbound-token-123',
    }).host,
  ).toBe('service.internal');
  expect(buildConfig({ AX_SERVICES_HOST: '::1' }).host).toBe('::1');
});

test('buildConfig rejects host values with whitespace or control characters', () => {
  expect(() =>
    buildConfig({ AX_SERVICES_HOST: '127.0.0.1 localhost' }),
  ).toThrow(
    'AX_SERVICES_HOST must not contain whitespace or control characters',
  );
  expect(() => buildConfig({ AX_SERVICES_HOST: 'localhost\nready' })).toThrow(
    'AX_SERVICES_HOST must not contain whitespace or control characters',
  );
});

test('buildConfig rejects ambiguous host listener values', () => {
  const message =
    'AX_SERVICES_HOST must be a hostname or IP address without scheme, path, or port';

  expect(() => buildConfig({ AX_SERVICES_HOST: 'http://localhost' })).toThrow(
    message,
  );
  expect(() => buildConfig({ AX_SERVICES_HOST: 'localhost:31424' })).toThrow(
    message,
  );
  expect(() =>
    buildConfig({ AX_SERVICES_HOST: '/tmp/ax-services.sock' }),
  ).toThrow(message);
});

test('buildConfig defaults blank numeric settings', () => {
  const config = buildConfig({
    AX_SERVICES_PORT: '   ',
    AXBI_TIMEOUT_MS: '   ',
  });

  expect(config.port).toBe(31424);
  expect(config.axbiTimeoutMs).toBe(2000);
});

test('buildConfig rejects invalid numeric settings', () => {
  expect(() => buildConfig({ AX_SERVICES_PORT: 'abc' })).toThrow(
    'AX_SERVICES_PORT must be a positive integer',
  );
  expect(() => buildConfig({ AX_SERVICES_PORT: '0x1392' })).toThrow(
    'AX_SERVICES_PORT must be a positive integer',
  );
  expect(() => buildConfig({ AX_SERVICES_PORT: '5_010' })).toThrow(
    'AX_SERVICES_PORT must be a positive integer',
  );
  expect(() => buildConfig({ AX_SERVICES_PORT: '65536' })).toThrow(
    'AX_SERVICES_PORT must be between 1 and 65535',
  );
  expect(() => buildConfig({ AXBI_TIMEOUT_MS: '0' })).toThrow(
    'AXBI_TIMEOUT_MS must be a positive integer',
  );
  expect(() => buildConfig({ AXBI_TIMEOUT_MS: '1e3' })).toThrow(
    'AXBI_TIMEOUT_MS must be a positive integer',
  );
  expect(() => buildConfig({ AXBI_TIMEOUT_MS: '1000.5' })).toThrow(
    'AXBI_TIMEOUT_MS must be a positive integer',
  );
  expect(() => buildConfig({ AXBI_TIMEOUT_MS: '2147483648' })).toThrow(
    'AXBI_TIMEOUT_MS must be between 1 and 2147483647',
  );
});

test('buildConfig accepts maximum supported AxBI timeout', () => {
  const config = buildConfig({ AXBI_TIMEOUT_MS: '2147483647' });

  expect(config.axbiTimeoutMs).toBe(2147483647);
});

test('buildConfig treats blank optional token as absent', () => {
  const config = buildConfig({ AXBI_INTERNAL_TOKEN: '   ' });

  expect(config.axbiInternalToken).toBeUndefined();
});

test('buildConfig rejects internal tokens with control characters', () => {
  expect(() =>
    buildConfig({ AXBI_INTERNAL_TOKEN: 'token-123\nX-Other: value' }),
  ).toThrow('AXBI_INTERNAL_TOKEN must not contain control characters');
  expect(() =>
    buildConfig({
      AX_SERVICES_INTERNAL_TOKEN: 'token-123\nX-Other: value',
    }),
  ).toThrow('AX_SERVICES_INTERNAL_TOKEN must not contain control characters');
});

test('buildConfig requires inbound auth for non-loopback listeners', () => {
  expect(() => buildConfig({ AX_SERVICES_HOST: '0.0.0.0' })).toThrow(
    'AX_SERVICES_INTERNAL_TOKEN is required when AX_SERVICES_HOST is not loopback',
  );

  expect(
    buildConfig({
      AX_SERVICES_HOST: '0.0.0.0',
      AX_SERVICES_INTERNAL_TOKEN: 'inbound-token-123',
    }).inboundToken,
  ).toBe('inbound-token-123');
});

test('buildConfig rejects invalid AxBI URL', () => {
  expect(() => buildConfig({ AXBI_BASE_URL: 'not a url' })).toThrow(
    'AXBI_BASE_URL must be a valid HTTP(S) URL',
  );
  expect(() => buildConfig({ AXBI_BASE_URL: 'http:dashboard' })).toThrow(
    'AXBI_BASE_URL must be a valid HTTP(S) URL',
  );
  expect(() => buildConfig({ AXBI_BASE_URL: 'https:/dashboard' })).toThrow(
    'AXBI_BASE_URL must be a valid HTTP(S) URL',
  );
});

test('buildConfig rejects unsupported AxBI URL protocols', () => {
  expect(() =>
    buildConfig({ AXBI_BASE_URL: 'ftp://ax-bi.example.test' }),
  ).toThrow('AXBI_BASE_URL must be a valid HTTP(S) URL');
});

test('buildConfig rejects AxBI base URLs with query or fragment', () => {
  expect(() =>
    buildConfig({ AXBI_BASE_URL: 'https://example.test?tenant=ax' }),
  ).toThrow('AXBI_BASE_URL must be a valid HTTP(S) URL');
  expect(() =>
    buildConfig({ AXBI_BASE_URL: 'https://example.test#dashboard' }),
  ).toThrow('AXBI_BASE_URL must be a valid HTTP(S) URL');
});

test('buildConfig rejects AxBI base URLs with credentials', () => {
  expect(() =>
    buildConfig({
      AXBI_BASE_URL: 'https://user:pass@example.test/ax-bi',
    }),
  ).toThrow('AXBI_BASE_URL must be a valid HTTP(S) URL');
});

test('buildConfig rejects ambiguous AxBI base URL paths', () => {
  for (const AXBI_BASE_URL of [
    'https://example.test/ax-bi/../admin',
    'https://example.test/ax-bi/%2e%2e/admin',
    'https://example.test/ax-bi%2fapi',
    'https://example.test/ax-bi%20admin',
    'https://example.test/ax-bi%00admin',
    'https://example.test/ax-bi/%zz',
  ]) {
    expect(() => buildConfig({ AXBI_BASE_URL })).toThrow(
      'AXBI_BASE_URL must be a valid HTTP(S) URL',
    );
  }
});

test('buildConfig rejects blank AxBI path overrides', () => {
  expect(() => buildConfig({ AXBI_HEALTH_PATH: '' })).toThrow(
    'AXBI_HEALTH_PATH must not be empty',
  );
  expect(() => buildConfig({ AXBI_HEALTH_PATH: '   ' })).toThrow(
    'AXBI_HEALTH_PATH must not be empty',
  );
  expect(() => buildConfig({ AXBI_CHART_LIST_PATH: '' })).toThrow(
    'AXBI_CHART_LIST_PATH must not be empty',
  );
});

test('buildConfig rejects ambiguous AxBI path overrides', () => {
  const message =
    'AXBI_HEALTH_PATH must be a URL path without query, fragment, backslash, whitespace, or control characters';

  expect(() =>
    buildConfig({ AXBI_HEALTH_PATH: '/health?verbose=true' }),
  ).toThrow(message);
  expect(() => buildConfig({ AXBI_HEALTH_PATH: '/health#ready' })).toThrow(
    message,
  );
  expect(() =>
    buildConfig({ AXBI_HEALTH_PATH: String.raw`api\v1\health` }),
  ).toThrow(message);
  expect(() => buildConfig({ AXBI_HEALTH_PATH: '/health\nready' })).toThrow(
    message,
  );
  expect(() => buildConfig({ AXBI_HEALTH_PATH: '/health ready' })).toThrow(
    message,
  );
});

test('buildConfig rejects AxBI path overrides with dot segments', () => {
  expect(() => buildConfig({ AXBI_HEALTH_PATH: '/../health' })).toThrow(
    'AXBI_HEALTH_PATH must not contain dot path segments',
  );
  expect(() => buildConfig({ AXBI_CHART_LIST_PATH: 'api/./v1/chart' })).toThrow(
    'AXBI_CHART_LIST_PATH must not contain dot path segments',
  );
  expect(() =>
    buildConfig({ AXBI_METADATA_PATH: 'api/%2e%2e/dashboard/_info' }),
  ).toThrow('AXBI_METADATA_PATH must not contain dot path segments');
});

test('buildConfig rejects ambiguous percent-encoded AxBI path overrides', () => {
  expect(() => buildConfig({ AXBI_HEALTH_PATH: '/api%2fhealth' })).toThrow(
    'AXBI_HEALTH_PATH must not contain encoded path separators',
  );
  expect(() => buildConfig({ AXBI_HEALTH_PATH: '/api%5chealth' })).toThrow(
    'AXBI_HEALTH_PATH must not contain encoded path separators',
  );
  expect(() => buildConfig({ AXBI_HEALTH_PATH: '/api%20health' })).toThrow(
    'AXBI_HEALTH_PATH must not contain whitespace or control characters',
  );
  expect(() => buildConfig({ AXBI_HEALTH_PATH: '/api%00health' })).toThrow(
    'AXBI_HEALTH_PATH must not contain whitespace or control characters',
  );
  expect(() => buildConfig({ AXBI_HEALTH_PATH: '/api/%zz/health' })).toThrow(
    'AXBI_HEALTH_PATH must contain valid percent-encoding',
  );
});

test('buildConfig rejects unsupported log levels', () => {
  expect(() => buildConfig({ AX_SERVICES_LOG_LEVEL: 'verbose' })).toThrow(
    'AX_SERVICES_LOG_LEVEL must be one of: debug, info, warn, error, silent',
  );
});

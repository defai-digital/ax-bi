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
  expect(config.supersetPermissionPath).toBe(
    '/api/v1/security/permissions/check',
  );
  expect(config.supersetTimeoutMs).toBe(2000);
  expect(config.supersetInternalToken).toBeUndefined();
  expect(config.logLevel).toBe('info');
});

test('buildConfig reads environment overrides', () => {
  const config = buildConfig({
    AX_SERVICES_HOST: '0.0.0.0',
    AX_SERVICES_PORT: '6010',
    AX_SUPERSET_BASE_URL: 'https://superset.example.test/',
    AX_SUPERSET_HEALTH_PATH: 'healthz',
    AX_SUPERSET_PERMISSION_PATH: 'permissions/check',
    AX_SUPERSET_TIMEOUT_MS: '1500',
    AX_SUPERSET_INTERNAL_TOKEN: 'token-123',
    AX_SERVICES_LOG_LEVEL: 'debug',
  });

  expect(config.host).toBe('0.0.0.0');
  expect(config.port).toBe(6010);
  expect(config.supersetBaseUrl).toBe('https://superset.example.test');
  expect(config.supersetHealthPath).toBe('/healthz');
  expect(config.supersetPermissionPath).toBe('/permissions/check');
  expect(config.supersetTimeoutMs).toBe(1500);
  expect(config.supersetInternalToken).toBe('token-123');
  expect(config.logLevel).toBe('debug');
});

test('buildConfig rejects invalid numeric settings', () => {
  expect(() => buildConfig({ AX_SERVICES_PORT: 'abc' })).toThrow(
    'AX_SERVICES_PORT must be a positive integer',
  );
  expect(() => buildConfig({ AX_SUPERSET_TIMEOUT_MS: '0' })).toThrow(
    'AX_SUPERSET_TIMEOUT_MS must be a positive integer',
  );
});

test('buildConfig rejects invalid Superset URL', () => {
  expect(() => buildConfig({ AX_SUPERSET_BASE_URL: 'not a url' })).toThrow(
    'AX_SUPERSET_BASE_URL must be a valid URL',
  );
});

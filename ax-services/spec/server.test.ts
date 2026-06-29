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
import { buildServer } from '../src/server';
import { SupersetHealthClient } from '../src/supersetClient';

const config = {
  ...buildConfig({}),
  logLevel: 'silent',
};

test('health endpoint returns service metadata', async () => {
  const server = buildServer(config, {
    async checkHealth() {
      return {
        ok: true,
        statusCode: 200,
        url: 'http://127.0.0.1:8088/health',
      };
    },
  } as SupersetHealthClient);

  const response = await server.inject({
    method: 'GET',
    url: '/health',
  });

  expect(response.statusCode).toBe(200);
  expect(response.headers['x-request-id']).toBeDefined();
  expect(response.json()).toEqual({
    contractVersion: 'runtime.v1',
    service: 'ax-services',
    status: 'ok',
  });
});

test('ready endpoint returns ok when Superset is reachable', async () => {
  const seenRequestIds: string[] = [];
  const server = buildServer(config, {
    async checkHealth(correlationId) {
      if (correlationId) {
        seenRequestIds.push(correlationId);
      }
      return {
        ok: true,
        statusCode: 200,
        url: 'http://127.0.0.1:8088/health',
      };
    },
  } as SupersetHealthClient);

  const response = await server.inject({
    method: 'GET',
    url: '/ready',
    headers: {
      'x-request-id': 'request-123',
    },
  });

  expect(response.statusCode).toBe(200);
  expect(response.headers['x-request-id']).toBe('request-123');
  expect(seenRequestIds).toEqual(['request-123']);
  expect(response.json()).toEqual({
    contractVersion: 'runtime.v1',
    service: 'ax-services',
    status: 'ready',
    dependencies: {
      superset: {
        ok: true,
        statusCode: 200,
        url: 'http://127.0.0.1:8088/health',
      },
    },
  });
});

test('ready endpoint returns unavailable when Superset is unreachable', async () => {
  const server = buildServer(config, {
    async checkHealth() {
      return {
        ok: false,
        error: 'connect ECONNREFUSED',
        url: 'http://127.0.0.1:8088/health',
      };
    },
  } as SupersetHealthClient);

  const response = await server.inject({
    method: 'GET',
    url: '/ready',
  });

  expect(response.statusCode).toBe(503);
  expect(response.json()).toEqual({
    contractVersion: 'runtime.v1',
    service: 'ax-services',
    status: 'not_ready',
    dependencies: {
      superset: {
        ok: false,
        error: 'connect ECONNREFUSED',
        url: 'http://127.0.0.1:8088/health',
      },
    },
  });
});

test('metrics endpoint returns request counters by route', async () => {
  const server = buildServer(config, {
    async checkHealth() {
      return {
        ok: false,
        error: 'connect ECONNREFUSED',
        url: 'http://127.0.0.1:8088/health',
      };
    },
  } as SupersetHealthClient);

  await server.inject({
    method: 'GET',
    url: '/health',
  });
  await server.inject({
    method: 'GET',
    url: '/ready',
  });

  const response = await server.inject({
    method: 'GET',
    url: '/metrics',
  });

  expect(response.statusCode).toBe(200);
  expect(response.json()).toMatchObject({
    contractVersion: 'runtime.v1',
    service: 'ax-services',
    status: 'ok',
    requests: {
      total: 2,
      errorCount: 1,
      routes: {
        'GET /health': {
          count: 1,
          errorCount: 0,
        },
        'GET /ready': {
          count: 1,
          errorCount: 1,
        },
      },
    },
  });
  expect(response.json().uptimeSeconds).toBeGreaterThanOrEqual(0);
  expect(response.json().requests.averageDurationMs).toBeGreaterThanOrEqual(0);
  expect(
    response.json().requests.routes['GET /health'].averageDurationMs,
  ).toBeGreaterThanOrEqual(0);
});

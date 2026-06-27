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
import { describe, expect, test, beforeEach, jest } from '@jest/globals';

const mockGetChartCache = jest.fn<(key: string) => Promise<string | null>>();
const mockHasChartCache = jest.fn<(key: string) => Promise<boolean>>();

jest.mock('../../src/fastCache', () => ({
  getChartCache: mockGetChartCache,
  hasChartCache: mockHasChartCache,
  fastCacheOpts: {
    fastCacheEnabled: true,
    fastCacheKeyPrefix: 'fc:',
    jwtSecret: 'test123-test123-test123-test123-test123-test123-test123',
    jwtCookieName: 'test-async-token',
    jwtAlgorithms: ['HS256'],
    jwtChannelIdKey: 'channel',
    logLevel: 'error',
    logToFile: false,
    logFilename: 'test.log',
  },
  fastCacheStatsd: {
    increment: jest.fn(),
    timing: jest.fn(),
  },
}));

jest.mock('hot-shots', () => {
  return jest.fn().mockImplementation(() => ({
    increment: jest.fn(),
    timing: jest.fn(),
    errorHandler: jest.fn(),
  }));
});

jest.mock('ioredis', () => {
  return jest.fn().mockImplementation(() => ({
    on: jest.fn(),
    xrange: jest.fn(),
  }));
});

jest.mock('ws');

import Fastify from 'fastify';
import { registerChartCacheRoutes } from '../../src/routes/chartCache';
import jwt from 'jsonwebtoken';

const JWT_SECRET =
  'test123-test123-test123-test123-test123-test123-test123';
const COOKIE_NAME = 'test-async-token';

const buildJwtCookie = (channelId: string): string => {
  const token = jwt.sign({ channel: channelId }, JWT_SECRET, {
    algorithm: 'HS256',
  });
  return `${COOKIE_NAME}=${token}`;
};

describe('chartCache routes', () => {
  beforeEach(() => {
    mockGetChartCache.mockClear();
    mockHasChartCache.mockClear();
  });

  test('GET /api/chart-cache/:cacheKey returns cached JSON on hit', async () => {
    const cachedJson = '{"result":[{"data":[{"x":1,"y":2}]}]}';
    mockGetChartCache.mockResolvedValue(cachedJson);

    const app = Fastify({ logger: false });
    registerChartCacheRoutes(app);

    const response = await app.inject({
      method: 'GET',
      url: '/api/chart-cache/qc-abc123def456',
      headers: {
        cookie: buildJwtCookie('test-channel'),
      },
    });

    expect(response.statusCode).toBe(200);
    expect(response.headers['x-cache']).toBe('HIT');
    expect(response.headers['content-type']).toContain('application/json');
    expect(response.body).toBe(cachedJson);
    expect(mockGetChartCache).toHaveBeenCalledWith('qc-abc123def456');

    await app.close();
  });

  test('GET /api/chart-cache/:cacheKey returns 404 on miss', async () => {
    mockGetChartCache.mockResolvedValue(null);

    const app = Fastify({ logger: false });
    registerChartCacheRoutes(app);

    const response = await app.inject({
      method: 'GET',
      url: '/api/chart-cache/qc-missing',
      headers: {
        cookie: buildJwtCookie('test-channel'),
      },
    });

    expect(response.statusCode).toBe(404);
    expect(response.headers['x-cache']).toBe('MISS');

    await app.close();
  });

  test('GET /api/chart-cache/:cacheKey returns 401 without JWT', async () => {
    const app = Fastify({ logger: false });
    registerChartCacheRoutes(app);

    const response = await app.inject({
      method: 'GET',
      url: '/api/chart-cache/qc-abc123',
    });

    expect(response.statusCode).toBe(401);

    await app.close();
  });

  test('GET /api/chart-cache/:cacheKey returns 401 with invalid JWT', async () => {
    const app = Fastify({ logger: false });
    registerChartCacheRoutes(app);

    const response = await app.inject({
      method: 'GET',
      url: '/api/chart-cache/qc-abc123',
      headers: {
        cookie: `${COOKIE_NAME}=invalid-token`,
      },
    });

    expect(response.statusCode).toBe(401);

    await app.close();
  });

  test('GET /api/chart-cache/:cacheKey returns 400 for invalid cache key', async () => {
    const app = Fastify({ logger: false });
    registerChartCacheRoutes(app);

    // Cache key with whitespace should be rejected
    const response = await app.inject({
      method: 'GET',
      url: '/api/chart-cache/key%20with%20spaces',
      headers: {
        cookie: buildJwtCookie('test-channel'),
      },
    });

    expect(response.statusCode).toBe(400);

    await app.close();
  });

  test('HEAD /api/chart-cache/:cacheKey returns 200 when key exists', async () => {
    mockHasChartCache.mockResolvedValue(true);

    const app = Fastify({ logger: false });
    registerChartCacheRoutes(app);

    const response = await app.inject({
      method: 'HEAD',
      url: '/api/chart-cache/qc-exists',
      headers: {
        cookie: buildJwtCookie('test-channel'),
      },
    });

    expect(response.statusCode).toBe(200);
    expect(response.headers['x-cache']).toBe('HIT');

    await app.close();
  });

  test('HEAD /api/chart-cache/:cacheKey returns 404 when key missing', async () => {
    mockHasChartCache.mockResolvedValue(false);

    const app = Fastify({ logger: false });
    registerChartCacheRoutes(app);

    const response = await app.inject({
      method: 'HEAD',
      url: '/api/chart-cache/qc-missing',
      headers: {
        cookie: buildJwtCookie('test-channel'),
      },
    });

    expect(response.statusCode).toBe(404);
    expect(response.headers['x-cache']).toBe('MISS');

    await app.close();
  });
});

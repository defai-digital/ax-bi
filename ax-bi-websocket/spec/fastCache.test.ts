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

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const mockRedisGet = jest.fn<(key: string) => Promise<string | null>>();
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const mockRedisExists = jest.fn<(key: string) => Promise<number>>();
const mockRedisOn = jest.fn();

jest.mock('ioredis', () => {
  return jest.fn().mockImplementation(() => ({
    get: mockRedisGet,
    exists: mockRedisExists,
    on: mockRedisOn,
    quit: jest.fn<() => Promise<void>>().mockResolvedValue(undefined),
    disconnect: jest.fn(),
    ping: jest.fn<() => Promise<string>>().mockResolvedValue('PONG'),
  }));
});

// Mock hot-shots to prevent actual StatsD connections
jest.mock('hot-shots', () => {
  return jest.fn().mockImplementation(() => ({
    increment: jest.fn(),
    timing: jest.fn(),
    errorHandler: jest.fn(),
  }));
});

import {
  getChartCache,
  hasChartCache,
  initFastCacheRedis,
  resetFastCacheRedis,
  closeFastCacheRedis,
} from '../src/fastCache';

describe('fastCache', () => {
  beforeEach(() => {
    mockRedisGet.mockClear();
    mockRedisExists.mockClear();
    resetFastCacheRedis();
  });

  describe('getChartCache', () => {
    test('returns cached JSON string on cache hit', async () => {
      const cachedJson = '{"result":[{"data":[{"x":1}]}]}';
      mockRedisGet.mockResolvedValue(cachedJson);

      const redis = initFastCacheRedis();
      expect(redis).not.toBeNull();

      const result = await getChartCache('abc123');
      expect(result).toEqual(cachedJson);
      expect(mockRedisGet).toHaveBeenCalledWith('fc:abc123');
    });

    test('returns null on cache miss', async () => {
      mockRedisGet.mockResolvedValue(null);

      initFastCacheRedis();
      const result = await getChartCache('missing-key');
      expect(result).toBeNull();
      expect(mockRedisGet).toHaveBeenCalledWith('fc:missing-key');
    });

    test('returns null when Redis errors occur', async () => {
      mockRedisGet.mockRejectedValue(new Error('Redis connection lost'));

      initFastCacheRedis();
      const result = await getChartCache('error-key');
      expect(result).toBeNull();
    });
  });

  describe('hasChartCache', () => {
    test('returns true when key exists', async () => {
      mockRedisExists.mockResolvedValue(1);

      initFastCacheRedis();
      const result = await hasChartCache('existing-key');
      expect(result).toBe(true);
      expect(mockRedisExists).toHaveBeenCalledWith('fc:existing-key');
    });

    test('returns false when key does not exist', async () => {
      mockRedisExists.mockResolvedValue(0);

      initFastCacheRedis();
      const result = await hasChartCache('missing-key');
      expect(result).toBe(false);
    });

    test('returns false when Redis errors occur', async () => {
      mockRedisExists.mockRejectedValue(new Error('Redis error'));

      initFastCacheRedis();
      const result = await hasChartCache('error-key');
      expect(result).toBe(false);
    });
  });

  describe('closeFastCacheRedis', () => {
    test('closes connection gracefully', async () => {
      initFastCacheRedis();
      await expect(closeFastCacheRedis()).resolves.not.toThrow();
    });
  });
});

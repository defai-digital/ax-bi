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
import Redis from 'ioredis';
import StatsD from 'hot-shots';
import { createLogger } from './logger';
import { buildConfig } from './config';
import { buildRedisOpts } from './redisOpts';

const opts = buildConfig();

const logger = createLogger({
  silent: process.env.NODE_ENV === 'test',
  logLevel: opts.logLevel,
  logToFile: opts.logToFile,
  logFilename: opts.logFilename,
});

const statsd = new StatsD({
  ...opts.statsd,
  errorHandler: (e: Error) => {
    logger.error(e);
  },
});

let fastCacheRedis: Redis | null = null;

/**
 * Initialize the dedicated Redis connection for fast-cache reads.
 * Uses the same Redis configuration as the event stream connection
 * but maintains a separate connection to avoid blocking the stream reader.
 */
export const initFastCacheRedis = (): Redis | null => {
  if (!opts.fastCacheEnabled) {
    logger.info('Fast cache gateway is disabled');
    return null;
  }

  if (fastCacheRedis) {
    return fastCacheRedis;
  }

  const redisOpts = buildRedisOpts(opts.redis);
  fastCacheRedis = new Redis({
    ...redisOpts,
    enableReadyCheck: true,
    lazyConnect: false,
  });

  fastCacheRedis.on('error', (err: Error) => {
    logger.error(`Fast cache Redis connection error: ${err.message}`);
    statsd.increment('fast_cache_redis_error');
  });

  fastCacheRedis.on('connect', () => {
    logger.info('Fast cache Redis connection established');
  });

  return fastCacheRedis;
};

/**
 * Returns the fast-cache Redis connection, initializing it lazily if needed.
 */
export const getFastCacheRedis = (): Redis | null => {
  if (!opts.fastCacheEnabled) {
    return null;
  }
  if (!fastCacheRedis) {
    return initFastCacheRedis();
  }
  return fastCacheRedis;
};

/**
 * Lightweight readiness probe against the fast-cache Redis connection.
 * Returns false when the feature is disabled or the PING fails.
 */
export const pingFastCacheRedis = async (): Promise<boolean> => {
  const redis = getFastCacheRedis();
  if (!redis) {
    return false;
  }
  try {
    const reply = await redis.ping();
    return reply === 'PONG';
  } catch (err) {
    logger.error(`Fast cache Redis PING failed: ${err}`);
    return false;
  }
};

/**
 * Retrieves a cached chart data JSON string from Redis.
 * Returns null if the key is not found or the feature is disabled.
 */
export const getChartCache = async (
  cacheKey: string,
): Promise<string | null> => {
  const redis = getFastCacheRedis();
  if (!redis) return null;

  const fullKey = `${opts.fastCacheKeyPrefix}${cacheKey}`;
  const start = Date.now();

  try {
    const value = await redis.get(fullKey);
    const elapsed = Date.now() - start;
    statsd.timing('fast_cache_get_latency', elapsed);

    if (value) {
      statsd.increment('fast_cache_hit');
      logger.debug(
        `Fast cache HIT: key=${fullKey}, size=${value.length}, latency=${elapsed}ms`,
      );
      return value;
    }

    statsd.increment('fast_cache_miss');
    logger.debug(`Fast cache MISS: key=${fullKey}, latency=${elapsed}ms`);
    return null;
  } catch (err) {
    statsd.increment('fast_cache_get_error');
    logger.error(`Fast cache GET error for key ${fullKey}: ${err}`);
    return null;
  }
};

/**
 * Checks whether a fast-cache entry exists for the given key.
 */
export const hasChartCache = async (cacheKey: string): Promise<boolean> => {
  const redis = getFastCacheRedis();
  if (!redis) return false;

  const fullKey = `${opts.fastCacheKeyPrefix}${cacheKey}`;
  try {
    return (await redis.exists(fullKey)) === 1;
  } catch (err) {
    logger.error(`Fast cache EXISTS error for key ${fullKey}: ${err}`);
    return false;
  }
};

/**
 * Disconnect the fast-cache Redis connection (for graceful shutdown).
 */
export const closeFastCacheRedis = async (): Promise<void> => {
  if (fastCacheRedis) {
    try {
      await fastCacheRedis.quit();
    } catch {
      fastCacheRedis.disconnect();
    }
    fastCacheRedis = null;
    logger.info('Fast cache Redis connection closed');
  }
};

/**
 * Reset the fast-cache Redis connection (for testing).
 * Disconnects any live client before clearing the module reference.
 */
export const resetFastCacheRedis = (): void => {
  if (fastCacheRedis) {
    try {
      fastCacheRedis.disconnect();
    } catch {
      // Best-effort cleanup for tests.
    }
    fastCacheRedis = null;
  }
};

// Export opts and statsd for use by route handlers that need them
export { opts as fastCacheOpts, statsd as fastCacheStatsd };

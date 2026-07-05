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
import { FastifyInstance, FastifyRequest, FastifyReply } from 'fastify';
import jwt, { Algorithm } from 'jsonwebtoken';
import { parse } from 'cookie';
import {
  getChartCache,
  hasChartCache,
  fastCacheOpts,
  fastCacheStatsd,
} from '../fastCache';
import { createLogger } from '../logger';

const opts = fastCacheOpts;

const logger = createLogger({
  silent: process.env.NODE_ENV === 'test',
  logLevel: opts.logLevel,
  logToFile: opts.logToFile,
  logFilename: opts.logFilename,
});

interface ChartCacheParams {
  cacheKey: string;
}

const hasInvalidCacheKeyCharacter = (cacheKey: string): boolean =>
  [...cacheKey].some(char => /\s/.test(char) || char.charCodeAt(0) <= 31);

const isValidCacheKey = (cacheKey: string | undefined): cacheKey is string => {
  if (!cacheKey) {
    return false;
  }
  return cacheKey.length <= 256 && !hasInvalidCacheKeyCharacter(cacheKey);
};

/**
 * Validates the JWT cookie from an HTTP request.
 * Returns the channel ID from the JWT payload, or null if invalid.
 */
const validateJwtCookie = (request: FastifyRequest): string | null => {
  const cookieHeader = request.headers.cookie as string | undefined;
  if (!cookieHeader) return null;

  const cookies = parse(cookieHeader);
  const token = cookies[opts.jwtCookieName];
  if (!token) return null;

  try {
    const jwtPayload = jwt.verify(token, opts.jwtSecret, {
      algorithms: opts.jwtAlgorithms as Algorithm[],
      complete: false,
    }) as Record<string, string>;
    return jwtPayload[opts.jwtChannelIdKey] ?? null;
  } catch (err) {
    logger.warn(`JWT validation failed: ${(err as Error).message}`);
    return null;
  }
};

/**
 * Pre-handler hook that validates the JWT cookie for protected routes.
 * Returns 401 if the JWT is missing or invalid.
 */
const jwtAuthPreHandler = async (
  request: FastifyRequest,
  reply: FastifyReply,
): Promise<void> => {
  // Skip auth check if fast cache is disabled
  if (!opts.fastCacheEnabled) {
    reply.status(503).send({ error: 'Fast cache gateway is disabled' });
    return;
  }

  const channelId = validateJwtCookie(request);
  if (!channelId) {
    fastCacheStatsd.increment('fast_cache_auth_failed');
    reply.status(401).send({ error: 'Authentication required' });
  }
};

/**
 * GET /api/chart-cache/:cacheKey
 *
 * Retrieves cached chart data from Redis. Returns the raw JSON string
 * that was written by the Python backend, bypassing Flask entirely.
 *
 * Response headers:
 *   - X-Cache: HIT | MISS (for observability)
 *   - Content-Type: application/json (on HIT)
 *
 * On cache miss, returns 404 so the frontend can fall back to the
 * Python API for a fresh query.
 */
const handleGetChartCache = async (
  request: FastifyRequest<{ Params: ChartCacheParams }>,
  reply: FastifyReply,
): Promise<void> => {
  const { cacheKey } = request.params;

  // Validate cache key format to prevent Redis injection via crafted keys
  if (!isValidCacheKey(cacheKey)) {
    reply.status(400).send({ error: 'Invalid cache key' });
    return;
  }

  fastCacheStatsd.increment('fast_cache_request');

  const value = await getChartCache(cacheKey);

  if (value) {
    fastCacheStatsd.increment('fast_cache_served');
    reply
      .status(200)
      .header('X-Cache', 'HIT')
      .header('Content-Type', 'application/json; charset=utf-8')
      .send(value);
    return;
  }

  fastCacheStatsd.increment('fast_cache_not_found');
  reply.status(404).header('X-Cache', 'MISS').send({
    error: 'Cache miss',
    cacheKey,
  });
};

/**
 * HEAD /api/chart-cache/:cacheKey
 *
 * Lightweight existence check without returning the full payload.
 * Useful for the frontend to decide whether to use the gateway or
 * fall back to the Python API without transferring the full payload.
 */
const handleHeadChartCache = async (
  request: FastifyRequest<{ Params: ChartCacheParams }>,
  reply: FastifyReply,
): Promise<void> => {
  const { cacheKey } = request.params;

  if (!isValidCacheKey(cacheKey)) {
    reply.status(400).send();
    return;
  }

  const exists = await hasChartCache(cacheKey);
  reply
    .status(exists ? 200 : 404)
    .header('X-Cache', exists ? 'HIT' : 'MISS')
    .send();
};

/**
 * Register all chart-cache gateway routes on the Fastify instance.
 */
export const registerChartCacheRoutes = (app: FastifyInstance): void => {
  if (!opts.fastCacheEnabled) {
    logger.info('Fast cache gateway routes are disabled');
    return;
  }

  // GET /api/chart-cache/:cacheKey - retrieve cached chart data
  // exposeHeadRoutes: false prevents Fastify from auto-generating a HEAD
  // route, since we register a custom HEAD handler with different logic.
  app.get<{ Params: ChartCacheParams }>(
    '/api/chart-cache/:cacheKey',
    { preHandler: jwtAuthPreHandler, exposeHeadRoute: false },
    handleGetChartCache,
  );

  // HEAD /api/chart-cache/:cacheKey - lightweight existence check
  app.head<{ Params: ChartCacheParams }>(
    '/api/chart-cache/:cacheKey',
    { preHandler: jwtAuthPreHandler },
    handleHeadChartCache,
  );

  logger.info('Fast cache gateway routes registered');
};

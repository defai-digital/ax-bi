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
import { FastifyInstance } from 'fastify';
import { activeSocketCount } from '../state';
import { pingFastCacheRedis, fastCacheOpts } from '../fastCache';

/**
 * Enhanced health/readiness endpoint that reports WebSocket connection count
 * and a lightweight Redis readiness probe (when fast-cache is enabled).
 */
export const registerHealthRoutes = (app: FastifyInstance): void => {
  app.get('/health', async (_request, reply) => {
    let redisOk: boolean | null = null;
    if (fastCacheOpts.fastCacheEnabled) {
      redisOk = await pingFastCacheRedis();
    }

    const body = {
      status: redisOk === false ? 'degraded' : 'ok',
      activeConnections: activeSocketCount(),
      redis: redisOk === null ? 'disabled' : redisOk ? 'ok' : 'unavailable',
      timestamp: new Date().toISOString(),
    };

    // Still return 200 for liveness when Redis is down so orchestrators that
    // only check /health for process liveness don't thrash restarts; readiness
    // can be inferred from the redis field / degraded status.
    return reply.status(200).send(body);
  });

  app.head('/health', async (_request, reply) => {
    reply.status(200).send();
  });
};

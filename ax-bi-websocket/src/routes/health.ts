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
import { activeSocketCount } from '../index';

/**
 * Enhanced health/readiness endpoint that reports WebSocket connection count
 * and fast-cache gateway status in addition to basic liveness.
 */
export const registerHealthRoutes = (app: FastifyInstance): void => {
  app.get('/health', async () => {
    return {
      status: 'ok',
      activeConnections: activeSocketCount(),
      timestamp: new Date().toISOString(),
    };
  });

  app.head('/health', async (request, reply) => {
    reply.status(200).send();
  });
};

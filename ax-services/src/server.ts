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
import Fastify, { FastifyInstance } from 'fastify';

import { ServiceConfig } from './config';
import {
  HealthResponseContract,
  healthResponseSchema,
  ReadinessResponseContract,
  readinessResponseSchema,
  RUNTIME_CONTRACT_VERSION,
} from './contracts/runtime';
import { SupersetHealthClient } from './supersetClient';

export function buildServer(
  config: ServiceConfig,
  supersetClient: SupersetHealthClient,
): FastifyInstance {
  const server = Fastify({
    logger: config.logLevel !== 'silent',
  });

  server.get(
    '/health',
    {
      schema: {
        response: {
          200: healthResponseSchema,
        },
      },
    },
    async (): Promise<HealthResponseContract> => ({
      contractVersion: RUNTIME_CONTRACT_VERSION,
      service: 'ax-services',
      status: 'ok',
    }),
  );

  server.get(
    '/ready',
    {
      schema: {
        response: {
          200: readinessResponseSchema,
          503: readinessResponseSchema,
        },
      },
    },
    async (request, reply): Promise<ReadinessResponseContract> => {
      const superset = await supersetClient.checkHealth();
      const ready = superset.ok;

      return reply.status(ready ? 200 : 503).send({
        contractVersion: RUNTIME_CONTRACT_VERSION,
        service: 'ax-services',
        status: ready ? 'ready' : 'not_ready',
        dependencies: {
          superset,
        },
      });
    },
  );

  return server;
}

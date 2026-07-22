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
import type { FastifyInstance } from 'fastify';

import { buildConfig } from './config';
import { createLogger, type ServiceLogger } from './logger';
import { buildServer } from './server';
import { AxBIClient } from './axbiClient';

let shuttingDown = false;

function installProcessHandlers(logger: ServiceLogger): void {
  process.on('unhandledRejection', (reason: unknown) => {
    logger.error('Unhandled promise rejection', { error: reason });
    process.exit(1);
  });
  process.on('uncaughtException', (error: unknown) => {
    logger.error('Uncaught exception', { error });
    process.exit(1);
  });
}

function installShutdownHandlers(
  logger: ServiceLogger,
  server: FastifyInstance,
): void {
  const shutdown = async (signal: string): Promise<void> => {
    if (shuttingDown) {
      return;
    }
    shuttingDown = true;
    logger.info(`Received ${signal}, shutting down gracefully`);
    try {
      await server.close();
      process.exit(0);
    } catch (error) {
      logger.error('Error during graceful shutdown', { error });
      process.exit(1);
    }
  };

  process.on('SIGTERM', () => {
    void shutdown('SIGTERM');
  });
  process.on('SIGINT', () => {
    void shutdown('SIGINT');
  });
}

export async function start(): Promise<void> {
  let logger = createLogger('error');

  try {
    const config = buildConfig();
    logger = createLogger(config.logLevel);
    installProcessHandlers(logger);

    const axbiClient = new AxBIClient(config);
    const server = buildServer(config, axbiClient);

    await server.listen({ host: config.host, port: config.port });
    logger.info('ax-services started', {
      host: config.host,
      port: config.port,
    });

    installShutdownHandlers(logger, server);
  } catch (error) {
    logger.error('ax-services failed to start', { error });
    process.exit(1);
  }
}

if (require.main === module) {
  void start();
}

export { buildConfig } from './config';
export { buildServer } from './server';
export { AxBIClient } from './axbiClient';

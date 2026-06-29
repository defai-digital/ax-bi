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
import { buildConfig } from './config';
import { createLogger } from './logger';
import { buildServer } from './server';
import { SupersetClient } from './supersetClient';

export async function start(): Promise<void> {
  const config = buildConfig();
  const logger = createLogger(config.logLevel);
  const supersetClient = new SupersetClient(config);
  const server = buildServer(config, supersetClient);

  try {
    await server.listen({ host: config.host, port: config.port });
    logger.info('ax-services started', {
      host: config.host,
      port: config.port,
    });
  } catch (error) {
    logger.error('ax-services failed to start', { error });
    process.exitCode = 1;
  }
}

if (require.main === module) {
  void start();
}

export { buildConfig } from './config';
export { buildServer } from './server';
export { SupersetClient } from './supersetClient';

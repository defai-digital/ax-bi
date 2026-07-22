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
import { RedisOptions } from 'ioredis';
import { checkServerIdentity, PeerCertificate } from 'tls';

import { RedisConfig } from './config';

/**
 * Build ioredis connection options from the shared RedisConfig shape.
 * Used by the stream reader, XRANGE catch-up connection, and fast-cache.
 */
export const buildRedisOpts = (baseConfig: RedisConfig): RedisOptions => {
  const redisOpts: RedisOptions = {
    port: baseConfig.port,
    host: baseConfig.host,
    db: baseConfig.db,
  };

  if (baseConfig.password !== '') {
    redisOpts.username = baseConfig.username;
    redisOpts.password = baseConfig.password;
  }

  if (baseConfig.ssl) {
    redisOpts.tls = {
      checkServerIdentity: (
        hostname: string,
        cert: PeerCertificate,
      ): Error | undefined => {
        if (baseConfig.validateHostname) {
          return checkServerIdentity(hostname, cert);
        }
      },
    };
  }

  return redisOpts;
};

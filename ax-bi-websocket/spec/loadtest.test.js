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
const { expect, test } = require('@jest/globals');

const { loadConfig, pushData } = require('../utils/loadtest');

test('loadConfig() falls back to the example config when local config is missing', () => {
  const config = loadConfig();

  expect(config.jwtSecret).toBe('CHANGE-ME');
  expect(config.redisStreamPrefix).toBe('async-events-');
});

test('pushData() writes channel events and firehose events', () => {
  const calls = [];
  const redis = {
    xadd: (...args) => {
      calls.push(args);
      return { then: () => undefined };
    },
  };
  const config = {
    redisStreamPrefix: 'events-',
  };

  pushData(redis, config);

  expect(calls).toHaveLength(512);
  expect(calls[0]).toEqual([
    'events-0',
    'MAXLEN',
    1000,
    '*',
    'data',
    expect.stringContaining('"channel_id":"0"'),
  ]);
  expect(calls[1]).toEqual([
    'events-full',
    'MAXLEN',
    100000,
    '*',
    'data',
    expect.stringContaining('"channel_id":"0"'),
  ]);
});

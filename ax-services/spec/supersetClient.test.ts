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
import { afterEach, expect, test } from '@jest/globals';

import { buildConfig } from '../src/config';
import { SupersetClient } from '../src/supersetClient';

const originalFetch = global.fetch;

afterEach(() => {
  global.fetch = originalFetch;
});

test('checkHealth returns Superset status and forwards request ID', async () => {
  let seenInput: RequestInfo | URL | undefined;
  let seenInit: RequestInit | undefined;
  global.fetch = async (input, init) => {
    seenInput = input;
    seenInit = init;
    return new Response('OK', { status: 200 });
  };
  const client = new SupersetClient(buildConfig({}));

  const result = await client.checkHealth('request-abc');

  expect(result).toEqual({
    ok: true,
    statusCode: 200,
    url: 'http://127.0.0.1:8088/health',
  });
  expect(seenInput).toBe('http://127.0.0.1:8088/health');
  expect(seenInit?.headers).toEqual({
    'x-request-id': 'request-abc',
  });
});

test('checkHealth returns an error result when fetch fails', async () => {
  global.fetch = async () => {
    throw new Error('connect failed');
  };
  const client = new SupersetClient(buildConfig({}));

  const result = await client.checkHealth();

  expect(result).toEqual({
    ok: false,
    error: 'connect failed',
    url: 'http://127.0.0.1:8088/health',
  });
});

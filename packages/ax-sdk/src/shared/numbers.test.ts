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

import { normalizeRetryCount, normalizeTimeoutMs } from './numbers.js';

test('normalizeTimeoutMs applies defaults and accepts valid timeouts', () => {
  expect(normalizeTimeoutMs(undefined, 30_000)).toBe(30_000);
  expect(normalizeTimeoutMs(1, 30_000)).toBe(1);
  expect(normalizeTimeoutMs(2_147_483_647, 30_000)).toBe(2_147_483_647);
});

test('normalizeTimeoutMs rejects invalid timeout values', () => {
  expect(() => normalizeTimeoutMs(0, 30_000)).toThrow(
    'timeout must be between 1 and 2147483647',
  );
  expect(() => normalizeTimeoutMs(2_147_483_648, 30_000)).toThrow(
    'timeout must be between 1 and 2147483647',
  );
  expect(() => normalizeTimeoutMs(1.5, 30_000)).toThrow(
    'timeout must be a safe integer',
  );
  expect(() => normalizeTimeoutMs(Number.NaN, 30_000)).toThrow(
    'timeout must be a safe integer',
  );
});

test('normalizeRetryCount applies defaults and accepts valid retry counts', () => {
  expect(normalizeRetryCount(undefined, 3)).toBe(3);
  expect(normalizeRetryCount(0, 3)).toBe(0);
  expect(normalizeRetryCount(5, 3)).toBe(5);
});

test('normalizeRetryCount rejects invalid retry counts', () => {
  expect(() => normalizeRetryCount(-1, 3)).toThrow(
    'retries must be a non-negative integer',
  );
  expect(() => normalizeRetryCount(1.5, 3)).toThrow(
    'retries must be a safe integer',
  );
  expect(() => normalizeRetryCount(Number.POSITIVE_INFINITY, 3)).toThrow(
    'retries must be a safe integer',
  );
});

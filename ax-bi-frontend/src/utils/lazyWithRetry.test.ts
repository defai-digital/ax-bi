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
import {
  CHUNK_LOAD_RELOAD_KEY,
  isChunkLoadError,
  lazyWithRetry,
  recoverFromChunkLoadError,
} from './lazyWithRetry';

test('lazyWithRetry returns a lazy component type', () => {
  const Comp = () => null;
  const LazyComp = lazyWithRetry(async () => ({ default: Comp }));
  expect(typeof LazyComp).toBe('object');
  expect(LazyComp).toHaveProperty('$$typeof');
});

test('isChunkLoadError detects webpack chunk failures', () => {
  const err = new Error(
    'Loading chunk ChartList failed.\n(timeout: http://127.0.0.1:9000/static/assets/ChartList.81383bd3.chunk.js)',
  );
  err.name = 'ChunkLoadError';
  expect(isChunkLoadError(err)).toBe(true);
  expect(isChunkLoadError(new Error('boom'))).toBe(false);
  expect(isChunkLoadError(null)).toBe(false);
});

test('recoverFromChunkLoadError reloads once', () => {
  const reload = jest.fn();
  const originalLocation = window.location;
  Object.defineProperty(window, 'location', {
    configurable: true,
    value: { ...originalLocation, reload },
  });
  window.sessionStorage.clear();

  const err = new Error('Loading chunk ChartList failed.');
  err.name = 'ChunkLoadError';

  expect(recoverFromChunkLoadError(err)).toBe(true);
  expect(window.sessionStorage.getItem(CHUNK_LOAD_RELOAD_KEY)).toBe('1');
  expect(reload).toHaveBeenCalledTimes(1);

  // Second attempt does not loop
  expect(recoverFromChunkLoadError(err)).toBe(false);
  expect(reload).toHaveBeenCalledTimes(1);

  Object.defineProperty(window, 'location', {
    configurable: true,
    value: originalLocation,
  });
});

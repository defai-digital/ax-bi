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
import { afterEach, expect, jest, test } from '@jest/globals';

import { createLogger } from '../src/logger';

afterEach(() => {
  jest.restoreAllMocks();
});

test('logger emits info messages at info level', () => {
  const log = jest.spyOn(console, 'log').mockImplementation(() => {});
  const error = jest.spyOn(console, 'error').mockImplementation(() => {});
  const logger = createLogger('info');

  logger.info('service started', { port: 5010 });

  expect(log).toHaveBeenCalledWith(
    JSON.stringify({
      level: 'info',
      message: 'service started',
      port: 5010,
    }),
  );
  expect(error).not.toHaveBeenCalled();
});

test('logger suppresses info messages at error level', () => {
  const log = jest.spyOn(console, 'log').mockImplementation(() => {});
  const error = jest.spyOn(console, 'error').mockImplementation(() => {});
  const logger = createLogger('error');

  logger.info('service started');
  logger.error('service failed');

  expect(log).not.toHaveBeenCalled();
  expect(error).toHaveBeenCalledWith(
    JSON.stringify({
      level: 'error',
      message: 'service failed',
    }),
  );
});

test('logger suppresses all messages at silent level', () => {
  const log = jest.spyOn(console, 'log').mockImplementation(() => {});
  const error = jest.spyOn(console, 'error').mockImplementation(() => {});
  const logger = createLogger('silent');

  logger.info('service started');
  logger.error('service failed');

  expect(log).not.toHaveBeenCalled();
  expect(error).not.toHaveBeenCalled();
});

test('logger serializes bigint context values without throwing', () => {
  const log = jest.spyOn(console, 'log').mockImplementation(() => {});
  const logger = createLogger('info');

  expect(() =>
    logger.info('request completed', { elapsedNanos: 123n }),
  ).not.toThrow();

  expect(log).toHaveBeenCalledWith(
    JSON.stringify({
      level: 'info',
      message: 'request completed',
      elapsedNanos: '123',
    }),
  );
});

test('logger serializes circular context values without throwing', () => {
  const log = jest.spyOn(console, 'log').mockImplementation(() => {});
  const logger = createLogger('info');
  const context: { requestId: string; self?: unknown } = {
    requestId: 'request-abc',
  };
  context.self = context;

  expect(() => logger.info('request completed', { context })).not.toThrow();

  expect(log).toHaveBeenCalledWith(
    JSON.stringify({
      level: 'info',
      message: 'request completed',
      context: {
        requestId: 'request-abc',
        self: '[Circular]',
      },
    }),
  );
});

test('logger falls back when context JSON serialization fails', () => {
  const log = jest.spyOn(console, 'log').mockImplementation(() => {});
  const logger = createLogger('info');

  expect(() =>
    logger.info('request completed', {
      context: {
        toJSON() {
          throw new Error('cannot serialize context');
        },
      },
    }),
  ).not.toThrow();

  expect(log).toHaveBeenCalledWith(
    JSON.stringify({
      level: 'info',
      message: 'request completed',
      serializationError: 'cannot serialize context',
    }),
  );
});

test('logger falls back when context normalization fails', () => {
  const log = jest.spyOn(console, 'log').mockImplementation(() => {});
  const logger = createLogger('info');
  const context = {};

  Object.defineProperty(context, 'broken', {
    enumerable: true,
    get() {
      throw new Error('cannot read context');
    },
  });

  expect(() =>
    logger.info('request completed', context as Record<string, unknown>),
  ).not.toThrow();

  expect(log).toHaveBeenCalledWith(
    JSON.stringify({
      level: 'info',
      message: 'request completed',
      serializationError: 'cannot read context',
    }),
  );
});

test('logger preserves fixed metadata when context includes reserved fields', () => {
  const log = jest.spyOn(console, 'log').mockImplementation(() => {});
  const logger = createLogger('info');

  logger.info('service started', {
    level: 'error',
    message: 'spoofed message',
    requestId: 'request-abc',
  });

  expect(log).toHaveBeenCalledWith(
    JSON.stringify({
      level: 'info',
      message: 'service started',
      requestId: 'request-abc',
    }),
  );
});

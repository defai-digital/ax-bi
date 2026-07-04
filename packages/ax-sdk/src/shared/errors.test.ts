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
  AxBIError,
  AxBIAuthError,
  AxBIForbiddenError,
  AxBINotFoundError,
  AxBIValidationError,
  AxBIConflictError,
  AxBIRateLimitError,
  errorFromStatus,
} from './errors.js';

describe('AxBIError hierarchy', () => {
  test('base AxBIError carries statusCode and responseBody', () => {
    const err = new AxBIError('test error', {
      statusCode: 500,
      responseBody: { detail: 'oops' },
    });
    expect(err.name).toBe('AxBIError');
    expect(err.message).toBe('test error');
    expect(err.statusCode).toBe(500);
    expect(err.responseBody).toEqual({ detail: 'oops' });
    expect(err).toBeInstanceOf(Error);
    expect(err).toBeInstanceOf(AxBIError);
  });

  test('AxBIAuthError defaults to 401', () => {
    const err = new AxBIAuthError();
    expect(err.name).toBe('AxBIAuthError');
    expect(err.statusCode).toBe(401);
    expect(err.message).toBe('Authentication failed');
  });

  test('AxBIForbiddenError defaults to 403', () => {
    const err = new AxBIForbiddenError();
    expect(err.name).toBe('AxBIForbiddenError');
    expect(err.statusCode).toBe(403);
  });

  test('AxBINotFoundError defaults to 404', () => {
    const err = new AxBINotFoundError();
    expect(err.name).toBe('AxBINotFoundError');
    expect(err.statusCode).toBe(404);
  });

  test('AxBIValidationError defaults to 422', () => {
    const err = new AxBIValidationError();
    expect(err.name).toBe('AxBIValidationError');
    expect(err.statusCode).toBe(422);
  });

  test('AxBIConflictError defaults to 409', () => {
    const err = new AxBIConflictError();
    expect(err.name).toBe('AxBIConflictError');
    expect(err.statusCode).toBe(409);
  });

  test('AxBIRateLimitError carries retryAfterMs', () => {
    const err = new AxBIRateLimitError('slow down', { retryAfterMs: 5000 });
    expect(err.name).toBe('AxBIRateLimitError');
    expect(err.statusCode).toBe(429);
    expect(err.retryAfterMs).toBe(5000);
  });
});

describe('errorFromStatus', () => {
  test('maps 401 to AxBIAuthError', () => {
    const err = errorFromStatus(401, null);
    expect(err).toBeInstanceOf(AxBIAuthError);
  });

  test('maps 403 to AxBIForbiddenError', () => {
    const err = errorFromStatus(403, null);
    expect(err).toBeInstanceOf(AxBIForbiddenError);
  });

  test('maps 404 to AxBINotFoundError', () => {
    const err = errorFromStatus(404, null);
    expect(err).toBeInstanceOf(AxBINotFoundError);
  });

  test('maps 409 to AxBIConflictError', () => {
    const err = errorFromStatus(409, null);
    expect(err).toBeInstanceOf(AxBIConflictError);
  });

  test('maps 422 to AxBIValidationError', () => {
    const err = errorFromStatus(422, null);
    expect(err).toBeInstanceOf(AxBIValidationError);
  });

  test('maps 429 to AxBIRateLimitError', () => {
    const err = errorFromStatus(429, null);
    expect(err).toBeInstanceOf(AxBIRateLimitError);
  });

  test('maps 500 to AxBIError', () => {
    const err = errorFromStatus(500, null);
    expect(err).toBeInstanceOf(AxBIError);
    expect(err.statusCode).toBe(500);
  });

  test('maps unknown 4xx to AxBIError with custom message', () => {
    const err = errorFromStatus(418, null, 'teapot');
    expect(err).toBeInstanceOf(AxBIError);
    expect(err.message).toBe('teapot');
    expect(err.statusCode).toBe(418);
  });
});

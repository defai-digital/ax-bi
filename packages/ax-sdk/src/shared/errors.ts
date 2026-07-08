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

/**
 * Base error for all AX BI SDK errors.
 * Provides structured context about the failure.
 */
export class AxBIError extends Error {
  public readonly statusCode?: number;
  public readonly responseBody?: unknown;

  constructor(
    message: string,
    options?: {
      statusCode?: number;
      responseBody?: unknown;
      cause?: Error;
    },
  ) {
    super(message, { cause: options?.cause });
    this.name = 'AxBIError';
    this.statusCode = options?.statusCode;
    this.responseBody = options?.responseBody;
  }
}

/** Authentication failure (401). */
export class AxBIAuthError extends AxBIError {
  constructor(message = 'Authentication failed', options?: { responseBody?: unknown; cause?: Error }) {
    super(message, { statusCode: 401, ...options });
    this.name = 'AxBIAuthError';
  }
}

/** The authenticated user lacks permission (403). */
export class AxBIForbiddenError extends AxBIError {
  constructor(message = 'Forbidden', options?: { responseBody?: unknown; cause?: Error }) {
    super(message, { statusCode: 403, ...options });
    this.name = 'AxBIForbiddenError';
  }
}

/** Requested resource does not exist (404). */
export class AxBINotFoundError extends AxBIError {
  constructor(message = 'Not found', options?: { responseBody?: unknown; cause?: Error }) {
    super(message, { statusCode: 404, ...options });
    this.name = 'AxBINotFoundError';
  }
}

/** Request body failed server-side validation (422). */
export class AxBIValidationError extends AxBIError {
  constructor(message = 'Validation error', options?: { responseBody?: unknown; cause?: Error }) {
    super(message, { statusCode: 422, ...options });
    this.name = 'AxBIValidationError';
  }
}

/** Conflict with existing resource (409). */
export class AxBIConflictError extends AxBIError {
  constructor(message = 'Conflict', options?: { responseBody?: unknown; cause?: Error }) {
    super(message, { statusCode: 409, ...options });
    this.name = 'AxBIConflictError';
  }
}

/** Rate limit exceeded (429). */
export class AxBIRateLimitError extends AxBIError {
  public readonly retryAfterMs?: number;

  constructor(
    message = 'Rate limit exceeded',
    options?: { responseBody?: unknown; retryAfterMs?: number; cause?: Error },
  ) {
    super(message, { statusCode: 429, ...options });
    this.name = 'AxBIRateLimitError';
    this.retryAfterMs = options?.retryAfterMs;
  }
}

/** Map an HTTP status code to the appropriate AxBIError subclass. */
export function errorFromStatus(
  status: number,
  body: unknown,
  message?: string,
  options?: { retryAfterMs?: number },
): AxBIError {
  switch (status) {
    case 401:
      return new AxBIAuthError(message ?? 'Authentication failed', { responseBody: body });
    case 403:
      return new AxBIForbiddenError(message ?? 'Forbidden', { responseBody: body });
    case 404:
      return new AxBINotFoundError(message ?? 'Not found', { responseBody: body });
    case 409:
      return new AxBIConflictError(message ?? 'Conflict', { responseBody: body });
    case 422:
      return new AxBIValidationError(message ?? 'Validation error', { responseBody: body });
    case 429:
      return new AxBIRateLimitError(message ?? 'Rate limit exceeded', {
        responseBody: body,
        retryAfterMs: options?.retryAfterMs,
      });
    default:
      if (status >= 500) {
        return new AxBIError(`Server error (${status})`, { statusCode: status, responseBody: body });
      }
      return new AxBIError(message ?? `Request failed (${status})`, {
        statusCode: status,
        responseBody: body,
      });
  }
}

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

const MAX_TIMEOUT_MS = 2_147_483_647;

/** Normalize a timeout value before passing it to AbortSignal.timeout. */
export function normalizeTimeoutMs(
  value: number | undefined,
  defaultValue: number,
  name = 'timeout',
): number {
  const normalized = normalizeIntegerOption(value, defaultValue, name);
  if (normalized < 1 || normalized > MAX_TIMEOUT_MS) {
    throw new Error(`${name} must be between 1 and ${MAX_TIMEOUT_MS}`);
  }
  return normalized;
}

/** Normalize a retry count used by bounded request retry loops. */
export function normalizeRetryCount(
  value: number | undefined,
  defaultValue: number,
  name = 'retries',
): number {
  const normalized = normalizeIntegerOption(value, defaultValue, name);
  if (normalized < 0) {
    throw new Error(`${name} must be a non-negative integer`);
  }
  return normalized;
}

function normalizeIntegerOption(
  value: number | undefined,
  defaultValue: number,
  name: string,
): number {
  const normalized = value ?? defaultValue;
  if (!Number.isSafeInteger(normalized)) {
    throw new Error(`${name} must be a safe integer`);
  }
  return normalized;
}

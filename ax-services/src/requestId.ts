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

const MAX_REQUEST_ID_LENGTH = 128;
const REQUEST_ID_PATTERN = /^[A-Za-z0-9._~-]+$/;

export function normalizeRequestId(value: string | undefined): string | undefined {
  const requestId = value?.trim();
  if (
    requestId === undefined ||
    requestId === '' ||
    requestId.length > MAX_REQUEST_ID_LENGTH ||
    !REQUEST_ID_PATTERN.test(requestId)
  ) {
    return undefined;
  }

  return requestId;
}

export function normalizeRequestIdHeader(
  value: string | string[] | undefined,
): string | undefined {
  if (Array.isArray(value)) {
    return value.length === 1 ? normalizeRequestId(value[0]) : undefined;
  }

  return normalizeRequestId(value);
}

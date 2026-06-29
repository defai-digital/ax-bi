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
import { expect, test } from '@jest/globals';

import {
  authorizationContractSchemas,
  AUTHORIZATION_CONTRACT_VERSION,
  permissionCheckRequestSchema,
} from '../src/contracts/authorization';
import {
  healthResponseSchema,
  metricsResponseSchema,
  readinessResponseSchema,
  RUNTIME_CONTRACT_VERSION,
  runtimeContractSchemas,
} from '../src/contracts/runtime';

test('runtime contract version is explicit', () => {
  expect(RUNTIME_CONTRACT_VERSION).toBe('runtime.v1');
});

test('authorization contract version is explicit', () => {
  expect(AUTHORIZATION_CONTRACT_VERSION).toBe('authorization.v1');
});

test('health response schema is stable', () => {
  expect(healthResponseSchema).toEqual({
    $id: 'ax-services.health.v1.response',
    type: 'object',
    required: ['contractVersion', 'service', 'status'],
    additionalProperties: false,
    properties: {
      contractVersion: { const: 'runtime.v1' },
      service: { const: 'ax-services' },
      status: { const: 'ok' },
    },
  });
});

test('readiness response schema is registered in runtime contracts', () => {
  expect(runtimeContractSchemas.readinessResponseSchema).toBe(
    readinessResponseSchema,
  );
  expect(readinessResponseSchema.properties.status).toEqual({
    enum: ['ready', 'not_ready'],
  });
});

test('metrics response schema is registered in runtime contracts', () => {
  expect(runtimeContractSchemas.metricsResponseSchema).toBe(metricsResponseSchema);
  expect(metricsResponseSchema.properties.requests.properties.routes).toEqual({
    type: 'object',
    additionalProperties: {
      type: 'object',
      required: ['count', 'errorCount', 'averageDurationMs', 'maxDurationMs'],
      additionalProperties: false,
      properties: {
        count: { type: 'number' },
        errorCount: { type: 'number' },
        averageDurationMs: { type: 'number' },
        maxDurationMs: { type: 'number' },
      },
    },
  });
});

test('permission check request schema is registered in authorization contracts', () => {
  expect(authorizationContractSchemas.permissionCheckRequestSchema).toBe(
    permissionCheckRequestSchema,
  );
  expect(permissionCheckRequestSchema.properties.action).toEqual({
    enum: ['create', 'delete', 'read', 'write'],
  });
});

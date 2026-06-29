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
export const RUNTIME_CONTRACT_VERSION = 'runtime.v1';

export interface DependencyHealthContract {
  ok: boolean;
  url: string;
  statusCode?: number;
  error?: string;
}

export interface HealthResponseContract {
  contractVersion: typeof RUNTIME_CONTRACT_VERSION;
  service: 'ax-services';
  status: 'ok';
}

export interface ReadinessResponseContract {
  contractVersion: typeof RUNTIME_CONTRACT_VERSION;
  service: 'ax-services';
  status: 'ready' | 'not_ready';
  dependencies: {
    superset: DependencyHealthContract;
  };
}

const dependencyHealthSchema = {
  type: 'object',
  required: ['ok', 'url'],
  additionalProperties: false,
  properties: {
    ok: { type: 'boolean' },
    url: { type: 'string' },
    statusCode: { type: 'number' },
    error: { type: 'string' },
  },
} as const;

export const healthResponseSchema = {
  $id: 'ax-services.health.v1.response',
  type: 'object',
  required: ['contractVersion', 'service', 'status'],
  additionalProperties: false,
  properties: {
    contractVersion: { const: RUNTIME_CONTRACT_VERSION },
    service: { const: 'ax-services' },
    status: { const: 'ok' },
  },
} as const;

export const readinessResponseSchema = {
  $id: 'ax-services.readiness.v1.response',
  type: 'object',
  required: ['contractVersion', 'service', 'status', 'dependencies'],
  additionalProperties: false,
  properties: {
    contractVersion: { const: RUNTIME_CONTRACT_VERSION },
    service: { const: 'ax-services' },
    status: { enum: ['ready', 'not_ready'] },
    dependencies: {
      type: 'object',
      required: ['superset'],
      additionalProperties: false,
      properties: {
        superset: dependencyHealthSchema,
      },
    },
  },
} as const;

export const runtimeContractSchemas = {
  healthResponseSchema,
  readinessResponseSchema,
} as const;

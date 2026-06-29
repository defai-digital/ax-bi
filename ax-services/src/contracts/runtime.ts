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

export interface DependencyMetadataContract extends DependencyHealthContract {
  keyCount?: number;
  keys?: string[];
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

export interface RouteMetricsContract {
  count: number;
  errorCount: number;
  averageDurationMs: number;
  maxDurationMs: number;
}

export interface MetricsResponseContract {
  contractVersion: typeof RUNTIME_CONTRACT_VERSION;
  service: 'ax-services';
  status: 'ok';
  uptimeSeconds: number;
  requests: {
    total: number;
    errorCount: number;
    averageDurationMs: number;
    maxDurationMs: number;
    routes: Record<string, RouteMetricsContract>;
  };
}

export interface MetadataResponseContract {
  contractVersion: typeof RUNTIME_CONTRACT_VERSION;
  service: 'ax-services';
  status: 'ok' | 'not_ready';
  dependencies: {
    supersetMetadata: DependencyMetadataContract;
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

const dependencyMetadataSchema = {
  type: 'object',
  required: ['ok', 'url'],
  additionalProperties: false,
  properties: {
    ok: { type: 'boolean' },
    url: { type: 'string' },
    statusCode: { type: 'number' },
    keyCount: { type: 'number' },
    keys: {
      type: 'array',
      items: { type: 'string' },
    },
    error: { type: 'string' },
  },
} as const;

const routeMetricsSchema = {
  type: 'object',
  required: ['count', 'errorCount', 'averageDurationMs', 'maxDurationMs'],
  additionalProperties: false,
  properties: {
    count: { type: 'number' },
    errorCount: { type: 'number' },
    averageDurationMs: { type: 'number' },
    maxDurationMs: { type: 'number' },
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

export const metricsResponseSchema = {
  $id: 'ax-services.metrics.v1.response',
  type: 'object',
  required: ['contractVersion', 'service', 'status', 'uptimeSeconds', 'requests'],
  additionalProperties: false,
  properties: {
    contractVersion: { const: RUNTIME_CONTRACT_VERSION },
    service: { const: 'ax-services' },
    status: { const: 'ok' },
    uptimeSeconds: { type: 'number' },
    requests: {
      type: 'object',
      required: [
        'total',
        'errorCount',
        'averageDurationMs',
        'maxDurationMs',
        'routes',
      ],
      additionalProperties: false,
      properties: {
        total: { type: 'number' },
        errorCount: { type: 'number' },
        averageDurationMs: { type: 'number' },
        maxDurationMs: { type: 'number' },
        routes: {
          type: 'object',
          additionalProperties: routeMetricsSchema,
        },
      },
    },
  },
} as const;

export const metadataResponseSchema = {
  $id: 'ax-services.metadata.v1.response',
  type: 'object',
  required: ['contractVersion', 'service', 'status', 'dependencies'],
  additionalProperties: false,
  properties: {
    contractVersion: { const: RUNTIME_CONTRACT_VERSION },
    service: { const: 'ax-services' },
    status: { enum: ['ok', 'not_ready'] },
    dependencies: {
      type: 'object',
      required: ['supersetMetadata'],
      additionalProperties: false,
      properties: {
        supersetMetadata: dependencyMetadataSchema,
      },
    },
  },
} as const;

export const runtimeContractSchemas = {
  healthResponseSchema,
  metadataResponseSchema,
  metricsResponseSchema,
  readinessResponseSchema,
} as const;

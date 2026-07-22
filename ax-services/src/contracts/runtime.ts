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
const externalMessageSchema = {
  type: 'string',
  minLength: 1,
  maxLength: 256,
  pattern: '^[^\\u0000-\\u001F\\u007F]+$',
} as const;
const metadataKeySchema = {
  type: 'string',
  minLength: 1,
  maxLength: 128,
  pattern: '^[^\\u0000-\\u001F\\u007F]+$',
} as const;
const httpStatusCodeSchema = {
  type: 'integer',
  minimum: 100,
  maximum: 599,
} as const;
const isoTimestampSchema = {
  type: 'string',
  format: 'date-time',
  maxLength: 32,
} as const;
const nodeVersionSchema = {
  type: 'string',
  maxLength: 64,
  pattern: '^v\\d+\\.\\d+\\.\\d+',
} as const;
const nodePlatformSchema = {
  enum: [
    'aix',
    'android',
    'darwin',
    'freebsd',
    'haiku',
    'linux',
    'openbsd',
    'sunos',
    'win32',
    'cygwin',
    'netbsd',
  ],
} as const;
const nonNegativeIntegerSchema = {
  type: 'integer',
  minimum: 0,
} as const;
const nonNegativeNumberSchema = {
  type: 'number',
  minimum: 0,
} as const;

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
  timestamp: string;
  version: string;
  /** Included only for loopback listeners to limit host fingerprinting. */
  nodeVersion?: string;
  /** Included only for loopback listeners to limit host fingerprinting. */
  platform?: string;
  uptimeSeconds: number;
}

export interface ReadinessResponseContract {
  contractVersion: typeof RUNTIME_CONTRACT_VERSION;
  service: 'ax-services';
  status: 'ready' | 'not_ready';
  dependencies: {
    axbi: DependencyHealthContract;
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
    axbiMetadata: DependencyMetadataContract;
  };
}

const dependencyHealthSchema = {
  type: 'object',
  required: ['ok', 'url'],
  additionalProperties: false,
  properties: {
    ok: { type: 'boolean' },
    url: { type: 'string' },
    statusCode: httpStatusCodeSchema,
    error: externalMessageSchema,
  },
} as const;

const dependencyMetadataSchema = {
  type: 'object',
  required: ['ok', 'url'],
  additionalProperties: false,
  properties: {
    ok: { type: 'boolean' },
    url: { type: 'string' },
    statusCode: httpStatusCodeSchema,
    keyCount: { type: 'integer', minimum: 0, maximum: 100 },
    keys: {
      type: 'array',
      maxItems: 100,
      items: metadataKeySchema,
    },
    error: externalMessageSchema,
  },
} as const;

const routeMetricsSchema = {
  type: 'object',
  required: ['count', 'errorCount', 'averageDurationMs', 'maxDurationMs'],
  additionalProperties: false,
  properties: {
    count: nonNegativeIntegerSchema,
    errorCount: nonNegativeIntegerSchema,
    averageDurationMs: nonNegativeNumberSchema,
    maxDurationMs: nonNegativeNumberSchema,
  },
} as const;

export const healthResponseSchema = {
  $id: 'ax-services.health.v1.response',
  type: 'object',
  required: [
    'contractVersion',
    'service',
    'status',
    'timestamp',
    'version',
    'uptimeSeconds',
  ],
  additionalProperties: false,
  properties: {
    contractVersion: { const: RUNTIME_CONTRACT_VERSION },
    service: { const: 'ax-services' },
    status: { const: 'ok' },
    timestamp: isoTimestampSchema,
    version: {
      type: 'string',
      minLength: 1,
      maxLength: 128,
      pattern: '^[^\\u0000-\\u001f\\u007f]+$',
    },
    nodeVersion: nodeVersionSchema,
    platform: nodePlatformSchema,
    uptimeSeconds: { type: 'number' },
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
      required: ['axbi'],
      additionalProperties: false,
      properties: {
        axbi: dependencyHealthSchema,
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
    uptimeSeconds: nonNegativeNumberSchema,
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
        total: nonNegativeIntegerSchema,
        errorCount: nonNegativeIntegerSchema,
        averageDurationMs: nonNegativeNumberSchema,
        maxDurationMs: nonNegativeNumberSchema,
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
      required: ['axbiMetadata'],
      additionalProperties: false,
      properties: {
        axbiMetadata: dependencyMetadataSchema,
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

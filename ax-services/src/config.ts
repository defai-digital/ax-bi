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
export interface ServiceConfig {
  host: string;
  port: number;
  supersetBaseUrl: string;
  supersetHealthPath: string;
  supersetMetadataPath: string;
  supersetPermissionPath: string;
  supersetAssetSearchPaths: {
    annotationLayer: string;
    chart: string;
    dashboard: string;
    database: string;
    dataset: string;
    query: string;
    report: string;
    role: string;
    rls: string;
    savedQuery: string;
    tag: string;
    task: string;
  };
  supersetTimeoutMs: number;
  supersetInternalToken: string | undefined;
  logLevel: LogLevel;
}

type EnvironmentVariable =
  | 'AX_SERVICES_HOST'
  | 'AX_SERVICES_PORT'
  | 'AX_SUPERSET_BASE_URL'
  | 'AX_SUPERSET_HEALTH_PATH'
  | 'AX_SUPERSET_METADATA_PATH'
  | 'AX_SUPERSET_PERMISSION_PATH'
  | 'AX_SUPERSET_ANNOTATION_LAYER_LIST_PATH'
  | 'AX_SUPERSET_CHART_LIST_PATH'
  | 'AX_SUPERSET_DASHBOARD_LIST_PATH'
  | 'AX_SUPERSET_DATABASE_LIST_PATH'
  | 'AX_SUPERSET_DATASET_LIST_PATH'
  | 'AX_SUPERSET_QUERY_LIST_PATH'
  | 'AX_SUPERSET_REPORT_LIST_PATH'
  | 'AX_SUPERSET_ROLE_LIST_PATH'
  | 'AX_SUPERSET_RLS_LIST_PATH'
  | 'AX_SUPERSET_SAVED_QUERY_LIST_PATH'
  | 'AX_SUPERSET_TAG_LIST_PATH'
  | 'AX_SUPERSET_TASK_LIST_PATH'
  | 'AX_SUPERSET_TIMEOUT_MS'
  | 'AX_SUPERSET_INTERNAL_TOKEN'
  | 'AX_SERVICES_LOG_LEVEL';

type Environment = Partial<Record<EnvironmentVariable, string | undefined>>;
export type LogLevel = 'debug' | 'info' | 'warn' | 'error' | 'silent';

const DEFAULT_HOST = '127.0.0.1';
const DEFAULT_PORT = 5010;
const DEFAULT_SUPERSET_BASE_URL = 'http://127.0.0.1:8088';
const DEFAULT_SUPERSET_HEALTH_PATH = '/health';
const DEFAULT_SUPERSET_METADATA_PATH = '/api/v1/dashboard/_info';
const DEFAULT_SUPERSET_PERMISSION_PATH = '/api/v1/security/permissions/check';
const DEFAULT_SUPERSET_ANNOTATION_LAYER_LIST_PATH = '/api/v1/annotation_layer/';
const DEFAULT_SUPERSET_CHART_LIST_PATH = '/api/v1/chart/';
const DEFAULT_SUPERSET_DASHBOARD_LIST_PATH = '/api/v1/dashboard/';
const DEFAULT_SUPERSET_DATABASE_LIST_PATH = '/api/v1/database/';
const DEFAULT_SUPERSET_DATASET_LIST_PATH = '/api/v1/dataset/';
const DEFAULT_SUPERSET_QUERY_LIST_PATH = '/api/v1/query/';
const DEFAULT_SUPERSET_REPORT_LIST_PATH = '/api/v1/report/';
const DEFAULT_SUPERSET_ROLE_LIST_PATH = '/api/v1/role/';
const DEFAULT_SUPERSET_RLS_LIST_PATH = '/api/v1/rowlevelsecurity/';
const DEFAULT_SUPERSET_SAVED_QUERY_LIST_PATH = '/api/v1/saved_query/';
const DEFAULT_SUPERSET_TAG_LIST_PATH = '/api/v1/tag/';
const DEFAULT_SUPERSET_TASK_LIST_PATH = '/api/v1/task/';
const DEFAULT_SUPERSET_TIMEOUT_MS = 2000;
const DEFAULT_LOG_LEVEL: LogLevel = 'info';
const MAX_PORT = 65535;
const MAX_SUPERSET_TIMEOUT_MS = 2_147_483_647;
const LOG_LEVELS = new Set<LogLevel>([
  'debug',
  'info',
  'warn',
  'error',
  'silent',
]);

function normalizeHost(value: string | undefined): string {
  const host = value?.trim();
  if (host === '' || host === undefined) {
    return DEFAULT_HOST;
  }
  if (/\s|[\u0000-\u001f\u007f]/.test(host)) {
    throw new Error(
      'AX_SERVICES_HOST must not contain whitespace or control characters',
    );
  }

  return host;
}

function parsePositiveInteger(
  value: string | undefined,
  defaultValue: number,
  name: string,
): number {
  const normalized = value?.trim();
  if (normalized === undefined || normalized === '') {
    return defaultValue;
  }

  if (!/^[1-9]\d*$/.test(normalized)) {
    throw new Error(`${name} must be a positive integer`);
  }

  const parsed = Number(normalized);
  return parsed;
}

function parsePort(value: string | undefined): number {
  const port = parsePositiveInteger(value, DEFAULT_PORT, 'AX_SERVICES_PORT');
  if (port > MAX_PORT) {
    throw new Error(`AX_SERVICES_PORT must be between 1 and ${MAX_PORT}`);
  }

  return port;
}

function parseSupersetTimeout(value: string | undefined): number {
  const timeout = parsePositiveInteger(
    value,
    DEFAULT_SUPERSET_TIMEOUT_MS,
    'AX_SUPERSET_TIMEOUT_MS',
  );
  if (timeout > MAX_SUPERSET_TIMEOUT_MS) {
    throw new Error(
      `AX_SUPERSET_TIMEOUT_MS must be between 1 and ${MAX_SUPERSET_TIMEOUT_MS}`,
    );
  }

  return timeout;
}

function normalizeSupersetBaseUrl(value: string): string {
  try {
    const trimmed = value.trim();
    if (!/^https?:\/\//i.test(trimmed)) {
      throw new Error('explicit HTTP(S) authority required');
    }

    const url = new URL(trimmed);
    if (url.protocol !== 'http:' && url.protocol !== 'https:') {
      throw new Error('unsupported protocol');
    }
    if (url.hostname === '') {
      throw new Error('host required');
    }
    if (url.username !== '' || url.password !== '') {
      throw new Error('credentials not allowed');
    }
    if (url.search !== '' || url.hash !== '') {
      throw new Error('query or fragment not allowed');
    }
    return url.toString().replace(/\/$/, '');
  } catch (error) {
    throw new Error('AX_SUPERSET_BASE_URL must be a valid HTTP(S) URL', {
      cause: error,
    });
  }
}

function normalizePath(value: string, name: string): string {
  const trimmed = value.trim();

  if (trimmed === '') {
    throw new Error(`${name} must not be empty`);
  }
  if (/[?#\\\s\u0000-\u001f\u007f]/.test(trimmed)) {
    throw new Error(
      `${name} must be a URL path without query, fragment, backslash, whitespace, or control characters`,
    );
  }
  if (trimmed.split('/').some(segment => segment === '.' || segment === '..')) {
    throw new Error(`${name} must not contain dot path segments`);
  }

  return `/${trimmed.replace(/^\/+/, '')}`;
}

function normalizeOptionalSecret(value: string | undefined): string | undefined {
  const trimmed = value?.trim();
  if (trimmed === '' || trimmed === undefined) {
    return undefined;
  }
  if (/[\u0000-\u001f\u007f]/.test(trimmed)) {
    throw new Error(
      'AX_SUPERSET_INTERNAL_TOKEN must not contain control characters',
    );
  }

  return trimmed;
}

function normalizeLogLevel(value: string | undefined): LogLevel {
  const logLevel = value?.trim().toLowerCase();
  if (logLevel === '' || logLevel === undefined) {
    return DEFAULT_LOG_LEVEL;
  }
  if (!LOG_LEVELS.has(logLevel as LogLevel)) {
    throw new Error(
      `AX_SERVICES_LOG_LEVEL must be one of: ${[...LOG_LEVELS].join(', ')}`,
    );
  }

  return logLevel as LogLevel;
}

export function buildConfig(env: Environment = process.env): ServiceConfig {
  return {
    host: normalizeHost(env.AX_SERVICES_HOST),
    port: parsePort(env.AX_SERVICES_PORT),
    supersetBaseUrl: normalizeSupersetBaseUrl(
      env.AX_SUPERSET_BASE_URL || DEFAULT_SUPERSET_BASE_URL,
    ),
    supersetHealthPath: normalizePath(
      env.AX_SUPERSET_HEALTH_PATH || DEFAULT_SUPERSET_HEALTH_PATH,
      'AX_SUPERSET_HEALTH_PATH',
    ),
    supersetMetadataPath: normalizePath(
      env.AX_SUPERSET_METADATA_PATH || DEFAULT_SUPERSET_METADATA_PATH,
      'AX_SUPERSET_METADATA_PATH',
    ),
    supersetPermissionPath: normalizePath(
      env.AX_SUPERSET_PERMISSION_PATH || DEFAULT_SUPERSET_PERMISSION_PATH,
      'AX_SUPERSET_PERMISSION_PATH',
    ),
    supersetAssetSearchPaths: {
      annotationLayer: normalizePath(
        env.AX_SUPERSET_ANNOTATION_LAYER_LIST_PATH ||
          DEFAULT_SUPERSET_ANNOTATION_LAYER_LIST_PATH,
        'AX_SUPERSET_ANNOTATION_LAYER_LIST_PATH',
      ),
      chart: normalizePath(
        env.AX_SUPERSET_CHART_LIST_PATH || DEFAULT_SUPERSET_CHART_LIST_PATH,
        'AX_SUPERSET_CHART_LIST_PATH',
      ),
      dashboard: normalizePath(
        env.AX_SUPERSET_DASHBOARD_LIST_PATH ||
          DEFAULT_SUPERSET_DASHBOARD_LIST_PATH,
        'AX_SUPERSET_DASHBOARD_LIST_PATH',
      ),
      database: normalizePath(
        env.AX_SUPERSET_DATABASE_LIST_PATH ||
          DEFAULT_SUPERSET_DATABASE_LIST_PATH,
        'AX_SUPERSET_DATABASE_LIST_PATH',
      ),
      dataset: normalizePath(
        env.AX_SUPERSET_DATASET_LIST_PATH || DEFAULT_SUPERSET_DATASET_LIST_PATH,
        'AX_SUPERSET_DATASET_LIST_PATH',
      ),
      query: normalizePath(
        env.AX_SUPERSET_QUERY_LIST_PATH || DEFAULT_SUPERSET_QUERY_LIST_PATH,
        'AX_SUPERSET_QUERY_LIST_PATH',
      ),
      report: normalizePath(
        env.AX_SUPERSET_REPORT_LIST_PATH || DEFAULT_SUPERSET_REPORT_LIST_PATH,
        'AX_SUPERSET_REPORT_LIST_PATH',
      ),
      role: normalizePath(
        env.AX_SUPERSET_ROLE_LIST_PATH || DEFAULT_SUPERSET_ROLE_LIST_PATH,
        'AX_SUPERSET_ROLE_LIST_PATH',
      ),
      rls: normalizePath(
        env.AX_SUPERSET_RLS_LIST_PATH || DEFAULT_SUPERSET_RLS_LIST_PATH,
        'AX_SUPERSET_RLS_LIST_PATH',
      ),
      savedQuery: normalizePath(
        env.AX_SUPERSET_SAVED_QUERY_LIST_PATH ||
          DEFAULT_SUPERSET_SAVED_QUERY_LIST_PATH,
        'AX_SUPERSET_SAVED_QUERY_LIST_PATH',
      ),
      tag: normalizePath(
        env.AX_SUPERSET_TAG_LIST_PATH || DEFAULT_SUPERSET_TAG_LIST_PATH,
        'AX_SUPERSET_TAG_LIST_PATH',
      ),
      task: normalizePath(
        env.AX_SUPERSET_TASK_LIST_PATH || DEFAULT_SUPERSET_TASK_LIST_PATH,
        'AX_SUPERSET_TASK_LIST_PATH',
      ),
    },
    supersetTimeoutMs: parseSupersetTimeout(env.AX_SUPERSET_TIMEOUT_MS),
    supersetInternalToken: normalizeOptionalSecret(
      env.AX_SUPERSET_INTERNAL_TOKEN,
    ),
    logLevel: normalizeLogLevel(env.AX_SERVICES_LOG_LEVEL),
  };
}

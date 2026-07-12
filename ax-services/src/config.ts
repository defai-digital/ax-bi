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
import { isIP } from 'net';

export interface ServiceConfig {
  host: string;
  port: number;
  axbiBaseUrl: string;
  axbiHealthPath: string;
  axbiMetadataPath: string;
  axbiPermissionPath: string;
  axbiAssetSearchPaths: {
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
  axbiTimeoutMs: number;
  axbiInternalToken: string | undefined;
  logLevel: LogLevel;
}

type EnvironmentVariable =
  | 'AX_SERVICES_HOST'
  | 'AX_SERVICES_PORT'
  | 'AXBI_BASE_URL'
  | 'AXBI_HEALTH_PATH'
  | 'AXBI_METADATA_PATH'
  | 'AXBI_PERMISSION_PATH'
  | 'AXBI_ANNOTATION_LAYER_LIST_PATH'
  | 'AXBI_CHART_LIST_PATH'
  | 'AXBI_DASHBOARD_LIST_PATH'
  | 'AXBI_DATABASE_LIST_PATH'
  | 'AXBI_DATASET_LIST_PATH'
  | 'AXBI_QUERY_LIST_PATH'
  | 'AXBI_REPORT_LIST_PATH'
  | 'AXBI_ROLE_LIST_PATH'
  | 'AXBI_RLS_LIST_PATH'
  | 'AXBI_SAVED_QUERY_LIST_PATH'
  | 'AXBI_TAG_LIST_PATH'
  | 'AXBI_TASK_LIST_PATH'
  | 'AXBI_TIMEOUT_MS'
  | 'AXBI_INTERNAL_TOKEN'
  | 'AX_SERVICES_LOG_LEVEL';

type Environment = Partial<Record<EnvironmentVariable, string | undefined>>;
export type LogLevel = 'debug' | 'info' | 'warn' | 'error' | 'silent';
type AxBIAssetSearchPathKey = keyof ServiceConfig['axbiAssetSearchPaths'];

const DEFAULT_HOST = '127.0.0.1';
const DEFAULT_PORT = 5010;
const DEFAULT_AXBI_BASE_URL = 'http://127.0.0.1:8088';
const DEFAULT_AXBI_HEALTH_PATH = '/health';
const DEFAULT_AXBI_METADATA_PATH = '/api/v1/dashboard/_info';
const DEFAULT_AXBI_PERMISSION_PATH = '/api/v1/security/permissions/check';
const DEFAULT_AXBI_ANNOTATION_LAYER_LIST_PATH = '/api/v1/annotation_layer/';
const DEFAULT_AXBI_CHART_LIST_PATH = '/api/v1/chart/';
const DEFAULT_AXBI_DASHBOARD_LIST_PATH = '/api/v1/dashboard/';
const DEFAULT_AXBI_DATABASE_LIST_PATH = '/api/v1/database/';
const DEFAULT_AXBI_DATASET_LIST_PATH = '/api/v1/dataset/';
const DEFAULT_AXBI_QUERY_LIST_PATH = '/api/v1/query/';
const DEFAULT_AXBI_REPORT_LIST_PATH = '/api/v1/report/';
const DEFAULT_AXBI_ROLE_LIST_PATH = '/api/v1/role/';
const DEFAULT_AXBI_RLS_LIST_PATH = '/api/v1/rowlevelsecurity/';
const DEFAULT_AXBI_SAVED_QUERY_LIST_PATH = '/api/v1/saved_query/';
const DEFAULT_AXBI_TAG_LIST_PATH = '/api/v1/tag/';
const DEFAULT_AXBI_TASK_LIST_PATH = '/api/v1/task/';
const DEFAULT_AXBI_TIMEOUT_MS = 2000;
const DEFAULT_LOG_LEVEL: LogLevel = 'info';
const MAX_PORT = 65535;
const MAX_AXBI_TIMEOUT_MS = 2_147_483_647;
const HOSTNAME_PATTERN =
  /^(?=.{1,253}$)(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)*[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?$/;
const LOG_LEVELS = new Set<LogLevel>([
  'debug',
  'info',
  'warn',
  'error',
  'silent',
]);

const AXBI_ASSET_SEARCH_PATHS = {
  annotationLayer: {
    env: 'AXBI_ANNOTATION_LAYER_LIST_PATH',
    defaultValue: DEFAULT_AXBI_ANNOTATION_LAYER_LIST_PATH,
  },
  chart: {
    env: 'AXBI_CHART_LIST_PATH',
    defaultValue: DEFAULT_AXBI_CHART_LIST_PATH,
  },
  dashboard: {
    env: 'AXBI_DASHBOARD_LIST_PATH',
    defaultValue: DEFAULT_AXBI_DASHBOARD_LIST_PATH,
  },
  database: {
    env: 'AXBI_DATABASE_LIST_PATH',
    defaultValue: DEFAULT_AXBI_DATABASE_LIST_PATH,
  },
  dataset: {
    env: 'AXBI_DATASET_LIST_PATH',
    defaultValue: DEFAULT_AXBI_DATASET_LIST_PATH,
  },
  query: {
    env: 'AXBI_QUERY_LIST_PATH',
    defaultValue: DEFAULT_AXBI_QUERY_LIST_PATH,
  },
  report: {
    env: 'AXBI_REPORT_LIST_PATH',
    defaultValue: DEFAULT_AXBI_REPORT_LIST_PATH,
  },
  role: {
    env: 'AXBI_ROLE_LIST_PATH',
    defaultValue: DEFAULT_AXBI_ROLE_LIST_PATH,
  },
  rls: {
    env: 'AXBI_RLS_LIST_PATH',
    defaultValue: DEFAULT_AXBI_RLS_LIST_PATH,
  },
  savedQuery: {
    env: 'AXBI_SAVED_QUERY_LIST_PATH',
    defaultValue: DEFAULT_AXBI_SAVED_QUERY_LIST_PATH,
  },
  tag: {
    env: 'AXBI_TAG_LIST_PATH',
    defaultValue: DEFAULT_AXBI_TAG_LIST_PATH,
  },
  task: {
    env: 'AXBI_TASK_LIST_PATH',
    defaultValue: DEFAULT_AXBI_TASK_LIST_PATH,
  },
} as const satisfies Record<
  AxBIAssetSearchPathKey,
  {
    env: EnvironmentVariable;
    defaultValue: string;
  }
>;

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
  if (!isListenHost(host)) {
    throw new Error(
      'AX_SERVICES_HOST must be a hostname or IP address without scheme, path, or port',
    );
  }

  return host;
}

function isListenHost(value: string): boolean {
  if (isIP(value) !== 0) {
    return true;
  }
  return HOSTNAME_PATTERN.test(value);
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

function parseAxBITimeout(value: string | undefined): number {
  const timeout = parsePositiveInteger(
    value,
    DEFAULT_AXBI_TIMEOUT_MS,
    'AXBI_TIMEOUT_MS',
  );
  if (timeout > MAX_AXBI_TIMEOUT_MS) {
    throw new Error(
      `AXBI_TIMEOUT_MS must be between 1 and ${MAX_AXBI_TIMEOUT_MS}`,
    );
  }

  return timeout;
}

function normalizeAxBIBaseUrl(value: string): string {
  try {
    const trimmed = value.trim();
    if (!/^https?:\/\//i.test(trimmed)) {
      throw new Error('explicit HTTP(S) authority required');
    }

    validatePathSegments(rawUrlPath(trimmed), 'AXBI_BASE_URL');
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
    throw new Error('AXBI_BASE_URL must be a valid HTTP(S) URL', {
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
  validatePathSegments(trimmed, name);

  return `/${trimmed.replace(/^\/+/, '')}`;
}

function normalizeEnvPath(
  env: Environment,
  name: EnvironmentVariable,
  defaultValue: string,
): string {
  return normalizePath(env[name] ?? defaultValue, name);
}

function rawUrlPath(value: string): string {
  return value.replace(/^[a-z][a-z0-9+.-]*:\/\/[^/?#]*/i, '');
}

function validatePathSegments(value: string, name: string): void {
  for (const segment of value.split('/')) {
    let decodedSegment: string;
    try {
      decodedSegment = decodeURIComponent(segment);
    } catch (error) {
      throw new Error(`${name} must contain valid percent-encoding`, {
        cause: error,
      });
    }
    if (decodedSegment === '.' || decodedSegment === '..') {
      throw new Error(`${name} must not contain dot path segments`);
    }
    if (/[\\/]/.test(decodedSegment)) {
      throw new Error(`${name} must not contain encoded path separators`);
    }
    if (/[\s\u0000-\u001f\u007f]/.test(decodedSegment)) {
      throw new Error(
        `${name} must not contain whitespace or control characters`,
      );
    }
  }
}

function normalizeOptionalSecret(value: string | undefined): string | undefined {
  const trimmed = value?.trim();
  if (trimmed === '' || trimmed === undefined) {
    return undefined;
  }
  if (/[\u0000-\u001f\u007f]/.test(trimmed)) {
    throw new Error(
      'AXBI_INTERNAL_TOKEN must not contain control characters',
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

function buildAxBIAssetSearchPaths(
  env: Environment,
): ServiceConfig['axbiAssetSearchPaths'] {
  return Object.fromEntries(
    Object.entries(AXBI_ASSET_SEARCH_PATHS).map(
      ([key, { env: envName, defaultValue }]) => [
        key,
        normalizeEnvPath(env, envName, defaultValue),
      ],
    ),
  ) as ServiceConfig['axbiAssetSearchPaths'];
}

export function buildConfig(env: Environment = process.env): ServiceConfig {
  return {
    host: normalizeHost(env.AX_SERVICES_HOST),
    port: parsePort(env.AX_SERVICES_PORT),
    axbiBaseUrl: normalizeAxBIBaseUrl(
      env.AXBI_BASE_URL || DEFAULT_AXBI_BASE_URL,
    ),
    axbiHealthPath: normalizeEnvPath(
      env,
      'AXBI_HEALTH_PATH',
      DEFAULT_AXBI_HEALTH_PATH,
    ),
    axbiMetadataPath: normalizeEnvPath(
      env,
      'AXBI_METADATA_PATH',
      DEFAULT_AXBI_METADATA_PATH,
    ),
    axbiPermissionPath: normalizeEnvPath(
      env,
      'AXBI_PERMISSION_PATH',
      DEFAULT_AXBI_PERMISSION_PATH,
    ),
    axbiAssetSearchPaths: buildAxBIAssetSearchPaths(env),
    axbiTimeoutMs: parseAxBITimeout(env.AXBI_TIMEOUT_MS),
    axbiInternalToken: normalizeOptionalSecret(
      env.AXBI_INTERNAL_TOKEN,
    ),
    logLevel: normalizeLogLevel(env.AX_SERVICES_LOG_LEVEL),
  };
}

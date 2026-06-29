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
    report: string;
    savedQuery: string;
    tag: string;
    task: string;
  };
  supersetTimeoutMs: number;
  supersetInternalToken?: string;
  logLevel: string;
}

type Environment = Partial<Record<string, string>>;

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
const DEFAULT_SUPERSET_REPORT_LIST_PATH = '/api/v1/report/';
const DEFAULT_SUPERSET_SAVED_QUERY_LIST_PATH = '/api/v1/saved_query/';
const DEFAULT_SUPERSET_TAG_LIST_PATH = '/api/v1/tag/';
const DEFAULT_SUPERSET_TASK_LIST_PATH = '/api/v1/task/';
const DEFAULT_SUPERSET_TIMEOUT_MS = 2000;
const DEFAULT_LOG_LEVEL = 'info';

function parsePositiveInteger(
  value: string | undefined,
  defaultValue: number,
  name: string,
): number {
  if (value === undefined || value === '') {
    return defaultValue;
  }

  const parsed = Number(value);
  if (!Number.isInteger(parsed) || parsed <= 0) {
    throw new Error(`${name} must be a positive integer`);
  }

  return parsed;
}

function normalizeSupersetBaseUrl(value: string): string {
  try {
    const url = new URL(value);
    return url.toString().replace(/\/$/, '');
  } catch (error) {
    throw new Error('AX_SUPERSET_BASE_URL must be a valid URL', {
      cause: error,
    });
  }
}

function normalizePath(value: string): string {
  return value.startsWith('/') ? value : `/${value}`;
}

export function buildConfig(env: Environment = process.env): ServiceConfig {
  return {
    host: env.AX_SERVICES_HOST || DEFAULT_HOST,
    port: parsePositiveInteger(
      env.AX_SERVICES_PORT,
      DEFAULT_PORT,
      'AX_SERVICES_PORT',
    ),
    supersetBaseUrl: normalizeSupersetBaseUrl(
      env.AX_SUPERSET_BASE_URL || DEFAULT_SUPERSET_BASE_URL,
    ),
    supersetHealthPath: normalizePath(
      env.AX_SUPERSET_HEALTH_PATH || DEFAULT_SUPERSET_HEALTH_PATH,
    ),
    supersetMetadataPath: normalizePath(
      env.AX_SUPERSET_METADATA_PATH || DEFAULT_SUPERSET_METADATA_PATH,
    ),
    supersetPermissionPath: normalizePath(
      env.AX_SUPERSET_PERMISSION_PATH || DEFAULT_SUPERSET_PERMISSION_PATH,
    ),
    supersetAssetSearchPaths: {
      annotationLayer: normalizePath(
        env.AX_SUPERSET_ANNOTATION_LAYER_LIST_PATH ||
          DEFAULT_SUPERSET_ANNOTATION_LAYER_LIST_PATH,
      ),
      chart: normalizePath(
        env.AX_SUPERSET_CHART_LIST_PATH || DEFAULT_SUPERSET_CHART_LIST_PATH,
      ),
      dashboard: normalizePath(
        env.AX_SUPERSET_DASHBOARD_LIST_PATH ||
          DEFAULT_SUPERSET_DASHBOARD_LIST_PATH,
      ),
      database: normalizePath(
        env.AX_SUPERSET_DATABASE_LIST_PATH ||
          DEFAULT_SUPERSET_DATABASE_LIST_PATH,
      ),
      dataset: normalizePath(
        env.AX_SUPERSET_DATASET_LIST_PATH || DEFAULT_SUPERSET_DATASET_LIST_PATH,
      ),
      report: normalizePath(
        env.AX_SUPERSET_REPORT_LIST_PATH || DEFAULT_SUPERSET_REPORT_LIST_PATH,
      ),
      savedQuery: normalizePath(
        env.AX_SUPERSET_SAVED_QUERY_LIST_PATH ||
          DEFAULT_SUPERSET_SAVED_QUERY_LIST_PATH,
      ),
      tag: normalizePath(
        env.AX_SUPERSET_TAG_LIST_PATH || DEFAULT_SUPERSET_TAG_LIST_PATH,
      ),
      task: normalizePath(
        env.AX_SUPERSET_TASK_LIST_PATH || DEFAULT_SUPERSET_TASK_LIST_PATH,
      ),
    },
    supersetTimeoutMs: parsePositiveInteger(
      env.AX_SUPERSET_TIMEOUT_MS,
      DEFAULT_SUPERSET_TIMEOUT_MS,
      'AX_SUPERSET_TIMEOUT_MS',
    ),
    supersetInternalToken: env.AX_SUPERSET_INTERNAL_TOKEN || undefined,
    logLevel: env.AX_SERVICES_LOG_LEVEL || DEFAULT_LOG_LEVEL,
  };
}

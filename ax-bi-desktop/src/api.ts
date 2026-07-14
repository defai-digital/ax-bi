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
 * Type definitions for the AX BI Desktop Client Tauri API
 */

import { invoke } from '@tauri-apps/api/core';

export interface AppConfig {
  server_url: string;
  sso_enabled: boolean;
  version: string;
}

export interface LocalRuntimeDependency {
  name: string;
  command: string;
  installed: boolean;
  version: string | null;
  install_hint: string;
}

export interface LocalRuntimeStatus {
  runtime_dir: string;
  compose_file: string;
  env_file: string;
  configured: boolean;
  dependencies: LocalRuntimeDependency[];
  /** OS id: `macos` | `windows` | `linux`. */
  platform: string;
  /** True on all desktop builds — local AX BI Docker is supported. */
  local_runtime_supported: boolean;
  /** Required CLI tools installed; engine may still need to start. */
  can_start_local: boolean;
  /** Engine identifier: `colima` (macOS) or `docker` (Windows/Linux). */
  engine_name: string;
  /** UI label for the VM/engine layer (e.g. "Colima", "Docker Engine"). */
  engine_label: string;
  /** Whether the container engine is ready enough to run Compose. */
  engine_running: boolean;
  /** Colima profile on macOS; empty on other platforms. */
  colima_profile: string;
  /** Alias of engine readiness for older clients. */
  colima_running: boolean;
  docker_host: string;
  docker_ready: boolean;
  axbi_running: boolean;
  axbi_healthy: boolean;
  web_url: string;
  mcp_url: string;
  services_url: string;
  admin_username: string;
  admin_password_present: boolean;
}

export interface LocalRuntimeCommandOutput {
  status: LocalRuntimeStatus;
  stdout: string;
  stderr: string;
}

export interface LocalAdminCredentials {
  username: string;
  password: string;
}

function isAppConfig(value: unknown): value is AppConfig {
  if (value === null || typeof value !== 'object' || Array.isArray(value)) {
    return false;
  }

  const config = value as Record<string, unknown>;
  return (
    typeof config['server_url'] === 'string' &&
    typeof config['sso_enabled'] === 'boolean' &&
    typeof config['version'] === 'string'
  );
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function isNullableString(value: unknown): value is string | null {
  return typeof value === 'string' || value === null;
}

function isLocalRuntimeDependency(
  value: unknown,
): value is LocalRuntimeDependency {
  if (!isRecord(value)) {
    return false;
  }

  return (
    typeof value['name'] === 'string' &&
    typeof value['command'] === 'string' &&
    typeof value['installed'] === 'boolean' &&
    isNullableString(value['version']) &&
    typeof value['install_hint'] === 'string'
  );
}

function isLocalRuntimeStatus(value: unknown): value is LocalRuntimeStatus {
  if (!isRecord(value)) {
    return false;
  }

  return (
    typeof value['runtime_dir'] === 'string' &&
    typeof value['compose_file'] === 'string' &&
    typeof value['env_file'] === 'string' &&
    typeof value['configured'] === 'boolean' &&
    Array.isArray(value['dependencies']) &&
    value['dependencies'].every(isLocalRuntimeDependency) &&
    typeof value['platform'] === 'string' &&
    typeof value['local_runtime_supported'] === 'boolean' &&
    typeof value['can_start_local'] === 'boolean' &&
    typeof value['engine_name'] === 'string' &&
    typeof value['engine_label'] === 'string' &&
    typeof value['engine_running'] === 'boolean' &&
    typeof value['colima_profile'] === 'string' &&
    typeof value['colima_running'] === 'boolean' &&
    typeof value['docker_host'] === 'string' &&
    typeof value['docker_ready'] === 'boolean' &&
    typeof value['axbi_running'] === 'boolean' &&
    typeof value['axbi_healthy'] === 'boolean' &&
    typeof value['web_url'] === 'string' &&
    typeof value['mcp_url'] === 'string' &&
    typeof value['services_url'] === 'string' &&
    typeof value['admin_username'] === 'string' &&
    typeof value['admin_password_present'] === 'boolean'
  );
}

function isLocalRuntimeCommandOutput(
  value: unknown,
): value is LocalRuntimeCommandOutput {
  if (!isRecord(value)) {
    return false;
  }

  return (
    isLocalRuntimeStatus(value['status']) &&
    typeof value['stdout'] === 'string' &&
    typeof value['stderr'] === 'string'
  );
}

function isLocalAdminCredentials(
  value: unknown,
): value is LocalAdminCredentials {
  if (!isRecord(value)) {
    return false;
  }

  return (
    typeof value['username'] === 'string' &&
    typeof value['password'] === 'string'
  );
}

function assertLocalRuntimeStatus(value: unknown): LocalRuntimeStatus {
  if (!isLocalRuntimeStatus(value)) {
    throw new Error('Native local runtime status response has an invalid shape');
  }

  return value;
}

function assertLocalRuntimeCommandOutput(
  value: unknown,
): LocalRuntimeCommandOutput {
  if (!isLocalRuntimeCommandOutput(value)) {
    throw new Error('Native local runtime command response has an invalid shape');
  }

  return value;
}

/**
 * Get the application configuration
 */
export async function getAppConfig(): Promise<AppConfig> {
  const config = await invoke<unknown>('get_app_config');
  if (!isAppConfig(config)) {
    throw new Error('Native app config response has an invalid shape');
  }

  return config;
}

/**
 * Navigate to a specific route in the web app
 */
export async function navigateTo(path: string): Promise<void> {
  return invoke('navigate_to', { path });
}

/**
 * Show a native notification
 */
export async function showNotification(
  title: string,
  body: string,
): Promise<void> {
  return invoke('show_notification', { title, body });
}

/**
 * Get the application version
 */
export async function getVersion(): Promise<string> {
  return invoke<string>('get_version');
}

/**
 * Get dependency and container status for the local AX BI runtime.
 */
export async function getLocalRuntimeStatus(): Promise<LocalRuntimeStatus> {
  return assertLocalRuntimeStatus(await invoke<unknown>('get_local_runtime_status'));
}

/**
 * Create the app-owned local runtime directory, Compose file, and secrets.
 */
export async function prepareLocalRuntime(): Promise<LocalRuntimeStatus> {
  return assertLocalRuntimeStatus(await invoke<unknown>('prepare_local_runtime'));
}

/**
 * Start the platform container engine and the app-owned AX BI Compose stack.
 */
export async function startLocalRuntime(): Promise<LocalRuntimeCommandOutput> {
  return assertLocalRuntimeCommandOutput(
    await invoke<unknown>('start_local_runtime'),
  );
}

/**
 * Stop the app-owned AX BI Compose stack without deleting volumes.
 */
export async function stopLocalRuntime(): Promise<LocalRuntimeCommandOutput> {
  return assertLocalRuntimeCommandOutput(
    await invoke<unknown>('stop_local_runtime'),
  );
}

/**
 * Restart the app-owned AX BI Compose stack.
 */
export async function restartLocalRuntime(): Promise<LocalRuntimeCommandOutput> {
  return assertLocalRuntimeCommandOutput(
    await invoke<unknown>('restart_local_runtime'),
  );
}

/**
 * Pull newer container images and restart the app-owned AX BI stack.
 */
export async function updateLocalRuntime(): Promise<LocalRuntimeCommandOutput> {
  return assertLocalRuntimeCommandOutput(
    await invoke<unknown>('update_local_runtime'),
  );
}

/**
 * Read recent logs from an allowlisted local AX BI service.
 */
export async function getLocalRuntimeLogs(
  service?: string,
  tail?: number,
): Promise<string> {
  return invoke<string>('get_local_runtime_logs', { service, tail });
}

/**
 * Read the generated local admin credentials.
 */
export async function getLocalAdminCredentials(): Promise<LocalAdminCredentials> {
  const credentials = await invoke<unknown>('get_local_admin_credentials');
  if (!isLocalAdminCredentials(credentials)) {
    throw new Error('Native local credentials response has an invalid shape');
  }

  return credentials;
}

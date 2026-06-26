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
 * Type definitions for the AX-BI Desktop Client Tauri API
 */

import { invoke } from '@tauri-apps/api/core';

export interface AppConfig {
  server_url: string;
  sso_enabled: boolean;
  version: string;
}

/**
 * Get the application configuration
 */
export async function getAppConfig(): Promise<AppConfig> {
  return invoke<AppConfig>('get_app_config');
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

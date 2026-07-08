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
import { ThemeMode } from '@apache-superset/core/theme';
import type { ThemeController } from './ThemeController';

export type DesktopThemeMode = 'default' | 'dark' | 'system';

export const DESKTOP_THEME_MESSAGE_SOURCE = 'ax-bi-desktop';
export const WEB_THEME_MESSAGE_SOURCE = 'ax-bi-web';
export const THEME_SET_MESSAGE_TYPE = 'theme:set-mode';
export const THEME_CHANGED_MESSAGE_TYPE = 'theme:changed';

const ALLOWED_DESKTOP_THEME_ORIGINS = new Set([
  'http://localhost:1430',
  'http://127.0.0.1:1430',
  'http://tauri.localhost',
  'https://tauri.localhost',
  'tauri://localhost',
  'asset://localhost',
]);

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value && typeof value === 'object');
}

export function isDesktopThemeMode(value: unknown): value is DesktopThemeMode {
  return value === 'default' || value === 'dark' || value === 'system';
}

export function desktopThemeModeToThemeMode(mode: DesktopThemeMode): ThemeMode {
  switch (mode) {
    case 'dark':
      return ThemeMode.DARK;
    case 'system':
      return ThemeMode.SYSTEM;
    case 'default':
    default:
      return ThemeMode.DEFAULT;
  }
}

export function themeModeToDesktopThemeMode(mode: ThemeMode): DesktopThemeMode {
  switch (mode) {
    case ThemeMode.DARK:
      return 'dark';
    case ThemeMode.SYSTEM:
      return 'system';
    case ThemeMode.DEFAULT:
    default:
      return 'default';
  }
}

export function resolvedThemeModeToDesktopThemeMode(
  mode: 'dark' | 'light',
): Exclude<DesktopThemeMode, 'system'> {
  return mode === 'dark' ? 'dark' : 'default';
}

export function parseDesktopThemeMode(data: unknown): DesktopThemeMode | null {
  if (!isRecord(data)) return null;
  if (data.source !== DESKTOP_THEME_MESSAGE_SOURCE) return null;
  if (data.type !== THEME_SET_MESSAGE_TYPE) return null;
  if (!isDesktopThemeMode(data.mode)) return null;
  return data.mode;
}

export function isAllowedDesktopThemeOrigin(origin: string): boolean {
  return ALLOWED_DESKTOP_THEME_ORIGINS.has(origin);
}

export function shouldAcceptDesktopThemeEvent(
  event: MessageEvent,
  parentWindow: WindowProxy = window.parent,
  selfWindow: Window = window,
): boolean {
  if (event.source && event.source !== parentWindow) return false;
  if (event.origin === 'null') return parentWindow !== selfWindow;
  return isAllowedDesktopThemeOrigin(event.origin);
}

export function installDesktopThemeBridge(
  themeController: ThemeController,
): () => void {
  let lastDesktopOrigin: string | null = null;

  const postThemeChange = () => {
    if (window.parent === window) return;

    const targetOrigin =
      lastDesktopOrigin && lastDesktopOrigin !== 'null'
        ? lastDesktopOrigin
        : '*';

    window.parent.postMessage(
      {
        source: WEB_THEME_MESSAGE_SOURCE,
        type: THEME_CHANGED_MESSAGE_TYPE,
        mode: themeModeToDesktopThemeMode(themeController.getCurrentMode()),
        resolvedMode: resolvedThemeModeToDesktopThemeMode(
          themeController.getCurrentModeResolved(),
        ),
      },
      targetOrigin,
    );
  };

  const handleMessage = (event: MessageEvent) => {
    if (!shouldAcceptDesktopThemeEvent(event)) return;

    const mode = parseDesktopThemeMode(event.data);
    if (!mode) return;

    lastDesktopOrigin = event.origin;
    try {
      themeController.setThemeMode(desktopThemeModeToThemeMode(mode));
    } catch {
      // Deployments can disable dark/system modes; ignore unsupported requests.
    }
  };

  window.addEventListener('message', handleMessage);
  const unsubscribe = themeController.onChange(postThemeChange);

  return () => {
    window.removeEventListener('message', handleMessage);
    unsubscribe();
  };
}

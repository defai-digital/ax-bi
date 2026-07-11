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
 * Desktop shell bridge — host (Tauri launcher) ↔ web app chrome actions.
 * Keeps shell controls out of a separate top bar and in the web navbar.
 */

import {
  DESKTOP_THEME_MESSAGE_SOURCE,
  WEB_THEME_MESSAGE_SOURCE,
  shouldAcceptDesktopThemeEvent,
} from './desktopThemeBridge';

export const SHELL_HELLO_MESSAGE_TYPE = 'shell:hello';
export const SHELL_OPEN_HOME_MESSAGE_TYPE = 'shell:open-home';
export const SHELL_OPEN_SETTINGS_MESSAGE_TYPE = 'shell:open-settings';

const DESKTOP_SHELL_ACTIVE_KEY = 'ax-bi-desktop-shell-active';
const DESKTOP_SHELL_STATUS_KEY = 'ax-bi-desktop-shell-status';
export const DESKTOP_SHELL_CHANGE_EVENT = 'ax-bi-desktop-shell-change';

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value && typeof value === 'object');
}

export function isDesktopShellActive(
  storage: Storage = window.sessionStorage,
): boolean {
  try {
    return storage.getItem(DESKTOP_SHELL_ACTIVE_KEY) === '1';
  } catch {
    return false;
  }
}

export function getDesktopShellStatus(
  storage: Storage = window.sessionStorage,
): string | null {
  try {
    return storage.getItem(DESKTOP_SHELL_STATUS_KEY);
  } catch {
    return null;
  }
}

export function markDesktopShellActive(
  status?: string | null,
  storage: Storage = window.sessionStorage,
): void {
  try {
    storage.setItem(DESKTOP_SHELL_ACTIVE_KEY, '1');
    if (status) {
      storage.setItem(DESKTOP_SHELL_STATUS_KEY, status);
    }
  } catch {
    // ignore
  }
  window.dispatchEvent(
    new CustomEvent(DESKTOP_SHELL_CHANGE_EVENT, {
      detail: { active: true, status: status ?? getDesktopShellStatus() },
    }),
  );
}

export function parseDesktopShellHello(data: unknown): {
  status: string | null;
} | null {
  if (!isRecord(data)) return null;
  if (data.source !== DESKTOP_THEME_MESSAGE_SOURCE) return null;
  if (data.type !== SHELL_HELLO_MESSAGE_TYPE) return null;
  const status =
    typeof data.status === 'string' && data.status.trim()
      ? data.status.trim()
      : null;
  return { status };
}

export function postDesktopShellAction(
  type:
    | typeof SHELL_OPEN_HOME_MESSAGE_TYPE
    | typeof SHELL_OPEN_SETTINGS_MESSAGE_TYPE,
  targetOrigin = '*',
): boolean {
  if (window.parent === window) {
    return false;
  }
  window.parent.postMessage(
    {
      source: WEB_THEME_MESSAGE_SOURCE,
      type,
    },
    targetOrigin,
  );
  return true;
}

export function installDesktopShellBridge(): () => void {
  const handleMessage = (event: MessageEvent) => {
    // Parent shell origin/source is validated the same way as theme messages.
    if (!shouldAcceptDesktopThemeEvent(event)) return;
    const hello = parseDesktopShellHello(event.data);
    if (!hello) return;
    markDesktopShellActive(hello.status);
  };

  window.addEventListener('message', handleMessage);
  return () => window.removeEventListener('message', handleMessage);
}

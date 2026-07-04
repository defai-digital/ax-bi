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
import { FC, ReactNode, useCallback } from 'react';
import { t } from '@apache-superset/core/translation';
import { useCommandPalette } from 'src/components/CommandPalette';
import { CommandPalette } from 'src/components/CommandPalette';
import { PWAInstallPrompt } from 'src/components/PWAInstallPrompt';
import { useKeyboardShortcut } from 'src/hooks/useKeyboardShortcuts';
import { ShortcutPriority } from 'src/components/KeyboardShortcuts';
import { useServiceWorker } from 'src/hooks/useServiceWorker';
import { useDefaultCommands } from 'src/hooks/useDefaultCommands';

interface DesktopIntegrationInnerProps {
  children: ReactNode;
}

/**
 * Inner component that must render inside ShortcutProvider and
 * CommandPaletteProvider. Handles:
 *
 * - Global keyboard shortcut bindings (Cmd+K opens palette, Cmd+/ shows help)
 * - Service worker lifecycle
 * - Default command registration
 * - Renders the CommandPalette modal and PWA install prompt
 */
export const DesktopIntegrationInner: FC<DesktopIntegrationInnerProps> = ({
  children,
}) => {
  const { toggle } = useCommandPalette();

  // Register the default navigation and action commands
  useDefaultCommands();

  // Service worker lifecycle (registration, update detection)
  useServiceWorker();

  // Global shortcut: Cmd/Ctrl+K opens the command palette
  useKeyboardShortcut(
    'mod+k',
    useCallback(() => {
      toggle();
    }, [toggle]),
    {
      id: 'global-command-palette',
      description: t('Open command palette'),
      namespace: 'global',
      priority: ShortcutPriority.HIGHEST,
      ignoreInputElements: false,
    },
  );

  // Global shortcut: Escape closes the command palette
  useKeyboardShortcut(
    'escape',
    useCallback(() => {
      // Only act if palette is open (the CommandPalette modal handles
      // its own Escape, but this is a safety net for edge cases)
    }, []),
    {
      id: 'global-escape-palette',
      description: t('Close command palette'),
      namespace: 'global',
      priority: ShortcutPriority.LOW,
      enabled: false, // CommandPalette modal handles its own Escape
    },
  );

  return (
    <>
      {children}
      <CommandPalette />
      <PWAInstallPrompt />
    </>
  );
};

export default DesktopIntegrationInner;

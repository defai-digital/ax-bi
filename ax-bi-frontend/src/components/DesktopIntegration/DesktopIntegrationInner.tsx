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
import { FC, ReactNode, useCallback, useEffect } from 'react';
import { t } from '@ax-bi/core/translation';
import { useCommandPalette } from 'src/components/CommandPalette';
import { CommandPalette } from 'src/components/CommandPalette';
import { useKeyboardShortcut } from 'src/hooks/useKeyboardShortcuts';
import {
  ShortcutPriority,
  useShortcutContext,
} from 'src/components/KeyboardShortcuts';
import { ShortcutHelpModal } from 'src/components/KeyboardShortcuts/ShortcutHelpModal';
import { useServiceWorker } from 'src/hooks/useServiceWorker';
import { useDefaultCommands } from 'src/hooks/useDefaultCommands';
import { useAssetSearchCommands } from 'src/hooks/useAssetSearchCommands';

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
 * - Asset search in the command palette
 * - Renders the CommandPalette modal and shortcut help
 */
export const DesktopIntegrationInner: FC<DesktopIntegrationInnerProps> = ({
  children,
}) => {
  const { toggle, registerCommand } = useCommandPalette();
  const { openHelp } = useShortcutContext();

  // Register the default navigation and action commands
  useDefaultCommands();
  useAssetSearchCommands();

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
      category: t('Global'),
      priority: ShortcutPriority.HIGHEST,
      ignoreInputElements: false,
    },
  );

  // Global shortcut: Cmd+/ opens keyboard shortcuts help
  useKeyboardShortcut(
    'mod+/',
    useCallback(() => {
      openHelp();
    }, [openHelp]),
    {
      id: 'global-shortcut-help',
      description: t('Show keyboard shortcuts'),
      namespace: 'global',
      category: t('Global'),
      priority: ShortcutPriority.HIGH,
      ignoreInputElements: true,
    },
  );

  // Shift+/ produces "?" on most layouts
  useKeyboardShortcut(
    'shift+/',
    useCallback(() => {
      openHelp();
    }, [openHelp]),
    {
      id: 'global-shortcut-help-question',
      description: t('Show keyboard shortcuts'),
      namespace: 'global',
      category: t('Global'),
      priority: ShortcutPriority.HIGH,
      ignoreInputElements: true,
    },
  );

  useEffect(() => {
    const cleanup = registerCommand({
      id: 'help-keyboard-shortcuts',
      name: t('Keyboard shortcuts'),
      description: t('Show all keyboard shortcuts'),
      type: 'help',
      keywords: ['shortcut', 'hotkey', 'help', 'keys'],
      shortcut: '?',
      action: () => openHelp(),
    });
    return cleanup;
  }, [registerCommand, openHelp]);

  // Global shortcut: Escape closes the command palette
  useKeyboardShortcut(
    'escape',
    useCallback(() => {
      // CommandPalette modal handles its own Escape
    }, []),
    {
      id: 'global-escape-palette',
      description: t('Close command palette'),
      namespace: 'global',
      category: t('Global'),
      priority: ShortcutPriority.LOW,
      enabled: false,
    },
  );

  return (
    <>
      {children}
      <CommandPalette />
      <ShortcutHelpModal />
    </>
  );
};

export default DesktopIntegrationInner;

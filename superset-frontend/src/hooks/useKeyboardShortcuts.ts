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
import { useEffect, useRef, useCallback } from 'react';
import { useShortcutContext } from '../components/KeyboardShortcuts/ShortcutProvider';
import {
  ShortcutConfig,
  ShortcutNamespace,
  ShortcutPriority,
  PlatformInfo,
  formatShortcutForDisplay,
} from '../components/KeyboardShortcuts/types';

/**
 * Options for the useKeyboardShortcut hook
 */
export interface UseKeyboardShortcutOptions {
  /** Unique ID for this shortcut (auto-generated if not provided) */
  id?: string;
  /** Namespace for organizing shortcuts */
  namespace?: ShortcutNamespace;
  /** Priority level */
  priority?: ShortcutPriority;
  /** Whether the shortcut is enabled */
  enabled?: boolean;
  /** Prevent default browser behavior (default: true) */
  preventDefault?: boolean;
  /** Only trigger when no input is focused (default: true) */
  ignoreInputElements?: boolean;
  /** Human-readable description */
  description?: string;
  /** Icon for help UI */
  icon?: string;
  /** Category for help UI */
  category?: string;
}

/**
 * Return value from useKeyboardShortcut
 */
export interface UseKeyboardShortcutResult {
  /** The generated or provided shortcut ID */
  id: string;
  /** Platform information */
  platform: PlatformInfo;
  /** Formatted shortcut string for display */
  displayShortcut: string;
  /** Unregister the shortcut manually (also happens on unmount) */
  unregister: () => void;
}

let shortcutIdCounter = 0;

/**
 * Hook to register a keyboard shortcut with the global registry
 *
 * @param keys - The key combination (e.g., "mod+k", "ctrl+shift+d")
 * @param handler - Callback when the shortcut is triggered
 * @param options - Configuration options
 * @returns Object with shortcut info and utilities
 *
 * @example
 * ```tsx
 * const { displayShortcut } = useKeyboardShortcut(
 *   'mod+k',
 *   () => openCommandPalette(),
 *   { description: 'Open command palette' }
 * );
 *
 * return <button>Open ({displayShortcut})</button>;
 * ```
 */
export function useKeyboardShortcut(
  keys: string,
  handler: (event: KeyboardEvent) => void,
  options: UseKeyboardShortcutOptions = {},
): UseKeyboardShortcutResult {
  const { registerShortcut, unregisterShortcut, platform } =
    useShortcutContext();

  // Use ref to always have latest handler
  const handlerRef = useRef(handler);
  handlerRef.current = handler;

  // Generate stable ID
  const idRef = useRef(
    options.id || `shortcut-${keys.replace(/\+/g, '-')}-${shortcutIdCounter++}`,
  );

  const unregister = useCallback(() => {
    unregisterShortcut(idRef.current);
  }, [unregisterShortcut]);

  useEffect(() => {
    const config: ShortcutConfig = {
      id: idRef.current,
      keys,
      handler: event => handlerRef.current(event),
      description: options.description || '',
      namespace: options.namespace,
      priority: options.priority,
      enabled: options.enabled,
      preventDefault: options.preventDefault,
      ignoreInputElements: options.ignoreInputElements,
      icon: options.icon,
      category: options.category,
    };

    const cleanup = registerShortcut(config);

    return () => {
      cleanup();
    };
  }, [
    keys,
    options.description,
    options.namespace,
    options.priority,
    options.enabled,
    options.preventDefault,
    options.ignoreInputElements,
    options.icon,
    options.category,
    registerShortcut,
  ]);

  const displayShortcut = formatShortcutForDisplay(keys, platform);

  return {
    id: idRef.current,
    platform,
    displayShortcut,
    unregister,
  };
}

/**
 * Hook to register multiple keyboard shortcuts at once
 *
 * @param shortcuts - Array of shortcut configurations
 * @returns Platform info and array of formatted shortcuts
 *
 * @example
 * ```tsx
 * const { shortcuts, platform } = useKeyboardShortcuts([
 *   { keys: 'mod+k', handler: openPalette, description: 'Command palette' },
 *   { keys: 'mod+/', handler: showHelp, description: 'Show shortcuts' },
 * ]);
 * ```
 */
export function useKeyboardShortcuts(
  shortcuts: Array<{
    keys: string;
    handler: (event: KeyboardEvent) => void;
    options?: UseKeyboardShortcutOptions;
  }>,
): { platform: PlatformInfo; shortcuts: UseKeyboardShortcutResult[] } {
  const { registerShortcut, unregisterShortcut, platform } =
    useShortcutContext();

  // Keep the latest shortcut definitions in a ref so the registration effect
  // can read current handlers without re-subscribing on every render. Calling
  // useKeyboardShortcut in a loop would violate the Rules of Hooks, so register
  // the whole batch in a single effect instead.
  const shortcutsRef = useRef(shortcuts);
  shortcutsRef.current = shortcuts;

  // Stable IDs for each slot, generated once per slot index.
  const idsRef = useRef<string[]>([]);
  if (idsRef.current.length !== shortcuts.length) {
    idsRef.current = shortcuts.map(
      ({ keys, options }, index) =>
        options?.id ||
        `shortcut-${keys.replace(/\+/g, '-')}-${shortcutIdCounter++}-${index}`,
    );
  }

  // Re-register when the set of keys changes (handlers are read via the ref).
  const keysSignature = shortcuts.map(s => s.keys).join('|');

  useEffect(() => {
    const ids = idsRef.current;
    const cleanups = shortcutsRef.current.map(({ keys, options }, index) => {
      const config: ShortcutConfig = {
        id: ids[index],
        keys,
        handler: event => shortcutsRef.current[index]?.handler(event),
        description: options?.description || '',
        namespace: options?.namespace,
        priority: options?.priority,
        enabled: options?.enabled,
        preventDefault: options?.preventDefault,
        ignoreInputElements: options?.ignoreInputElements,
        icon: options?.icon,
        category: options?.category,
      };
      return registerShortcut(config);
    });

    return () => {
      cleanups.forEach(cleanup => cleanup());
    };
    // keysSignature captures changes to the registered key set.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [keysSignature, registerShortcut]);

  const results: UseKeyboardShortcutResult[] = shortcuts.map(
    ({ keys }, index) => ({
      id: idsRef.current[index],
      platform,
      displayShortcut: formatShortcutForDisplay(keys, platform),
      unregister: () => unregisterShortcut(idsRef.current[index]),
    }),
  );

  return {
    platform,
    shortcuts: results,
  };
}

export default useKeyboardShortcut;

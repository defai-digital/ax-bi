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
import {
  createContext,
  useContext,
  useEffect,
  useCallback,
  useMemo,
  useState,
  FC,
  ReactNode,
} from 'react';
import {
  ShortcutConfig,
  RegisteredShortcut,
  ShortcutNamespace,
  ShortcutPriority,
  PlatformInfo,
  matchesShortcut,
} from './types';

/** Context value type for the shortcut registry */
interface ShortcutContextValue {
  /** Register a new keyboard shortcut */
  registerShortcut: (config: ShortcutConfig) => () => void;
  /** Unregister a keyboard shortcut by ID */
  unregisterShortcut: (id: string) => void;
  /** Get all registered shortcuts */
  getShortcuts: () => RegisteredShortcut[];
  /** Get shortcuts filtered by namespace */
  getShortcutsByNamespace: (
    namespace: ShortcutNamespace,
  ) => RegisteredShortcut[];
  /** Platform information */
  platform: PlatformInfo;
  /** Whether the shortcut help modal is open */
  isHelpOpen: boolean;
  /** Open the shortcut help modal */
  openHelp: () => void;
  /** Close the shortcut help modal */
  closeHelp: () => void;
}

const ShortcutContext = createContext<ShortcutContextValue | null>(null);

/**
 * Detect the current platform
 */
function detectPlatform(): PlatformInfo {
  const userAgent = navigator.userAgent.toLowerCase();
  const platform = navigator.platform?.toLowerCase() || '';

  const isMac =
    platform.includes('mac') ||
    userAgent.includes('mac') ||
    userAgent.includes('darwin');
  const isWindows = platform.includes('win') || userAgent.includes('win');
  const isLinux = platform.includes('linux') && !isMac;

  return {
    isMac,
    isWindows,
    isLinux,
    modKeyDisplay: isMac ? '⌘' : 'Ctrl',
    modKeySymbol: isMac ? '⌘' : 'Ctrl',
  };
}

/**
 * Check if the active element is an input element
 */
function isInputElement(element: Element | null): boolean {
  if (!element) return false;

  const tagName = element.tagName.toLowerCase();
  if (tagName === 'input' || tagName === 'textarea' || tagName === 'select') {
    return true;
  }

  // Check for contenteditable
  if ((element as HTMLElement).isContentEditable) {
    return true;
  }

  // Check for Ace editor
  if (element.closest('.ace_editor')) {
    return true;
  }

  return false;
}

interface ShortcutProviderProps {
  children: ReactNode;
  /** Enable debug logging */
  debug?: boolean;
}

/**
 * Provider component that manages keyboard shortcut registration and handling
 */
export const ShortcutProvider: FC<ShortcutProviderProps> = ({
  children,
  debug = false,
}) => {
  const [shortcuts, setShortcuts] = useState<Map<string, RegisteredShortcut>>(
    () => new Map<string, RegisteredShortcut>(),
  );
  const [isHelpOpen, setIsHelpOpen] = useState(false);
  const [platform] = useState<PlatformInfo>(detectPlatform);

  // Register a shortcut
  const registerShortcut = useCallback(
    (config: ShortcutConfig): (() => void) => {
      const registered: RegisteredShortcut = {
        ...config,
        namespace: config.namespace || 'global',
        priority: config.priority || ShortcutPriority.NORMAL,
        enabled: config.enabled !== false,
        preventDefault: config.preventDefault !== false,
        ignoreInputElements: config.ignoreInputElements !== false,
        registeredAt: Date.now(),
      };

      setShortcuts((prev: Map<string, RegisteredShortcut>) => {
        const next = new Map(prev);
        next.set(config.id, registered);
        return next;
      });

      if (debug) {
        console.log(
          `[KeyboardShortcuts] Registered: ${config.id} (${config.keys})`,
        );
      }

      // Return cleanup function
      return () => {
        setShortcuts((prev: Map<string, RegisteredShortcut>) => {
          const next = new Map(prev);
          next.delete(config.id);
          return next;
        });
        if (debug) {
          console.log(`[KeyboardShortcuts] Unregistered: ${config.id}`);
        }
      };
    },
    [debug],
  );

  // Unregister a shortcut by ID
  const unregisterShortcut = useCallback((id: string) => {
    setShortcuts((prev: Map<string, RegisteredShortcut>) => {
      const next = new Map(prev);
      next.delete(id);
      return next;
    });
  }, []);

  // Get all shortcuts
  const getShortcuts = useCallback((): RegisteredShortcut[] => {
    const values = shortcuts.values() as IterableIterator<RegisteredShortcut>;
    return Array.from(values).sort(
      (a: RegisteredShortcut, b: RegisteredShortcut) =>
        (b.priority || 0) - (a.priority || 0),
    );
  }, [shortcuts]);

  // Get shortcuts by namespace
  const getShortcutsByNamespace = useCallback(
    (namespace: ShortcutNamespace): RegisteredShortcut[] =>
      getShortcuts().filter(
        (s: RegisteredShortcut) => s.namespace === namespace,
      ),
    [getShortcuts],
  );

  // Help modal controls
  const openHelp = useCallback(() => setIsHelpOpen(true), []);
  const closeHelp = useCallback(() => setIsHelpOpen(false), []);

  // Handle keyboard events
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      const { activeElement } = document;
      const isInInput = isInputElement(activeElement);

      // Get enabled shortcuts sorted by priority (highest first)
      const enabledShortcuts: RegisteredShortcut[] = Array.from(
        shortcuts.values() as IterableIterator<RegisteredShortcut>,
      )
        .filter((s: RegisteredShortcut) => s.enabled !== false)
        .sort(
          (a: RegisteredShortcut, b: RegisteredShortcut) =>
            (b.priority || 0) - (a.priority || 0),
        );

      for (const shortcut of enabledShortcuts) {
        // Skip if we should ignore input elements and we're in one
        if (shortcut.ignoreInputElements && isInInput) {
          continue;
        }

        // Check if the event matches this shortcut
        if (matchesShortcut(event, shortcut.keys, platform.isMac)) {
          if (debug) {
            console.log(`[KeyboardShortcuts] Matched: ${shortcut.id}`);
          }

          // Prevent default if configured
          if (shortcut.preventDefault) {
            event.preventDefault();
            event.stopPropagation();
          }

          // Call the handler
          try {
            shortcut.handler(event);
          } catch (error) {
            console.error(
              `[KeyboardShortcuts] Handler error for ${shortcut.id}:`,
              error,
            );
          }

          // Stop processing other shortcuts (highest priority wins)
          return;
        }
      }
    };

    // Use capture phase to intercept before other handlers
    document.addEventListener('keydown', handleKeyDown, true);

    return () => {
      document.removeEventListener('keydown', handleKeyDown, true);
    };
  }, [shortcuts, platform.isMac, debug]);

  const contextValue = useMemo<ShortcutContextValue>(
    () => ({
      registerShortcut,
      unregisterShortcut,
      getShortcuts,
      getShortcutsByNamespace,
      platform,
      isHelpOpen,
      openHelp,
      closeHelp,
    }),
    [
      registerShortcut,
      unregisterShortcut,
      getShortcuts,
      getShortcutsByNamespace,
      platform,
      isHelpOpen,
      openHelp,
      closeHelp,
    ],
  );

  return (
    <ShortcutContext.Provider value={contextValue}>
      {children}
    </ShortcutContext.Provider>
  );
};

/**
 * Hook to access the shortcut context
 * @throws Error if used outside of ShortcutProvider
 */
export function useShortcutContext(): ShortcutContextValue {
  const context = useContext(ShortcutContext);
  if (!context) {
    throw new Error(
      'useShortcutContext must be used within a ShortcutProvider',
    );
  }
  return context;
}

export default ShortcutProvider;

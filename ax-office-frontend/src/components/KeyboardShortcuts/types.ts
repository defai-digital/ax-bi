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
 * Keyboard shortcut type definitions and utilities
 */

/** Modifier keys that can be combined with other keys */
export type ModifierKey = 'ctrl' | 'shift' | 'alt' | 'meta' | 'mod';

/** Common key names */
export type KeyName =
  | 'a'
  | 'b'
  | 'c'
  | 'd'
  | 'e'
  | 'f'
  | 'g'
  | 'h'
  | 'i'
  | 'j'
  | 'k'
  | 'l'
  | 'm'
  | 'n'
  | 'o'
  | 'p'
  | 'q'
  | 'r'
  | 's'
  | 't'
  | 'u'
  | 'v'
  | 'w'
  | 'x'
  | 'y'
  | 'z'
  | '0'
  | '1'
  | '2'
  | '3'
  | '4'
  | '5'
  | '6'
  | '7'
  | '8'
  | '9'
  | 'enter'
  | 'escape'
  | 'space'
  | 'tab'
  | 'backspace'
  | 'delete'
  | 'arrowup'
  | 'arrowdown'
  | 'arrowleft'
  | 'arrowright'
  | 'home'
  | 'end'
  | 'pageup'
  | 'pagedown'
  | '/'
  | '?'
  | '['
  | ']'
  | ','
  | '.'
  | ';'
  | ':';

/**
 * A keyboard shortcut string like "mod+k" or "ctrl+shift+d"
 * Use "mod" for platform-aware modifier (Cmd on Mac, Ctrl on Windows/Linux)
 */
export type ShortcutString = string;

/** Namespaces for organizing shortcuts by context */
export type ShortcutNamespace =
  | 'global'
  | 'dashboard'
  | 'explore'
  | 'sqlLab'
  | 'home'
  | string;

/** Priority levels for shortcut handling */
export enum ShortcutPriority {
  LOW = 0,
  NORMAL = 10,
  HIGH = 20,
  HIGHEST = 100,
}

/** Configuration for a single keyboard shortcut */
export interface ShortcutConfig {
  /** Unique identifier for the shortcut */
  id: string;
  /** The key combination (e.g., "mod+k", "ctrl+shift+d") */
  keys: ShortcutString;
  /** Human-readable description of what the shortcut does */
  description: string;
  /** The callback to execute when the shortcut is triggered */
  handler: (event: KeyboardEvent) => void;
  /** Namespace for organizing shortcuts */
  namespace?: ShortcutNamespace;
  /** Priority for handling overlapping shortcuts */
  priority?: ShortcutPriority;
  /** Whether the shortcut is enabled */
  enabled?: boolean;
  /** Prevent default browser behavior */
  preventDefault?: boolean;
  /** Only trigger when no input is focused */
  ignoreInputElements?: boolean;
  /** Icon to display in shortcut help UI */
  icon?: string;
  /** Category for grouping in help UI */
  category?: string;
}

/** Registered shortcut entry with internal metadata */
export interface RegisteredShortcut extends ShortcutConfig {
  /** Timestamp when the shortcut was registered */
  registeredAt: number;
}

/** Options for the shortcut registry */
export interface ShortcutRegistryOptions {
  /** Whether to enable debug logging */
  debug?: boolean;
  /** Default namespace for shortcuts */
  defaultNamespace?: ShortcutNamespace;
  /** Default priority for shortcuts */
  defaultPriority?: ShortcutPriority;
}

/** Information about the current platform */
export interface PlatformInfo {
  /** Whether the platform is macOS */
  isMac: boolean;
  /** Whether the platform is Windows */
  isWindows: boolean;
  /** Whether the platform is Linux */
  isLinux: boolean;
  /** Display name for the "mod" key on this platform */
  modKeyDisplay: string;
  /** Symbol for the mod key */
  modKeySymbol: string;
}

/** Event data passed to shortcut handlers */
export interface ShortcutEvent {
  /** The original keyboard event */
  originalEvent: KeyboardEvent;
  /** The shortcut configuration that matched */
  shortcut: ShortcutConfig;
  /** Whether to prevent the default action */
  preventDefault: () => void;
  /** Whether to stop propagation */
  stopPropagation: () => void;
}

/**
 * Parse a shortcut string into its component parts
 * @param shortcut - The shortcut string (e.g., "mod+shift+k")
 * @returns Object with modifier flags and the key
 */
export function parseShortcut(shortcut: string): {
  ctrl: boolean;
  shift: boolean;
  alt: boolean;
  meta: boolean;
  key: string;
} {
  const parts = shortcut.toLowerCase().split('+');
  const key = parts[parts.length - 1];

  return {
    ctrl: parts.includes('ctrl'),
    shift: parts.includes('shift'),
    alt: parts.includes('alt'),
    meta: parts.includes('meta') || parts.includes('mod'),
    key,
  };
}

/**
 * Format a shortcut string for display based on the current platform
 * @param shortcut - The shortcut string (e.g., "mod+k")
 * @param platform - The platform info
 * @returns Formatted string for display (e.g., "⌘K" on Mac, "Ctrl+K" on Windows)
 */
export function formatShortcutForDisplay(
  shortcut: string,
  platform: PlatformInfo,
): string {
  const parts = shortcut.toLowerCase().split('+');
  const formatted = parts.map(part => {
    switch (part) {
      case 'mod':
        return platform.modKeySymbol;
      case 'ctrl':
        return platform.isMac ? '⌃' : 'Ctrl';
      case 'shift':
        return platform.isMac ? '⇧' : 'Shift';
      case 'alt':
        return platform.isMac ? '⌥' : 'Alt';
      case 'meta':
        return platform.isMac ? '⌘' : 'Win';
      case 'enter':
        return '↵';
      case 'escape':
        return platform.isMac ? '⎋' : 'Esc';
      case 'backspace':
        return platform.isMac ? '⌫' : 'Backspace';
      case 'delete':
        return platform.isMac ? '⌦' : 'Del';
      case 'arrowup':
        return '↑';
      case 'arrowdown':
        return '↓';
      case 'arrowleft':
        return '←';
      case 'arrowright':
        return '→';
      case 'tab':
        return '⇥';
      case 'space':
        return 'Space';
      default:
        return part.toUpperCase();
    }
  });

  // On Mac, join without separator; on Windows/Linux, use +
  return platform.isMac ? formatted.join('') : formatted.join('+');
}

/**
 * Check if a keyboard event matches a shortcut string
 */
export function matchesShortcut(
  event: KeyboardEvent,
  shortcut: ShortcutString,
  isMac: boolean,
): boolean {
  const parsed = parseShortcut(shortcut);

  // Handle 'mod' key based on platform
  const modPressed = isMac ? event.metaKey : event.ctrlKey;
  const ctrlPressed = event.ctrlKey;

  const ctrlMatch = parsed.ctrl ? (isMac ? ctrlPressed : modPressed) : true;
  const metaMatch = parsed.meta ? modPressed : true;
  const shiftMatch = parsed.shift ? event.shiftKey : !event.shiftKey;
  const altMatch = parsed.alt ? event.altKey : !event.altKey;

  // Handle 'mod' specifically
  if (shortcut.toLowerCase().includes('mod')) {
    const keyMatch = event.key.toLowerCase() === parsed.key;
    return modPressed && shiftMatch && altMatch && keyMatch;
  }

  const keyMatch = event.key.toLowerCase() === parsed.key;
  return ctrlMatch && metaMatch && shiftMatch && altMatch && keyMatch;
}

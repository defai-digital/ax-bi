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
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  FC,
  ReactNode,
} from 'react';

/**
 * Command types for categorization
 */
export type CommandType = 'navigation' | 'action' | 'recent' | 'help' | string;

/**
 * Command configuration
 */
export interface Command {
  /** Unique identifier */
  id: string;
  /** Display name */
  name: string;
  /** Optional description */
  description?: string;
  /** Command type for categorization */
  type: CommandType;
  /** Icon name or React node */
  icon?: string | ReactNode;
  /** Keyboard shortcut hint (e.g., "⌘K") */
  shortcut?: string;
  /** Whether the command is enabled */
  enabled?: boolean;
  /** The action to execute */
  action: () => void | Promise<void>;
  /** Keywords for search (in addition to name) */
  keywords?: string[];
}

/**
 * Command palette state
 */
interface CommandPaletteState {
  /** Whether the palette is open */
  isOpen: boolean;
  /** Open the palette */
  open: () => void;
  /** Close the palette */
  close: () => void;
  /** Toggle the palette */
  toggle: () => void;
  /** Register a command */
  registerCommand: (command: Command) => () => void;
  /** Unregister a command */
  unregisterCommand: (id: string) => void;
  /** Get all registered commands */
  getCommands: () => Command[];
  /** Get commands filtered by type */
  getCommandsByType: (type: CommandType) => Command[];
  /** Live search query (the palette input value) */
  query: string;
  /** Update the palette search query */
  setQuery: (query: string) => void;
}

const CommandPaletteContext = createContext<CommandPaletteState | null>(null);

interface CommandPaletteProviderProps {
  children: ReactNode;
}

/**
 * Provider component for command palette functionality
 */
export const CommandPaletteProvider: FC<CommandPaletteProviderProps> = ({
  children,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [commands, setCommands] = useState<Map<string, Command>>(new Map());

  const open = useCallback(() => setIsOpen(true), []);
  const close = useCallback(() => setIsOpen(false), []);
  const toggle = useCallback(() => setIsOpen((prev: boolean) => !prev), []);

  const registerCommand = useCallback((command: Command): (() => void) => {
    setCommands((prev: Map<string, Command>) => {
      const next = new Map(prev);
      next.set(command.id, { ...command, enabled: command.enabled !== false });
      return next;
    });

    // Return cleanup function
    return () => {
      setCommands((prev: Map<string, Command>) => {
        const next = new Map(prev);
        next.delete(command.id);
        return next;
      });
    };
  }, []);

  const unregisterCommand = useCallback((id: string) => {
    setCommands((prev: Map<string, Command>) => {
      const next = new Map(prev);
      next.delete(id);
      return next;
    });
  }, []);

  const getCommands = useCallback((): Command[] => {
    const values = commands.values() as IterableIterator<Command>;
    return Array.from(values).filter((cmd: Command) => cmd.enabled !== false);
  }, [commands]);

  const getCommandsByType = useCallback(
    (type: CommandType): Command[] =>
      getCommands().filter((cmd: Command) => cmd.type === type),
    [getCommands],
  );

  const contextValue = useMemo<CommandPaletteState>(
    () => ({
      isOpen,
      open,
      close,
      toggle,
      registerCommand,
      unregisterCommand,
      getCommands,
      getCommandsByType,
      query,
      setQuery,
    }),
    [
      isOpen,
      open,
      close,
      toggle,
      registerCommand,
      unregisterCommand,
      getCommands,
      getCommandsByType,
      query,
      setQuery,
    ],
  );

  return (
    <CommandPaletteContext.Provider value={contextValue}>
      {children}
    </CommandPaletteContext.Provider>
  );
};

/**
 * Hook to access the command palette.
 * Throws if called outside a CommandPaletteProvider.
 */
export function useCommandPalette(): CommandPaletteState {
  const context = useContext(CommandPaletteContext);
  if (!context) {
    throw new Error(
      'useCommandPalette must be used within a CommandPaletteProvider',
    );
  }
  return context;
}

/**
 * Optional variant of useCommandPalette that returns null when no
 * CommandPaletteProvider is present. Safe to use in components that
 * may render outside the main app tree (e.g. embedded dashboards).
 */
export function useOptionalCommandPalette(): CommandPaletteState | null {
  return useContext(CommandPaletteContext);
}

/**
 * Hook to register a command.
 *
 * Registration is a side-effect with a cleanup, so it must run in an effect
 * (not useMemo, which never invokes the returned cleanup). The command is
 * re-registered only when its identifying fields change.
 */
export function useCommand(command: Command): void {
  const { registerCommand } = useCommandPalette();

  // Keep the latest command object without forcing re-registration on every
  // render (handlers/closures change identity each render).
  const commandRef = useRef(command);
  commandRef.current = command;

  useEffect(
    () => registerCommand(commandRef.current),
    // Re-register only when identifying fields change.
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [registerCommand, command.id, command.name, command.type, command.enabled],
  );
}

export default CommandPaletteProvider;

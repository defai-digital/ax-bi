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
import { FC, useState, useEffect, useMemo, useCallback, useRef } from 'react';
import { t } from '@apache-superset/core/translation';
import { styled } from '@apache-superset/core/theme';
import { Modal } from 'antd';
import Fuse from 'fuse.js';
import {
  useCommandPalette,
  Command,
  CommandType,
} from './CommandPaletteContext';

// Styled components
const PaletteModal = styled(Modal)`
  .ant-modal-content {
    padding: 0;
    border-radius: 12px;
    overflow: hidden;
  }
  .ant-modal-body {
    padding: 0;
  }
`;

const SearchContainer = styled.div`
  padding: ${({ theme }) => theme.paddingLG}px;
  border-bottom: 1px solid ${({ theme }) => theme.colorBorderSecondary};
`;

const SearchInput = styled.input`
  width: 100%;
  padding: ${({ theme }) => `${theme.paddingSM}px ${theme.paddingLG}px`};
  font-size: ${({ theme }) => theme.fontSizeLG}px;
  border: none;
  outline: none;
  background: ${({ theme }) => theme.colorBgContainer};
  color: ${({ theme }) => theme.colorText};

  &::placeholder {
    color: ${({ theme }) => theme.colorTextPlaceholder};
  }
`;

const CommandList = styled.div`
  max-height: 400px;
  overflow-y: auto;
  padding: ${({ theme }) => theme.paddingXS}px 0;
`;

const CommandGroup = styled.div`
  &:not(:first-child) {
    border-top: 1px solid ${({ theme }) => theme.colorBorderSecondary};
    margin-top: ${({ theme }) => theme.marginXS}px;
    padding-top: ${({ theme }) => theme.paddingXS}px;
  }
`;

const GroupHeader = styled.div`
  padding: ${({ theme }) => `${theme.paddingXS}px ${theme.paddingLG}px`};
  font-size: ${({ theme }) => theme.fontSizeSM}px;
  color: ${({ theme }) => theme.colorTextSecondary};
  text-transform: uppercase;
  letter-spacing: 0.5px;
`;

interface CommandItemProps {
  $isSelected: boolean;
}

const CommandItem = styled.div<CommandItemProps>`
  display: flex;
  align-items: center;
  gap: ${({ theme }) => theme.marginSM}px;
  padding: ${({ theme }) => `${theme.paddingSM}px ${theme.paddingLG}px`};
  cursor: pointer;
  background: ${({ $isSelected, theme }) =>
    $isSelected ? theme.colorPrimaryBg : 'transparent'};

  &:hover {
    background: ${({ theme }) => theme.colorPrimaryBg};
  }
`;

const CommandIcon = styled.span`
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: ${({ theme }) => theme.fontSizeLG}px;
  color: ${({ theme }) => theme.colorTextSecondary};
`;

const CommandContent = styled.div`
  flex: 1;
  min-width: 0;
`;

const CommandName = styled.div`
  font-size: ${({ theme }) => theme.fontSize}px;
  color: ${({ theme }) => theme.colorText};
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
`;

const CommandDescription = styled.div`
  font-size: ${({ theme }) => theme.fontSizeSM}px;
  color: ${({ theme }) => theme.colorTextSecondary};
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
`;

const CommandShortcut = styled.span`
  font-size: ${({ theme }) => theme.fontSizeSM}px;
  color: ${({ theme }) => theme.colorTextSecondary};
  padding: ${({ theme }) => `${theme.paddingXXS}px ${theme.paddingXS}px`};
  background: ${({ theme }) => theme.colorFillSecondary};
  border-radius: ${({ theme }) => theme.borderRadiusSM}px;
`;

const EmptyState = styled.div`
  padding: ${({ theme }) => theme.paddingXL}px;
  text-align: center;
  color: ${({ theme }) => theme.colorTextSecondary};
`;

// Default icons for command types
const TYPE_ICONS: Record<CommandType, string> = {
  navigation: '🧭',
  action: '⚡',
  recent: '🕐',
  help: '❓',
};

// Group labels
const TYPE_LABELS: Record<CommandType, string> = {
  navigation: 'Navigation',
  action: 'Actions',
  recent: 'Recent',
  help: 'Help',
};

interface CommandPaletteProps {
  /** Placeholder text for search */
  placeholder?: string;
  /** Maximum number of results to show */
  maxResults?: number;
}

/**
 * Command Palette component - provides quick access to all commands
 */
export const CommandPalette: FC<CommandPaletteProps> = ({
  placeholder = t('Type a command or search...'),
  maxResults = 20,
}) => {
  const { isOpen, close, getCommands } = useCommandPalette();
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);

  // Get all commands
  const commands = useMemo(() => getCommands(), [getCommands]);

  // Setup fuzzy search
  const fuse = useMemo(
    () =>
      new Fuse(commands, {
        keys: ['name', 'description', 'keywords'],
        threshold: 0.3,
        includeScore: true,
      }),
    [commands],
  );

  // Filter commands based on search
  const filteredCommands = useMemo(() => {
    if (!searchQuery.trim()) {
      return commands.slice(0, maxResults);
    }

    const results = fuse.search(searchQuery);
    return results.slice(0, maxResults).map(result => result.item);
  }, [searchQuery, commands, fuse, maxResults]);

  // Group commands by type
  const groupedCommands = useMemo(() => {
    const groups = new Map<CommandType, Command[]>();

    filteredCommands.forEach(cmd => {
      const { type } = cmd;
      if (!groups.has(type)) {
        groups.set(type, []);
      }
      groups.get(type)!.push(cmd);
    });

    return groups;
  }, [filteredCommands]);

  // Reset state when palette opens
  useEffect(() => {
    if (isOpen) {
      setSearchQuery('');
      setSelectedIndex(0);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [isOpen]);

  // Scroll selected item into view
  useEffect(() => {
    if (!listRef.current) return;

    const selectedElement = listRef.current.querySelector(
      `[data-index="${selectedIndex}"]`,
    );
    if (selectedElement) {
      selectedElement.scrollIntoView({ block: 'nearest' });
    }
  }, [selectedIndex]);

  // Handle command execution
  const executeCommand = useCallback(
    (command: Command) => {
      close();
      command.action();
    },
    [close],
  );

  // Flatten grouped commands for index-based selection. selectedIndex,
  // data-index attributes, and keyboard navigation all index into this
  // (grouped/display) order so they stay in sync.
  const flatCommands = useMemo(
    () => Array.from(groupedCommands.values()).flat(),
    [groupedCommands],
  );

  // Handle keyboard navigation
  const handleKeyDown = useCallback(
    (event: React.KeyboardEvent) => {
      const totalItems = flatCommands.length;

      switch (event.key) {
        case 'ArrowDown':
          if (totalItems === 0) break;
          event.preventDefault();
          setSelectedIndex(prev => (prev + 1) % totalItems);
          break;

        case 'ArrowUp':
          if (totalItems === 0) break;
          event.preventDefault();
          setSelectedIndex(prev => (prev - 1 + totalItems) % totalItems);
          break;

        case 'Enter':
          event.preventDefault();
          if (flatCommands[selectedIndex]) {
            executeCommand(flatCommands[selectedIndex]);
          }
          break;

        case 'Escape':
          event.preventDefault();
          close();
          break;
      }
    },
    [flatCommands, selectedIndex, executeCommand, close],
  );

  let itemIndex = 0;

  return (
    <PaletteModal
      open={isOpen}
      onCancel={close}
      footer={null}
      centered
      width={560}
      destroyOnClose
    >
      <SearchContainer>
        <SearchInput
          ref={inputRef}
          type="text"
          placeholder={placeholder}
          value={searchQuery}
          onChange={e => {
            setSearchQuery(e.target.value);
            setSelectedIndex(0);
          }}
          onKeyDown={handleKeyDown}
        />
      </SearchContainer>

      <CommandList ref={listRef}>
        {filteredCommands.length === 0 ? (
          <EmptyState>{t('No commands found')}</EmptyState>
        ) : (
          Array.from(groupedCommands.entries()).map(([type, cmds]) => (
            <CommandGroup key={type}>
              <GroupHeader>{TYPE_LABELS[type] || type}</GroupHeader>
              {cmds.map(cmd => {
                const currentIndex = itemIndex++;
                const isSelected = currentIndex === selectedIndex;

                return (
                  <CommandItem
                    key={cmd.id}
                    $isSelected={isSelected}
                    data-index={currentIndex}
                    onClick={() => executeCommand(cmd)}
                    onMouseEnter={() => setSelectedIndex(currentIndex)}
                  >
                    <CommandIcon>
                      {typeof cmd.icon === 'string'
                        ? cmd.icon
                        : cmd.icon || TYPE_ICONS[type] || '⚡'}
                    </CommandIcon>
                    <CommandContent>
                      <CommandName>{cmd.name}</CommandName>
                      {cmd.description && (
                        <CommandDescription>
                          {cmd.description}
                        </CommandDescription>
                      )}
                    </CommandContent>
                    {cmd.shortcut && (
                      <CommandShortcut>{cmd.shortcut}</CommandShortcut>
                    )}
                  </CommandItem>
                );
              })}
            </CommandGroup>
          ))
        )}
      </CommandList>
    </PaletteModal>
  );
};

export default CommandPalette;

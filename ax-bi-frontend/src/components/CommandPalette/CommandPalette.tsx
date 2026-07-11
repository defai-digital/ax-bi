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
  FC,
  KeyboardEvent,
  ReactNode,
  useState,
  useEffect,
  useMemo,
  useCallback,
  useRef,
} from 'react';
import { t } from '@apache-superset/core/translation';
import { styled } from '@apache-superset/core/theme';
import { Icons, Modal } from '@superset-ui/core/components';
import Fuse from 'fuse.js';
import {
  useCommandPalette,
  Command,
  CommandType,
} from './CommandPaletteContext';

const PaletteModal = styled(Modal)`
  .ant-modal-content {
    padding: 0;
    border-radius: ${({ theme }) => theme.borderRadiusLG}px;
    overflow: hidden;
    box-shadow: ${({ theme }) => theme.boxShadowSecondary};
  }
  .ant-modal-close {
    display: none;
  }
  .ant-modal-body {
    padding: 0;
    overflow: hidden;
  }
`;

const SearchContainer = styled.div`
  display: flex;
  align-items: center;
  gap: ${({ theme }) => theme.marginSM}px;
  padding: ${({ theme }) => `${theme.padding}px ${theme.paddingLG}px`};
  border-bottom: 1px solid ${({ theme }) => theme.colorBorderSecondary};
  background: ${({ theme }) => theme.colorBgElevated};
`;

const SearchIcon = styled.span`
  display: flex;
  color: ${({ theme }) => theme.colorTextTertiary};
`;

const SearchInput = styled.input`
  width: 100%;
  padding: ${({ theme }) => `${theme.paddingXS}px 0`};
  font-size: ${({ theme }) => theme.fontSizeLG}px;
  border: none;
  outline: none;
  background: transparent;
  color: ${({ theme }) => theme.colorText};
  line-height: ${({ theme }) => theme.lineHeightLG};

  &::placeholder {
    color: ${({ theme }) => theme.colorTextPlaceholder};
  }
`;

const SearchHint = styled.span`
  flex: 0 0 auto;
  color: ${({ theme }) => theme.colorTextTertiary};
  font-size: ${({ theme }) => theme.fontSizeSM}px;

  @media (max-width: 576px) {
    display: none;
  }
`;

const CommandList = styled.div`
  max-height: min(448px, calc(100vh - 184px));
  overflow-y: auto;
  padding: ${({ theme }) => theme.paddingSM}px;
  background: ${({ theme }) => theme.colorBgContainer};
`;

const CommandGroup = styled.div`
  &:not(:first-child) {
    margin-top: ${({ theme }) => theme.marginXS}px;
  }
`;

const GroupHeader = styled.div`
  padding: ${({ theme }) => `${theme.paddingXS}px ${theme.paddingSM}px`};
  font-size: ${({ theme }) => theme.fontSizeSM}px;
  color: ${({ theme }) => theme.colorTextSecondary};
  text-transform: uppercase;
  letter-spacing: 0;
  font-weight: ${({ theme }) => theme.fontWeightStrong};
`;

interface CommandItemProps {
  $isSelected: boolean;
}

const CommandItem = styled.div<CommandItemProps>`
  display: flex;
  align-items: center;
  gap: ${({ theme }) => theme.marginSM}px;
  min-height: 56px;
  padding: ${({ theme }) => `${theme.paddingSM}px ${theme.padding}px`};
  cursor: pointer;
  border-radius: ${({ theme }) => theme.borderRadius}px;
  background: ${({ $isSelected, theme }) =>
    $isSelected ? theme.colorPrimaryBg : 'transparent'};
  outline: none;

  &:hover,
  &:focus-visible {
    background: ${({ theme }) => theme.colorPrimaryBg};
  }

  &:focus-visible {
    box-shadow: inset 0 0 0 2px ${({ theme }) => theme.colorPrimaryBorder};
  }
`;

const CommandIcon = styled.span`
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 auto;
  border-radius: ${({ theme }) => theme.borderRadius}px;
  color: ${({ theme }) => theme.colorPrimary};
  background: ${({ theme }) => theme.colorFillQuaternary};
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
  padding: ${({ theme }) => `${theme.paddingXXS}px ${theme.paddingSM}px`};
  background: ${({ theme }) => theme.colorFillSecondary};
  border-radius: ${({ theme }) => theme.borderRadiusSM}px;
  white-space: nowrap;
`;

const EmptyState = styled.div`
  padding: ${({ theme }) => `${theme.paddingXL * 2}px ${theme.paddingXL}px`};
  text-align: center;
  color: ${({ theme }) => theme.colorTextSecondary};
`;

const TYPE_ICONS: Record<string, ReactNode> = {
  navigation: <Icons.DashboardOutlined iconSize="m" />,
  action: <Icons.ThunderboltOutlined iconSize="m" />,
  recent: <Icons.HistoryOutlined iconSize="m" />,
  help: <Icons.QuestionCircleOutlined iconSize="m" />,
  asset: <Icons.SearchOutlined iconSize="m" />,
};

const TYPE_LABELS: Record<string, string> = {
  navigation: t('Navigation'),
  action: t('Actions'),
  recent: t('Recent'),
  help: t('Help'),
  asset: t('Dashboards & charts'),
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

  const commands = useMemo(() => getCommands(), [getCommands]);

  const fuse = useMemo(
    () =>
      new Fuse(commands, {
        keys: ['name', 'description', 'keywords'],
        threshold: 0.3,
        includeScore: true,
      }),
    [commands],
  );

  const filteredCommands = useMemo(() => {
    if (!searchQuery.trim()) {
      return commands.slice(0, maxResults);
    }

    const results = fuse.search(searchQuery);
    return results.slice(0, maxResults).map(result => result.item);
  }, [searchQuery, commands, fuse, maxResults]);

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

  useEffect(() => {
    if (isOpen) {
      setSearchQuery('');
      setSelectedIndex(0);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [isOpen]);

  // Notify asset-search hook of the live query (debounced search elsewhere).
  useEffect(() => {
    if (!isOpen) {
      return;
    }
    window.dispatchEvent(
      new CustomEvent('axbi-command-palette-query', { detail: searchQuery }),
    );
  }, [searchQuery, isOpen]);

  // Flatten grouped commands for index-based selection. selectedIndex,
  // data-index attributes, and keyboard navigation all index into this
  // (grouped/display) order so they stay in sync.
  const flatCommands = useMemo(
    () => Array.from(groupedCommands.values()).flat(),
    [groupedCommands],
  );

  // Keep selection in range when the filtered list shrinks (search, unregister).
  useEffect(() => {
    if (flatCommands.length === 0) {
      if (selectedIndex !== 0) {
        setSelectedIndex(0);
      }
      return;
    }
    if (selectedIndex > flatCommands.length - 1) {
      setSelectedIndex(flatCommands.length - 1);
    }
  }, [flatCommands.length, selectedIndex]);

  useEffect(() => {
    if (!listRef.current) return;

    const selectedElement = listRef.current.querySelector(
      `[data-index="${selectedIndex}"]`,
    );
    if (selectedElement) {
      selectedElement.scrollIntoView({ block: 'nearest' });
    }
  }, [selectedIndex]);

  const executeCommand = useCallback(
    (command: Command) => {
      close();
      command.action();
    },
    [close],
  );

  const handleKeyDown = useCallback(
    (event: KeyboardEvent) => {
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

  const renderCommandIcon = (command: Command, type: CommandType) =>
    typeof command.icon === 'string'
      ? command.icon
      : command.icon || TYPE_ICONS[type] || TYPE_ICONS.action;

  let itemIndex = 0;

  return (
    <PaletteModal
      show={isOpen}
      onHide={close}
      footer={null}
      hideFooter
      centered
      width={640}
      title={t('Command palette')}
      name="command-palette"
      destroyOnHidden
    >
      <SearchContainer>
        <SearchIcon>
          <Icons.SearchOutlined iconSize="l" />
        </SearchIcon>
        <SearchInput
          ref={inputRef}
          type="text"
          role="combobox"
          aria-label={t('Search commands')}
          aria-expanded={isOpen}
          aria-controls="axbi-command-palette-list"
          aria-autocomplete="list"
          aria-activedescendant={
            flatCommands[selectedIndex]
              ? `axbi-command-option-${flatCommands[selectedIndex].id}`
              : undefined
          }
          placeholder={placeholder}
          value={searchQuery}
          onChange={e => {
            setSearchQuery(e.target.value);
            setSelectedIndex(0);
          }}
          onKeyDown={handleKeyDown}
        />
        <SearchHint>{t('Esc to close')}</SearchHint>
      </SearchContainer>

      <CommandList
        id="axbi-command-palette-list"
        ref={listRef}
        role="listbox"
        aria-label={t('Commands')}
      >
        {filteredCommands.length === 0 ? (
          <EmptyState>{t('No commands found')}</EmptyState>
        ) : (
          Array.from(groupedCommands.entries()).map(([type, cmds]) => (
            <CommandGroup key={type}>
              <GroupHeader>{TYPE_LABELS[type] || type}</GroupHeader>
              {cmds.map(cmd => {
                const currentIndex = itemIndex;
                itemIndex += 1;
                const isSelected = currentIndex === selectedIndex;

                return (
                  <CommandItem
                    id={`axbi-command-option-${cmd.id}`}
                    key={cmd.id}
                    $isSelected={isSelected}
                    data-index={currentIndex}
                    role="option"
                    aria-selected={isSelected}
                    tabIndex={-1}
                    onClick={() => executeCommand(cmd)}
                    onMouseEnter={() => setSelectedIndex(currentIndex)}
                  >
                    <CommandIcon>{renderCommandIcon(cmd, type)}</CommandIcon>
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

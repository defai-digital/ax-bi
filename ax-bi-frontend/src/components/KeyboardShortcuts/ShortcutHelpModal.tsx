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
import { FC, useMemo } from 'react';
import { t } from '@apache-superset/core/translation';
import { styled } from '@apache-superset/core/theme';
import { Modal } from '@superset-ui/core/components';
import { useShortcutContext } from './ShortcutProvider';
import { formatShortcutForDisplay, RegisteredShortcut } from './types';

const List = styled.div`
  max-height: min(420px, 60vh);
  overflow-y: auto;
`;

const Group = styled.div`
  margin-bottom: ${({ theme }) => theme.sizeUnit * 4}px;
`;

const GroupTitle = styled.div`
  font-size: ${({ theme }) => theme.fontSizeSM}px;
  font-weight: ${({ theme }) => theme.fontWeightStrong};
  color: ${({ theme }) => theme.colorTextSecondary};
  text-transform: uppercase;
  margin-bottom: ${({ theme }) => theme.sizeUnit * 2}px;
`;

const Row = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: ${({ theme }) => theme.sizeUnit * 3}px;
  padding: ${({ theme }) => theme.sizeUnit * 1.5}px 0;
  border-bottom: 1px solid ${({ theme }) => theme.colorBorderSecondary};
`;

const Description = styled.div`
  color: ${({ theme }) => theme.colorText};
  font-size: ${({ theme }) => theme.fontSize}px;
`;

const Keys = styled.kbd`
  font-family: ${({ theme }) => theme.fontFamilyCode};
  font-size: ${({ theme }) => theme.fontSizeSM}px;
  padding: ${({ theme }) =>
    `${theme.sizeUnit}px ${theme.sizeUnit * 2}px`};
  background: ${({ theme }) => theme.colorFillSecondary};
  border-radius: ${({ theme }) => theme.borderRadiusSM}px;
  color: ${({ theme }) => theme.colorText};
  white-space: nowrap;
`;

const Empty = styled.div`
  color: ${({ theme }) => theme.colorTextSecondary};
  padding: ${({ theme }) => theme.sizeUnit * 4}px 0;
`;

function groupKey(shortcut: RegisteredShortcut): string {
  return shortcut.category || shortcut.namespace || 'global';
}

/**
 * Lists registered keyboard shortcuts. Controlled by ShortcutProvider isHelpOpen.
 */
export const ShortcutHelpModal: FC = () => {
  const { isHelpOpen, closeHelp, getShortcuts, platform } = useShortcutContext();

  const groups = useMemo(() => {
    const map = new Map<string, RegisteredShortcut[]>();
    getShortcuts()
      .filter(s => s.enabled !== false && s.description)
      .forEach(s => {
        const key = groupKey(s);
        if (!map.has(key)) {
          map.set(key, []);
        }
        map.get(key)!.push(s);
      });
    return Array.from(map.entries()).sort(([a], [b]) => a.localeCompare(b));
  }, [getShortcuts, isHelpOpen]);

  return (
    <Modal
      show={isHelpOpen}
      onHide={closeHelp}
      title={t('Keyboard shortcuts')}
      footer={null}
      responsive
      destroyOnClose
      data-test="shortcut-help-modal"
    >
      {groups.length === 0 ? (
        <Empty>{t('No shortcuts registered yet.')}</Empty>
      ) : (
        <List>
          {groups.map(([name, items]) => (
            <Group key={name}>
              <GroupTitle>{name}</GroupTitle>
              {items.map(item => (
                <Row key={item.id}>
                  <Description>{item.description}</Description>
                  <Keys>{formatShortcutForDisplay(item.keys, platform)}</Keys>
                </Row>
              ))}
            </Group>
          ))}
        </List>
      )}
    </Modal>
  );
};

export default ShortcutHelpModal;

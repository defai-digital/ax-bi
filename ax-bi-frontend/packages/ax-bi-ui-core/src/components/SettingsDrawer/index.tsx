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
import { useEffect, useMemo, useState } from 'react';
import { styled, useTheme } from '@ax-bi/core/theme';
import { t } from '@ax-bi/core/translation';
import { Drawer } from '../Drawer';
import Tabs from '../Tabs';
import { ConfirmModal } from '../ConfirmModal';
import type { SettingsDrawerProps, SettingsDrawerWidth } from './types';

// Width presets are multiples of the theme sizeUnit so they scale with the
// theme: 'default' = 600px and 'wide' = 960px at the default 4px sizeUnit.
const WIDTH_PRESET_SIZE_UNITS: Record<
  Exclude<SettingsDrawerWidth, number>,
  number
> = {
  default: 150,
  wide: 240,
};

const SectionContent = styled.div`
  ${({ theme }) => `
    padding: ${theme.sizeUnit * 4}px ${theme.sizeUnit * 6}px;
  `}
`;

const FooterActions = styled.div`
  ${({ theme }) => `
    display: flex;
    justify-content: flex-end;
    align-items: center;
    gap: ${theme.sizeUnit * 2}px;
  `}
`;

export const SettingsDrawer = ({
  open,
  onClose,
  title,
  width = 'default',
  sections,
  activeSection,
  onSectionChange,
  footer,
  dirty = false,
  onConfirmClose,
  children,
  'data-test': dataTest,
}: SettingsDrawerProps) => {
  const theme = useTheme();
  const [confirmCloseVisible, setConfirmCloseVisible] = useState(false);
  const hasSections = !!sections?.length;

  const drawerWidth = useMemo(() => {
    if (typeof width === 'number') {
      return width;
    }
    return theme.sizeUnit * WIDTH_PRESET_SIZE_UNITS[width];
  }, [width, theme.sizeUnit]);

  // Hide the dirty-guard confirm if the drawer is closed externally
  useEffect(() => {
    if (!open) {
      setConfirmCloseVisible(false);
    }
  }, [open]);

  const requestClose = () => {
    if (dirty) {
      setConfirmCloseVisible(true);
    } else {
      onClose();
    }
  };

  const handleConfirmClose = () => {
    setConfirmCloseVisible(false);
    (onConfirmClose ?? onClose)();
  };

  const tabItems = useMemo(
    () =>
      sections?.map(({ key, label, content }) => ({
        key,
        label,
        children: <SectionContent>{content}</SectionContent>,
      })),
    [sections],
  );

  return (
    <>
      <Drawer
        open={open}
        onClose={requestClose}
        title={title}
        width={drawerWidth}
        placement="right"
        data-test={dataTest}
        footer={footer ? <FooterActions>{footer}</FooterActions> : null}
        styles={hasSections ? { body: { padding: 0 } } : undefined}
      >
        {hasSections ? (
          <Tabs
            tabPosition="left"
            fullHeight
            items={tabItems}
            {...(activeSection !== undefined
              ? { activeKey: activeSection }
              : { defaultActiveKey: sections[0].key })}
            onChange={onSectionChange}
          />
        ) : (
          children
        )}
      </Drawer>
      <ConfirmModal
        show={confirmCloseVisible}
        onHide={() => setConfirmCloseVisible(false)}
        onConfirm={handleConfirmClose}
        title={t('Unsaved changes')}
        body={t(
          'You have unsaved changes. Are you sure you want to discard them?',
        )}
        confirmText={t('Discard')}
        cancelText={t('Keep editing')}
        confirmButtonStyle="danger"
      />
    </>
  );
};

export type {
  SettingsDrawerProps,
  SettingsDrawerSection,
  SettingsDrawerWidth,
} from './types';

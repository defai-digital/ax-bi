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
import { FC } from 'react';
import { t } from '@apache-superset/core/translation';
import { styled } from '@apache-superset/core/theme';
import { Button, Icons, Space } from '@superset-ui/core/components';
import { usePWAInstall } from '../../hooks/usePWAInstall';

const InstallBanner = styled.div`
  position: fixed;
  bottom: ${({ theme }) => theme.marginLG}px;
  right: ${({ theme }) => theme.marginLG}px;
  display: flex;
  align-items: center;
  gap: ${({ theme }) => theme.margin}px;
  padding: ${({ theme }) => `${theme.padding}px ${theme.paddingLG}px`};
  background: ${({ theme }) => theme.colorBgContainer};
  border: 1px solid ${({ theme }) => theme.colorBorder};
  border-radius: ${({ theme }) => theme.borderRadiusLG}px;
  box-shadow: ${({ theme }) => theme.boxShadowSecondary};
  z-index: 1000;
  width: min(448px, calc(100vw - 32px));

  @media (max-width: 576px) {
    bottom: ${({ theme }) => theme.marginSM}px;
    left: ${({ theme }) => theme.marginSM}px;
    right: ${({ theme }) => theme.marginSM}px;
    width: auto;
    align-items: flex-start;
  }
`;

const InstallIcon = styled.div`
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 auto;
  width: 40px;
  height: 40px;
  border-radius: ${({ theme }) => theme.borderRadius}px;
  color: ${({ theme }) => theme.colorPrimary};
  background: ${({ theme }) => theme.colorPrimaryBg};
`;

const InstallContent = styled.div`
  display: flex;
  flex-direction: column;
  gap: 2px;
  flex: 1;
  min-width: 0;
`;

const InstallTitle = styled.div`
  font-size: ${({ theme }) => theme.fontSize}px;
  font-weight: ${({ theme }) => theme.fontWeightStrong};
  color: ${({ theme }) => theme.colorText};
`;

const InstallDescription = styled.div`
  font-size: ${({ theme }) => theme.fontSizeSM}px;
  color: ${({ theme }) => theme.colorTextSecondary};
  line-height: ${({ theme }) => theme.lineHeightSM};
`;

const CloseButton = styled.button`
  background: none;
  border: none;
  padding: ${({ theme }) => theme.paddingXXS}px;
  cursor: pointer;
  color: ${({ theme }) => theme.colorTextSecondary};
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: ${({ theme }) => theme.borderRadiusSM}px;

  &:hover,
  &:focus-visible {
    color: ${({ theme }) => theme.colorText};
    background: ${({ theme }) => theme.colorFillSecondary};
    outline: none;
  }
`;

/**
 * PWA Install Prompt component
 * Shows a subtle banner when the app can be installed
 */
export const PWAInstallPrompt: FC = () => {
  const { canInstall, promptInstall, dismissInstall, platform } =
    usePWAInstall();

  if (!canInstall) {
    return null;
  }

  const handleInstall = async () => {
    await promptInstall();
  };

  const getPlatformText = () => {
    if (platform?.includes('windows')) {
      return t('Install AX-BI on Windows');
    }
    if (platform?.includes('mac')) {
      return t('Install AX-BI on Mac');
    }
    if (platform?.includes('linux')) {
      return t('Install AX-BI on Linux');
    }
    return t('Install AX-BI');
  };

  return (
    <InstallBanner role="status">
      <InstallIcon aria-hidden="true">
        <Icons.DownloadOutlined iconSize="l" />
      </InstallIcon>
      <InstallContent>
        <InstallTitle>{getPlatformText()}</InstallTitle>
        <InstallDescription>
          {t('Get quick access from your desktop with the installable app')}
        </InstallDescription>
      </InstallContent>
      <Space>
        <Button
          buttonStyle="primary"
          aria-label={t('Install')}
          icon={<Icons.DownloadOutlined iconColor="light" />}
          onClick={handleInstall}
        >
          {t('Install')}
        </Button>
        <CloseButton onClick={dismissInstall} aria-label={t('Dismiss')}>
          <Icons.CloseOutlined iconSize="m" />
        </CloseButton>
      </Space>
    </InstallBanner>
  );
};

/**
 * PWA Install Button - for use in menus or toolbars
 */
export const PWAInstallButton: FC<{ size?: 'small' | 'middle' | 'large' }> = ({
  size = 'middle',
}) => {
  const { canInstall, promptInstall } = usePWAInstall();

  if (!canInstall) {
    return null;
  }

  return (
    <Button
      size={size}
      type="text"
      aria-label={t('Install App')}
      icon={<Icons.DownloadOutlined />}
      onClick={promptInstall}
    >
      {t('Install App')}
    </Button>
  );
};

export default PWAInstallPrompt;

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
import { Button, Space } from 'antd';
import { CloseOutlined, DownloadOutlined } from '@ant-design/icons';
import { usePWAInstall } from '../../hooks/usePWAInstall';

// Styled components
const InstallBanner = styled.div`
  position: fixed;
  bottom: ${({ theme }) => theme.marginLG}px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  align-items: center;
  gap: ${({ theme }) => theme.marginSM}px;
  padding: ${({ theme }) => `${theme.paddingSM}px ${theme.paddingLG}px`};
  background: ${({ theme }) => theme.colorBgContainer};
  border: 1px solid ${({ theme }) => theme.colorBorder};
  border-radius: ${({ theme }) => theme.borderRadiusLG}px;
  box-shadow: ${({ theme }) => theme.boxShadowSecondary};
  z-index: 1000;
  max-width: calc(100vw - 32px);

  @media (max-width: 576px) {
    bottom: ${({ theme }) => theme.marginSM}px;
    flex-direction: column;
    text-align: center;
  }
`;

const InstallContent = styled.div`
  display: flex;
  flex-direction: column;
  gap: 2px;
`;

const InstallTitle = styled.div`
  font-size: ${({ theme }) => theme.fontSize}px;
  font-weight: ${({ theme }) => theme.fontWeightStrong};
  color: ${({ theme }) => theme.colorText};
`;

const InstallDescription = styled.div`
  font-size: ${({ theme }) => theme.fontSizeSM}px;
  color: ${({ theme }) => theme.colorTextSecondary};
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

  &:hover {
    color: ${({ theme }) => theme.colorText};
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
    <InstallBanner>
      <InstallContent>
        <InstallTitle>{getPlatformText()}</InstallTitle>
        <InstallDescription>
          {t('Get quick access from your desktop with the installable app')}
        </InstallDescription>
      </InstallContent>
      <Space>
        <Button
          type="primary"
          icon={<DownloadOutlined />}
          onClick={handleInstall}
        >
          {t('Install')}
        </Button>
        <CloseButton onClick={dismissInstall} aria-label={t('Dismiss')}>
          <CloseOutlined />
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
      icon={<DownloadOutlined />}
      onClick={promptInstall}
    >
      {t('Install App')}
    </Button>
  );
};

export default PWAInstallPrompt;

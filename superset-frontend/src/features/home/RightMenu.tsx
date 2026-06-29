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
import { FC, PureComponent, useMemo } from 'react';
import { useSelector } from 'react-redux';
import { Link } from 'react-router-dom';
import { t } from '@apache-superset/core/translation';
import {
  getExtensionsRegistry,
  isFeatureEnabled,
  FeatureFlag,
  CACHE_KEY,
} from '@superset-ui/core';
import {
  styled,
  css,
  SupersetTheme,
  useTheme,
} from '@apache-superset/core/theme';
import {
  Tag,
  Tooltip,
  Menu,
  Icons,
  Typography,
  TelemetryPixel,
} from '@superset-ui/core/components';
import type { ItemType, MenuItem } from '@superset-ui/core/components/Menu';
import { ensureAppRoot } from 'src/utils/pathUtils';
import { findPermission } from 'src/utils/findPermission';
import { isEmbedded } from 'src/dashboard/util/isEmbedded';
import { RootState } from 'src/dashboard/types';
import { useThemeContext } from 'src/theme/ThemeProvider';
import { useThemeMenuItems } from 'src/hooks/useThemeMenuItems';
import { useOptionalCommandPalette } from 'src/components/CommandPalette';
import { useLanguageMenuItems } from './LanguagePicker';
import { RightMenuProps } from './types';
import { NAVBAR_MENU_POPUP_OFFSET } from './commonMenuData';

const extensionsRegistry = getExtensionsRegistry();

const StyledDiv = styled.div<{ align: string }>`
  display: flex;
  height: 100%;
  flex-direction: row;
  justify-content: ${({ align }) => align};
  align-items: center;
`;

const StyledMenuItemWithIcon = styled.div`
  display: flex;
  flex-direction: row;
  justify-content: space-between;
  align-items: center;
`;

const RightMenu = ({
  align,
  settings,
  navbarRight,
  isFrontendRoute,
  environmentTag,
}: RightMenuProps) => {
  const theme = useTheme();
  const commandPalette = useOptionalCommandPalette();
  const isMac = navigator.platform?.toLowerCase().includes('mac') ?? false;
  const dashboardId = useSelector<RootState, number | undefined>(
    state => state.dashboardInfo?.id,
  );
  const canUploadData = useSelector((state: RootState) =>
    findPermission('can_upload', 'Database', state.user?.roles),
  );
  const {
    setThemeMode,
    themeMode,
    clearLocalOverrides,
    hasDevOverride,
    canSetMode,
    canDetectOSPreference,
  } = useThemeContext();
  const RightMenuExtension = extensionsRegistry.get('navbar.right');
  const RightMenuItemIconExtension = extensionsRegistry.get(
    'navbar.right-menu.item.icon',
  );

  const handleLogout = () => {
    try {
      window.localStorage.removeItem('redux');
      window.sessionStorage.removeItem('login_attempted');
      // Purge the namespaced Cache API store so cached GET responses are not
      // retained on the device after the session ends. Best-effort: the
      // returned promise is not awaited since logout navigates away.
      if (typeof caches !== 'undefined') {
        caches.delete(CACHE_KEY).catch(() => {
          /* best-effort: ignore cache deletion failures */
        });
      }
    } catch (error) {
      console.warn('Failed to clear storage on logout:', error);
    }
  };

  // Use the theme menu hook
  const themeMenuItem = useThemeMenuItems({
    setThemeMode,
    themeMode,
    hasLocalOverride: hasDevOverride(),
    onClearLocalSettings: clearLocalOverrides,
    allowOSPreference: canDetectOSPreference(),
  });

  const languageMenuItem = useLanguageMenuItems({
    locale: navbarRight.locale || 'en',
    languages: navbarRight.languages || {},
  });

  // Build main menu items
  const menuItems = useMemo(() => {
    // Build settings menu items
    const buildSettingsMenuItems = (): MenuItem[] => {
      const items: MenuItem[] = [];

      // Create group (previously in the "+" dropdown)
      const createItems: MenuItem[] = [];
      if (!navbarRight.user_is_anonymous) {
        createItems.push({
          key: 'create-sql',
          label: <Link to="/sqllab?new=true">{t('SQL query')}</Link>,
          icon: <Icons.SearchOutlined />,
        });
        createItems.push({
          key: 'create-chart',
          label: (
            <Link
              to={
                Number.isInteger(dashboardId)
                  ? `/chart/add?dashboard_id=${dashboardId}`
                  : '/chart/add'
              }
            >
              {t('Chart')}
            </Link>
          ),
          icon: <Icons.BarChartOutlined />,
        });
        createItems.push({
          key: 'create-dashboard',
          label: (
            <Typography.Link href="/dashboard/new/">
              {t('Dashboard')}
            </Typography.Link>
          ),
          icon: <Icons.DashboardOutlined />,
        });
        if (
          canUploadData &&
          isFeatureEnabled(FeatureFlag.EnableLocalFileUpload)
        ) {
          createItems.push({
            key: 'create-upload-data',
            label: <Link to="/upload/">{t('Upload data')}</Link>,
            icon: <Icons.UploadOutlined />,
          });
        }
      }
      if (createItems.length > 0) {
        items.push({
          type: 'group',
          label: t('Create'),
          key: 'create-section',
          children: createItems,
        });
        items.push({ type: 'divider', key: 'create-divider' });
      }

      settings?.forEach((section, index) => {
        const sectionItems: MenuItem[] = [];

        section.childs?.forEach(child => {
          if (typeof child !== 'string') {
            const menuItemDisplay = RightMenuItemIconExtension ? (
              <StyledMenuItemWithIcon>
                {child.label}
                <RightMenuItemIconExtension menuChild={child} />
              </StyledMenuItemWithIcon>
            ) : (
              child.label
            );

            sectionItems.push({
              key: child.label,
              label: isFrontendRoute(child.url) ? (
                <Link to={child.url || ''}>{menuItemDisplay}</Link>
              ) : (
                <Typography.Link
                  href={child.url || ''}
                  css={css`
                    display: flex;
                    align-items: center;
                    line-height: ${theme.sizeUnit * 10}px;
                  `}
                >
                  {menuItemDisplay}
                </Typography.Link>
              ),
            });
          }
        });

        items.push({
          type: 'group',
          label: section.label,
          key: section.label,
          children: sectionItems,
        });

        if (index < settings.length - 1) {
          items.push({ type: 'divider', key: `divider_${index}` });
        }
      });

      if (!navbarRight.user_is_anonymous) {
        items.push({ type: 'divider', key: 'user-divider' });

        const userItems: MenuItem[] = [];
        if (navbarRight.user_info_url) {
          userItems.push({
            key: 'info',
            label: (
              <Typography.Link href={ensureAppRoot(navbarRight.user_info_url)}>
                {t('Info')}
              </Typography.Link>
            ),
          });
        }
        const showLogout =
          !isEmbedded() ||
          !isFeatureEnabled(FeatureFlag.DisableEmbeddedSupersetLogout);
        if (showLogout) {
          userItems.push({
            key: 'logout',
            label: (
              <Typography.Link
                href={ensureAppRoot(navbarRight.user_logout_url)}
              >
                {t('Logout')}
              </Typography.Link>
            ),
            onClick: handleLogout,
          });
        }

        items.push({
          type: 'group',
          label: t('User'),
          key: 'user-section',
          children: userItems,
        });
      }

      // Environment tag (moved from top-level navbar)
      if (environmentTag?.text) {
        items.push({ type: 'divider', key: 'env-divider' });
        items.push({
          type: 'group',
          label: t('Environment'),
          key: 'env-section',
          children: [
            {
              key: 'env-tag',
              style: { height: 'auto', minHeight: 'auto' },
              label: (
                <Tag
                  color={
                    [
                      'error',
                      'warning',
                      'success',
                      'processing',
                      'default',
                    ].includes(environmentTag.color)
                      ? environmentTag.color
                      : 'default'
                  }
                >
                  {environmentTag.text}
                </Tag>
              ),
            },
          ],
        });
      }

      if (navbarRight.version_string || navbarRight.version_sha) {
        items.push({ type: 'divider', key: 'version-info-divider' });

        const aboutItem: ItemType = {
          type: 'group',
          label: t('About'),
          key: 'about-section',
          children: [
            {
              key: 'about-info',
              style: { height: 'auto', minHeight: 'auto' },
              label: (
                <div
                  css={(theme: SupersetTheme) => css`
                    font-size: ${theme.fontSizeSM}px;
                    color: ${theme.colorTextSecondary || theme.colorText};
                    white-space: pre-wrap;
                    padding: ${theme.sizeUnit}px ${theme.sizeUnit * 2}px;
                  `}
                >
                  {[
                    navbarRight.show_watermark && t('Powered by AX-BI'),
                    navbarRight.version_string &&
                      `${t('Version')}: ${navbarRight.version_string}`,
                    navbarRight.version_sha &&
                      `${t('SHA')}: ${navbarRight.version_sha}`,
                    navbarRight.build_number &&
                      `${t('Build')}: ${navbarRight.build_number}`,
                  ]
                    .filter(Boolean)
                    .join('\n')}
                </div>
              ),
            },
          ],
        };
        items.push(aboutItem);
      }

      // Help group (documentation and bug report links moved from top-level navbar)
      const helpItems: MenuItem[] = [];
      if (navbarRight.documentation_url) {
        helpItems.push({
          key: 'documentation',
          label: (
            <Typography.Link
              href={navbarRight.documentation_url}
              target="_blank"
              rel="noreferrer"
            >
              {navbarRight.documentation_text || t('Documentation')}
            </Typography.Link>
          ),
          icon: navbarRight.documentation_icon ? (
            <Icons.BookOutlined />
          ) : (
            <Icons.QuestionCircleOutlined />
          ),
        });
      }
      if (navbarRight.bug_report_url) {
        helpItems.push({
          key: 'bug-report',
          label: (
            <Typography.Link
              href={navbarRight.bug_report_url}
              target="_blank"
              rel="noreferrer"
            >
              {navbarRight.bug_report_text || t('Report a bug')}
            </Typography.Link>
          ),
          icon: navbarRight.bug_report_icon ? undefined : <Icons.BugOutlined />,
        });
      }
      if (helpItems.length > 0) {
        items.push({ type: 'divider', key: 'help-divider' });
        items.push({
          type: 'group',
          label: t('Help'),
          key: 'help-section',
          children: helpItems,
        });
      }

      return items;
    };

    const items: MenuItem[] = [];

    if (commandPalette) {
      items.push({
        key: 'command-palette',
        label: (
          <Tooltip title={t('Search (%s)', isMac ? '⌘K' : 'Ctrl+K')}>
            <Icons.SearchOutlined
              data-test="command-palette-trigger"
              onClick={() => commandPalette.open()}
            />
          </Tooltip>
        ),
      });
    }

    if (RightMenuExtension) {
      items.push({
        key: 'extension',
        label: <RightMenuExtension />,
      });
    }

    if (canSetMode()) {
      items.push(themeMenuItem);
    }

    if (navbarRight.show_language_picker && languageMenuItem) {
      items.push(languageMenuItem);
    }

    items.push({
      key: 'settings',
      label: t('Settings'),
      icon: <Icons.DownOutlined iconSize="xs" />,
      children: buildSettingsMenuItems(),
      className: 'submenu-with-caret',
      popupOffset: NAVBAR_MENU_POPUP_OFFSET,
    });

    return items;
  }, [
    commandPalette,
    isMac,
    RightMenuExtension,
    RightMenuItemIconExtension,
    navbarRight,
    dashboardId,
    canUploadData,
    canSetMode,
    themeMenuItem,
    languageMenuItem,
    settings,
    isFrontendRoute,
    theme,
    environmentTag,
    handleLogout,
  ]);

  return (
    <StyledDiv align={align}>
      <Menu
        css={css`
          display: flex;
          flex-direction: row;
          align-items: center;
          height: 100%;
          border-bottom: none !important;
          gap: ${theme.sizeUnit}px;

          /* Remove the underline from menu items */
          .ant-menu-item:after,
          .ant-menu-submenu:after {
            content: none !important;
          }

          .ant-menu-item,
          .ant-menu-submenu {
            padding: 0 ${theme.sizeUnit}px;
          }

          .submenu-with-caret {
            height: 100%;
            padding: 0;
            .ant-menu-submenu-title {
              align-items: center;
              display: flex;
              gap: ${theme.sizeUnit}px;
              flex-direction: row-reverse;
              height: 100%;
            }
            &.ant-menu-submenu::after {
              inset-inline: ${theme.sizeUnit}px;
            }
            &.ant-menu-submenu:hover,
            &.ant-menu-submenu-active {
              .ant-menu-title-content {
                color: ${theme.colorPrimary};
              }
            }
          }
        `}
        selectable={false}
        mode="horizontal"
        disabledOverflow
        items={menuItems}
      />
      <TelemetryPixel
        version={navbarRight.version_string}
        sha={navbarRight.version_sha}
        build={navbarRight.build_number}
      />
    </StyledDiv>
  );
};

const RightMenuWithQueryWrapper: FC<RightMenuProps> = props => (
  <RightMenu {...props} />
);

// Query param manipulation requires that, during the setup, the
// QueryParamProvider is present and configured.
// Superset still has multiple entry points, and not all of them have
// the same setup, and critically, not all of them have the QueryParamProvider.
// This wrapper ensures the RightMenu renders regardless of the provider being present.
class RightMenuErrorWrapper extends PureComponent<RightMenuProps> {
  state = {
    hasError: false,
  };

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  render() {
    if (this.state.hasError) {
      return <RightMenu {...this.props} />;
    }

    return this.props.children;
  }
}

const RightMenuWrapper: FC<RightMenuProps> = props => (
  <RightMenuErrorWrapper {...props}>
    <RightMenuWithQueryWrapper {...props} />
  </RightMenuErrorWrapper>
);

export default RightMenuWrapper;

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
import { FC, PureComponent, useEffect, useMemo, useState } from 'react';
import { useSelector } from 'react-redux';
import { t } from '@ax-bi/core/translation';
import {
  getExtensionsRegistry,
  isFeatureEnabled,
  FeatureFlag,
  CACHE_KEY,
} from '@ax-bi/ui-core';
import { styled, css, AxBITheme, useTheme } from '@ax-bi/core/theme';
import {
  Tag,
  Tooltip,
  Menu,
  Icons,
  Typography,
} from '@ax-bi/ui-core/components';
import type { ItemType, MenuItem } from '@ax-bi/ui-core/components/Menu';
import { ensureAppRoot } from 'src/utils/pathUtils';
import { findPermission } from 'src/utils/findPermission';
import { isEmbedded } from 'src/dashboard/util/isEmbedded';
import { RootState } from 'src/dashboard/types';
import { useThemeContext } from 'src/theme/ThemeProvider';
import { useThemeMenuItems } from 'src/hooks/useThemeMenuItems';
import { useOptionalCommandPalette } from 'src/components/CommandPalette';
import { useHistory } from 'src/hooks/useAppHistory';
import { useLanguageMenuItems } from './LanguagePicker';
import { RightMenuProps } from './types';
import { NAVBAR_MENU_POPUP_OFFSET } from './commonMenuData';
import { orderCreateMenuItems } from './createMenuOrder';
import {
  DESKTOP_SHELL_CHANGE_EVENT,
  getDesktopShellStatus,
  isDesktopShellActive,
  postDesktopShellAction,
  SHELL_OPEN_HOME_MESSAGE_TYPE,
  SHELL_OPEN_SETTINGS_MESSAGE_TYPE,
} from 'src/theme/desktopShell';
import { resolveSettingsMenuIconKey } from './settingsMenuIcons';

/**
 * Navigate from Settings/Create menu items.
 * Prefer menu item onClick over nested <Link>/<a> labels: antd 6 Menu
 * swallows nested anchor clicks in submenus, which made Settings links dead.
 */
function navigateMenuUrl(
  url: string | undefined,
  history: ReturnType<typeof useHistory>,
  isFrontendRoute?: (path?: string) => boolean,
) {
  if (!url) {
    return;
  }
  if (isFrontendRoute?.(url)) {
    history.push(url);
    return;
  }
  // Backend / external pages: full navigation
  window.location.assign(ensureAppRoot(url));
}

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

// Span (not button): Ant Design Menu items already provide the interactive
// host; nesting a <button> inside a menuitem is invalid HTML and double-fires.
const CommandPaletteChip = styled.span`
  ${({ theme }) => css`
    display: inline-flex;
    align-items: center;
    gap: ${theme.sizeUnit * 2}px;
    height: ${theme.sizeUnit * 8}px;
    padding: 0 ${theme.sizeUnit * 3}px;
    margin: 0 ${theme.sizeUnit}px;
    border: 1px solid ${theme.colorBorderSecondary};
    border-radius: ${theme.borderRadiusLG}px;
    background: ${theme.colorBgContainer};
    color: ${theme.colorTextSecondary};
    cursor: pointer;
    font-size: ${theme.fontSizeSM}px;
    line-height: 1;
    transition:
      border-color 0.16s ease,
      color 0.16s ease,
      background 0.16s ease;

    .ant-menu-item:hover &,
    .ant-menu-item-selected &,
    &:hover {
      border-color: ${theme.colorPrimaryBorder};
      color: ${theme.colorText};
    }

    .shortcut {
      display: inline-flex;
      align-items: center;
      padding: ${theme.sizeUnit / 2}px ${theme.sizeUnit}px;
      border-radius: ${theme.borderRadiusSM}px;
      background: ${theme.colorFillSecondary};
      color: ${theme.colorTextTertiary};
      font-size: ${theme.fontSizeSM}px;
    }

    @media (max-width: 576px) {
      .chip-label,
      .shortcut {
        display: none;
      }
      padding: 0 ${theme.sizeUnit * 2}px;
    }
  `}
`;

const RightMenu = ({
  align,
  settings,
  navbarRight,
  isFrontendRoute,
  environmentTag,
}: RightMenuProps) => {
  const theme = useTheme();
  const history = useHistory();
  const commandPalette = useOptionalCommandPalette();
  const isMac = navigator.platform?.toLowerCase().includes('mac') ?? false;
  const [desktopShellActive, setDesktopShellActive] = useState(() =>
    isDesktopShellActive(),
  );
  const [desktopShellStatus, setDesktopShellStatus] = useState(() =>
    getDesktopShellStatus(),
  );

  useEffect(() => {
    const onShellChange = (event: Event) => {
      const detail = (event as CustomEvent).detail as
        { active?: boolean; status?: string | null } | undefined;
      setDesktopShellActive(Boolean(detail?.active ?? isDesktopShellActive()));
      setDesktopShellStatus(detail?.status ?? getDesktopShellStatus());
    };
    window.addEventListener(DESKTOP_SHELL_CHANGE_EVENT, onShellChange);
    // Parent may have already sent shell:hello before this mounted.
    setDesktopShellActive(isDesktopShellActive());
    setDesktopShellStatus(getDesktopShellStatus());
    return () => {
      window.removeEventListener(DESKTOP_SHELL_CHANGE_EVENT, onShellChange);
    };
  }, []);
  const dashboardId = useSelector<RootState, number | undefined>(
    state => state.dashboardInfo?.id,
  );
  const canUploadData = useSelector((state: RootState) =>
    findPermission('can_upload', 'Database', state.user?.roles),
  );
  const localFileUploadEnabled = isFeatureEnabled(
    FeatureFlag.EnableLocalFileUpload,
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
      const simplifiedNav = isFeatureEnabled(FeatureFlag.SimplifiedNav);
      if (!navbarRight.user_is_anonymous) {
        const chartItem: MenuItem = {
          key: 'create-chart',
          label: t('Chart'),
          icon: <Icons.BarChartOutlined />,
          onClick: () =>
            navigateMenuUrl(
              Number.isInteger(dashboardId)
                ? `/chart/add?dashboard_id=${dashboardId}`
                : '/chart/add',
              history,
              isFrontendRoute,
            ),
        };
        const dashboardItem: MenuItem = {
          key: 'create-dashboard',
          label: t('Dashboard'),
          icon: <Icons.DashboardOutlined />,
          onClick: () =>
            // Full assign matches other "new dashboard" entry points
            window.location.assign(ensureAppRoot('/dashboard/new/')),
        };
        const uploadItem: MenuItem | null =
          canUploadData && localFileUploadEnabled
            ? {
                key: 'create-upload-data',
                label: t('Upload data'),
                icon: <Icons.UploadOutlined />,
                onClick: () =>
                  navigateMenuUrl('/upload/', history, isFrontendRoute),
              }
            : null;
        const sqlItem: MenuItem = {
          key: 'create-sql',
          label: t('SQL query'),
          icon: <Icons.ConsoleSqlOutlined />,
          onClick: () =>
            navigateMenuUrl('/sqllab?new=true', history, isFrontendRoute),
        };

        // Simplified mode: consumer create paths first; SQL last inside the
        // same Create group (avoids a second "Advanced" label that collides
        // with SIMPLIFIED_NAV's demoted SQL Lab settings group).
        createItems.push(
          ...orderCreateMenuItems(
            {
              chart: chartItem,
              dashboard: dashboardItem,
              upload: uploadItem,
              sql: sqlItem,
            },
            simplifiedNav,
          ),
        );
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

            const iconKey = resolveSettingsMenuIconKey({
              name: child.name,
              label: child.label,
              url: child.url,
            });
            const IconComp = iconKey ? Icons[iconKey] : undefined;

            sectionItems.push({
              key: child.label,
              icon: IconComp ? <IconComp /> : undefined,
              label: menuItemDisplay,
              onClick: () =>
                navigateMenuUrl(child.url, history, isFrontendRoute),
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

      if (desktopShellActive) {
        items.push({ type: 'divider', key: 'desktop-divider' });
        const desktopChildren: MenuItem[] = [];
        if (desktopShellStatus) {
          desktopChildren.push({
            key: 'desktop-status',
            disabled: true,
            label: desktopShellStatus,
          });
        }
        desktopChildren.push(
          {
            key: 'desktop-home',
            icon: <Icons.HomeOutlined />,
            label: t('Desktop home'),
            onClick: () => postDesktopShellAction(SHELL_OPEN_HOME_MESSAGE_TYPE),
          },
          {
            key: 'desktop-settings',
            icon: <Icons.SettingOutlined />,
            label: t('Desktop settings'),
            onClick: () =>
              postDesktopShellAction(SHELL_OPEN_SETTINGS_MESSAGE_TYPE),
          },
        );
        items.push({
          type: 'group',
          label: t('Desktop'),
          key: 'desktop-section',
          children: desktopChildren,
        });
      }

      if (!navbarRight.user_is_anonymous) {
        items.push({ type: 'divider', key: 'user-divider' });

        const userItems: MenuItem[] = [];
        if (navbarRight.user_info_url) {
          userItems.push({
            key: 'info',
            icon: <Icons.InfoCircleOutlined />,
            label: t('Info'),
            onClick: () =>
              navigateMenuUrl(
                navbarRight.user_info_url,
                history,
                isFrontendRoute,
              ),
          });
        }
        const showLogout =
          !isEmbedded() ||
          !isFeatureEnabled(FeatureFlag.DisableEmbeddedAxBILogout);
        if (showLogout) {
          userItems.push({
            key: 'logout',
            icon: <Icons.LogoutOutlined />,
            label: t('Logout'),
            onClick: () => {
              handleLogout();
              // Full navigation so the server session ends cleanly
              window.location.assign(
                ensureAppRoot(navbarRight.user_logout_url || '/logout/'),
              );
            },
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
                  css={(theme: AxBITheme) => css`
                    font-size: ${theme.fontSizeSM}px;
                    color: ${theme.colorTextSecondary || theme.colorText};
                    white-space: pre-wrap;
                    padding: ${theme.sizeUnit}px ${theme.sizeUnit * 2}px;
                  `}
                >
                  {[
                    navbarRight.show_watermark && t('Powered by AX BI'),
                    navbarRight.version_string &&
                      `${t('Runtime version')}: ${navbarRight.version_string}`,
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
      const shortcutLabel = isMac ? '⌘K' : 'Ctrl+K';
      items.push({
        key: 'command-palette',
        label: (
          <Tooltip title={t('Search commands and pages (%s)', shortcutLabel)}>
            <CommandPaletteChip
              data-test="command-palette-trigger"
              aria-label={t('Search (%s)', shortcutLabel)}
            >
              <Icons.SearchOutlined iconSize="m" />
              <span className="chip-label">{t('Search')}</span>
              <span className="shortcut">{shortcutLabel}</span>
            </CommandPaletteChip>
          </Tooltip>
        ),
        onClick: () => commandPalette.open(),
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

    if (canUploadData && localFileUploadEnabled) {
      items.push({
        key: 'upload-data',
        label: t('Upload data'),
        icon: <Icons.UploadOutlined />,
        className: 'primary-upload-action',
        onClick: () => navigateMenuUrl('/upload/', history, isFrontendRoute),
      });
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
    localFileUploadEnabled,
    canSetMode,
    themeMenuItem,
    languageMenuItem,
    settings,
    isFrontendRoute,
    history,
    theme,
    environmentTag,
    handleLogout,
    desktopShellActive,
    desktopShellStatus,
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

          .primary-upload-action {
            border: 1px solid ${theme.colorPrimaryBorder};
            border-radius: ${theme.borderRadius}px;
            background: ${theme.colorPrimaryBg};
            padding: 0 ${theme.sizeUnit * 3}px;

            .ant-menu-title-content a {
              color: ${theme.colorPrimaryText};
              font-weight: ${theme.fontWeightStrong};
            }
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
    </StyledDiv>
  );
};

const RightMenuWithQueryWrapper: FC<RightMenuProps> = props => (
  <RightMenu {...props} />
);

// Query param manipulation requires that, during the setup, the
// QueryParamProvider is present and configured.
// AxBI still has multiple entry points, and not all of them have
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

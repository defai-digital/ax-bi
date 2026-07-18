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
import { useSelector } from 'react-redux';
import { t } from '@ax-bi/core/translation';
import {
  isFeatureEnabled,
  FeatureFlag,
  getExtensionsRegistry,
  JsonObject,
} from '@ax-bi/ui-core';
import { styled, useTheme } from '@ax-bi/core/theme';
import rison from 'rison';
import {
  ActionRow,
  AntdThemeProvider,
  Button,
  EmptyCallout,
  EmptyCalloutText,
  EmptyCalloutTitle,
  Eyebrow,
  Hero,
  HeroText,
  HeroTitle,
  ListViewCard,
  Page,
  Panel,
  QuickAction,
  QuickActionGrid,
  Section,
  SectionDescription,
  SectionHeader,
  SectionTitle,
  Stat,
  StatsGrid,
} from '@ax-bi/ui-core/components';
import {
  BootstrapUser,
  User,
  UserWithPermissionsAndRoles,
} from 'src/types/bootstrapTypes';
import { reject } from 'lodash';
import { getItem, LocalStorageKeys } from 'src/utils/localStorageHelpers';
import { useUxPreference } from 'src/hooks/useUxPreference';
import withToasts from 'src/components/MessageToasts/withToasts';
import {
  CardContainer,
  createErrorHandler,
  getRecentActivityObjs,
  getUserOwnedObjects,
  loadingCardCount,
} from 'src/views/CRUD/utils';
import { Switch } from '@ax-bi/ui-core/components/Switch';
import getBootstrapData from 'src/utils/getBootstrapData';
import { TableTab } from 'src/views/CRUD/types';
import SubMenu, { SubMenuProps } from 'src/features/home/SubMenu';
import { userHasPermission } from 'src/dashboard/util/permissionUtils';
import { WelcomePageLastTab } from 'src/features/home/types';
import ActivityTable from 'src/features/home/ActivityTable';
import ChartTable from 'src/features/home/ChartTable';
import SavedQueries from 'src/features/home/SavedQueries';
import DashboardTable from 'src/features/home/DashboardTable';
import { Icons } from '@ax-bi/ui-core/components/Icons';
import { navigateTo } from 'src/utils/navigationUtils';
import { useOptionalCommandPalette } from 'src/components/CommandPalette';
import OnboardingChecklist from 'src/features/home/OnboardingChecklist';

const extensionsRegistry = getExtensionsRegistry();

interface WelcomeProps {
  user: User;
  addDangerToast: (arg0: string) => void;
}

export interface ActivityData {
  [TableTab.Created]?: JsonObject[];
  [TableTab.Edited]?: JsonObject[];
  [TableTab.Viewed]?: JsonObject[];
  [TableTab.Other]?: JsonObject[];
}

interface LoadingProps {
  cover?: boolean;
}

const WelcomeContainer = styled.div`
  background: ${({ theme }) => theme.colorBgLayout};
`;

/**
 * Placeholder cover for loading cards: reduced loading height with the same
 * bottom hairline the list-card cover renders.
 */
const LoadingCover = styled.div`
  ${({ theme }) => `
    height: ${theme.sizeUnit * 42}px;
    border-bottom: 1px solid ${theme.colorSplit};
  `}
`;

const SectionLink = styled.button`
  ${({ theme }) => `
    appearance: none;
    border: none;
    background: transparent;
    color: ${theme.colorPrimary};
    font-size: ${theme.fontSizeSM}px;
    font-weight: ${theme.fontWeightStrong};
    cursor: pointer;
    padding: 0;
    white-space: nowrap;

    &:hover,
    &:focus-visible {
      text-decoration: underline;
      outline: none;
    }
  `}
`;

const WelcomeNav = styled.div`
  ${({ theme }) => `
    .switch {
      display: flex;
      flex-direction: row;
      margin: ${theme.sizeUnit * 4}px;
      span {
        display: block;
        margin: ${theme.sizeUnit}px;
        line-height: ${theme.sizeUnit * 3.5}px;
      }
    }
  `}
`;

const bootstrapData = getBootstrapData();

export const LoadingCards = ({ cover }: LoadingProps) => (
  <CardContainer showThumbnails={cover} className="loading-cards">
    {Array.from({ length: loadingCardCount }, (_, index) => (
      <ListViewCard
        key={index}
        cover={cover ? <LoadingCover /> : <></>}
        description=""
        loading
      />
    ))}
  </CardContainer>
);

/** Prefer a user object that carries userId (bootstrap guest payloads omit it). */
export function resolveHomeUser(
  propUser: User | undefined,
  storeUser: BootstrapUser | Record<string, never> | undefined,
): User {
  const propId = propUser?.userId;
  if (propId != null) {
    return propUser as User;
  }
  const storeId =
    storeUser && 'userId' in storeUser
      ? (storeUser as UserWithPermissionsAndRoles).userId
      : undefined;
  if (storeId != null) {
    return storeUser as User;
  }
  return (propUser ?? {}) as User;
}

function Welcome({ user: userProp, addDangerToast }: WelcomeProps) {
  const theme = useTheme();
  // Scoped antd Card token overrides (replacing the old raw-class CSS
  // overrides): Home cards use the stronger border color, and the meta
  // title-to-description gap absorbs the old description margin-top.
  const cardTokenOverrides = useMemo(
    () => ({
      components: {
        Card: {
          colorBorderSecondary: theme.colorBorder,
          marginXS: theme.marginXS + theme.sizeUnit,
        },
      },
    }),
    [theme],
  );
  const storeUser = useSelector(
    (state: { user?: BootstrapUser | Record<string, never> }) => state.user,
  );
  // Prefer a user with userId — bootstrap guest/anonymous payloads omit it,
  // and some SPA navigations only keep a full user in Redux.
  const user = resolveHomeUser(userProp, storeUser);
  const canReadSavedQueries = userHasPermission(user, 'SavedQuery', 'can_read');
  const canUploadData =
    userHasPermission(user, 'Database', 'can_upload') &&
    isFeatureEnabled(FeatureFlag.EnableLocalFileUpload);
  const genaiEnabled = isFeatureEnabled(FeatureFlag.GenaiBi);
  const commandPalette = useOptionalCommandPalette();
  // Guest / anonymous bootstrap payloads omit userId (see bootstrap_user_data).
  const userid = user?.userId;
  const id = userid != null ? String(userid) : null;
  const params = rison.encode({ page_size: 24, distinct: false });
  const recent = `/api/v1/log/recent_activity/?q=${params}`;
  const [activeChild, setActiveChild] = useState('Loading');
  const isThumbnailsEnabled = isFeatureEnabled(FeatureFlag.Thumbnails);
  // Pre-migration this lived in localStorage under the user id as
  // { thumbnails: boolean }; keep that key as the offline/anonymous
  // fallback so behavior degrades gracefully.
  const [thumbnailsPref, setThumbnailsPref] = useUxPreference(
    'ux.home.thumbnails',
    true,
    {
      localStorageKey: id ?? 'ux.home.thumbnails',
      readLegacy: raw =>
        raw != null && typeof raw === 'object'
          ? (raw as { thumbnails?: boolean }).thumbnails
          : undefined,
    },
  );
  const checked = isThumbnailsEnabled ? thumbnailsPref : false;
  const [activityData, setActivityData] = useState<ActivityData | null>(null);
  const [chartData, setChartData] = useState<Array<object> | null>(null);
  const [queryData, setQueryData] = useState<Array<object> | null>(null);
  const [dashboardData, setDashboardData] = useState<Array<object> | null>(
    null,
  );
  const [isFetchingActivityData, setIsFetchingActivityData] = useState(true);

  const SubmenuExtension = extensionsRegistry.get('home.submenu');
  const WelcomeMessageExtension = extensionsRegistry.get('welcome.message');
  const WelcomeTopExtension = extensionsRegistry.get('welcome.banner');
  const WelcomeMainExtension = extensionsRegistry.get(
    'welcome.main.replacement',
  );

  const [otherTabTitle, otherTabFilters] = useMemo(() => {
    const lastTab = bootstrapData.common?.conf
      .WELCOME_PAGE_LAST_TAB as WelcomePageLastTab;
    const [customTitle, customFilter] = Array.isArray(lastTab)
      ? lastTab
      : [undefined, undefined];
    if (customTitle && customFilter) {
      return [t(customTitle), customFilter];
    }
    if (lastTab === 'all') {
      return [t('All'), []];
    }
    return [
      t('Examples'),
      [
        {
          col: 'created_by',
          opr: 'rel_o_m',
          value: 0,
        },
      ],
    ];
  }, []);

  useEffect(() => {
    if (id == null) {
      setIsFetchingActivityData(false);
      setDashboardData([]);
      setChartData([]);
      setQueryData([]);
      setActivityData({
        [TableTab.Viewed]: [],
        [TableTab.Other]: [],
        [TableTab.Created]: [],
      });
      setActiveChild(TableTab.Other);
      return;
    }
    if (!otherTabFilters || WelcomeMainExtension) {
      return;
    }
    const activeTab = getItem(LocalStorageKeys.HomepageActivityFilter, null);
    getRecentActivityObjs(Number(id), recent, addDangerToast, otherTabFilters)
      .then((res: { other: JsonObject[]; viewed?: JsonObject[] }) => {
        const data: ActivityData | null = {};
        data[TableTab.Other] = res.other;
        if (res.viewed) {
          const filtered = reject(res.viewed, ['item_url', null]).map(r => r);
          data[TableTab.Viewed] = filtered;
          if (!activeTab && data[TableTab.Viewed]) {
            setActiveChild(TableTab.Viewed);
          } else if (!activeTab && !data[TableTab.Viewed]) {
            setActiveChild(TableTab.Created);
          } else setActiveChild(activeTab || TableTab.Created);
        } else if (!activeTab) setActiveChild(TableTab.Created);
        else setActiveChild(activeTab);
        setActivityData(activityData => ({ ...activityData, ...data }));
      })
      .catch(
        createErrorHandler((errMsg: unknown) => {
          setActivityData(activityData => ({
            ...activityData,
            [TableTab.Viewed]: [],
          }));
          addDangerToast(
            t('There was an issue fetching your recent activity: %s', errMsg),
          );
        }),
      );

    // Sets other activity data in parallel with recents api call
    const ownSavedQueryFilters = [
      {
        col: 'created_by',
        opr: 'rel_o_m',
        value: id,
      },
    ];
    Promise.all([
      getUserOwnedObjects(id, 'dashboard')
        .then(r => {
          setDashboardData(r);
          return Promise.resolve();
        })
        .catch((err: unknown) => {
          setDashboardData([]);
          addDangerToast(
            t('There was an issue fetching your dashboards: %s', err),
          );
          return Promise.resolve();
        }),
      getUserOwnedObjects(id, 'chart')
        .then(r => {
          setChartData(r);
          return Promise.resolve();
        })
        .catch((err: unknown) => {
          setChartData([]);
          addDangerToast(t('There was an issue fetching your chart: %s', err));
          return Promise.resolve();
        }),
      canReadSavedQueries
        ? getUserOwnedObjects(id, 'saved_query', ownSavedQueryFilters)
            .then(r => {
              setQueryData(r);
              return Promise.resolve();
            })
            .catch((err: unknown) => {
              setQueryData([]);
              addDangerToast(
                t('There was an issue fetching your saved queries: %s', err),
              );
              return Promise.resolve();
            })
        : Promise.resolve(),
    ]).then(() => {
      setIsFetchingActivityData(false);
    });
  }, [
    id,
    otherTabFilters,
    WelcomeMainExtension,
    canReadSavedQueries,
    recent,
    addDangerToast,
  ]);

  const handleToggle = () => {
    setThumbnailsPref(!thumbnailsPref);
  };

  useEffect(() => {
    setActivityData(activityData => ({
      ...activityData,
      Created: [
        ...(chartData?.slice(0, 3) || []),
        ...(dashboardData?.slice(0, 3) || []),
        ...(queryData?.slice(0, 3) || []),
      ],
    }));
  }, [chartData, queryData, dashboardData]);

  const isRecentActivityLoading =
    !activityData?.[TableTab.Other] && !activityData?.[TableTab.Viewed];
  const dashboardCount = dashboardData?.length ?? 0;
  const chartCount = chartData?.length ?? 0;
  const recentCount =
    (activityData?.[TableTab.Viewed]?.length ?? 0) +
    (activityData?.[TableTab.Other]?.length ?? 0);
  const isWorkspaceLoaded = dashboardData !== null && chartData !== null;
  const isFirstRun =
    isWorkspaceLoaded &&
    !isFetchingActivityData &&
    dashboardCount === 0 &&
    chartCount === 0;

  const menuData: SubMenuProps = {
    activeChild: 'Home',
    name: t('Home'),
  };

  if (isThumbnailsEnabled) {
    menuData.buttons = [
      {
        name: (
          <WelcomeNav>
            <div className="switch">
              <Switch checked={checked} onClick={handleToggle} />
              <span>{t('Thumbnails')}</span>
            </div>
          </WelcomeNav>
        ),
        onClick: handleToggle,
        buttonStyle: 'link',
      },
    ];
  }

  const isReturningUser = isWorkspaceLoaded && !isFirstRun && recentCount > 0;
  const scrollToRecents = () => {
    document
      .getElementById('home-recents')
      ?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  if (id == null) {
    return (
      <>
        {SubmenuExtension ? (
          <SubmenuExtension {...menuData} />
        ) : (
          <SubMenu {...menuData} />
        )}
        <WelcomeContainer>
          <Page>
            <Hero>
              <div>
                <Eyebrow>{t('AX BI workspace')}</Eyebrow>
                <HeroTitle>{t('Sign in to open your workspace')}</HeroTitle>
                <HeroText>
                  {t(
                    'The home page needs a signed-in user account. Sign in to see recents, dashboards, and charts.',
                  )}
                </HeroText>
                <ActionRow>
                  <Button
                    buttonStyle="primary"
                    onClick={() => navigateTo('/login/')}
                  >
                    {t('Sign in')}
                  </Button>
                  <Button
                    buttonStyle="secondary"
                    onClick={() => navigateTo('/dashboard/list/')}
                  >
                    {t('Browse dashboards')}
                  </Button>
                </ActionRow>
              </div>
            </Hero>
          </Page>
        </WelcomeContainer>
      </>
    );
  }

  return (
    <>
      {SubmenuExtension ? (
        <SubmenuExtension {...menuData} />
      ) : (
        <SubMenu {...menuData} />
      )}
      <AntdThemeProvider theme={cardTokenOverrides}>
        <WelcomeContainer>
          {WelcomeMessageExtension && <WelcomeMessageExtension />}
          {WelcomeTopExtension && <WelcomeTopExtension />}
          <Page>
            <Hero>
              <div>
                <Eyebrow>{t('AX BI workspace')}</Eyebrow>
                <HeroTitle>
                  {isReturningUser
                    ? t('Continue where you left off')
                    : t('Start from data. Build charts and dashboards.')}
                </HeroTitle>
                <HeroText>
                  {isReturningUser
                    ? t(
                        'Open recent work below, or create something new when you are ready.',
                      )
                    : t(
                        'Upload a file or pick a dataset, then turn insights into shareable dashboards.',
                      )}
                </HeroText>
                {/* One primary + one secondary CTA — first-run uses the empty callout for full choices */}
                {!isFirstRun && (
                  <ActionRow>
                    {canUploadData ? (
                      <>
                        <Button
                          buttonStyle="primary"
                          icon={<Icons.UploadOutlined />}
                          onClick={() => navigateTo('/upload/')}
                        >
                          {t('Upload data')}
                        </Button>
                        <Button
                          buttonStyle="secondary"
                          icon={<Icons.BarChartOutlined />}
                          onClick={() => navigateTo('/chart/add')}
                        >
                          {t('Create chart')}
                        </Button>
                      </>
                    ) : (
                      <>
                        <Button
                          buttonStyle="primary"
                          icon={<Icons.BarChartOutlined />}
                          onClick={() => navigateTo('/chart/add')}
                        >
                          {t('Create chart')}
                        </Button>
                        <Button
                          buttonStyle="secondary"
                          icon={<Icons.DashboardOutlined />}
                          onClick={() =>
                            navigateTo('/dashboard/new/', { assign: true })
                          }
                        >
                          {t('New dashboard')}
                        </Button>
                      </>
                    )}
                  </ActionRow>
                )}
              </div>
              <Panel>
                <SectionTitle>{t('What do you want to do?')}</SectionTitle>
                <SectionDescription>
                  {t('Jump in with search or open your library.')}
                </SectionDescription>
                <QuickActionGrid>
                  {genaiEnabled && commandPalette && (
                    <QuickAction
                      type="button"
                      data-test="home-ask-axbi"
                      onClick={() => commandPalette.open()}
                    >
                      <span className="quick-action-icon">
                        <Icons.ThunderboltOutlined />
                      </span>
                      <span>
                        <div className="quick-action-title">
                          {t('Ask AX BI')}
                        </div>
                        <div className="quick-action-text">
                          {t(
                            'Search actions (⌘K). Prompt flows via AX-Studio.',
                          )}
                        </div>
                      </span>
                    </QuickAction>
                  )}
                  {commandPalette && (
                    <QuickAction
                      type="button"
                      onClick={() => commandPalette.open()}
                    >
                      <span className="quick-action-icon">
                        <Icons.SearchOutlined />
                      </span>
                      <span>
                        <div className="quick-action-title">{t('Search')}</div>
                        <div className="quick-action-text">
                          {t('Find pages and actions. Press ⌘K or Ctrl+K.')}
                        </div>
                      </span>
                    </QuickAction>
                  )}
                  <QuickAction
                    type="button"
                    onClick={() => navigateTo('/dashboard/list/')}
                  >
                    <span className="quick-action-icon">
                      <Icons.DashboardOutlined />
                    </span>
                    <span>
                      <div className="quick-action-title">
                        {t('Browse dashboards')}
                      </div>
                      <div className="quick-action-text">
                        {t('Open saved analytics and reports.')}
                      </div>
                    </span>
                  </QuickAction>
                  {!canUploadData && !commandPalette && (
                    <QuickAction
                      type="button"
                      onClick={() => navigateTo('/chart/add')}
                    >
                      <span className="quick-action-icon">
                        <Icons.BarChartOutlined />
                      </span>
                      <span>
                        <div className="quick-action-title">
                          {t('Create chart')}
                        </div>
                        <div className="quick-action-text">
                          {t('Build a visualization from a dataset.')}
                        </div>
                      </span>
                    </QuickAction>
                  )}
                </QuickActionGrid>
              </Panel>
            </Hero>

            <StatsGrid>
              <Stat
                label={t('Dashboards')}
                value={dashboardData ? dashboardCount : '...'}
                hint={t('Saved dashboards')}
                onClick={() => navigateTo('/dashboard/list/')}
                aria-label={t('Browse dashboards')}
              />
              <Stat
                label={t('Charts')}
                value={chartData ? chartCount : '...'}
                hint={t('Saved charts')}
                onClick={() => navigateTo('/chart/list/')}
                aria-label={t('Browse charts')}
              />
              <Stat
                label={t('Recent activity')}
                value={activityData ? recentCount : '...'}
                hint={t('Viewed and edited analytics')}
                onClick={scrollToRecents}
                aria-label={t('Jump to recent activity')}
              />
            </StatsGrid>

            {isFirstRun && (
              <EmptyCallout data-test="home-first-run">
                <EmptyCalloutTitle>
                  {t('Your workspace is empty')}
                </EmptyCalloutTitle>
                <EmptyCalloutText>
                  {t(
                    'Upload a file or create your first chart to start building dashboards.',
                  )}
                </EmptyCalloutText>
                <ActionRow style={{ justifyContent: 'center', marginTop: 0 }}>
                  {canUploadData && (
                    <Button
                      buttonStyle="primary"
                      icon={<Icons.UploadOutlined />}
                      onClick={() => navigateTo('/upload/')}
                    >
                      {t('Upload data')}
                    </Button>
                  )}
                  <Button
                    buttonStyle={canUploadData ? 'secondary' : 'primary'}
                    icon={<Icons.BarChartOutlined />}
                    onClick={() => navigateTo('/chart/add')}
                  >
                    {t('Create chart')}
                  </Button>
                  <Button
                    buttonStyle="secondary"
                    icon={<Icons.DashboardOutlined />}
                    onClick={() =>
                      navigateTo('/dashboard/new/', { assign: true })
                    }
                  >
                    {t('New dashboard')}
                  </Button>
                </ActionRow>
              </EmptyCallout>
            )}

            {!isFirstRun && (
              <OnboardingChecklist
                canUploadData={canUploadData}
                hasChart={chartCount > 0}
                hasDashboard={dashboardCount > 0}
                onOpenSearch={() => commandPalette?.open()}
              />
            )}

            {WelcomeMainExtension && <WelcomeMainExtension />}
            {(!WelcomeTopExtension || !WelcomeMainExtension) && (
              <>
                <Section id="home-recents">
                  <SectionHeader>
                    <div>
                      <SectionTitle>{t('Recents')}</SectionTitle>
                      <SectionDescription>
                        {t(
                          'Continue from what you viewed or created recently.',
                        )}
                      </SectionDescription>
                    </div>
                  </SectionHeader>
                  {activityData &&
                  (activityData[TableTab.Viewed] ||
                    activityData[TableTab.Other] ||
                    activityData[TableTab.Created]) &&
                  activeChild !== 'Loading' ? (
                    <ActivityTable
                      user={{ userId: userid as number }}
                      activeChild={activeChild}
                      setActiveChild={setActiveChild}
                      activityData={activityData}
                      isFetchingActivityData={isFetchingActivityData}
                    />
                  ) : (
                    <LoadingCards />
                  )}
                </Section>

                <Section id="home-dashboards">
                  <SectionHeader>
                    <div>
                      <SectionTitle>{t('Dashboards')}</SectionTitle>
                      <SectionDescription>
                        {t('Your dashboards and shared examples.')}
                      </SectionDescription>
                    </div>
                    <SectionLink
                      type="button"
                      onClick={() => navigateTo('/dashboard/list/')}
                    >
                      {t('See all')}
                    </SectionLink>
                  </SectionHeader>
                  {!dashboardData || isRecentActivityLoading ? (
                    <LoadingCards cover={checked} />
                  ) : (
                    <DashboardTable
                      user={user}
                      mine={dashboardData}
                      showThumbnails={checked}
                      otherTabData={activityData?.[TableTab.Other]}
                      otherTabFilters={otherTabFilters}
                      otherTabTitle={otherTabTitle}
                    />
                  )}
                </Section>

                <Section id="home-charts">
                  <SectionHeader>
                    <div>
                      <SectionTitle>{t('Charts')}</SectionTitle>
                      <SectionDescription>
                        {t('Saved visualizations you can reuse on dashboards.')}
                      </SectionDescription>
                    </div>
                    <SectionLink
                      type="button"
                      onClick={() => navigateTo('/chart/list/')}
                    >
                      {t('See all')}
                    </SectionLink>
                  </SectionHeader>
                  {!chartData || isRecentActivityLoading ? (
                    <LoadingCards cover={checked} />
                  ) : (
                    <ChartTable
                      showThumbnails={checked}
                      user={user}
                      mine={chartData}
                      otherTabData={activityData?.[TableTab.Other]}
                      otherTabFilters={otherTabFilters}
                      otherTabTitle={otherTabTitle}
                    />
                  )}
                </Section>

                {canReadSavedQueries && (
                  <Section id="home-saved-queries">
                    <SectionHeader>
                      <div>
                        <SectionTitle>{t('Saved queries')}</SectionTitle>
                        <SectionDescription>
                          {t('SQL you saved for reuse.')}
                        </SectionDescription>
                      </div>
                      <SectionLink
                        type="button"
                        onClick={() => navigateTo('/saved-queries')}
                      >
                        {t('See all')}
                      </SectionLink>
                    </SectionHeader>
                    {!queryData ? (
                      <LoadingCards cover={checked} />
                    ) : (
                      <SavedQueries
                        showThumbnails={checked}
                        user={user}
                        mine={queryData}
                        featureFlag={isThumbnailsEnabled}
                      />
                    )}
                  </Section>
                )}
              </>
            )}
          </Page>
        </WelcomeContainer>
      </AntdThemeProvider>
    </>
  );
}

export default withToasts(Welcome);

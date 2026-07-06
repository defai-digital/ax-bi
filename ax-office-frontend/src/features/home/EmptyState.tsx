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
import { useSelector } from 'react-redux';
import {
  Button,
  EmptyState as EmptyStateComponent,
} from '@superset-ui/core/components';
import { FeatureFlag, isFeatureEnabled } from '@superset-ui/core';
import { TableTab } from 'src/views/CRUD/types';
import { t } from '@apache-superset/core/translation';
import { styled } from '@apache-superset/core/theme';
import { navigateTo } from 'src/utils/navigationUtils';
import { findPermission } from 'src/utils/findPermission';
import type { RootState } from 'src/views/store';
import { WelcomeTable } from './types';

const EmptyContainer = styled.div`
  min-height: 260px;
  display: flex;
  color: ${({ theme }) => theme.colorTextDescription};
  flex-direction: column;
  justify-content: space-around;
  border: 1px dashed ${({ theme }) => theme.colorBorderSecondary};
  border-radius: ${({ theme }) => theme.borderRadius}px;
  background: ${({ theme }) => theme.colorBgLayout};
  margin: ${({ theme }) => theme.sizeUnit * 4}px
    ${({ theme }) => theme.sizeUnit * 5}px;
  padding: ${({ theme }) => theme.sizeUnit * 5}px;
`;

const EmptyActions = styled.div`
  ${({ theme }) => `
    display: flex;
    flex-wrap: wrap;
    justify-content: center;
    gap: ${theme.sizeUnit * 2}px;
    margin-top: ${theme.sizeUnit * 3}px;
  `}
`;

const ICONS = {
  [WelcomeTable.Charts]: 'empty-charts.svg',
  [WelcomeTable.Dashboards]: 'empty-dashboard.svg',
  [WelcomeTable.Recents]: 'union.svg',
  [WelcomeTable.SavedQueries]: 'empty.svg',
} as const;

const LABELS = {
  create: {
    [WelcomeTable.Charts]: t('Chart'),
    [WelcomeTable.Dashboards]: t('Dashboard'),
    [WelcomeTable.SavedQueries]: t('SQL query'),
  },
  viewAll: {
    [WelcomeTable.Charts]: t('charts'),
    [WelcomeTable.Dashboards]: t('dashboards'),
    [WelcomeTable.SavedQueries]: t('SQL Lab queries'),
  },
} as const;

const REDIRECTS = {
  create: {
    [WelcomeTable.Charts]: '/chart/add',
    [WelcomeTable.Dashboards]: '/dashboard/new/',
    // navigateTo() applies the application root internally; keep this
    // relative so the prefix isn't added twice.
    [WelcomeTable.SavedQueries]: '/sqllab?new=true',
  },
  viewAll: {
    [WelcomeTable.Charts]: '/chart/list',
    [WelcomeTable.Dashboards]: '/dashboard/list/',
    [WelcomeTable.SavedQueries]: '/savedqueryview/list/',
  },
} as const;

export interface EmptyStateProps {
  tableName: WelcomeTable;
  tab?: string;
  otherTabTitle?: string;
}

export default function EmptyState({ tableName, tab }: EmptyStateProps) {
  // Surface a discoverable path to the streamlined upload page at the moment of
  // confusion (an empty Charts/Dashboards surface = "no data yet"). Gated by the
  // same predicate the "+" Create menu uses, so it can never widen access.
  const canUploadData = useSelector((state: RootState) =>
    findPermission('can_upload', 'Database', state.user?.roles),
  );
  const uploadEnabled =
    canUploadData && isFeatureEnabled(FeatureFlag.EnableLocalFileUpload);
  const showUploadCta =
    uploadEnabled &&
    tab !== TableTab.Favorite &&
    (tableName === WelcomeTable.Charts ||
      tableName === WelcomeTable.Dashboards);

  const getActionButton = () => {
    if (tableName === WelcomeTable.Recents) {
      return null;
    }

    const isFavorite = tab === TableTab.Favorite;
    const buttonText = isFavorite
      ? LABELS.viewAll[tableName]
      : LABELS.create[tableName];

    const url = isFavorite
      ? REDIRECTS.viewAll[tableName]
      : REDIRECTS.create[tableName];

    return {
      buttonText: isFavorite
        ? t('See all %(tableName)s', { tableName: buttonText })
        : t('Create %(tableName)s', { tableName: buttonText }),
      url,
    };
  };

  const image =
    tab === TableTab.Favorite ? 'star-circle.svg' : ICONS[tableName];

  const action = getActionButton();
  const description =
    tableName === WelcomeTable.Charts
      ? t('Upload data or create a chart to start visual analysis.')
      : tableName === WelcomeTable.Dashboards
        ? t('Create a dashboard or generate one from uploaded data.')
        : t('Your recent analytics activity will appear here.');

  return (
    <EmptyContainer>
      <EmptyStateComponent image={image} size="large" description={description}>
        <EmptyActions>
          {showUploadCta && (
            <Button
              buttonStyle="primary"
              onClick={() => navigateTo('/upload/')}
              data-test="empty-state-upload-data"
            >
              {t('Upload data')}
            </Button>
          )}
          {action && (
            <Button
              buttonStyle={showUploadCta ? 'secondary' : 'primary'}
              onClick={() => {
                navigateTo(action.url);
              }}
            >
              {action.buttonText}
            </Button>
          )}
        </EmptyActions>
      </EmptyStateComponent>
    </EmptyContainer>
  );
}

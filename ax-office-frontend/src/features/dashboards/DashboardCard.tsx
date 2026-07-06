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
import { Link, useHistory } from 'react-router-dom';
import { t } from '@apache-superset/core/translation';
import { isFeatureEnabled, FeatureFlag } from '@superset-ui/core';
import { css, styled } from '@apache-superset/core/theme';
import { CardStyles } from 'src/views/CRUD/utils';
import {
  Dropdown,
  Button,
  FaveStar,
  PublishedLabel,
  ListViewCard,
} from '@superset-ui/core/components';
import { MenuItem } from '@superset-ui/core/components/Menu';
import { Icons } from '@superset-ui/core/components/Icons';
import { Dashboard } from 'src/views/CRUD/types';
import { assetUrl } from 'src/utils/assetUrl';
import { FacePile } from 'src/components';

interface DashboardCardProps {
  isChart?: boolean;
  dashboard: Dashboard;
  hasPerm: (name: string) => boolean;
  bulkSelectEnabled: boolean;
  loading: boolean;
  openDashboardEditModal?: (d: Dashboard) => void;
  saveFavoriteStatus: (id: number, isStarred: boolean) => void;
  favoriteStatus: boolean;
  userId?: string | number;
  showThumbnails?: boolean;
  handleBulkDashboardExport: (dashboardsToExport: Dashboard[]) => void;
  onDelete: (dashboard: Dashboard) => void;
}

const StyledDashboardCard = styled(CardStyles)`
  ${({ theme }) => css`
    border-radius: ${theme.borderRadius}px;
    transition:
      transform 0.16s ease,
      box-shadow 0.16s ease;

    .ant-card {
      border: 1px solid ${theme.colorBorderSecondary};
      border-radius: ${theme.borderRadius}px;
      overflow: hidden;
      background: ${theme.colorBgContainer};
      box-shadow: 0 ${theme.sizeUnit}px ${theme.sizeUnit * 3}px
        rgba(15, 23, 42, 0.04);
    }

    &:hover {
      transform: translateY(-2px);

      .ant-card {
        border-color: ${theme.colorPrimaryBorder};
        box-shadow: 0 ${theme.sizeUnit * 2}px ${theme.sizeUnit * 7}px
          rgba(15, 23, 42, 0.08);
      }
    }

    .ant-card-meta-title,
    .ant-card-meta-description {
      white-space: normal;
    }

    .ant-card-cover {
      background:
        linear-gradient(135deg, ${theme.colorPrimaryBg} 0%, transparent 52%),
        ${theme.colorBgLayout};
      border-bottom: 1px solid ${theme.colorBorderSecondary};
    }

    .ant-card-body {
      padding: ${theme.sizeUnit * 4}px;
    }
  `}
`;

function DashboardCard({
  dashboard,
  hasPerm,
  bulkSelectEnabled,
  userId,
  openDashboardEditModal,
  favoriteStatus,
  saveFavoriteStatus,
  showThumbnails,
  handleBulkDashboardExport,
  onDelete,
}: DashboardCardProps) {
  const history = useHistory();
  const canEdit = hasPerm('can_write');
  const canDelete = hasPerm('can_write');
  const canExport = hasPerm('can_export');
  const digest = dashboard.changed_on_utc || dashboard.changed_on;
  const thumbnailUrl =
    isFeatureEnabled(FeatureFlag.Thumbnails) && dashboard.id && digest
      ? `/api/v1/dashboard/${dashboard.id}/thumbnail/${encodeURIComponent(digest)}/`
      : '';

  const menuItems: MenuItem[] = [];

  if (canEdit && openDashboardEditModal) {
    menuItems.push({
      key: 'edit',
      label: (
        <div
          role="button"
          tabIndex={0}
          className="action-button"
          onClick={() => openDashboardEditModal(dashboard)}
          data-test="dashboard-card-option-edit-button"
        >
          <Icons.EditOutlined iconSize="l" data-test="edit-alt" /> {t('Edit')}
        </div>
      ),
    });
  }

  if (canExport) {
    menuItems.push({
      key: 'export',
      label: (
        <div
          role="button"
          tabIndex={0}
          onClick={() => handleBulkDashboardExport([dashboard])}
          className="action-button"
          data-test="dashboard-card-option-export-button"
        >
          <Icons.UploadOutlined iconSize="l" /> {t('Export')}
        </div>
      ),
    });
  }

  if (canDelete) {
    menuItems.push({
      key: 'delete',
      label: (
        <div
          role="button"
          tabIndex={0}
          className="action-button"
          onClick={() => onDelete(dashboard)}
          data-test="dashboard-card-option-delete-button"
        >
          <Icons.DeleteOutlined iconSize="l" /> {t('Delete')}
        </div>
      ),
    });
  }

  return (
    <StyledDashboardCard
      onClick={() => {
        if (!bulkSelectEnabled) {
          history.push(dashboard.url);
        }
      }}
    >
      <ListViewCard
        loading={dashboard.loading || false}
        title={dashboard.dashboard_title}
        certifiedBy={dashboard.certified_by}
        certificationDetails={dashboard.certification_details}
        titleRight={<PublishedLabel isPublished={dashboard.published} />}
        cover={
          !isFeatureEnabled(FeatureFlag.Thumbnails) || !showThumbnails ? (
            <></>
          ) : null
        }
        url={bulkSelectEnabled ? undefined : dashboard.url}
        linkComponent={Link}
        imgURL={thumbnailUrl}
        imgFallbackURL={assetUrl(
          '/static/assets/images/dashboard-card-fallback.svg',
        )}
        description={t('Modified %s', dashboard.changed_on_delta_humanized)}
        coverLeft={<FacePile users={dashboard.owners || []} />}
        actions={
          <ListViewCard.Actions
            onClick={e => {
              e.stopPropagation();
              e.preventDefault();
            }}
          >
            {userId && (
              <FaveStar
                itemId={dashboard.id}
                saveFaveStar={saveFavoriteStatus}
                isStarred={favoriteStatus}
              />
            )}
            <Dropdown menu={{ items: menuItems }} trigger={['hover', 'click']}>
              <Button buttonSize="xsmall" buttonStyle="link">
                <Icons.MoreOutlined iconSize="xl" />
              </Button>
            </Dropdown>
          </ListViewCard.Actions>
        }
      />
    </StyledDashboardCard>
  );
}

export default DashboardCard;

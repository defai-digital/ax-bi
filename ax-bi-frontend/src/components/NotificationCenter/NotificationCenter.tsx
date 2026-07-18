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
import { useCallback, useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import rison from 'rison';
import { t } from '@ax-bi/core/translation';
import { css, styled } from '@ax-bi/core/theme';
import { AxBIClient, FeatureFlag, isFeatureEnabled } from '@ax-bi/ui-core';
import {
  Badge,
  Button,
  EmptyState,
  Icons,
  Popover,
  Skeleton,
  Tag,
} from '@ax-bi/ui-core/components';
import { extendedDayjs } from '@ax-bi/ui-core/utils/dates';
import AlertStatusIcon from 'src/features/alerts/components/AlertStatusIcon';
import { AlertState } from 'src/features/alerts/types';
import {
  countUnread,
  getNotificationUrl,
  NOTIFICATIONS_MAX_CONSECUTIVE_ERRORS,
  NOTIFICATIONS_PAGE_SIZE,
  NOTIFICATIONS_POLL_INTERVAL_MS,
  NOTIFICATIONS_VIEW_ALL_URL,
  NotificationItem,
  RawReportSchedule,
  readLastSeen,
  toNotificationItem,
  writeLastSeen,
} from './utils';

const PanelContainer = styled.div`
  ${({ theme }) => css`
    width: ${theme.sizeUnit * 90}px;
    max-width: 90vw;
  `}
`;

const PanelHeader = styled.div`
  ${({ theme }) => css`
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: ${theme.sizeUnit * 2}px ${theme.sizeUnit * 3}px;
    border-bottom: 1px solid ${theme.colorBorderSecondary};
    font-weight: ${theme.fontWeightStrong};
  `}
`;

const PanelBody = styled.div`
  ${({ theme }) => css`
    max-height: ${theme.sizeUnit * 100}px;
    overflow-y: auto;
  `}
`;

const ItemLink = styled(Link)<{ $isError: boolean }>`
  ${({ theme, $isError }) => css`
    display: flex;
    align-items: flex-start;
    gap: ${theme.sizeUnit * 2}px;
    padding: ${theme.sizeUnit * 2}px ${theme.sizeUnit * 3}px;
    border-bottom: 1px solid ${theme.colorBorderSecondary};
    ${$isError && `background-color: ${theme.colorErrorBg};`}

    &:hover {
      background-color: ${
        $isError ? theme.colorErrorBgHover : theme.colorFillQuaternary
      };
    }
  `}
`;

const ItemBody = styled.div`
  min-width: 0;
  flex: 1;
`;

const ItemName = styled.div<{ $isError: boolean }>`
  ${({ theme, $isError }) => css`
    color: ${$isError ? theme.colorErrorText : theme.colorText};
    font-weight: ${$isError ? theme.fontWeightStrong : theme.fontWeightNormal};
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  `}
`;

const ItemMeta = styled.div`
  ${({ theme }) => css`
    display: flex;
    align-items: center;
    gap: ${theme.sizeUnit}px;
    margin-top: ${theme.sizeUnit / 2}px;
    font-size: ${theme.fontSizeSM}px;
    color: ${theme.colorTextSecondary};
  `}
`;

const StatusIconWrapper = styled.span`
  ${({ theme }) => css`
    display: inline-flex;
    margin-top: ${theme.sizeUnit / 2}px;
  `}
`;

const PanelFooter = styled.div`
  ${({ theme }) => css`
    padding: ${theme.sizeUnit * 2}px ${theme.sizeUnit * 3}px;
    text-align: center;

    a {
      color: ${theme.colorPrimary};
      font-weight: ${theme.fontWeightStrong};
    }
  `}
`;

const SkeletonWrapper = styled.div`
  ${({ theme }) => css`
    padding: ${theme.sizeUnit * 3}px;
  `}
`;

const AlertStateLabel: Record<string, string> = {
  [AlertState.Success]: t('Success'),
  [AlertState.Working]: t('Working'),
  [AlertState.Error]: t('Error'),
  [AlertState.Noop]: t('Not triggered'),
  [AlertState.Grace]: t('On Grace'),
};

const fetchRecentExecutions = async (): Promise<NotificationItem[]> => {
  const queryParams = rison.encode_uri({
    order_column: 'last_eval_dttm',
    order_direction: 'desc',
    page: 0,
    page_size: NOTIFICATIONS_PAGE_SIZE,
  });
  const { json = {} } = await AxBIClient.get({
    endpoint: `/api/v1/report/?q=${queryParams}`,
  });
  const result: RawReportSchedule[] = Array.isArray(json.result)
    ? json.result
    : [];
  return result
    .map(toNotificationItem)
    .filter((item): item is NotificationItem => item !== null);
};

/**
 * Navbar notification center: a bell with an unread badge opening a panel of
 * recent alert/report execution results. Requires the NOTIFICATION_CENTER
 * feature flag; hides entirely unless ALERT_REPORTS is enabled, since the
 * execution data comes from the report schedule API.
 */
const NotificationCenter = () => {
  const enabled =
    isFeatureEnabled(FeatureFlag.NotificationCenter) &&
    isFeatureEnabled(FeatureFlag.AlertReports);

  const [open, setOpen] = useState(false);
  const [items, setItems] = useState<NotificationItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [failed, setFailed] = useState(false);
  // 401/403 means the user cannot read report schedules at all — hide the
  // bell entirely instead of offering a panel that can never load.
  const [unauthorized, setUnauthorized] = useState(false);
  const [lastSeen, setLastSeen] = useState(() =>
    readLastSeen(window.localStorage),
  );
  const openRef = useRef(open);
  openRef.current = open;

  const markAllSeen = useCallback(() => {
    const now = Date.now();
    writeLastSeen(window.localStorage, now);
    setLastSeen(now);
  }, []);

  // Fetches fail soft: the panel falls back to an empty/unavailable state
  // instead of surfacing toasts, since a 403/404 here is an RBAC or feature
  // configuration detail, not a user error.
  const fetchNotifications = useCallback(async () => {
    try {
      const next = await fetchRecentExecutions();
      setItems(next);
      setFailed(false);
      if (openRef.current) {
        // Anything rendered in the open panel counts as seen.
        markAllSeen();
      }
      return true;
    } catch (error) {
      const status = (error as Response | undefined)?.status;
      if (status === 401 || status === 403) {
        setUnauthorized(true);
      }
      setFailed(true);
      return false;
    } finally {
      setLoading(false);
    }
  }, [markAllSeen]);

  const active = enabled && !unauthorized;

  // Initial fetch so the badge reflects unread executions on page load.
  useEffect(() => {
    if (active) {
      fetchNotifications();
    }
  }, [active, fetchNotifications]);

  // Poll while the panel is open; stop after repeated failures.
  useEffect(() => {
    if (!active || !open) {
      return undefined;
    }
    let cancelled = false;
    let timer: number | undefined;
    let consecutiveErrors = 0;
    const tick = async () => {
      const ok = await fetchNotifications();
      if (cancelled) {
        return;
      }
      consecutiveErrors = ok ? 0 : consecutiveErrors + 1;
      if (consecutiveErrors < NOTIFICATIONS_MAX_CONSECUTIVE_ERRORS) {
        timer = window.setTimeout(tick, NOTIFICATIONS_POLL_INTERVAL_MS);
      }
    };
    timer = window.setTimeout(tick, NOTIFICATIONS_POLL_INTERVAL_MS);
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [active, open, fetchNotifications]);

  if (!active) {
    return null;
  }

  const unread = countUnread(items, lastSeen);

  const handleOpenChange = (nextOpen: boolean) => {
    setOpen(nextOpen);
    if (nextOpen) {
      // Opening the panel marks everything currently listed as seen.
      markAllSeen();
      fetchNotifications();
    }
  };

  const renderItem = (item: NotificationItem) => {
    const isError = item.state === AlertState.Error;
    return (
      <ItemLink
        key={`${item.type}-${item.id}`}
        to={getNotificationUrl(item)}
        $isError={isError}
        onClick={() => setOpen(false)}
        data-test="notification-item"
      >
        <StatusIconWrapper>
          <AlertStatusIcon
            state={item.state}
            isReportEnabled={item.type === 'Report'}
          />
        </StatusIconWrapper>
        <ItemBody>
          <ItemName $isError={isError}>{item.name}</ItemName>
          <ItemMeta>
            <Tag>{item.type === 'Report' ? t('Report') : t('Alert')}</Tag>
            <span>{AlertStateLabel[item.state] || item.state}</span>
            <span aria-hidden="true">·</span>
            <span>{extendedDayjs.utc(item.timestamp).local().fromNow()}</span>
          </ItemMeta>
        </ItemBody>
      </ItemLink>
    );
  };

  let body;
  if (loading && items.length === 0) {
    body = (
      <SkeletonWrapper>
        <Skeleton active title={false} paragraph={{ rows: 3 }} />
      </SkeletonWrapper>
    );
  } else if (failed && items.length === 0) {
    body = (
      <EmptyState
        size="small"
        title={t('Notifications unavailable')}
        description={t(
          'Alert and report execution results could not be loaded.',
        )}
      />
    );
  } else if (items.length === 0) {
    body = (
      <EmptyState
        size="small"
        title={t('No notifications')}
        description={t('Alert and report execution results will appear here.')}
      />
    );
  } else {
    body = items.map(renderItem);
  }

  const panel = (
    <PanelContainer>
      <PanelHeader>{t('Notifications')}</PanelHeader>
      <PanelBody>{body}</PanelBody>
      <PanelFooter>
        <Link to={NOTIFICATIONS_VIEW_ALL_URL} onClick={() => setOpen(false)}>
          {t('View all')}
        </Link>
      </PanelFooter>
    </PanelContainer>
  );

  return (
    <Popover
      content={panel}
      trigger="click"
      placement="bottomRight"
      arrow={false}
      open={open}
      onOpenChange={handleOpenChange}
    >
      <Button
        data-test="notification-center-trigger"
        aria-label={
          unread > 0
            ? t('Notifications (%s unread)', unread)
            : t('Notifications')
        }
        buttonStyle="link"
        icon={
          <Badge count={unread} size="small">
            <Icons.BellOutlined iconSize="l" />
          </Badge>
        }
      />
    </Popover>
  );
};

export default NotificationCenter;

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
import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from 'spec/helpers/testing-library';
import { AxBIClient, FeatureFlag } from '@ax-bi/ui-core';
import NotificationCenter from 'src/components/NotificationCenter';
import {
  NOTIFICATIONS_LAST_SEEN_KEY,
  RawReportSchedule,
} from 'src/components/NotificationCenter/utils';

const buildResponse = (items: RawReportSchedule[]) => ({
  json: { result: items, count: items.length },
});

const recentExecution = (
  overrides: Partial<RawReportSchedule> = {},
): RawReportSchedule => ({
  id: 1,
  name: 'Nightly sales report',
  type: 'Report',
  last_state: 'Success',
  last_eval_dttm: new Date(Date.now() - 60000).toISOString(),
  ...overrides,
});

let getSpy: jest.SpyInstance;

beforeEach(() => {
  window.localStorage.clear();
  window.featureFlags = {
    [FeatureFlag.NotificationCenter]: true,
    [FeatureFlag.AlertReports]: true,
  };
  getSpy = jest
    .spyOn(AxBIClient, 'get')
    .mockResolvedValue(buildResponse([]) as never);
});

afterEach(() => {
  getSpy.mockRestore();
  window.featureFlags = {};
});

test('renders the bell when NOTIFICATION_CENTER and ALERT_REPORTS are on', async () => {
  render(<NotificationCenter />, { useRouter: true, useTheme: true });
  expect(
    await screen.findByTestId('notification-center-trigger'),
  ).toBeInTheDocument();
});

test('renders nothing when NOTIFICATION_CENTER is off', () => {
  window.featureFlags = { [FeatureFlag.AlertReports]: true };
  render(<NotificationCenter />, { useRouter: true, useTheme: true });
  expect(
    screen.queryByTestId('notification-center-trigger'),
  ).not.toBeInTheDocument();
  expect(getSpy).not.toHaveBeenCalled();
});

test('renders nothing when ALERT_REPORTS is off', () => {
  window.featureFlags = { [FeatureFlag.NotificationCenter]: true };
  render(<NotificationCenter />, { useRouter: true, useTheme: true });
  expect(
    screen.queryByTestId('notification-center-trigger'),
  ).not.toBeInTheDocument();
  expect(getSpy).not.toHaveBeenCalled();
});

test('fetches recent executions on mount from the report schedule API', async () => {
  render(<NotificationCenter />, { useRouter: true, useTheme: true });
  await screen.findByTestId('notification-center-trigger');
  await waitFor(() => expect(getSpy).toHaveBeenCalledTimes(1));
  const endpoint = getSpy.mock.calls[0][0].endpoint as string;
  expect(endpoint).toContain('/api/v1/report/?q=');
  expect(decodeURIComponent(endpoint)).toContain('order_column:last_eval_dttm');
  expect(decodeURIComponent(endpoint)).toContain('page_size:20');
});

test('shows an unread badge for executions newer than last_seen', async () => {
  window.localStorage.setItem(
    NOTIFICATIONS_LAST_SEEN_KEY,
    String(Date.now() - 120000),
  );
  getSpy.mockResolvedValue(
    buildResponse([
      recentExecution({ id: 1, name: 'Fresh failure' }),
      recentExecution({
        id: 2,
        name: 'Old success',
        last_eval_dttm: new Date(Date.now() - 3600000).toISOString(),
      }),
    ]) as never,
  );
  render(<NotificationCenter />, { useRouter: true, useTheme: true });

  const trigger = await screen.findByTestId('notification-center-trigger');
  await waitFor(() =>
    expect(trigger).toHaveAttribute('aria-label', 'Notifications (1 unread)'),
  );
});

test('opening the panel marks executions seen and clears the badge', async () => {
  getSpy.mockResolvedValue(buildResponse([recentExecution()]) as never);
  render(<NotificationCenter />, { useRouter: true, useTheme: true });

  const trigger = await screen.findByTestId('notification-center-trigger');
  await waitFor(() =>
    expect(trigger).toHaveAttribute('aria-label', 'Notifications (1 unread)'),
  );

  fireEvent.click(trigger);

  expect(await screen.findByText('Nightly sales report')).toBeInTheDocument();
  expect(trigger).toHaveAttribute('aria-label', 'Notifications');
  const lastSeen = Number(
    window.localStorage.getItem(NOTIFICATIONS_LAST_SEEN_KEY),
  );
  expect(lastSeen).toBeGreaterThan(Date.now() - 60000);
});

test('lists executions with type, state, and deep links to the log page', async () => {
  getSpy.mockResolvedValue(
    buildResponse([
      recentExecution({
        id: 11,
        name: 'Broken alert',
        type: 'Alert',
        last_state: 'Error',
      }),
      recentExecution({ id: 12, name: 'Weekly report', type: 'Report' }),
    ]) as never,
  );
  render(<NotificationCenter />, { useRouter: true, useTheme: true });

  fireEvent.click(await screen.findByTestId('notification-center-trigger'));

  const alertLink = (await screen.findByText('Broken alert')).closest('a');
  expect(alertLink).toHaveAttribute('href', '/alert/11/log/');
  const reportLink = (await screen.findByText('Weekly report')).closest('a');
  expect(reportLink).toHaveAttribute('href', '/report/12/log/');
  expect(screen.getByText('Alert')).toBeInTheDocument();
  expect(screen.getByText('Error')).toBeInTheDocument();
  expect(screen.getByText('Success')).toBeInTheDocument();

  const viewAll = screen.getByText('View all').closest('a');
  expect(viewAll).toHaveAttribute('href', '/alert/list/');
});

test('drops schedules that never ran from the panel', async () => {
  getSpy.mockResolvedValue(
    buildResponse([
      recentExecution({ id: 21, name: 'Executed report' }),
      {
        id: 22,
        name: 'Never ran report',
        type: 'Report',
        last_state: 'Not triggered',
        last_eval_dttm: null,
      },
    ]) as never,
  );
  render(<NotificationCenter />, { useRouter: true, useTheme: true });

  fireEvent.click(await screen.findByTestId('notification-center-trigger'));

  expect(await screen.findByText('Executed report')).toBeInTheDocument();
  expect(screen.queryByText('Never ran report')).not.toBeInTheDocument();
});

test('shows an empty state when there are no executions', async () => {
  render(<NotificationCenter />, { useRouter: true, useTheme: true });

  fireEvent.click(await screen.findByTestId('notification-center-trigger'));

  expect(await screen.findByText('No notifications')).toBeInTheDocument();
});

test('fails soft to an unavailable state when the fetch errors', async () => {
  getSpy.mockRejectedValue(new Error('403 Forbidden') as never);
  render(<NotificationCenter />, { useRouter: true, useTheme: true });

  fireEvent.click(await screen.findByTestId('notification-center-trigger'));

  expect(
    await screen.findByText('Notifications unavailable'),
  ).toBeInTheDocument();
  // No unread badge on failure.
  expect(screen.getByTestId('notification-center-trigger')).toHaveAttribute(
    'aria-label',
    'Notifications',
  );
});

test.each([401, 403])(
  'hides the bell entirely when the API rejects with %i',
  async status => {
    // AxBIClient rejects failed requests with the raw Response object.
    getSpy.mockRejectedValue({ ok: false, status } as never);
    render(<NotificationCenter />, { useRouter: true, useTheme: true });

    await waitFor(() => expect(getSpy).toHaveBeenCalledTimes(1));
    await waitFor(() =>
      expect(
        screen.queryByTestId('notification-center-trigger'),
      ).not.toBeInTheDocument(),
    );
  },
);

test('polls every 60s while the panel is open and stops when closed', async () => {
  jest.useFakeTimers();
  try {
    render(<NotificationCenter />, { useRouter: true, useTheme: true });
    await act(async () => {});
    expect(getSpy).toHaveBeenCalledTimes(1);

    fireEvent.click(screen.getByTestId('notification-center-trigger'));
    await act(async () => {});
    expect(getSpy).toHaveBeenCalledTimes(2);

    await act(async () => {
      jest.advanceTimersByTime(60000);
    });
    expect(getSpy).toHaveBeenCalledTimes(3);

    await act(async () => {
      jest.advanceTimersByTime(60000);
    });
    expect(getSpy).toHaveBeenCalledTimes(4);

    fireEvent.click(screen.getByTestId('notification-center-trigger'));
    await act(async () => {
      jest.advanceTimersByTime(120000);
    });
    expect(getSpy).toHaveBeenCalledTimes(4);
  } finally {
    jest.useRealTimers();
  }
});

test('stops polling after consecutive errors', async () => {
  jest.useFakeTimers();
  try {
    getSpy.mockRejectedValue(new Error('boom') as never);
    render(<NotificationCenter />, { useRouter: true, useTheme: true });
    await act(async () => {});
    expect(getSpy).toHaveBeenCalledTimes(1);

    fireEvent.click(screen.getByTestId('notification-center-trigger'));
    await act(async () => {});
    expect(getSpy).toHaveBeenCalledTimes(2);

    // Three consecutive polling failures stop the interval.
    await act(async () => {
      jest.advanceTimersByTime(60000);
    });
    expect(getSpy).toHaveBeenCalledTimes(3);
    await act(async () => {
      jest.advanceTimersByTime(60000);
    });
    expect(getSpy).toHaveBeenCalledTimes(4);
    await act(async () => {
      jest.advanceTimersByTime(60000);
    });
    expect(getSpy).toHaveBeenCalledTimes(5);
    await act(async () => {
      jest.advanceTimersByTime(120000);
    });
    expect(getSpy).toHaveBeenCalledTimes(5);
  } finally {
    jest.useRealTimers();
  }
});

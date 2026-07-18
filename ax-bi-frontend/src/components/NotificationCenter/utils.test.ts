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
  countUnread,
  getNotificationUrl,
  NOTIFICATIONS_LAST_SEEN_KEY,
  NotificationItem,
  parseLastSeen,
  parseTimestamp,
  readLastSeen,
  toNotificationItem,
  writeLastSeen,
} from './utils';

test('parseTimestamp handles ISO strings, epoch numbers, and junk', () => {
  expect(parseTimestamp('2026-07-18T10:00:00Z')).toBe(
    Date.parse('2026-07-18T10:00:00Z'),
  );
  expect(parseTimestamp(1770000000000)).toBe(1770000000000);
  expect(parseTimestamp(null)).toBe(0);
  expect(parseTimestamp(undefined)).toBe(0);
  expect(parseTimestamp('not-a-date')).toBe(0);
  expect(parseTimestamp(Number.NaN)).toBe(0);
});

test('parseLastSeen reads numeric timestamps and rejects junk', () => {
  expect(parseLastSeen('1770000000000')).toBe(1770000000000);
  expect(parseLastSeen(null)).toBe(0);
  expect(parseLastSeen('')).toBe(0);
  expect(parseLastSeen('garbage')).toBe(0);
  expect(parseLastSeen('-5')).toBe(0);
});

test('readLastSeen/writeLastSeen roundtrip through storage', () => {
  const store = new Map<string, string>();
  const storage = {
    getItem: (key: string) => store.get(key) ?? null,
    setItem: (key: string, value: string) => {
      store.set(key, value);
    },
  } as Storage;

  expect(readLastSeen(storage)).toBe(0);
  writeLastSeen(storage, 1234567890);
  expect(store.get(NOTIFICATIONS_LAST_SEEN_KEY)).toBe('1234567890');
  expect(readLastSeen(storage)).toBe(1234567890);
});

test('readLastSeen/writeLastSeen tolerate throwing storage', () => {
  const throwingStorage = {
    getItem: () => {
      throw new Error('denied');
    },
    setItem: () => {
      throw new Error('denied');
    },
  } as unknown as Storage;

  expect(readLastSeen(throwingStorage)).toBe(0);
  expect(() => writeLastSeen(throwingStorage, 1)).not.toThrow();
});

test('toNotificationItem maps a raw schedule to a notification', () => {
  expect(
    toNotificationItem({
      id: 7,
      name: 'Daily sales',
      type: 'Report',
      last_state: 'Success',
      last_eval_dttm: '2026-07-18T10:00:00Z',
    }),
  ).toEqual({
    id: 7,
    name: 'Daily sales',
    type: 'Report',
    state: 'Success',
    timestamp: Date.parse('2026-07-18T10:00:00Z'),
  });
});

test('toNotificationItem defaults unknown types to Alert', () => {
  const item = toNotificationItem({
    id: 3,
    name: 'Watchdog',
    type: 'Alert',
    last_state: 'Error',
    last_eval_dttm: 1770000000000,
  });
  expect(item?.type).toBe('Alert');

  const missing = toNotificationItem({
    id: 4,
    last_eval_dttm: 1770000000000,
  });
  expect(missing?.type).toBe('Alert');
  expect(missing?.name).toBe('');
});

test('toNotificationItem drops schedules that never ran or lack an id', () => {
  expect(
    toNotificationItem({
      id: 1,
      name: 'Never ran',
      type: 'Report',
      last_state: 'Not triggered',
      last_eval_dttm: null,
    }),
  ).toBeNull();
  expect(toNotificationItem({ name: 'No id' })).toBeNull();
  expect(toNotificationItem({ id: 2, last_eval_dttm: 'garbage' })).toBeNull();
});

test('countUnread counts only items newer than last_seen', () => {
  const items: NotificationItem[] = [
    { id: 1, name: 'a', type: 'Alert', state: 'Success', timestamp: 300 },
    { id: 2, name: 'b', type: 'Report', state: 'Error', timestamp: 200 },
    { id: 3, name: 'c', type: 'Alert', state: 'Success', timestamp: 100 },
  ];
  expect(countUnread(items, 0)).toBe(3);
  expect(countUnread(items, 100)).toBe(2);
  expect(countUnread(items, 200)).toBe(1);
  expect(countUnread(items, 300)).toBe(0);
  expect(countUnread([], 0)).toBe(0);
});

test('getNotificationUrl deep-links to the execution log of the resource', () => {
  expect(
    getNotificationUrl({
      id: 5,
      name: 'x',
      type: 'Alert',
      state: 'Error',
      timestamp: 1,
    }),
  ).toBe('/alert/5/log/');
  expect(
    getNotificationUrl({
      id: 9,
      name: 'y',
      type: 'Report',
      state: 'Success',
      timestamp: 1,
    }),
  ).toBe('/report/9/log/');
});

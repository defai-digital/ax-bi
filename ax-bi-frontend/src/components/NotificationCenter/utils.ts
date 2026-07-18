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

/**
 * Pure helpers for the notification center. Kept free of React and network
 * concerns so they can be unit-tested in isolation.
 */

export const NOTIFICATIONS_LAST_SEEN_KEY = 'notifications__last_seen';
export const NOTIFICATIONS_PAGE_SIZE = 20;
export const NOTIFICATIONS_POLL_INTERVAL_MS = 60000;
export const NOTIFICATIONS_MAX_CONSECUTIVE_ERRORS = 3;
export const NOTIFICATIONS_VIEW_ALL_URL = '/alert/list/';

export interface NotificationItem {
  id: number;
  name: string;
  type: 'Alert' | 'Report';
  state: string;
  /** Last execution time in epoch milliseconds. */
  timestamp: number;
}

/** Shape of one entry in the `GET /api/v1/report/` list response. */
export interface RawReportSchedule {
  id?: number;
  name?: string;
  type?: string;
  last_state?: string;
  last_eval_dttm?: string | number | null;
}

export function parseTimestamp(value: string | number | null | undefined) {
  if (value === null || value === undefined) {
    return 0;
  }
  if (typeof value === 'number') {
    return Number.isFinite(value) ? value : 0;
  }
  const parsed = Date.parse(value);
  return Number.isNaN(parsed) ? 0 : parsed;
}

export function parseLastSeen(raw: string | null) {
  if (!raw) {
    return 0;
  }
  const parsed = Number(raw);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : 0;
}

export function readLastSeen(storage: Storage) {
  try {
    return parseLastSeen(storage.getItem(NOTIFICATIONS_LAST_SEEN_KEY));
  } catch {
    // Storage may be unavailable (e.g. private browsing); degrade to
    // "nothing seen" for the session instead of breaking the navbar.
    return 0;
  }
}

export function writeLastSeen(storage: Storage, timestamp: number) {
  try {
    storage.setItem(NOTIFICATIONS_LAST_SEEN_KEY, String(timestamp));
  } catch {
    // Best-effort persistence; unread tracking degrades to session-only.
  }
}

/**
 * Map a raw report schedule to a notification. Schedules that never ran have
 * no execution result to surface, so they are excluded (null return).
 */
export function toNotificationItem(
  raw: RawReportSchedule,
): NotificationItem | null {
  if (typeof raw?.id !== 'number') {
    return null;
  }
  const timestamp = parseTimestamp(raw.last_eval_dttm);
  if (timestamp === 0) {
    return null;
  }
  return {
    id: raw.id,
    name: raw.name || '',
    type: raw.type === 'Report' ? 'Report' : 'Alert',
    state: raw.last_state || '',
    timestamp,
  };
}

export function countUnread(items: NotificationItem[], lastSeen: number) {
  return items.filter(item => item.timestamp > lastSeen).length;
}

export function getNotificationUrl(item: NotificationItem) {
  return item.type === 'Report'
    ? `/report/${item.id}/log/`
    : `/alert/${item.id}/log/`;
}

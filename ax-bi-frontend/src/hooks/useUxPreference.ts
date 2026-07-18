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
import { useCallback, useEffect, useState } from 'react';
import { AxBIClient } from '@ax-bi/ui-core';
import {
  dangerouslyGetItemDoNotUse,
  dangerouslySetItemDoNotUse,
} from 'src/utils/localStorageHelpers';
import getBootstrapData from 'src/utils/getBootstrapData';

const UX_PREFERENCES_ENDPOINT = '/api/v1/me/preferences/';

export type UxPreferenceScalar = string | number | boolean | null;
type UxPreferenceMap = Record<string, UxPreferenceScalar>;

export interface UseUxPreferenceOptions<T> {
  /**
   * localStorage key used as the offline/anonymous fallback and as the
   * write-through migration source. Defaults to the server key itself.
   */
  localStorageKey?: string;
  /**
   * Interpret a legacy localStorage value (e.g. an object shape or a
   * mismatched scalar type) when the stored value is not already a JSON
   * scalar of the preference's type. Return undefined to ignore.
   */
  readLegacy?: (raw: unknown) => T | undefined;
}

type LoadState = 'idle' | 'loading' | 'ready' | 'failed';

// Module-level store: every hook instance shares one server document so the
// preferences endpoint is fetched at most once per page session. The store is
// anchored to the bootstrap user id so a user switch within the same page
// session (logout then a different login without a full reload) never leaks
// the previous user's preferences.
let cacheUserId: number | null | undefined;
let serverPreferences: UxPreferenceMap = {};
let loadState: LoadState = 'idle';
let inflight: Promise<void> | null = null;
const listeners = new Set<() => void>();

function currentUserId(): number | null {
  return getBootstrapData()?.user?.userId ?? null;
}

// Drop the cached server document when the bootstrap user changes.
function reanchorCacheToCurrentUser(): void {
  const userId = currentUserId();
  if (cacheUserId === undefined) {
    cacheUserId = userId;
    return;
  }
  if (cacheUserId !== userId) {
    serverPreferences = {};
    loadState = 'idle';
    inflight = null;
    cacheUserId = userId;
  }
}

function notify() {
  listeners.forEach(listener => listener());
}

async function fetchPreferences(): Promise<void> {
  try {
    const { json } = await AxBIClient.get({
      endpoint: UX_PREFERENCES_ENDPOINT,
    });
    serverPreferences =
      (json as { result?: UxPreferenceMap } | undefined)?.result ?? {};
    loadState = 'ready';
  } catch {
    // Anonymous users (401) and offline sessions fall back to localStorage.
    loadState = 'failed';
  } finally {
    inflight = null;
    notify();
  }
}

function ensurePreferencesLoaded(): void {
  if (loadState === 'ready' || loadState === 'failed') {
    return;
  }
  if (!inflight) {
    loadState = 'loading';
    inflight = fetchPreferences();
  }
}

function isScalar(value: unknown): value is UxPreferenceScalar {
  return (
    value === null ||
    typeof value === 'string' ||
    typeof value === 'number' ||
    typeof value === 'boolean'
  );
}

function persistPreferences(patch: UxPreferenceMap): void {
  AxBIClient.put({
    endpoint: UX_PREFERENCES_ENDPOINT,
    body: JSON.stringify(patch),
    headers: { 'Content-Type': 'application/json' },
  }).catch(() => {
    // The optimistic local update already landed in localStorage; a failed
    // write (offline, anonymous) simply leaves the server copy stale.
  });
}

/**
 * Reset the shared preference store. Intended for tests and logout flows.
 */
export function resetUxPreferencesCache(): void {
  serverPreferences = {};
  loadState = 'idle';
  inflight = null;
  cacheUserId = undefined;
}

/**
 * Read/write a single namespaced ``ux.*`` UX preference.
 *
 * The server document (GET/PUT /api/v1/me/preferences/) is the source of
 * truth; localStorage mirrors every write so anonymous or offline sessions
 * degrade gracefully to the pre-migration behavior. On first load with a
 * server document that lacks the key, a present localStorage value is
 * written through to the server.
 */
export function useUxPreference<T extends UxPreferenceScalar>(
  key: string,
  defaultValue: T,
  options: UseUxPreferenceOptions<T> = {},
): [T, (value: T) => void] {
  const { localStorageKey = key, readLegacy } = options;

  // Anchor the shared cache to the current user before any read below; the
  // userId also re-runs the effect (and a refetch) when it changes.
  reanchorCacheToCurrentUser();
  const userId = currentUserId();

  const readLocal = useCallback((): T | undefined => {
    const raw = dangerouslyGetItemDoNotUse(localStorageKey, undefined);
    if (raw === undefined) {
      return undefined;
    }
    if (isScalar(raw) && (raw === null || typeof raw === typeof defaultValue)) {
      return raw as T;
    }
    // Non-conforming stored value (legacy shape or another type): let the
    // caller's legacy interpreter decide before discarding it.
    return readLegacy?.(raw);
  }, [localStorageKey, defaultValue, readLegacy]);

  const [value, setValue] = useState<T>(() => {
    if (loadState === 'ready' && key in serverPreferences) {
      return serverPreferences[key] as T;
    }
    const local = readLocal();
    return local === undefined ? defaultValue : local;
  });

  useEffect(() => {
    reanchorCacheToCurrentUser();
    const listener = () => {
      if (loadState !== 'ready') {
        return;
      }
      if (key in serverPreferences) {
        // The server is authoritative; mirror it locally.
        const serverValue = serverPreferences[key] as T;
        setValue(serverValue);
        dangerouslySetItemDoNotUse(localStorageKey, serverValue);
        return;
      }
      // Write-through migration: server lacks the key but localStorage has
      // a value from before the migration — adopt it and persist.
      const local = readLocal();
      if (local !== undefined) {
        serverPreferences[key] = local;
        persistPreferences({ [key]: local });
      }
    };
    listeners.add(listener);
    ensurePreferencesLoaded();
    return () => {
      listeners.delete(listener);
    };
  }, [key, localStorageKey, readLocal, userId]);

  const set = useCallback(
    (next: T) => {
      setValue(next);
      serverPreferences[key] = next;
      dangerouslySetItemDoNotUse(localStorageKey, next);
      persistPreferences({ [key]: next });
      notify();
    },
    [key, localStorageKey],
  );

  return [value, set];
}

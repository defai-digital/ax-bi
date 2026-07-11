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
import { DataMaskStateWithId } from '@superset-ui/core';

export interface PersonalView {
  id: string;
  name: string;
  createdAt: number;
  /** Partial data mask keyed by native filter id */
  dataMask: DataMaskStateWithId;
}

export interface PersonalViewsStore {
  views: PersonalView[];
  defaultViewId?: string | null;
}

const MAX_VIEWS = 12;

export function personalViewsStorageKey(
  userId: string | number,
  dashboardId: string | number,
): string {
  return `dashboard__personal_views__${userId}__${dashboardId}`;
}

export function loadPersonalViewsStore(
  userId: string | number,
  dashboardId: string | number,
): PersonalViewsStore {
  try {
    const raw = localStorage.getItem(
      personalViewsStorageKey(userId, dashboardId),
    );
    if (!raw) {
      return { views: [] };
    }
    const parsed = JSON.parse(raw) as PersonalViewsStore;
    if (!parsed || !Array.isArray(parsed.views)) {
      return { views: [] };
    }
    return {
      views: parsed.views.slice(0, MAX_VIEWS),
      defaultViewId: parsed.defaultViewId ?? null,
    };
  } catch {
    return { views: [] };
  }
}

function persist(
  userId: string | number,
  dashboardId: string | number,
  store: PersonalViewsStore,
): void {
  localStorage.setItem(
    personalViewsStorageKey(userId, dashboardId),
    JSON.stringify(store),
  );
}

export function savePersonalView(
  userId: string | number,
  dashboardId: string | number,
  name: string,
  dataMask: DataMaskStateWithId,
  makeDefault = false,
): PersonalView {
  const store = loadPersonalViewsStore(userId, dashboardId);
  const view: PersonalView = {
    id: `pv_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
    name: name.trim() || 'My view',
    createdAt: Date.now(),
    dataMask: JSON.parse(JSON.stringify(dataMask)) as DataMaskStateWithId,
  };
  store.views = [view, ...store.views].slice(0, MAX_VIEWS);
  if (makeDefault) {
    store.defaultViewId = view.id;
  }
  persist(userId, dashboardId, store);
  return view;
}

export function deletePersonalView(
  userId: string | number,
  dashboardId: string | number,
  viewId: string,
): PersonalViewsStore {
  const store = loadPersonalViewsStore(userId, dashboardId);
  store.views = store.views.filter(v => v.id !== viewId);
  if (store.defaultViewId === viewId) {
    store.defaultViewId = null;
  }
  persist(userId, dashboardId, store);
  return store;
}

export function setDefaultPersonalView(
  userId: string | number,
  dashboardId: string | number,
  viewId: string | null,
): void {
  const store = loadPersonalViewsStore(userId, dashboardId);
  store.defaultViewId = viewId;
  persist(userId, dashboardId, store);
}

/**
 * Return only data-mask entries that still exist in the live filter set.
 */
export function filterDataMaskToKnownIds(
  dataMask: DataMaskStateWithId,
  knownFilterIds: Set<string>,
): DataMaskStateWithId {
  const next: DataMaskStateWithId = {};
  Object.entries(dataMask).forEach(([id, mask]) => {
    if (knownFilterIds.has(String(id))) {
      next[id] = mask;
    }
  });
  return next;
}

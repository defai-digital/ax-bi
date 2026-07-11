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
  deletePersonalView,
  filterDataMaskToKnownIds,
  loadPersonalViewsStore,
  personalViewsStorageKey,
  savePersonalView,
} from './personalViews';

beforeEach(() => {
  localStorage.clear();
});

test('save and load personal views', () => {
  const mask = {
    f1: { id: 'f1', filterState: { value: ['a'] } },
  } as any;
  const view = savePersonalView(1, 42, 'West region', mask);
  expect(view.name).toBe('West region');
  const store = loadPersonalViewsStore(1, 42);
  expect(store.views).toHaveLength(1);
  expect(store.views[0].dataMask.f1.filterState?.value).toEqual(['a']);
});

test('delete personal view', () => {
  const mask = { f1: { id: 'f1' } } as any;
  const view = savePersonalView(1, 42, 'Tmp', mask);
  deletePersonalView(1, 42, view.id);
  expect(loadPersonalViewsStore(1, 42).views).toHaveLength(0);
});

test('filterDataMaskToKnownIds drops unknown filters', () => {
  const mask = {
    keep: { id: 'keep' },
    gone: { id: 'gone' },
  } as any;
  const filtered = filterDataMaskToKnownIds(mask, new Set(['keep']));
  expect(Object.keys(filtered)).toEqual(['keep']);
});

test('storage key is namespaced', () => {
  expect(personalViewsStorageKey(3, 9)).toBe(
    'dashboard__personal_views__3__9',
  );
});

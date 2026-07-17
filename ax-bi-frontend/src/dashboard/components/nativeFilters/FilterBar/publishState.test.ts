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
  isSamePublishedFilterState,
  PublishedFilterState,
} from './publishState';

const published: PublishedFilterState = {
  dashboardId: 7,
  tabId: 'tab-1',
  cacheKey: 'filter-key',
  value: '{"filter":[]}',
};

test('identifies an unchanged published dashboard filter state', () => {
  expect(
    isSamePublishedFilterState(
      published,
      7,
      'tab-1',
      'filter-key',
      '{"filter":[]}',
    ),
  ).toBe(true);
});

test.each([
  [8, 'tab-1', 'filter-key', '{"filter":[]}'],
  [7, 'tab-2', 'filter-key', '{"filter":[]}'],
  [7, 'tab-1', 'other-key', '{"filter":[]}'],
  [7, 'tab-1', 'filter-key', '{"filter":[1]}'],
  [7, 'tab-1', null, '{"filter":[]}'],
])(
  'publishes when dashboard, tab, key, or payload changes',
  (dashboardId, tabId, cacheKey, value) => {
    expect(
      isSamePublishedFilterState(
        published,
        dashboardId as number,
        tabId as string,
        cacheKey as string | null,
        value as string,
      ),
    ).toBe(false);
  },
);

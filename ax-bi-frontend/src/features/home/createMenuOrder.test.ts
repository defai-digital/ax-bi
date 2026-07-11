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
import { orderCreateMenuItems } from './createMenuOrder';

test('orderCreateMenuItems puts consumer items before SQL when simplified', () => {
  const ordered = orderCreateMenuItems(
    {
      chart: 'chart',
      dashboard: 'dashboard',
      upload: 'upload',
      sql: 'sql',
    },
    true,
  );
  expect(ordered).toEqual(['chart', 'dashboard', 'upload', 'sql']);
});

test('orderCreateMenuItems omits upload when not provided under simplified', () => {
  const ordered = orderCreateMenuItems(
    {
      chart: 'chart',
      dashboard: 'dashboard',
      upload: null,
      sql: 'sql',
    },
    true,
  );
  expect(ordered).toEqual(['chart', 'dashboard', 'sql']);
  expect(ordered).not.toContain('upload');
});

test('orderCreateMenuItems leads with SQL when not simplified', () => {
  const ordered = orderCreateMenuItems(
    {
      chart: 'chart',
      dashboard: 'dashboard',
      upload: 'upload',
      sql: 'sql',
    },
    false,
  );
  expect(ordered).toEqual(['sql', 'chart', 'dashboard', 'upload']);
});

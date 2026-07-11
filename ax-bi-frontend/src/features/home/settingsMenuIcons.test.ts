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
import { resolveSettingsMenuIconKey } from './settingsMenuIcons';

test('resolveSettingsMenuIconKey maps stable FAB names', () => {
  expect(resolveSettingsMenuIconKey({ name: 'Databases' })).toBe(
    'DatabaseOutlined',
  );
  expect(resolveSettingsMenuIconKey({ name: 'List Roles' })).toBe(
    'SafetyCertificateOutlined',
  );
  expect(resolveSettingsMenuIconKey({ name: 'Themes' })).toBe(
    'BgColorsOutlined',
  );
  expect(resolveSettingsMenuIconKey({ name: 'SQL Lab' })).toBe(
    'ConsoleSqlOutlined',
  );
  expect(resolveSettingsMenuIconKey({ name: 'Row Level Security' })).toBe(
    'LockOutlined',
  );
});

test('resolveSettingsMenuIconKey falls back to url/label keywords', () => {
  expect(
    resolveSettingsMenuIconKey({
      label: 'Connexions',
      url: '/databaseview/list/',
    }),
  ).toBe('DatabaseOutlined');
  expect(
    resolveSettingsMenuIconKey({
      label: 'Historas',
      url: '/theme/list/',
    }),
  ).toBe('BgColorsOutlined');
  expect(resolveSettingsMenuIconKey({ label: 'Logout' })).toBe(
    'LogoutOutlined',
  );
});

test('resolveSettingsMenuIconKey returns undefined for unknown items', () => {
  expect(resolveSettingsMenuIconKey({})).toBeUndefined();
  expect(
    resolveSettingsMenuIconKey({ name: 'UnknownThing', label: 'zzz' }),
  ).toBeUndefined();
});

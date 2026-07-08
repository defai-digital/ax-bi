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
import { ThemeMode } from '@apache-superset/core/theme';
import type { ThemeController } from './ThemeController';
import {
  DESKTOP_THEME_MESSAGE_SOURCE,
  THEME_SET_MESSAGE_TYPE,
  desktopThemeModeToThemeMode,
  installDesktopThemeBridge,
  isAllowedDesktopThemeOrigin,
  parseDesktopThemeMode,
  resolvedThemeModeToDesktopThemeMode,
  themeModeToDesktopThemeMode,
} from './desktopThemeBridge';

function createThemeControllerMock(): jest.Mocked<ThemeController> {
  return {
    getCurrentMode: jest.fn().mockReturnValue(ThemeMode.DEFAULT),
    getCurrentModeResolved: jest.fn().mockReturnValue('light'),
    onChange: jest.fn().mockReturnValue(jest.fn()),
    setThemeMode: jest.fn(),
  } as unknown as jest.Mocked<ThemeController>;
}

test('desktop theme bridge maps desktop modes to ThemeMode values', () => {
  expect(desktopThemeModeToThemeMode('default')).toBe(ThemeMode.DEFAULT);
  expect(desktopThemeModeToThemeMode('dark')).toBe(ThemeMode.DARK);
  expect(desktopThemeModeToThemeMode('system')).toBe(ThemeMode.SYSTEM);
});

test('desktop theme bridge maps ThemeMode values to desktop modes', () => {
  expect(themeModeToDesktopThemeMode(ThemeMode.DEFAULT)).toBe('default');
  expect(themeModeToDesktopThemeMode(ThemeMode.DARK)).toBe('dark');
  expect(themeModeToDesktopThemeMode(ThemeMode.SYSTEM)).toBe('system');
  expect(resolvedThemeModeToDesktopThemeMode('light')).toBe('default');
  expect(resolvedThemeModeToDesktopThemeMode('dark')).toBe('dark');
});

test('desktop theme bridge validates desktop origins', () => {
  expect(isAllowedDesktopThemeOrigin('http://localhost:1430')).toBe(true);
  expect(isAllowedDesktopThemeOrigin('http://127.0.0.1:1430')).toBe(true);
  expect(isAllowedDesktopThemeOrigin('tauri://localhost')).toBe(true);
  expect(isAllowedDesktopThemeOrigin('https://example.com')).toBe(false);
});

test('desktop theme bridge parses valid theme messages', () => {
  expect(
    parseDesktopThemeMode({
      source: DESKTOP_THEME_MESSAGE_SOURCE,
      type: THEME_SET_MESSAGE_TYPE,
      mode: 'dark',
    }),
  ).toBe('dark');
  expect(
    parseDesktopThemeMode({
      source: DESKTOP_THEME_MESSAGE_SOURCE,
      type: THEME_SET_MESSAGE_TYPE,
      mode: 'unknown',
    }),
  ).toBeNull();
});

test('desktop theme bridge applies valid desktop messages', () => {
  const themeController = createThemeControllerMock();
  const cleanup = installDesktopThemeBridge(themeController);

  window.dispatchEvent(
    new MessageEvent('message', {
      origin: 'http://localhost:1430',
      data: {
        source: DESKTOP_THEME_MESSAGE_SOURCE,
        type: THEME_SET_MESSAGE_TYPE,
        mode: 'dark',
      },
    }),
  );

  expect(themeController.setThemeMode).toHaveBeenCalledWith(ThemeMode.DARK);

  cleanup();
});

test('desktop theme bridge ignores unexpected origins', () => {
  const themeController = createThemeControllerMock();
  const cleanup = installDesktopThemeBridge(themeController);

  window.dispatchEvent(
    new MessageEvent('message', {
      origin: 'https://example.com',
      data: {
        source: DESKTOP_THEME_MESSAGE_SOURCE,
        type: THEME_SET_MESSAGE_TYPE,
        mode: 'dark',
      },
    }),
  );

  expect(themeController.setThemeMode).not.toHaveBeenCalled();

  cleanup();
});

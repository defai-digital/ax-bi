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
  DEFAULT_ECHARTS_THEME_ID,
  ECHARTS_THEME_OPTIONS,
  getEchartsInitThemeName,
  getEchartsThemeColorSchemeConfigs,
  getEchartsThemeColorSchemeId,
  getEchartsThemeOption,
  normalizeEchartsThemeId,
  shouldUseNamedEchartsTheme,
} from './echartsThemeRegistry';

test('default theme is AX BI and has no ECharts init name', () => {
  expect(normalizeEchartsThemeId(undefined)).toBe(DEFAULT_ECHARTS_THEME_ID);
  expect(normalizeEchartsThemeId(null)).toBe(DEFAULT_ECHARTS_THEME_ID);
  expect(normalizeEchartsThemeId('not-a-theme')).toBe(DEFAULT_ECHARTS_THEME_ID);
  expect(getEchartsInitThemeName('default')).toBeNull();
  expect(shouldUseNamedEchartsTheme('default')).toBe(false);
  expect(getEchartsThemeColorSchemeId('default')).toBeUndefined();
});

test('screenshot templates are registered with palettes', () => {
  const ids = ECHARTS_THEME_OPTIONS.map(o => o.id);
  expect(ids).toEqual([
    'default',
    'vintage',
    'dark',
    'macarons',
    'infographic',
    'shine',
    'roma',
  ]);

  ['vintage', 'dark', 'macarons', 'infographic', 'shine', 'roma'].forEach(
    id => {
      expect(getEchartsInitThemeName(id)).toBe(id);
      expect(shouldUseNamedEchartsTheme(id)).toBe(true);
      const option = getEchartsThemeOption(id);
      expect(option.colors.length).toBeGreaterThan(0);
      expect(getEchartsThemeColorSchemeId(id)).toBe(`echartsTheme_${id}`);
    },
  );
});

test('color scheme configs cover non-default templates', () => {
  const configs = getEchartsThemeColorSchemeConfigs();
  expect(configs).toHaveLength(6);
  expect(configs.map(c => c.id)).toEqual([
    'echartsTheme_vintage',
    'echartsTheme_dark',
    'echartsTheme_macarons',
    'echartsTheme_infographic',
    'echartsTheme_shine',
    'echartsTheme_roma',
  ]);
  configs.forEach(config => {
    expect(config.colors[0]).toMatch(/^#/);
  });
});

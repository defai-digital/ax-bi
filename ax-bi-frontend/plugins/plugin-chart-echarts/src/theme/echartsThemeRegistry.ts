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
import { registerTheme } from 'echarts/core';
import darkTheme from './echartsTemplates/dark.json';
import infographicTheme from './echartsTemplates/infographic.json';
import macaronsTheme from './echartsTemplates/macarons.json';
import romaTheme from './echartsTemplates/roma.json';
import shineTheme from './echartsTemplates/shine.json';
import vintageTheme from './echartsTemplates/vintage.json';

/**
 * AX BI default chart style: token-driven Japandi look (not an ECharts named theme).
 * Stored as null / "default" in dashboard metadata.
 */
export const DEFAULT_ECHARTS_THEME_ID = 'default';

export type EchartsThemeId =
  | typeof DEFAULT_ECHARTS_THEME_ID
  | 'vintage'
  | 'dark'
  | 'macarons'
  | 'infographic'
  | 'shine'
  | 'roma';

export type EchartsThemeOption = {
  id: EchartsThemeId;
  /** Display label for UI selects */
  label: string;
  /** Official ECharts registerTheme name; null means init(dom, null) */
  echartsName: string | null;
  /** Series palette used when dashboard color scheme is unset */
  colors: string[];
  /** Categorical scheme id registered for color-scheme fallback */
  colorSchemeId: string | null;
};

const themeJsonByName: Record<string, Record<string, unknown>> = {
  vintage: vintageTheme as Record<string, unknown>,
  dark: darkTheme as Record<string, unknown>,
  macarons: macaronsTheme as Record<string, unknown>,
  infographic: infographicTheme as Record<string, unknown>,
  shine: shineTheme as Record<string, unknown>,
  roma: romaTheme as Record<string, unknown>,
};

function colorsFromTheme(theme: Record<string, unknown>): string[] {
  const color = theme.color;
  return Array.isArray(color) ? (color as string[]) : [];
}

/**
 * Dashboard chart-style templates (ECharts download-theme set + AX BI default).
 * Keep in sync with the official ECharts theme gallery subset chosen for v1.
 */
export const ECHARTS_THEME_OPTIONS: EchartsThemeOption[] = [
  {
    id: DEFAULT_ECHARTS_THEME_ID,
    label: 'Default (AX BI)',
    echartsName: null,
    colors: [],
    colorSchemeId: null,
  },
  {
    id: 'vintage',
    label: 'Vintage',
    echartsName: 'vintage',
    colors: colorsFromTheme(themeJsonByName.vintage),
    colorSchemeId: 'echartsTheme_vintage',
  },
  {
    id: 'dark',
    label: 'Dark',
    echartsName: 'dark',
    colors: colorsFromTheme(themeJsonByName.dark),
    colorSchemeId: 'echartsTheme_dark',
  },
  {
    id: 'macarons',
    label: 'Macarons',
    echartsName: 'macarons',
    colors: colorsFromTheme(themeJsonByName.macarons),
    colorSchemeId: 'echartsTheme_macarons',
  },
  {
    id: 'infographic',
    label: 'Infographic',
    echartsName: 'infographic',
    colors: colorsFromTheme(themeJsonByName.infographic),
    colorSchemeId: 'echartsTheme_infographic',
  },
  {
    id: 'shine',
    label: 'Shine',
    echartsName: 'shine',
    colors: colorsFromTheme(themeJsonByName.shine),
    colorSchemeId: 'echartsTheme_shine',
  },
  {
    id: 'roma',
    label: 'Roma',
    echartsName: 'roma',
    colors: colorsFromTheme(themeJsonByName.roma),
    colorSchemeId: 'echartsTheme_roma',
  },
];

const optionById = Object.fromEntries(
  ECHARTS_THEME_OPTIONS.map(opt => [opt.id, opt]),
) as Record<EchartsThemeId, EchartsThemeOption>;

let themesRegistered = false;

/**
 * Register official ECharts theme objects once. Safe to call repeatedly.
 */
export function ensureEchartsThemesRegistered(): void {
  if (themesRegistered) {
    return;
  }
  Object.entries(themeJsonByName).forEach(([name, theme]) => {
    registerTheme(name, theme);
  });
  themesRegistered = true;
}

export function isEchartsThemeId(value: unknown): value is EchartsThemeId {
  return typeof value === 'string' && value in optionById;
}

export function normalizeEchartsThemeId(
  value: unknown,
): EchartsThemeId {
  if (isEchartsThemeId(value)) {
    return value;
  }
  return DEFAULT_ECHARTS_THEME_ID;
}

export function getEchartsThemeOption(
  id: unknown,
): EchartsThemeOption {
  return optionById[normalizeEchartsThemeId(id)];
}

/**
 * Resolve the ECharts init theme name. Returns null for AX BI default.
 */
export function getEchartsInitThemeName(id: unknown): string | null {
  return getEchartsThemeOption(id).echartsName;
}

/**
 * Color-scheme id for a template when the dashboard has no explicit color scheme.
 */
export function getEchartsThemeColorSchemeId(
  id: unknown,
): string | undefined {
  return getEchartsThemeOption(id).colorSchemeId ?? undefined;
}

/**
 * Whether this selection should skip Ant Design token chrome overrides so the
 * named ECharts theme can control axes, legend, tooltip, background, etc.
 */
export function shouldUseNamedEchartsTheme(id: unknown): boolean {
  return getEchartsInitThemeName(id) != null;
}

/**
 * Categorical scheme configs for setupColors registration.
 */
export function getEchartsThemeColorSchemeConfigs(): {
  id: string;
  label: string;
  colors: string[];
}[] {
  return ECHARTS_THEME_OPTIONS.filter(
    (opt): opt is EchartsThemeOption & { colorSchemeId: string } =>
      Boolean(opt.colorSchemeId && opt.colors.length),
  ).map(opt => ({
    id: opt.colorSchemeId,
    label: `ECharts ${opt.label}`,
    colors: opt.colors,
  }));
}
